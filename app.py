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
    # Temiz başlangıç için veritabanı adı güncellendi
    conn = sqlite3.connect("mini_erp_v2.db", check_same_thread=False)
    cursor = conn.cursor()
    
    # Kullanıcılar tablosu
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS kullanicilar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kullanici_adi TEXT UNIQUE NOT NULL,
        sifre TEXT NOT NULL
    )
    """)

    # Ürünler tablosu
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS urunler (
        urun_id INTEGER PRIMARY KEY AUTOINCREMENT,
        kullanici_id INTEGER NOT NULL,
        urun_adi TEXT NOT NULL,
        stok_miktari INTEGER NOT NULL,
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
        bakiye REAL DEFAULT 0.0,
        FOREIGN KEY (kullanici_id) REFERENCES kullanicilar (id)
    )
    """)

    # Satışlar tablosu
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS satislar (
        satis_id INTEGER PRIMARY KEY AUTOINCREMENT,
        kullanici_id INTEGER NOT NULL,
        urun_id INTEGER NOT NULL,
        musteri_id INTEGER NOT NULL,
        adet INTEGER NOT NULL,
        toplam_tutar REAL NOT NULL,
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

# Eğer giriş yapılmadıysa login ekranını göster
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
    "👥 Müşteri (Cari) Yönetimi", 
    "🛒 Satış Yap (ERP Döngüsü)", 
    "📊 Genel Raporlar"
])

# 1. SEKME: STOK & ÜRÜN YÖNETİMİ
with sekme1:
    st.header("📦 Ürün Ekle, Düzenle ve Sil")
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("➕ Yeni Ürün Tanımla")
        with st.form("urun_formu", clear_on_submit=True):
            urun_adi = st.text_input("Ürün Adı")
            stok = st.number_input("Başlangıç Stok Miktarı", min_value=0, step=1, value=10)
            fiyat = st.number_input("Birim Fiyat (TL)", min_value=0.0, step=10.0, value=100.0)
            kritik = st.number_input("Kritik Stok Uyarı Seviyesi", min_value=1, step=1, value=5)
            kaydet = st.form_submit_button("Ürünü Kaydet")
            
            if kaydet:
                if urun_adi.strip():
                    cursor.execute("""
                    INSERT INTO urunler (kullanici_id, urun_adi, stok_miktari, fiyat, kritik_seviye) 
                    VALUES (?, ?, ?, ?, ?)
                    """, (user_id, urun_adi, stok, fiyat, kritik))
                    conn.commit()
                    st.success(f"{urun_adi} başarıyla eklendi!")
                    st.rerun()
                else:
                    st.error("Lütfen bir ürün adı yazın.")

    with col2:
        st.subheader("📋 Mevcut Depo Stok Durumu")
        df_urunler = pd.read_sql_query("SELECT urun_id, urun_adi, stok_miktari, fiyat, kritik_seviye FROM urunler WHERE kullanici_id = ?", conn, params=(user_id,))
        if not df_urunler.empty:
            st.dataframe(df_urunler, use_container_width=True)
            kritikler = df_urunler[df_urunler['stok_miktari'] <= df_urunler['kritik_seviye']]
            if not kritikler.empty:
                for _, row in kritikler.iterrows():
                    st.warning(f"⚠️ **DİKKAT:** '{row['urun_adi']}' stoğu kritik seviyede! (Kalan: {row['stok_miktari']})")
        else:
            st.info("Henüz depoda ürün yok. Sol taraftan ürün ekleyebilirsin.")

# 2. SEKME: MÜŞTERİ YÖNETİMİ
with sekme2:
    st.header("👥 Cari Hesaplar")
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("➕ Yeni Müşteri Ekle")
        with st.form("musteri_formu", clear_on_submit=True):
            firma = st.text_input("Firma / Müşteri Adı")
            yetkili = st.text_input("Yetkili Kişi")
            tel = st.text_input("Telefon Numarası")
            bakiye = st.number_input("Başlangıç Borç/Bakiye (TL)", min_value=0.0, step=50.0)
            m_kaydet = st.form_submit_button("Müşteriyi Kaydet")
            
            if m_kaydet:
                if firma.strip():
                    cursor.execute("""
                    INSERT INTO musteriler (kullanici_id, firma_adi, yetkili, telefon, bakiye) 
                    VALUES (?, ?, ?, ?, ?)
                    """, (user_id, firma, yetkili, tel, bakiye))
                    conn.commit()
                    st.success(f"{firma} başarıyla kaydedildi!")
                    st.rerun()
                else:
                    st.error("Lütfen firma adı girin.")
                    
    with col2:
        st.subheader("📋 Müşteri Listesi")
        df_musteri = pd.read_sql_query("SELECT musteri_id, firma_adi, yetkili, telefon, bakiye FROM musteriler WHERE kullanici_id = ?", conn, params=(user_id,))
        if not df_musteri.empty:
            st.dataframe(df_musteri, use_container_width=True)
        else:
            st.info("Henüz kayıtlı müşteri yok.")

