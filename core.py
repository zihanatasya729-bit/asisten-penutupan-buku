"""
Logika bisnis Asisten Penutupan Buku:
- Data demo & checklist
- Adjusted trial balance
- Jurnal penutup
- Export Excel
"""
import io
from datetime import date

import pandas as pd
import streamlit as st

# ============================================================
# DATA DEMO
# ============================================================
DEMO_TB = pd.DataFrame([
    {"Kode": "101", "Nama Akun": "Kas", "Tipe": "Aset", "Debit": 75_000_000, "Kredit": 0},
    {"Kode": "102", "Nama Akun": "Piutang Usaha", "Tipe": "Aset", "Debit": 120_000_000, "Kredit": 0},
    {"Kode": "103", "Nama Akun": "Perlengkapan", "Tipe": "Aset", "Debit": 15_000_000, "Kredit": 0},
    {"Kode": "104", "Nama Akun": "Sewa Dibayar Dimuka", "Tipe": "Aset", "Debit": 24_000_000, "Kredit": 0},
    {"Kode": "121", "Nama Akun": "Peralatan", "Tipe": "Aset", "Debit": 200_000_000, "Kredit": 0},
    {"Kode": "122", "Nama Akun": "Akum. Penyusutan Peralatan", "Tipe": "Aset", "Debit": 0, "Kredit": 40_000_000},
    {"Kode": "201", "Nama Akun": "Utang Usaha", "Tipe": "Kewajiban", "Debit": 0, "Kredit": 85_000_000},
    {"Kode": "202", "Nama Akun": "Utang Gaji", "Tipe": "Kewajiban", "Debit": 0, "Kredit": 0},
    {"Kode": "301", "Nama Akun": "Modal Saham", "Tipe": "Ekuitas", "Debit": 0, "Kredit": 200_000_000},
    {"Kode": "302", "Nama Akun": "Laba Ditahan", "Tipe": "Ekuitas", "Debit": 0, "Kredit": 41_000_000},
    {"Kode": "401", "Nama Akun": "Pendapatan Penjualan", "Tipe": "Pendapatan", "Debit": 0, "Kredit": 450_000_000},
    {"Kode": "501", "Nama Akun": "Beban Pokok Penjualan", "Tipe": "Beban", "Debit": 280_000_000, "Kredit": 0},
    {"Kode": "502", "Nama Akun": "Beban Gaji", "Tipe": "Beban", "Debit": 90_000_000, "Kredit": 0},
    {"Kode": "503", "Nama Akun": "Beban Listrik & Air", "Tipe": "Beban", "Debit": 12_000_000, "Kredit": 0},
    {"Kode": "504", "Nama Akun": "Beban Penyusutan", "Tipe": "Beban", "Debit": 0, "Kredit": 0},
])

CHECKLIST_ITEMS = [
    ("bank",       "Rekonsiliasi bank",               "Cocokkan saldo kas buku besar dengan rekening koran"),
    ("kas_kecil",  "Verifikasi kas kecil",            "Hitung fisik kas kecil dan cocokkan"),
    ("piutang",    "Konfirmasi piutang usaha",        "Kirim konfirmasi ke pelanggan besar"),
    ("utang",      "Konfirmasi utang usaha",          "Cocokkan saldo utang dengan supplier"),
    ("persediaan", "Stock opname persediaan",         "Hitung fisik persediaan & sesuaikan"),
    ("prepaid",    "Amortisasi biaya dibayar dimuka", "Catat beban sewa/asuransi periode ini"),
    ("akrual",     "Akrual beban & pendapatan",       "Catat yang masih harus diakui"),
    ("penyusutan", "Penyusutan aset tetap",           "Catat penyusutan periode berjalan"),
    ("interco",    "Rekonsiliasi intercompany",       "Cocokkan transaksi antar entitas"),
    ("review",     "Review saldo abnormal",           "Review saldo tidak lazim / negatif"),
    ("backup",     "Backup & arsip dokumen",          "Backup data & arsipkan bukti"),
    ("closing",    "Posting jurnal penutup",          "Tutup akun nominal ke laba ditahan"),
]

# ============================================================
# SESSION STATE
# ============================================================
DEFAULTS = {
    "tb": None,
    "adjustments": [],
    "checklist": {},
    "bank": {},
    "period": date.today(),
    "closing_df": None,
    "laba": 0.0,
}

def init_state():
    for k, v in DEFAULTS.items():
        if k not in st.session_state:
            st.session_state[k] = v.copy() if isinstance(v, (list, dict)) else v

def reset_state():
    for k in DEFAULTS:
        if k in st.session_state:
            del st.session_state[k]
    for k in list(st.session_state.keys()):
        if k.startswith("chk_"):
            del st.session_state[k]
    init_state()

