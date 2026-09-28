import sqlite3
import pandas as pd
import streamlit as st
import hashlib

# Sayfa yapılandırması
st.set_page_config(page_title="Mini ERP", page_icon="🏢", layout="wide")

# Şifreleri güvenli hashlemek için fonksiyon
def sifre_hashle(sifre):
    return hashlib.sha256(sifre.encode()).hexdigest()

# 1. Veri Tabanı Bağlantısı ve Tablolar
def vt_kur():
    # Temiz ve hatasız başlangıç için v4 veritabanı
    conn = sqlite3.connect("mini_erp_v4.db", check_same_thread=False)
    cursor = conn.cursor()
    
    # Kullanıcılar tablosu
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS kullanicilar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kullanici_adi TEXT UNIQUE NOT NULL,
        sifre TEXT NOT NULL
    )
    """)

    # Ürünler tablosu (alis_fiyati eklendi)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS urunler (
        urun_id INTEGER PRIMARY KEY AUTOINCREMENT,
        kullanici_id INTEGER NOT NULL,
        urun_adi TEXT NOT NULL,
        stok_miktari INTEGER NOT NULL,
        alis_fiyati REAL NOT NULL DEFAULT 0.0,
        fiyat REAL NOT NULL,
        kritik_seviye INTEGER DEFAULT 5,
        FOREIGN KEY (kullanici_id) REFERENCES kullanicilar (id)
    )
    """)

    # Müşteriler tablosu
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS musteriler (
        musteri_id INTEGER PRIMARY KEY AUTOINCREMENT,
        kullanici_id INTEGER NOT NULL,
        firma_adi TEXT NOT NULL,
        yetkili TEXT,
        telefon TEXT,
        FOREIGN KEY (kullanici_id) REFERENCES kullanicilar (id)
    )
    """)

    # Satışlar tablosu (kar_tutari eklendi)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS satislar (
        satis_id INTEGER PRIMARY KEY AUTOINCREMENT,
        kullanici_id INTEGER NOT NULL,
        urun_id INTEGER NOT NULL,
        musteri_id INTEGER NOT NULL,
        adet INTEGER NOT NULL,
        toplam_tutar REAL NOT NULL,
        kar_tutari REAL NOT NULL DEFAULT 0.0,
        tarih TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (kullanici_id) REFERENCES kullanicilar (id)
    )
    """)
    conn.commit()
    return conn

conn = vt_kur()
cursor = conn.cursor()

# 2. Oturum (Session) Kontrolü
if "giris_yapildi" not in st.session_state:
    st.session_state.giris_yapildi = False
    st.session_state.kullanici_id = None
    st.session_state.kullanici_adi = ""

# Giriş / Kayıt Arayüzü
def auth_ekrani():
    st.title("🏢 Mini ERP - Kurumsal Giriş")
    tab_giris, tab_kayit = st.tabs(["🔑 Giriş Yap", "📝 Yeni Hesap Oluştur"])

    with tab_giris:
        st.subheader("Giriş Paneli")
        k_adi = st.text_input("Kullanıcı Adı", key="login_user")
        k_sifre = st.text_input("Şifre", type="password", key="login_pass")
        
        if st.button("Giriş Yap", use_container_width=True):
            if k_adi and k_sifre:
                hashed = sifre_hashle(k_sifre)
                cursor.execute("SELECT id, kullanici_adi FROM kullanicilar WHERE kullanici_adi = ? AND sifre = ?", (k_adi, hashed))
                user = cursor.fetchone()
                if user:
                    st.session_state.giris_yapildi = True
                    st.session_state.kullanici_id = user[0]
                    st.session_state.kullanici_adi = user[1]
                    st.success(f"Hoş geldin, {user[1]}!")
                    st.rerun()
                else:
                    st.error("Kullanıcı adı veya şifre hatalı!")
            else:
                st.warning("Lütfen tüm alanları doldurun.")

    with tab_kayit:
        st.subheader("Yeni Kullanıcı Kaydı")
        yeni_k_adi = st.text_input("Kullanıcı Adı Seçin", key="reg_user")
        yeni_sifre = st.text_input("Şifre Belirleyin", type="password", key="reg_pass")
        yeni_sifre_tekrar = st.text_input("Şifre Tekrar", type="password", key="reg_pass_rep")

        if st.button("Kayıt Ol", use_container_width=True):
            if yeni_k_adi and yeni_sifre:
                if yeni_sifre != yeni_sifre_tekrar:
                    st.error("Şifreler birbiriyle uyuşmuyor!")
                else:
                    try:
                        hashed = sifre_hashle(yeni_sifre)
                        cursor.execute("INSERT INTO kullanicilar (kullanici_adi, sifre) VALUES (?, ?)", (yeni_k_adi, hashed))
                        conn.commit()
                        st.success("Hesabın başarıyla oluşturuldu! Şimdi Giriş Yap sekmesinden giriş yapabilirsin.")
                    except sqlite3.IntegrityError:
                        st.error("Bu kullanıcı adı zaten alınmış, başka bir ad deneyin.")
            else:
                st.warning("Lütfen tüm alanları doldurun.")

