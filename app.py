"""
Asisten Penutupan Buku — Entry point
Semua halaman UI ada di file ini.
"""
import pandas as pd
import streamlit as st

from core import (
    DEMO_TB,
    CHECKLIST_ITEMS,
    init_state,
    reset_state,
    get_adjusted_tb,
    build_closing_entries,
    build_excel,
)

st.set_page_config(
    page_title="Asisten Penutupan Buku",
    page_icon="📚",
    layout="wide",
)

init_state()

# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.title("📚 Asisten Tutup Buku")
    st.caption("Month-end / Year-end Closing Assistant")
    st.markdown("---")

    st.session_state.period = st.date_input(
        "Periode Penutupan",
        value=st.session_state.period,
        help="Pilih tanggal akhir periode yang akan ditutup",
    )

    st.markdown("---")
    menu = st.radio("Navigasi", [
        "🏠 Dashboard",
        "📤 Data & Upload",
        "✅ Checklist",
        "📝 Jurnal Penyesuaian",
        "🏦 Rekonsiliasi Bank",
        "📊 TB Setelah Penyesuaian",
        "🔒 Tutup Buku",
        "📥 Export",
    ], label_visibility="collapsed")

    st.markdown("---")
    st.caption(f"Periode aktif: **{st.session_state.period.strftime('%B %Y')}**")
    if st.button("🔄 Reset Semua Data", use_container_width=True):
        reset_state()
        st.rerun()

# ============================================================
# PAGE: Dashboard
# ============================================================
if menu == "🏠 Dashboard":
    st.title("🏠 Dashboard Penutupan Buku")
    st.caption(f"Periode: {st.session_state.period.strftime('%B %Y')}")

    adj = get_adjusted_tb()
    done = sum(1 for key, *_ in CHECKLIST_ITEMS if st.session_state.checklist.get(key))
    total = len(CHECKLIST_ITEMS)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Checklist", f"{done}/{total}", f"{done / total * 100:.0f}%")
    c2.metric("Jurnal Penyesuaian", len(st.session_state.adjustments))

    if adj is not None:
        c3.metric("Total Debit", f"Rp {adj['Debit Akhir'].sum():,.0f}")
        c4.metric("Total Kredit", f"Rp {adj['Kredit Akhir'].sum():,.0f}")

        selisih = adj["Debit Akhir"].sum() - adj["Kredit Akhir"].sum()
        if abs(selisih) < 1:
            st.success(f"✅ Neraca saldo seimbang (selisih Rp {selisih:,.2f})")
        else:
            st.error(f"⚠️ Neraca saldo TIDAK seimbang. Selisih: Rp {selisih:,.2f}")

        _, laba = build_closing_entries(adj)
        st.info(f"📈 Laba/Rugi periode berjalan: **Rp {laba:,.2f}**")

        with st.expander("📊 Ringkasan per Tipe Akun"):
            ring = adj.groupby("Tipe").agg(
                Debit=("Debit Akhir", "sum"),
                Kredit=("Kredit Akhir", "sum"),
            )
            ring["Saldo"] = ring["Debit"] - ring["Kredit"]
            st.dataframe(ring.style.format("Rp {:,.0f}"), use_container_width=True)
    else:
        c3.metric("Total Debit", "-")
        c4.metric("Total Kredit", "-")
        st.warning("Silakan upload trial balance di menu **Data & Upload**.")

    st.markdown("---")
    st.subheader("🚀 Alur Closing yang Disarankan")
    st.markdown(
        "1. **📤 Data & Upload** — upload TB Anda\n"
        "2. **✅ Checklist** — pastikan semua prosedur closing sudah dilakukan\n"
        "3. **📝 Jurnal Penyesuaian** — catat penyesuaian (penyusutan, akrual, dll.)\n"
        "4. **🏦 Rekonsiliasi Bank** — cocokkan saldo kas\n"
        "5. **📊 TB Setelah Penyesuaian** — verifikasi debit = kredit\n"
        "6. **🔒 Tutup Buku** — generate jurnal penutup otomatis\n"
        "7. **📥 Export** — unduh Excel berisi semua sheet"
    )

