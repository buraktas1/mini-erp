import sqlite3
import pandas as pd
import streamlit as st

# 1. Veri Tabanı Bağlantısı ve Tablo Oluşturma
def vt_kur():
    conn = sqlite3.connect("mini_erp.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS urunler (
            urun_id INTEGER PRIMARY KEY AUTOINCREMENT,
            urun_adi TEXT NOT NULL,
            stok_miktari INTEGER NOT NULL,
            fiyat REAL NOT NULL,
            kritik_seviye INTEGER DEFAULT 5
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS musteriler (
            musteri_id INTEGER PRIMARY KEY AUTOINCREMENT,
            firma_adi TEXT NOT NULL,
            telefon TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS satislar (
            satis_id INTEGER PRIMARY KEY AUTOINCREMENT,
            musteri_id INTEGER,
            urun_id INTEGER,
            adet INTEGER,
            toplam_tutar REAL,
            tarih TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (musteri_id) REFERENCES musteriler(musteri_id),
            FOREIGN KEY (urun_id) REFERENCES urunler(urun_id)
        )
    """)

    conn.commit()
    conn.close()

vt_kur()

# Sayfa Yapılandırması
st.set_page_config(page_title="Mini ERP", page_icon="🏢", layout="wide")
st.title("🏢 Mini ERP - Kurumsal Kaynak Planlama")

# Sekmeler
sekme_stok, sekme_musteri, sekme_satis, sekme_rapor = st.tabs([
    "📦 Stok & Ürün Yönetimi", 
    "👥 Müşteri (Cari) Yönetimi", 
    "🛒 Satış Yap (ERP Döngüsü)",
    "📊 Genel Raporlar"
])

# ----------------------------------------------------
# 1. SEKME: STOK & ÜRÜN YÖNETİMİ
# ----------------------------------------------------
with sekme_stok:
    st.header("📦 Ürün Ekle, Düzenle ve Sil")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("➕ Yeni Ürün Tanımla")
        with st.form("urun_ekle_form", clear_on_submit=True):
            urun_adi = st.text_input("Ürün Adı")
            stok_miktari = st.number_input("Başlangıç Stok Miktarı", min_value=1, value=10)
            fiyat = st.number_input("Birim Fiyat (TL)", min_value=0.0, value=100.0, step=10.0)
            kritik_seviye = st.number_input("Kritik Stok Uyarı Seviyesi", min_value=1, value=5)
            
            kaydet_btn = st.form_submit_button("Ürünü Kaydet")
            
            if kaydet_btn:
                if urun_adi != "":
                    conn = sqlite3.connect("mini_erp.db")
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO urunler (urun_adi, stok_miktari, fiyat, kritik_seviye) VALUES (?, ?, ?, ?)",
                        (urun_adi, int(stok_miktari), float(fiyat), int(kritik_seviye))
                    )
                    conn.commit()
                    conn.close()
                    st.success(f"'{urun_adi}' başarıyla depoya eklendi!")
                    st.rerun()
                else:
                    st.warning("Lütfen ürün adını boş bırakmayın.")

        st.divider()

        # ÜRÜN SİLME KISMI
        st.subheader("🗑️ Yanlış / Eski Ürün Sil")
        conn = sqlite3.connect("mini_erp.db")
        df_sil = pd.read_sql_query("SELECT * FROM urunler", conn)
        conn.close()

        if not df_sil.empty:
            sil_dict = dict(zip(df_sil['urun_adi'], df_sil['urun_id']))
            silinecek_urun = st.selectbox("Silinecek Ürünü Seç", list(sil_dict.keys()))
            
            if st.button("❌ Seçilen Ürünü Depodan Sil", type="primary"):
                conn = sqlite3.connect("mini_erp.db")
                cursor = conn.cursor()
                cursor.execute("DELETE FROM urunler WHERE urun_id = ?", (sil_dict[silinecek_urun],))
                conn.commit()
                conn.close()
                st.success(f"'{silinecek_urun}' veri tabanından silindi!")
                st.rerun()
        else:
            st.caption("Silinecek ürün yok.")

    with col2:
        st.subheader("📊 Mevcut Depo Stok Durumu")
        conn = sqlite3.connect("mini_erp.db")
        df_urunler = pd.read_sql_query("SELECT * FROM urunler", conn)
        conn.close()
        
        if not df_urunler.empty:
            # HATAYI ÖNLEYEN KISIM: errors='coerce' ekledik (bozuk verileri 0 yapar, patlamaz)
            df_urunler['stok_miktari'] = pd.to_numeric(df_urunler['stok_miktari'], errors='coerce').fillna(0)
            df_urunler['kritik_seviye'] = pd.to_numeric(df_urunler['kritik_seviye'], errors='coerce').fillna(5)
            df_urunler['fiyat'] = pd.to_numeric(df_urunler['fiyat'], errors='coerce').fillna(0.0)

            st.dataframe(df_urunler, use_container_width=True)
            
            # Kritik Stok Uyarısı
            kritik_urunler = df_urunler[df_urunler['stok_miktari'] <= df_urunler['kritik_seviye']]
            if not kritik_urunler.empty:
                st.error("🚨 KRİTİK STOK UYARISI: Aşağıdaki ürünlerin stoğu azaldı!")
                st.table(kritik_urunler[['urun_adi', 'stok_miktari', 'kritik_seviye']])
        else:
            st.info("Henüz depoda ürün yok. Sol taraftan ürün ekleyebilirsin.")

# ----------------------------------------------------
# 2. SEKME: MÜŞTERİ YÖNETİMİ
# ----------------------------------------------------
with sekme_musteri:
    st.header("👥 Müşteri Kayıtları")
    
    col_m1, col_m2 = st.columns([1, 2])
    
    with col_m1:
        st.subheader("Yeni Müşteri Ekle")
        with st.form("musteri_ekle_form", clear_on_submit=True):
            firma_adi = st.text_input("Firma / Müşteri Adı")
            telefon = st.text_input("Telefon / İletişim")
            
            musteri_kaydet_btn = st.form_submit_button("Müşteriyi Kaydet")
            
            if musteri_kaydet_btn:
                if firma_adi != "":
                    conn = sqlite3.connect("mini_erp.db")
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO musteriler (firma_adi, telefon) VALUES (?, ?)",
                        (firma_adi, telefon)
                    )
                    conn.commit()
                    conn.close()
                    st.success(f"'{firma_adi}' müşteri portföyüne eklendi!")
                    st.rerun()
                else:
                    st.warning("Lütfen firma adını boş bırakmayın.")

    with col_m2:
        st.subheader("📋 Kayıtlı Müşteri Listesi")
        conn = sqlite3.connect("mini_erp.db")
        df_musteriler = pd.read_sql_query("SELECT * FROM musteriler", conn)
        conn.close()
        
        if not df_musteriler.empty:
            st.dataframe(df_musteriler, use_container_width=True)
        else:
            st.info("Henüz kayıtlı müşteri yok.")

# ----------------------------------------------------
# 3. SEKME: SATIŞ YAP
# ----------------------------------------------------
with sekme_satis:
    st.header("🛒 Satış İşlemi (Stok Otomatik Güncellenir)")
    
    conn = sqlite3.connect("mini_erp.db")
    df_m = pd.read_sql_query("SELECT * FROM musteriler", conn)
    df_u = pd.read_sql_query("SELECT * FROM urunler", conn)
    conn.close()

    if df_m.empty or df_u.empty:
        st.warning("⚠️ Satış yapabilmek için önce 'Stok' ve 'Müşteri' sekmelerinden en az 1 ürün ve 1 müşteri eklemelisiniz!")
    else:
        df_u['stok_miktari'] = pd.to_numeric(df_u['stok_miktari'], errors='coerce').fillna(0)
        df_u['fiyat'] = pd.to_numeric(df_u['fiyat'], errors='coerce').fillna(0.0)

        col_s1, col_s2 = st.columns(2)
        
        with col_s1:
            musteri_dict = dict(zip(df_m['firma_adi'], df_m['musteri_id']))
            secilen_musteri_adi = st.selectbox("Müşteri / Firma Seç", list(musteri_dict.keys()))
            secilen_musteri_id = int(musteri_dict[secilen_musteri_adi])
            
            urun_dict = dict(zip(df_u['urun_adi'], df_u['urun_id']))
            secilen_urun_adi = st.selectbox("Satılacak Ürün Seç", list(urun_dict.keys()))
            secilen_urun_id = int(urun_dict[secilen_urun_adi])

        with col_s2:
            secilen_urun_bilgi = df_u[df_u['urun_id'] == secilen_urun_id].iloc[0]
            mevcut_stok = int(secilen_urun_bilgi['stok_miktari'])
            birim_fiyat = float(secilen_urun_bilgi['fiyat'])

            st.write(f"*Mevcut Stok:* {mevcut_stok} adet")
            st.write(f"*Birim Fiyat:* {birim_fiyat} TL")

            satis_adedi = st.number_input("Satış Adedi", min_value=1, max_value=int(mevcut_stok) if mevcut_stok > 0 else 1, value=1)
            toplam_tutar = float(satis_adedi * birim_fiyat)
            st.subheader(f"Toplam Tutar: {toplam_tutar:,} TL")

        if mevcut_stok <= 0:
            st.error("❌ Bu ürünün stoğu bitmiştir! Satış yapılamaz.")
        else:
            if st.button("🛒 Satışı Onayla ve İşle"):
                conn = sqlite3.connect("mini_erp.db")
                cursor = conn.cursor()

                cursor.execute(
                    "INSERT INTO satislar (musteri_id, urun_id, adet, toplam_tutar) VALUES (?, ?, ?, ?)",
                    (secilen_musteri_id, secilen_urun_id, int(satis_adedi), toplam_tutar)
                )

                yeni_stok = mevcut_stok - int(satis_adedi)
                cursor.execute(
                    "UPDATE urunler SET stok_miktari = ? WHERE urun_id = ?",
                    (yeni_stok, secilen_urun_id)
                )

                conn.commit()
                conn.close()

                st.balloons()
                st.success(f"Satış Başarılı! {secilen_urun_adi} yeni stoğu: {yeni_stok}")
                st.rerun()

# ----------------------------------------------------
# 4. SEKME: GENEL RAPORLAR
# ----------------------------------------------------
with sekme_rapor:
    st.header("📊 Satış ve Ciro Raporları")
    
    conn = sqlite3.connect("mini_erp.db")
    satis_sorgu = """
        SELECT 
            s.satis_id as 'Satış ID',
            m.firma_adi as 'Müşteri',
            u.urun_adi as 'Ürün',
            s.adet as 'Adet',
            s.toplam_tutar as 'Toplam Tutar (TL)',
            s.tarih as 'Tarih'
        FROM satislar s
        JOIN musteriler m ON s.musteri_id = m.musteri_id
        JOIN urunler u ON s.urun_id = u.urun_id
        ORDER BY s.satis_id DESC
    """
    df_satislar = pd.read_sql_query(satis_sorgu, conn)
    conn.close()

    if not df_satislar.empty:
        df_satislar['Toplam Tutar (TL)'] = pd.to_numeric(df_satislar['Toplam Tutar (TL)'], errors='coerce').fillna(0.0)
        df_satislar['Adet'] = pd.to_numeric(df_satislar['Adet'], errors='coerce').fillna(0)

        toplam_ciro = df_satislar['Toplam Tutar (TL)'].sum()
        toplam_satis_adedi = df_satislar['Adet'].sum()

        col_r1, col_r2 = st.columns(2)
        col_r1.metric("💰 Toplam Ciro", f"{toplam_ciro:,} TL")
        col_r2.metric("📦 Toplam Satılan Ürün", f"{toplam_satis_adedi} Adet")

        st.subheader("Geçmiş Satış Hareketleri")
        st.dataframe(df_satislar, use_container_width=True)
    else:
        st.info("Henüz gerçekleşmiş bir satış yok.")