# ============================================================
# KALKULASI
# ============================================================
def get_adjusted_tb():
    """Gabungkan trial balance awal dengan jurnal penyesuaian."""
    tb = st.session_state.tb
    if tb is None:
        return None

    base = tb.copy()
    
    # PERBAIKAN BUG: Paksa kolom Kode menjadi string agar bisa digabung (merge)
    base["Kode"] = base["Kode"].astype(str)
    
    for c in ["Debit", "Kredit"]:
        base[c] = pd.to_numeric(base[c], errors="coerce").fillna(0)

    adj = st.session_state.adjustments
    if not adj:
        base["Debit Adj"] = 0
        base["Kredit Adj"] = 0
        base["Debit Akhir"] = base["Debit"]
        base["Kredit Akhir"] = base["Kredit"]
        return base[["Kode", "Nama Akun", "Tipe", "Debit", "Kredit",
                     "Debit Adj", "Kredit Adj", "Debit Akhir", "Kredit Akhir"]]

    adj_df = pd.DataFrame(adj)
    
    # PERBAIKAN BUG: Paksa kolom Kode di penyesuaian menjadi string
    adj_df["Kode"] = adj_df["Kode"].astype(str)
    
    agg = adj_df.groupby("Kode", as_index=False).agg(
        Nama_Akun_Adj=("Nama Akun", "first"),
        Debit_Adj=("Debit", "sum"),
        Kredit_Adj=("Kredit", "sum"),
    )
    
    m = base.merge(agg, on="Kode", how="outer")
    m["Nama Akun"] = m["Nama Akun"].fillna(m["Nama_Akun_Adj"])
    m["Tipe"] = m["Tipe"].fillna("Belum diklasifikasi")
    
    for c in ["Debit", "Kredit", "Debit_Adj", "Kredit_Adj"]:
        m[c] = pd.to_numeric(m[c], errors="coerce").fillna(0)

    m = m.rename(columns={"Debit_Adj": "Debit Adj", "Kredit_Adj": "Kredit Adj"})
    m["Debit Akhir"] = m["Debit"] + m["Debit Adj"]
    m["Kredit Akhir"] = m["Kredit"] + m["Kredit Adj"]

    return m[["Kode", "Nama Akun", "Tipe", "Debit", "Kredit",
              "Debit Adj", "Kredit Adj", "Debit Akhir", "Kredit Akhir"]]


def build_closing_entries(adj_tb):
    """Jurnal penutup: Pendapatan & Beban → Ikhtisar L/R → Laba Ditahan."""
    rows, no = [], 1

    for _, r in adj_tb.iterrows():
        if r["Tipe"] == "Pendapatan":
            bal = r["Kredit Akhir"] - r["Debit Akhir"]
            if bal:
                rows.append({"No": no, "Keterangan": "Menutup pendapatan",
                             "Kode": r["Kode"], "Nama Akun": r["Nama Akun"],
                             "Debit": bal, "Kredit": 0})
                rows.append({"No": no, "Keterangan": "Menutup pendapatan",
                             "Kode": "3300", "Nama Akun": "Ikhtisar Laba Rugi",
                             "Debit": 0, "Kredit": bal})
                no += 1
        elif r["Tipe"] == "Beban":
            bal = r["Debit Akhir"] - r["Kredit Akhir"]
            if bal:
                rows.append({"No": no, "Keterangan": "Menutup beban",
                             "Kode": "3300", "Nama Akun": "Ikhtisar Laba Rugi",
                             "Debit": bal, "Kredit": 0})
                rows.append({"No": no, "Keterangan": "Menutup beban",
                             "Kode": r["Kode"], "Nama Akun": r["Nama Akun"],
                             "Debit": 0, "Kredit": bal})
                no += 1

    pendapatan = (adj_tb[adj_tb["Tipe"] == "Pendapatan"]["Kredit Akhir"].sum()
                  - adj_tb[adj_tb["Tipe"] == "Pendapatan"]["Debit Akhir"].sum())
    beban = (adj_tb[adj_tb["Tipe"] == "Beban"]["Debit Akhir"].sum()
             - adj_tb[adj_tb["Tipe"] == "Beban"]["Kredit Akhir"].sum())
    laba = pendapatan - beban

    if laba > 0:
        rows.append({"No": no, "Keterangan": "Memindahkan laba ke laba ditahan",
                     "Kode": "3300", "Nama Akun": "Ikhtisar Laba Rugi",
                     "Debit": laba, "Kredit": 0})
        rows.append({"No": no, "Keterangan": "Memindahkan laba ke laba ditahan",
                     "Kode": "302", "Nama Akun": "Laba Ditahan",
                     "Debit": 0, "Kredit": laba})
    elif laba < 0:
        rows.append({"No": no, "Keterangan": "Memindahkan rugi ke laba ditahan",
                     "Kode": "302", "Nama Akun": "Laba Ditahan",
                     "Debit": -laba, "Kredit": 0})
        rows.append({"No": no, "Keterangan": "Memindahkan rugi ke laba ditahan",
                     "Kode": "3300", "Nama Akun": "Ikhtisar Laba Rugi",
                     "Debit": 0, "Kredit": -laba})

    return pd.DataFrame(rows), laba


def build_excel():
    """Bundel semua data ke satu file Excel."""
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        if st.session_state.tb is not None:
            st.session_state.tb.to_excel(w, sheet_name="TB", index=False)

        if st.session_state.adjustments:
            pd.DataFrame(st.session_state.adjustments).to_excel(
                w, sheet_name="Penyesuaian", index=False)

        adj = get_adjusted_tb()
        if adj is not None:
            adj.to_excel(w, sheet_name="TB Setelah Penyesuaian", index=False)
            close, _ = build_closing_entries(adj)
            if not close.empty:
                close.to_excel(w, sheet_name="Jurnal Penutup", index=False)

        if st.session_state.bank:
            pd.DataFrame([st.session_state.bank]).T.to_excel(
                w, sheet_name="Rekonsiliasi Bank")

        chk = pd.DataFrame([
            {"Item": d, "Keterangan": k,
             "Status": "✔" if st.session_state.checklist.get(key) else "✘"}
            for key, d, k in CHECKLIST_ITEMS
        ])
        chk.to_excel(w, sheet_name="Checklist", index=False)

    return buf.getvalue()