# ============================================================
# PAGE: Data & Upload
# ============================================================
elif menu == "📤 Data & Upload":
    st.title("📤 Data & Upload Trial Balance")
    st.write("Format kolom wajib: **Kode, Nama Akun, Tipe, Debit, Kredit**")
    st.caption("Tipe yang valid: Aset, Kewajiban, Ekuitas, Pendapatan, Beban")

    # Tombol download template
    template = DEMO_TB.head(0).to_csv(index=False).encode()
    st.download_button("⬇️ Unduh Template CSV", template, "template_tb.csv", "text/csv")
    
    st.markdown("---")

    # File uploader (Full width)
    uploaded = st.file_uploader("Upload file Trial Balance (CSV/Excel):", type=["xlsx", "csv"])
    
    if uploaded:
        try:
            # Membaca file (otomatis mendeteksi koma atau titik koma)
            if uploaded.name.endswith(".csv"):
                df = pd.read_csv(uploaded, sep=None, engine='python')
            else:
                df = pd.read_excel(uploaded)
            
            if df.empty:
                st.warning("⚠️ File yang diupload kosong. Pastikan ada baris data di bawah judul kolom.")
            else:
                need = {"Kode", "Nama Akun", "Tipe", "Debit", "Kredit"}
                if not need.issubset(df.columns):
                    st.error(f"Kolom tidak lengkap. Wajib ada: {need}. Ditemukan: {list(df.columns)}")
                else:
                    # Tampilkan Preview
                    st.write("### Preview Data (Belum Diproses)")
                    st.dataframe(df, use_container_width=True)
                    
                    # TOMBOL PROSES DATA
                    if st.button("✅ Proses Data Trial Balance", type="primary"):
                        st.session_state.tb = df
                        st.success("✅ Data Trial Balance berhasil diproses!")
                        st.rerun()
        except Exception as exc:
            st.error(f"Gagal membaca file: {exc}")

    # Tampilkan data yang sedang aktif (jika sudah diproses)
    if st.session_state.tb is not None:
        st.markdown("---")
        st.subheader("📌 Data Trial Balance Aktif")
        st.dataframe(st.session_state.tb, use_container_width=True)

        tb = st.session_state.tb
        d = pd.to_numeric(tb["Debit"], errors="coerce").fillna(0).sum()
        k = pd.to_numeric(tb["Kredit"], errors="coerce").fillna(0).sum()
        st.write(f"Total Debit: **Rp {d:,.0f}** | Total Kredit: **Rp {k:,.0f}** | "
                 f"Selisih: **Rp {d - k:,.0f}**")

        if st.button("🗑️ Hapus Data Aktif"):
            st.session_state.tb = None
            st.rerun()

# ============================================================
# PAGE: Checklist
# ============================================================
elif menu == "✅ Checklist":
    st.title("✅ Checklist Penutupan Buku")
    st.caption("Centang item yang sudah diselesaikan sebelum menutup buku.")

    for key, title, desc in CHECKLIST_ITEMS:
        skey = f"chk_{key}"
        if skey not in st.session_state:
            st.session_state[skey] = st.session_state.checklist.get(key, False)
        val = st.checkbox(f"**{title}** — {desc}", key=skey)
        st.session_state.checklist[key] = val

    done = sum(1 for v in st.session_state.checklist.values() if v)
    st.progress(done / len(CHECKLIST_ITEMS))
    st.caption(f"{done} dari {len(CHECKLIST_ITEMS)} item selesai")

    if st.button("🔄 Reset Checklist"):
        st.session_state.checklist = {}
        for key, *_ in CHECKLIST_ITEMS:
            st.session_state.pop(f"chk_{key}", None)
        st.rerun()

