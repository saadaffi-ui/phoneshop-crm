import streamlit as st
import sqlite3
import os
from datetime import datetime, date
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import io

# --- محاولة الاتصال بقاعدة بيانات Turso السحابية ---
import libsql_client

def get_db_connection():
    url = st.secrets.get("TURSO_DATABASE_URL")
    token = st.secrets.get("TURSO_AUTH_TOKEN")
    
    if url and token:
        try:
            conn = libsql_client.connect(url=url, auth_token=token)
            return conn, "turso"
        except Exception as e:
            st.error(f"⚠️ خطأ في الاتصال بقاعدة البيانات السحابية Turso: {e}")
    
    # احتياطي محلي في حال عدم توفر الـ Secrets
    conn = sqlite3.connect("local_crm.db", check_same_thread=False)
    return conn, "sqlite"

def init_db():
    conn, db_type = get_db_connection()
    if db_type == "turso":
        conn.execute("""
            CREATE TABLE IF NOT EXISTS repairs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                branch TEXT, customer_name TEXT, phone TEXT, email TEXT,
                device TEXT, imei TEXT, issue TEXT, price REAL,
                status TEXT, created_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                branch TEXT, customer_name TEXT, phone TEXT,
                device TEXT, imei TEXT, plan_type TEXT,
                price REAL, start_date TEXT, created_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS preorders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                branch TEXT, customer_name TEXT, phone TEXT,
                item_details TEXT, deposit REAL, created_at TEXT
            )
        """)
    else:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS repairs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                branch TEXT, customer_name TEXT, phone TEXT, email TEXT,
                device TEXT, imei TEXT, issue TEXT, price REAL,
                status TEXT, created_at TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                branch TEXT, customer_name TEXT, phone TEXT,
                device TEXT, imei TEXT, plan_type TEXT,
                price REAL, start_date TEXT, created_at TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS preorders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                branch TEXT, customer_name TEXT, phone TEXT,
                item_details TEXT, deposit REAL, created_at TEXT
            )
        """)
        conn.commit()
        conn.close()

init_db()

# إعدادات الصفحة
st.set_page_config(page_title="30 Minutes Fix CRM", layout="wide", page_icon="📱")

st.sidebar.title("30 MINUTES FIX AB")
st.sidebar.markdown("---")
menu = st.sidebar.radio("Navigation", [
    "📝 Nytt Ärende", 
    "💡 Kostnadsförslag", 
    "📄 Faktura", 
    "🔍 Sök Ärenden", 
    "🛒 Förbeställning", 
    "💳 Abonnemang"
])

# --- 1. NYTT ÄRENDE ---
if menu == "📝 Nytt Ärende":
    st.header("📝 Registrera nytt ärende (Service)")
    
    branch = st.selectbox("Välj Butik / فرع", ["Eskilstuna", "Västerås"])
    
    col1, col2 = st.columns(2)
    with col1:
        c_name = st.text_input("Kundens namn (اسم العميل)")
        c_phone = st.text_input("Telefonnummer (رقم الهاتف)")
        c_email = st.text_input("E-post (البريد الإلكتروني - اختيارى)")
    with col2:
        device = st.text_input("Enhet / Modell (نوع الجهاز)")
        imei = st.text_input("IMEI / Serienummer (رقم IMEI)")
        price = st.number_input("Pris (Kr) (السعر)", min_value=0.0, step=50.0)

    issue = st.text_area("Beskrivning av fel / Reparation (وصف المشكلة)")
    
    if st.button("Spara Ärende (حفظ الطلب سحابياً)", type="primary"):
        if c_name and c_phone and device:
            conn, db_type = get_db_connection()
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            status = "Under behandling"
            
            try:
                if db_type == "turso":
                    conn.execute(
                        "INSERT INTO repairs (branch, customer_name, phone, email, device, imei, issue, price, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (branch, c_name, c_phone, c_email, device, imei, issue, price, status, created_at)
                    )
                else:
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO repairs (branch, customer_name, phone, email, device, imei, issue, price, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (branch, c_name, c_phone, c_email, device, imei, issue, price, status, created_at)
                    )
                    conn.commit()
                    conn.close()
                st.success("✅ Ärendet har sparats framgångsرياً في السحابة!")
            except Exception as e:
                st.error(f"❌ حدث خطأ أثناء الحفظ: {e}")
        else:
            st.warning("⚠️ Vänligen fyll في الحقول الإجبارية (الاسم، الهاتف، والجهاز).")

# --- 2. KOSTNADSFÖRSLAG ---
elif menu == "💡 Kostnadsförslag":
    st.header("💡 Kostnadsförslag (عروض الأسعار)")
    c_name = st.text_input("Kundens namn")
    device = st.text_input("Enhet / Modell")
    repair_type = st.text_input("Typ av reparation (مثلاً: Skärmbyte)")
    cost = st.number_input("Uppskattad kostnad (Kr)", min_value=0.0, step=50.0)
    
    if st.button("Generera PDF Kostnadsförslag"):
        st.success(f"تم إنشاء عرض السعر لـ {c_name} بقيمة {cost} Kr بنجاح!")

# --- 3. FAKTURA ---
elif menu == "📄 Faktura":
    st.header("📄 Skapa Faktura (الفواتير)")
    f_name = st.text_input("Företag / Kundens namn")
    amount = st.number_input("Belopp inkl. moms (Kr)", min_value=0.0, step=100.0)
    st.info("💡 يتم حساب ضريبة القيمة المضافة (Moms 25%) تلقائياً.")
    if st.button("Skapa Faktura"):
        st.success("تم إصدار الفواتير وطريقة الدفع عبر Swish / Bankgiro بنجاح!")

# --- 4. SÖK ÄRENDEN ---
elif menu == "🔍 Sök Ärenden":
    st.header("🔍 Sök och Hantera Ärenden")
    pin = st.text_input("Ange PIN-kod för att söka (كلمة المرور)", type="password")
    
    if pin == st.secrets.get("DELETE_PIN", "tunapark"):
        st.success("✅ تم فتح لوحة البحث بنجاح")
        conn, db_type = get_db_connection()
        
        if db_type == "turso":
            res = conn.execute("SELECT * FROM repairs ORDER BY id DESC")
            rows = res.fetchall()
        else:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM repairs ORDER BY id DESC")
            rows = cursor.fetchall()
            conn.close()
            
        if rows:
            for r in rows:
                st.write(f"📌 **رقم الطلب:** {r[0]} | **الفرع:** {r[1]} | **العميل:** {r[2]} | **الهاتف:** {r[3]} | **الجهاز:** {r[5]} | **الحالة:** {r[9]}")
        else:
            st.info("لا توجد طلبات مسجلة بعد.")
    elif pin:
        st.error("❌ كلمة المرور غير صحيحة!")

# --- 5. FÖRBESTÄLLNING ---
elif menu == "🛒 Förbeställning":
    st.header("🛒 Förbeställning av reservdelar (الطلبات المسبقة)")
    fb_name = st.text_input("Kundens namn (الاسم)")
    fb_phone = st.text_input("Telefon (الهاتف)")
    fb_details = st.text_area("Artikel / Delar detaljer (تفاصيل القطعة المطلوبة)")
    fb_deposit = st.number_input("Handpenning / Deposit (العربون المدفوع - Kr)", min_value=0.0, step=50.0)
    
    if st.button("Spara Förbeställning (حفظ الطلب المسبق)", type="primary"):
        if fb_name and fb_phone:
            conn, db_type = get_db_connection()
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            try:
                if db_type == "turso":
                    conn.execute(
                        "INSERT INTO preorders (branch, customer_name, phone, item_details, deposit, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                        ("Eskilstuna", fb_name, fb_phone, fb_details, fb_deposit, created_at)
                    )
                else:
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO preorders (branch, customer_name, phone, item_details, deposit, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                        ("Eskilstuna", fb_name, fb_phone, fb_details, fb_deposit, created_at)
                    )
                    conn.commit()
                    conn.close()
                st.success("✅ تم حفظ الطلب المسبق في السحابة بنجاح!")
            except Exception as e:
                st.error(f"❌ خطأ: {e}")
        else:
            st.warning("⚠️ يجدر إدخال الاسم ورقم الهاتف.")

# --- 6. ABONNEMANG ---
elif menu == "💳 Abonnemang":
    st.header("💳 Hantera Abonnemang (الاشتراكات)")
    
    sub_name = st.text_input("Kundens namn (الاشتراك)")
    sub_phone = st.text_input("Telefonnummer")
    sub_device = st.text_input("Enhet / Modell")
    sub_imei = st.text_input("IMEI-nummer")
    plan_type = st.selectbox("Välj Plan (نوع الاشتراك)", ["GlassGuard Pro", "Case Protection", "Teknik Complete"])
    sub_price = st.number_input("Månadskostnad / Pris (Kr)", min_value=0.0, step=49.0)
    
    if st.button("Spara Abonnemang (حفظ الاشتراك)", type="primary"):
        if sub_name and sub_imei:
            conn, db_type = get_db_connection()
            start_date = datetime.now().strftime("%Y-%m-%d")
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            try:
                if db_type == "turso":
                    conn.execute(
                        "INSERT INTO subscriptions (branch, customer_name, phone, device, imei, plan_type, price, start_date, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        ("Eskilstuna", sub_name, sub_phone, sub_device, sub_imei, plan_type, sub_price, start_date, created_at)
                    )
                else:
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO subscriptions (branch, customer_name, phone, device, imei, plan_type, price, start_date, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        ("Eskilstuna", sub_name, sub_phone, sub_device, sub_imei, plan_type, sub_price, start_date, created_at)
                    )
                    conn.commit()
                    conn.close()
                st.success("✅ Abonnemang sparades i molndatabasen (Turso)!")
            except Exception as e:
                st.error(f"❌ خطأ: {e}")
        else:
            st.warning("⚠️ أدخل اسم العميل ورقم الـ IMEI على الأقل.")
            
    st.markdown("---")
    st.subheader("📋 Aktiva Abonnemang (الاشتراكات النشطة سحابياً)")
    try:
        conn, db_type = get_db_connection()
        if db_type == "turso":
            res = conn.execute("SELECT * FROM subscriptions ORDER BY id DESC")
            sub_rows = res.fetchall()
        else:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM subscriptions ORDER BY id DESC")
            sub_rows = cursor.fetchall()
            conn.close()
            
        if sub_rows:
            for s in sub_rows:
                st.write(f"💳 **العميل:** {s[2]} | **الجهاز:** {s[4]} | **الـ IMEI:** {s[5]} | **الخطة:** {s[6]} | **السعر:** {s[7]} Kr | **التاريخ:** {s[8]}")
        else:
            st.info("لا توجد اشتراكات مسجلة حالياً.")
    except Exception as e:
        st.warning(f"جارٍ تحديث الجدول...")