# Eğer giriş yapılmadıysa login ekranını göster ve durdur
if not st.session_state.giris_yapildi:
    auth_ekrani()
    st.stop()

# ----------------- GİRİŞ YAPILDIKTAN SONRAKİ ERP PANELİ -----------------
user_id = st.session_state.kullanici_id

with st.sidebar:
    st.write(f"👤 Aktif Kullanıcı: **{st.session_state.kullanici_adi}**")
    if st.button("Çıkış Yap"):
        st.session_state.giris_yapildi = False
        st.session_state.kullanici_id = None
        st.session_state.kullanici_adi = ""
        st.rerun()

st.title("🏢 Mini ERP - Kurumsal Kaynak Planlama")

sekme1, sekme2, sekme3, sekme4 = st.tabs([
    "📦 Stok & Ürün Yönetimi", 
    "👥 Müşteri Rehberi", 
    "🛒 Satış Yap (ERP Döngüsü)", 
    "📊 Genel Raporlar"
])

# 1. SEKME: STOK & ÜRÜN YÖNETİMİ
with sekme1:
    st.header("📦 Ürün Ekle ve Depo Yönetimi")
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("➕ Yeni Ürün Tanımla")
        with st.form("urun_formu", clear_on_submit=True):
            urun_adi = st.text_input("Ürün Adı")
            stok = st.number_input("Başlangıç Stok Miktarı", min_value=0, step=1, value=10)
            alis_fiyat = st.number_input("Alış / Maliyet Fiyatı (TL)", min_value=0.0, step=10.0, value=70.0)
            satis_fiyat = st.number_input("Satış Fiyatı (TL)", min_value=0.0, step=10.0, value=100.0)
            kritik = st.number_input("Kritik Stok Uyarı Seviyesi", min_value=1, step=1, value=5)
            kaydet = st.form_submit_button("Ürünü Kaydet")
            
            if kaydet:
                if urun_adi.strip():
                    cursor.execute("""
                    INSERT INTO urunler (kullanici_id, urun_adi, stok_miktari, alis_fiyati, fiyat, kritik_seviye) 
                    VALUES (?, ?, ?, ?, ?, ?)
                    """, (user_id, urun_adi, stok, alis_fiyat, satis_fiyat, kritik))
                    conn.commit()
                    st.success(f"{urun_adi} başarıyla eklendi!")
                    st.rerun()
                else:
                    st.error("Lütfen bir ürün adı yazın.")

    with col2:
        st.subheader("📋 Mevcut Depo Stok Durumu")
        df_urunler = pd.read_sql_query("""
            SELECT urun_id as [ID], urun_adi as [Ürün Adı], stok_miktari as [Stok], 
                   alis_fiyati as [Alış (TL)], fiyat as [Satış (TL)], kritik_seviye as [Kritik Sınır] 
            FROM urunler WHERE kullanici_id = ?
        """, conn, params=(user_id,))
        
        if not df_urunler.empty:
            st.dataframe(df_urunler, use_container_width=True)
            
            # Excel / CSV İndir Butonu
            csv_stok = df_urunler.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 Stok Listesini İndir (Excel/CSV)",
                data=csv_stok,
                file_name="depo_stok_listesi.csv",
                mime="text/csv"
            )
            
            # Kritik stok ikazı
            kritikler = df_urunler[df_urunler['Stok'] <= df_urunler['Kritik Sınır']]
            if not kritikler.empty:
                for _, row in kritikler.iterrows():
                    st.warning(f"⚠️ **DİKKAT:** '{row['Ürün Adı']}' stoğu kritik seviyede! (Kalan: {row['Stok']})")
        else:
            st.info("Henüz depoda ürün yok. Sol taraftan ürün ekleyebilirsin.")