# ============================================================
# PAGE: Jurnal Penyesuaian
# ============================================================
elif menu == "📝 Jurnal Penyesuaian":
    st.title("📝 Jurnal Penyesuaian")
    adj_tb = get_adjusted_tb()

    if adj_tb is None:
        st.warning("Upload trial balance dulu di menu **Data & Upload**.")
    else:
        accounts = adj_tb[["Kode", "Nama Akun"]].dropna().values.tolist()
        options = [f"{k} - {n}" for k, n in accounts]

        with st.form("form_adj", clear_on_submit=True):
            c1, c2, c3 = st.columns([2, 1, 1])
            acc = c1.selectbox("Akun", options)
            tgl = c2.date_input("Tanggal", value=st.session_state.period)
            ket = c3.text_input("Keterangan", placeholder="cth: Penyusutan bulan ini")

            c4, c5 = st.columns(2)
            deb = c4.number_input("Debit", min_value=0.0, step=1000.0, format="%.2f")
            kre = c5.number_input("Kredit", min_value=0.0, step=1000.0, format="%.2f")
            submit = st.form_submit_button("➕ Tambah Baris Jurnal")

            if submit:
                if deb == 0 and kre == 0:
                    st.error("Isi salah satu Debit atau Kredit.")
                elif deb > 0 and kre > 0:
                    st.error("Isi hanya salah satu (Debit ATAU Kredit).")
                else:
                    kode, nama = acc.split(" - ", 1)
                    st.session_state.adjustments.append({
                        "Tanggal": str(tgl), "Keterangan": ket,
                        "Kode": kode, "Nama Akun": nama,
                        "Debit": deb, "Kredit": kre,
                    })
                    st.rerun()

        if st.session_state.adjustments:
            df = pd.DataFrame(st.session_state.adjustments)
            st.subheader("Daftar Jurnal Penyesuaian")
            st.dataframe(df, use_container_width=True)
            d, k = df["Debit"].sum(), df["Kredit"].sum()
            st.write(f"Total Debit: **Rp {d:,.0f}** | Total Kredit: **Rp {k:,.0f}** | "
                     f"Selisih: **Rp {d - k:,.0f}**")
            if st.button("🗑️ Hapus semua jurnal"):
                st.session_state.adjustments = []
                st.rerun()
        else:
            st.info("Belum ada jurnal penyesuaian.")

# ============================================================
# PAGE: Rekonsiliasi Bank
# ============================================================
elif menu == "🏦 Rekonsiliasi Bank":
    st.title("🏦 Rekonsiliasi Bank")

    with st.form("bank_form"):
        st.subheader("Sisi Bank")
        bank_bal = st.number_input("Saldo menurut rekening koran", value=0.0, step=1000.0)
        dep_transit = st.number_input("Setoran dalam perjalanan (+)", value=0.0, step=1000.0)
        out_check = st.number_input("Cek beredar (−)", value=0.0, step=1000.0)

        st.subheader("Sisi Buku")
        book_bal = st.number_input("Saldo menurut buku kas", value=0.0, step=1000.0)
        jasa_giro = st.number_input("Jasa giro / bunga bank (+)", value=0.0, step=1000.0)
        biaya_bank = st.number_input("Biaya administrasi bank (−)", value=0.0, step=1000.0)

        if st.form_submit_button("Hitung Rekonsiliasi"):
            adj_bank = bank_bal + dep_transit - out_check
            adj_book = book_bal + jasa_giro - biaya_bank
            st.session_state.bank = {
                "Saldo Bank": bank_bal,
                "Setoran Dalam Perjalanan": dep_transit,
                "Cek Beredar": out_check,
                "Saldo Bank Disesuaikan": adj_bank,
                "Saldo Buku": book_bal,
                "Jasa Giro": jasa_giro,
                "Biaya Bank": biaya_bank,
                "Saldo Buku Disesuaikan": adj_book,
                "Selisih": adj_bank - adj_book,
            }

    if st.session_state.bank:
        b = st.session_state.bank
        st.subheader("Hasil Rekonsiliasi")
        st.dataframe(pd.DataFrame(b.items(), columns=["Item", "Nilai"]),
                     use_container_width=True)
        if abs(b["Selisih"]) < 1:
            st.success("✅ Rekonsiliasi cocok — saldo bank & buku disesuaikan sama.")
        else:
            st.warning(f"⚠️ Masih ada selisih Rp {b['Selisih']:,.0f}. Periksa kembali.")