# 3. SEKME: SATIŞ İŞLEMİ
with sekme3:
    st.header("🛒 Satış Faturası ve Stok Çıkışı")
    df_u = pd.read_sql_query("SELECT urun_id, urun_adi, stok_miktari, fiyat FROM urunler WHERE kullanici_id = ?", conn, params=(user_id,))
    df_m = pd.read_sql_query("SELECT musteri_id, firma_adi FROM musteriler WHERE kullanici_id = ?", conn, params=(user_id,))
    
    if df_u.empty or df_m.empty:
        st.warning("⚠️ Satış yapabilmek için önce en az 1 Ürün ve 1 Müşteri tanımlamalısın!")
    else:
        with st.form("satis_formu"):
            secilen_urun_adi = st.selectbox("Satılacak Ürünü Seç", df_u['urun_adi'].tolist())
            secilen_musteri_adi = st.selectbox("Müşteriyi Seç", df_m['firma_adi'].tolist())
            
            urun_bilgi = df_u[df_u['urun_adi'] == secilen_urun_adi].iloc[0]
            stok_durumu = urun_bilgi['stok_miktari']
            birim_fiyat = urun_bilgi['fiyat']
            
            st.write(f"Mevcut Depo Stoğu: **{stok_durumu} Adet** | Satış Fiyatı: **{birim_fiyat} TL**")
            satilan_adet = st.number_input("Satılacak Adet", min_value=1, max_value=max(1, int(stok_durumu)), step=1)
            
            toplam_tutar = satilan_adet * birim_fiyat
            st.markdown(f"### Toplam Tutar: :green[{toplam_tutar:.2f} TL]")
            
            satisi_tamamla = st.form_submit_button("Satışı Onayla ve Kaydet")
            
            if satisi_tamamla:
                if satilan_adet > stok_durumu:
                    st.error("Yetersiz stok!")
                else:
                    m_id = int(df_m[df_m['firma_adi'] == secilen_musteri_adi].iloc[0]['musteri_id'])
                    u_id = int(urun_bilgi['urun_id'])
                    
                    cursor.execute("""
                    INSERT INTO satislar (kullanici_id, urun_id, musteri_id, adet, toplam_tutar) 
                    VALUES (?, ?, ?, ?, ?)
                    """, (user_id, u_id, m_id, satilan_adet, toplam_tutar))
                    
                    cursor.execute("UPDATE urunler SET stok_miktari = stok_miktari - ? WHERE urun_id = ? AND kullanici_id = ?", (satilan_adet, u_id, user_id))
                    cursor.execute("UPDATE musteriler SET bakiye = bakiye + ? WHERE musteri_id = ? AND kullanici_id = ?", (toplam_tutar, m_id, user_id))
                    
                    conn.commit()
                    st.success("✅ Satış başarıyla yapıldı! Stok düşüldü ve cari bakiye güncellendi.")
                    st.rerun()

# 4. SEKME: RAPORLAR
with sekme4:
    st.header("📊 Finansal ve Operasyonel Raporlar")
    df_satislar = pd.read_sql_query("""
    SELECT s.satis_id, u.urun_adi, m.firma_adi, s.adet, s.toplam_tutar, s.tarih 
    FROM satislar s
    JOIN urunler u ON s.urun_id = u.urun_id
    JOIN musteriler m ON s.musteri_id = m.musteri_id
    WHERE s.kullanici_id = ?
    ORDER BY s.tarih DESC
    """, conn, params=(user_id,))
    
    c1, c2, c3 = st.columns(3)
    toplam_ciro = df_satislar['toplam_tutar'].sum() if not df_satislar.empty else 0
    toplam_adet = df_satislar['adet'].sum() if not df_satislar.empty else 0
    toplam_islem = len(df_satislar)
    
    c1.metric("Toplam Satış Cirosu", f"{toplam_ciro:,.2f} TL")
    c2.metric("Satılan Toplam Ürün", f"{toplam_adet} Adet")
    c3.metric("Toplam Fatura / İşlem", f"{toplam_islem}")
    
    st.divider()
    st.subheader("Geçmiş Satış Hareketleri")
    if not df_satislar.empty:
        st.dataframe(df_satislar, use_container_width=True)
    else:
        st.info("Henüz gerçekleşen bir satış hareketi yok.")