# 2. SEKME: MÜŞTERİ YÖNETİMİ
with sekme2:
    st.header("👥 Müşteri Rehberi")
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("➕ Yeni Müşteri Ekle")
        with st.form("musteri_formu", clear_on_submit=True):
            firma = st.text_input("Firma / Müşteri Adı")
            yetkili = st.text_input("Yetkili Kişi")
            tel = st.text_input("Telefon Numarası")
            m_kaydet = st.form_submit_button("Müşteriyi Kaydet")
            
            if m_kaydet:
                if firma.strip():
                    cursor.execute("""
                    INSERT INTO musteriler (kullanici_id, firma_adi, yetkili, telefon) 
                    VALUES (?, ?, ?, ?)
                    """, (user_id, firma, yetkili, tel))
                    conn.commit()
                    st.success(f"{firma} başarıyla kaydedildi!")
                    st.rerun()
                else:
                    st.error("Lütfen firma adı girin.")
                    
    with col2:
        st.subheader("📋 Kayıtlı Müşteriler")
        df_musteri = pd.read_sql_query("""
            SELECT musteri_id as [ID], firma_adi as [Firma Adı], yetkili as [Yetkili], telefon as [Telefon] 
            FROM musteriler WHERE kullanici_id = ?
        """, conn, params=(user_id,))
        if not df_musteri.empty:
            st.dataframe(df_musteri, use_container_width=True)
        else:
            st.info("Henüz kayıtlı müşteri yok.")