# ============================================================
# PAGE: TB Setelah Penyesuaian
# ============================================================
elif menu == "📊 TB Setelah Penyesuaian":
    st.title("📊 Neraca Saldo Setelah Penyesuaian")
    adj = get_adjusted_tb()
    if adj is None:
        st.warning("Upload trial balance dulu.")
    else:
        st.dataframe(adj.style.format({
            "Debit": "Rp {:,.0f}", "Kredit": "Rp {:,.0f}",
            "Debit Adj": "Rp {:,.0f}", "Kredit Adj": "Rp {:,.0f}",
            "Debit Akhir": "Rp {:,.0f}", "Kredit Akhir": "Rp {:,.0f}",
        }), use_container_width=True)

        d, k = adj["Debit Akhir"].sum(), adj["Kredit Akhir"].sum()
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Debit", f"Rp {d:,.0f}")
        c2.metric("Total Kredit", f"Rp {k:,.0f}")
        c3.metric("Selisih", f"Rp {d - k:,.0f}")

        st.subheader("Ringkasan per Tipe Akun")
        ring = adj.groupby("Tipe").agg(
            Debit=("Debit Akhir", "sum"), Kredit=("Kredit Akhir", "sum"))
        ring["Saldo"] = ring["Debit"] - ring["Kredit"]
        st.dataframe(ring.style.format("Rp {:,.0f}"), use_container_width=True)

# ============================================================
# PAGE: Tutup Buku
# ============================================================
elif menu == "🔒 Tutup Buku":
    st.title("🔒 Tutup Buku — Jurnal Penutup")
    adj = get_adjusted_tb()
    if adj is None:
        st.warning("Upload trial balance dulu.")
    else:
        st.info("Jurnal penutup akan menutup akun **Pendapatan** dan **Beban** ke "
                "**Ikhtisar Laba Rugi**, lalu memindahkan saldonya ke **Laba Ditahan**.")

        if st.button("🔒 Generate Jurnal Penutup", type="primary"):
            close, laba = build_closing_entries(adj)
            st.session_state["closing_df"] = close
            st.session_state["laba"] = laba

        if st.session_state.get("closing_df") is not None:
            df = st.session_state["closing_df"]
            st.success(f"Laba/Rugi periode: **Rp {st.session_state['laba']:,.2f}**")
            st.dataframe(df.style.format({"Debit": "Rp {:,.0f}", "Kredit": "Rp {:,.0f}"}),
                         use_container_width=True)
            st.caption(f"Total Debit: Rp {df['Debit'].sum():,.0f} | "
                       f"Total Kredit: Rp {df['Kredit'].sum():,.0f}")

# ============================================================
# PAGE: Export
# ============================================================
elif menu == "📥 Export":
    st.title("📥 Export Hasil Penutupan Buku")
    if st.session_state.tb is None:
        st.warning("Belum ada data untuk diexport.")
    else:
        data = build_excel()
        st.download_button(
            "⬇️ Download Excel (semua sheet)",
            data=data,
            file_name=f"penutupan_buku_{st.session_state.period.strftime('%Y%m')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        st.write("Sheet yang disertakan: **TB**, **Penyesuaian**, "
                 "**TB Setelah Penyesuaian**, **Jurnal Penutup**, "
                 "**Rekonsiliasi Bank**, **Checklist**.")