# 3. SEKME: SATIŞ İŞLEMİ (KÂR HESAPLAMALI)
with sekme3:
    st.header("🛒 Satış Faturası ve Stok Çıkışı")
    df_u = pd.read_sql_query("SELECT urun_id, urun_adi, stok_miktari, alis_fiyati, fiyat FROM urunler WHERE kullanici_id = ?", conn, params=(user_id,))
    df_m = pd.read_sql_query("SELECT musteri_id, firma_adi FROM musteriler WHERE kullanici_id = ?", conn, params=(user_id,))
    
    if df_u.empty or df_m.empty:
        st.warning("⚠️ Satış yapabilmek için önce en az 1 Ürün ve 1 Müşteri tanımlamalısın!")
    else:
        with st.form("satis_formu"):
            secilen_urun_adi = st.selectbox("Satılacak Ürünü Seç", df_u['urun_adi'].tolist())
            secilen_musteri_adi = st.selectbox("Müşteriyi Seç", df_m['firma_adi'].tolist())
            
            urun_bilgi = df_u[df_u['urun_adi'] == secilen_urun_adi].iloc[0]
            stok_durumu = urun_bilgi['stok_miktari']
            alis_fiyati = urun_bilgi['alis_fiyati']
            birim_fiyat = urun_bilgi['fiyat']
            
            st.write(f"Mevcut Depo Stoğu: **{stok_durumu} Adet** | Satış Fiyatı: **{birim_fiyat:.2f} TL** (Maliyet: {alis_fiyati:.2f} TL)")
            satilan_adet = st.number_input("Satılacak Adet", min_value=1, max_value=max(1, int(stok_durumu)), step=1)
            
            toplam_tutar = satilan_adet * birim_fiyat
            tahmini_kar = (birim_fiyat - alis_fiyati) * satilan_adet
            
            c_tut1, c_tut2 = st.columns(2)
            c_tut1.markdown(f"### Toplam Tutar: :green[{toplam_tutar:.2f} TL]")
            c_tut2.markdown(f"### Tahmini Net Kâr: :blue[{tahmini_kar:.2f} TL]")
            
            satisi_tamamla = st.form_submit_button("Satışı Onayla ve Kaydet")
            
            if satisi_tamamla:
                if satilan_adet > stok_durumu:
                    st.error("Yetersiz stok!")
                else:
                    m_id = int(df_m[df_m['firma_adi'] == secilen_musteri_adi].iloc[0]['musteri_id'])
                    u_id = int(urun_bilgi['urun_id'])
                    net_kar = (birim_fiyat - alis_fiyati) * satilan_adet
                    
                    # 1. Satışı ve kârı kaydet
                    cursor.execute("""
                    INSERT INTO satislar (kullanici_id, urun_id, musteri_id, adet, toplam_tutar, kar_tutari) 
                    VALUES (?, ?, ?, ?, ?, ?)
                    """, (user_id, u_id, m_id, satilan_adet, toplam_tutar, net_kar))
                    
                    # 2. Ürün stoğunu düş
                    cursor.execute("UPDATE urunler SET stok_miktari = stok_miktari - ? WHERE urun_id = ? AND kullanici_id = ?", (satilan_adet, u_id, user_id))
                    
                    conn.commit()
                    st.success("✅ Satış başarıyla tamamlandı, stok güncellendi ve kâr kaydedildi!")
                    st.rerun()

# 4. SEKME: RAPORLAR VE ANALİZ
with sekme4:
    st.header("📊 Finansal ve Operasyonel Raporlar")
    df_satislar = pd.read_sql_query("""
    SELECT s.satis_id as [Fatura No], u.urun_adi as [Ürün], m.firma_adi as [Müşteri], 
           s.adet as [Adet], s.toplam_tutar as [Tutar (TL)], s.kar_tutari as [Kâr (TL)], s.tarih as [Tarih] 
    FROM satislar s
    JOIN urunler u ON s.urun_id = u.urun_id
    JOIN musteriler m ON s.musteri_id = m.musteri_id
    WHERE s.kullanici_id = ?
    ORDER BY s.tarih DESC
    """, conn, params=(user_id,))
    
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    toplam_ciro = df_satislar['Tutar (TL)'].sum() if not df_satislar.empty else 0
    toplam_kar = df_satislar['Kâr (TL)'].sum() if not df_satislar.empty else 0
    toplam_adet = df_satislar['Adet'].sum() if not df_satislar.empty else 0
    kar_marji = (toplam_kar / toplam_ciro * 100) if toplam_ciro > 0 else 0
    
    col_m1.metric("Toplam Satış Cirosu", f"{toplam_ciro:,.2f} TL")
    col_m2.metric("Toplam Net Kâr", f"{toplam_kar:,.2f} TL")
    col_m3.metric("Kâr Marjı", f"%{kar_marji:.1f}")
    col_m4.metric("Satılan Toplam Ürün", f"{toplam_adet} Adet")
    
    st.divider()
    st.subheader("Geçmiş Satış Hareketleri")
    
    if not df_satislar.empty:
        st.dataframe(df_satislar, use_container_width=True)
        
        # Satış Raporunu İndir
        csv_satis = df_satislar.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 Satış Raporunu İndir (Excel/CSV)",
            data=csv_satis,
            file_name="satis_raporlari.csv",
            mime="text/csv"
        )
    else:
        st.info("Henüz gerçekleşen bir satış hareketi yok.")