import streamlit as st
import sqlite3
import os
from datetime import datetime, date
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import io
import pandas as pd
import base64
import threading

# --- Database Connection with Instant SQLite Fallback ---
import libsql_client

def get_db_connection():
    try:
        url = st.secrets.get("TURSO_DATABASE_URL", "")
        token = st.secrets.get("TURSO_AUTH_TOKEN", "")
        
        if url and token:
            if hasattr(libsql_client, "create_client_sync"):
                conn = libsql_client.create_client_sync(url=url, auth_token=token)
            elif hasattr(libsql_client, "create_client"):
                conn = libsql_client.create_client(url=url, auth_token=token)
            else:
                conn = libsql_client.connect(url=url, auth_token=token)
            return conn, "turso"
    except Exception:
        pass
    
    conn = sqlite3.connect("local_crm.db", check_same_thread=False)
    return conn, "sqlite"

def init_db():
    conn, db_type = get_db_connection()
    if db_type == "turso":
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS repairs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    branch TEXT, customer_name TEXT, phone TEXT, email TEXT,
                    device TEXT, imei TEXT, issue TEXT, price REAL,
                    status TEXT, employee TEXT, created_at TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    branch TEXT, customer_name TEXT, phone TEXT,
                    device TEXT, imei TEXT, plan_type TEXT,
                    price REAL, employee TEXT, start_date TEXT, created_at TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS preorders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    branch TEXT, customer_name TEXT, phone TEXT,
                    item_details TEXT, deposit REAL, employee TEXT, created_at TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS quotes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    branch TEXT, customer_name TEXT, phone TEXT, email TEXT,
                    device TEXT, issues TEXT, total REAL, profit REAL, employee TEXT, created_at TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS invoices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    branch TEXT, customer_name TEXT, phone TEXT, invoice_no TEXT,
                    amount REAL, moms REAL, currency TEXT, moms_rate TEXT, employee TEXT, created_at TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS inventory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    part_name TEXT, stock_qty INTEGER, min_limit INTEGER, branch TEXT
                )
            """)
            for col_sql in [
                "ALTER TABLE quotes ADD COLUMN profit REAL",
                "ALTER TABLE quotes ADD COLUMN employee TEXT",
                "ALTER TABLE subscriptions ADD COLUMN employee TEXT",
                "ALTER TABLE repairs ADD COLUMN employee TEXT",
                "ALTER TABLE preorders ADD COLUMN employee TEXT",
                "ALTER TABLE invoices ADD COLUMN employee TEXT"
            ]:
                try:
                    conn.execute(col_sql)
                except Exception:
                    pass
            return
        except Exception:
            pass

    conn = sqlite3.connect("local_crm.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS repairs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            branch TEXT, customer_name TEXT, phone TEXT, email TEXT,
            device TEXT, imei TEXT, issue TEXT, price REAL,
            status TEXT, employee TEXT, created_at TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            branch TEXT, customer_name TEXT, phone TEXT,
            device TEXT, imei TEXT, plan_type TEXT,
            price REAL, employee TEXT, start_date TEXT, created_at TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS preorders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            branch TEXT, customer_name TEXT, phone TEXT,
            item_details TEXT, deposit REAL, employee TEXT, created_at TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS quotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            branch TEXT, customer_name TEXT, phone TEXT, email TEXT,
            device TEXT, issues TEXT, total REAL, profit REAL, employee TEXT, created_at TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            branch TEXT, customer_name TEXT, phone TEXT, invoice_no TEXT,
            amount REAL, moms REAL, currency TEXT, moms_rate TEXT, employee TEXT, created_at TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            part_name TEXT, stock_qty INTEGER, min_limit INTEGER, branch TEXT
        )
    """)
    
    for col in ["profit", "employee"]:
        try:
            cursor.execute(f"ALTER TABLE quotes ADD COLUMN {col} TEXT")
        except Exception:
            pass
            
    for tbl in ["subscriptions", "repairs", "preorders", "quotes", "invoices"]:
        try:
            cursor.execute(f"ALTER TABLE {tbl} ADD COLUMN employee TEXT")
        except Exception:
            pass

    conn.commit()
    conn.close()

init_db()

# --- FastAPI Webhook Server for Website Integration ---
try:
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
    import uvicorn

    app = FastAPI(title="30 Minutes Phone Fix - Website Webhook API")

    class WebhookSubscription(BaseModel):
        branch: str
        customer_name: str
        phone: str
        device: str
        imei: str
        plan_type: str
        price: float
        employee: str = "Website Online"

    @app.post("/api/webhook/subscription")
    def api_save_subscription(data: WebhookSubscription):
        try:
            conn, db_type = get_db_connection()
            start_date = date.today().strftime('%Y-%m-%d')
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            if db_type == "turso":
                conn.execute(
                    "INSERT INTO subscriptions (branch, customer_name, phone, device, imei, plan_type, price, employee, start_date, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (data.branch, data.customer_name, data.phone, data.device, data.imei, data.plan_type, data.price, data.employee, start_date, created_at)
                )
            else:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO subscriptions (branch, customer_name, phone, device, imei, plan_type, price, employee, start_date, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (data.branch, data.customer_name, data.phone, data.device, data.imei, data.plan_type, data.price, data.employee, start_date, created_at)
                )
                conn.commit()
                conn.close()
            return {"status": "success", "message": "Subscription successfully saved from website!"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    def run_fastapi():
        uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")

    if 'fastapi_started' not in st.session_state:
        st.session_state['fastapi_started'] = True
        threading.Thread(target=run_fastapi, daemon=True).start()
except Exception:
    pass

st.set_page_config(page_title="30 Minutes Phone Fix CRM", layout="wide", page_icon="📱")

# --- Custom CSS Styling for Mobile & Eye-Friendly Modern Interface ---
st.markdown("""
<style>
    /* Global Background & Font Tuning */
    .stApp {
        background-color: #f7f9fa;
        color: #2c3e50;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e1e8ed;
    }
    
    /* Headers Customization */
    h1, h2, h3 {
        color: #1a252f;
        font-weight: 700;
    }
    
    /* Mobile-Friendly Adjustments for Buttons and Inputs */
    div.stButton > button {
        border-radius: 8px;
        font-weight: 600;
        padding: 0.6rem 1.2rem;
        width: 100%;
        transition: all 0.3s ease;
    }
    
    /* Success / Info Box Soft Styling */
    div.stAlert {
        border-radius: 8px;
        border: none;
    }

    /* Responsive adjustments for smaller screens */
    @media (max-width: 768px) {
        .main .block-container {
            padding: 1rem 1rem;
        }
    }
</style>
""", unsafe_allow_html=True)

COMPANY_INFO = {
    "Eskilstuna": {
        "name": "30 MINUTES PHONE FIX",
        "address": "Gunborg Nymans Väg 2, Eskilstuna",
        "phone": "0700122444",
        "org_nr": "5593708034",
        "swish": "123 407 16 76",
        "bankgiro": "5837-0354"
    },
    "Västerås": {
        "name": "30 MINUTES PHONE FIX",
        "address": "Västerås",
        "phone": "0700122444",
        "org_nr": "559537-1724",
        "swish": "123 339 15 47",
        "bankgiro": "5837-0354"
    }
}

TRANSLATIONS = {
    "Svenska": {
        "title": "30 MINUTES PHONE FIX",
        "menu_dashboard": "📊 Dashboard & Statistik",
        "menu_repair": "🛠️ Nytt Ärende / New Repair",
        "menu_quote": "💡 Kostnadsförslag / Quote",
        "menu_invoice": "📄 Faktura / Invoice",
        "menu_preorder": "🛒 Förbeställning / Pre-order",
        "menu_sub": "💳 Abonnemang / Subscriptions",
        "menu_inventory": "📦 Lager & Reservdelar / Inventory",
        "menu_history": "🖨️ Dokument & Historik / Print Hub",
        "menu_datacenter": "🔍 Data Center & Sök / Search & Data",
        "branch_select": "Välj Butik / Select Branch",
        "phone": "Telefonnummer / Phone Number",
        "customer_name": "Kundens namn / Customer Name",
        "employee": "Handläggare / Säljare (Employee Name)",
        "email": "E-post / Email (Valfritt / Optional)",
        "device": "Enhet / Modell / Device Model",
        "imei": "IMEI / Serienummer / IMEI / Serial Number",
        "price": "Pris / Price",
        "issue": "Beskrivning av fel / Issue Description",
        "save_repair": "Spara Ärende / Save Repair",
        "success_repair": "✅ Ärendet har sparats! / Repair saved successfully!",
        "dash_header": "📊 Dashboard & Statistik",
        "quote_header": "💡 Kostnadsförslag & Vinstberäkning",
        "invoice_header": "📄 Professionell Faktura",
        "preorder_header": "🛒 Förbeställning av reservdelar",
        "sub_header": "💳 IMEI-kopplade Abonnemang & Villkor",
        "inv_header": "📦 Lager & Reservdelar",
        "history_header": "🖨️ Visa och Skriv ut tidigare sparade dokument",
        "datacenter_header": "🔍 Data Center, Sök, Export & Hantering"
    },
    "English": {
        "title": "30 MINUTES PHONE FIX",
        "menu_dashboard": "📊 Dashboard & Analytics",
        "menu_repair": "🛠️ New Repair",
        "menu_quote": "💡 Quote",
        "menu_invoice": "📄 Invoice",
        "menu_preorder": "🛒 Pre-order",
        "menu_sub": "💳 Subscriptions",
        "menu_inventory": "📦 Inventory & Parts",
        "menu_history": "🖨️ Print Hub",
        "menu_datacenter": "🔍 Data Center & Search",
        "branch_select": "Select Branch",
        "phone": "Phone Number",
        "customer_name": "Customer Name",
        "employee": "Employee Name",
        "email": "Email (Optional)",
        "device": "Device Model",
        "imei": "IMEI / Serial Number",
        "price": "Price",
        "issue": "Issue Description",
        "save_repair": "Save Repair",
        "success_repair": "✅ Repair saved successfully!",
        "dash_header": "📊 Dashboard & Analytics",
        "quote_header": "💡 Price Quotation & Profit",
        "invoice_header": "📄 Professional Invoice",
        "preorder_header": "🛒 Spare Parts Pre-order",
        "sub_header": "💳 IMEI Subscriptions & Terms",
        "inv_header": "📦 Inventory Management",
        "history_header": "🖨️ Print & History Hub",
        "datacenter_header": "🔍 Search & Management"
    },
    "العربية (Arabic)": {
        "title": "صيانة الهواتف 30 دقيقة",
        "menu_dashboard": "📊 لوحة المؤشرات والإحصاءات العامة",
        "menu_repair": "🛠️ تسجيل إصلاح جديد",
        "menu_quote": "💡 عرض سعر وحساب الأرباح",
        "menu_invoice": "📄 فاتورة رسمية",
        "menu_preorder": "🛒 طلب مسبق لقطع الغيار",
        "menu_sub": "💳 الاشتراكات وضمان IMEI",
        "menu_inventory": "📦 إدارة المخزون وقطع الغيار",
        "menu_history": "🖨️ مركز الطباعة والأرشيف",
        "menu_datacenter": "🔍 إدارة البيانات والبحث الشامل",
        "branch_select": "اختر الفرع",
        "phone": "رقم الهاتف",
        "customer_name": "اسم العميل",
        "employee": "اسم الموظف المسؤول (Employee Name)",
        "email": "البريد الإلكتروني (اختياري)",
        "device": "نوع وطراز الجهاز",
        "imei": "رقم الـ IMEI أو الرقم التسلسلي",
        "price": "السعر",
        "issue": "وصف العطل أو الإصلاح المطلوب",
        "save_repair": "حفظ بيانات الإصلاح",
        "success_repair": "✅ تم حفظ طلب الإصلاح بنجاح!",
        "dash_header": "📊 لوحة المؤشرات والإحصاءات العامة",
        "quote_header": "💡 عرض سعر وحاسبة الأرباح",
        "invoice_header": "📄 الفاتورة الرسمية للمحل",
        "preorder_header": "🛒 طلب مسبق لقطع الغيار",
        "sub_header": "💳 الاشتراكات وضمان IMEI",
        "inv_header": "📦 إدارة المخزون وقطع الغيار",
        "history_header": "🖨️ مركز الطباعة والأرشيف",
        "datacenter_header": "🔍 إدارة البيانات والبحث الشامل"
    }
}

st.sidebar.title("📱 30 Minutes Phone Fix")
if os.path.exists("logo.png"):
    st.sidebar.image("logo.png", use_container_width=True)

lang_choice = st.sidebar.selectbox("🌐 Välj Språk / Language / لغة الواجهة", ["Svenska", "English", "العربية (Arabic)"])
t = TRANSLATIONS[lang_choice]

st.sidebar.markdown("**Eskilstuna & Västerås**")
st.sidebar.markdown("---")

if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

if not st.session_state['authenticated']:
    try:
        default_pin = st.secrets.get("DELETE_PIN", "tunapark")
    except Exception:
        default_pin = "tunapark"
        
    sidebar_pin = st.sidebar.text_input("🔑 System Login / Inloggning", type="password")
    remember_device = st.sidebar.checkbox("💾 تذكرني على هذا الجهاز / Remember on this device")
    
    if sidebar_pin == default_pin:
        st.session_state['authenticated'] = True
        if remember_device:
            st.session_state['remember_me'] = True
        st.sidebar.success("✅ System Unlocked / Systemet upplåst")
        st.rerun()
    elif sidebar_pin:
        st.sidebar.error("❌ Fel PIN-kod / Incorrect PIN")

if not st.session_state.get('authenticated') and st.session_state.get('remember_me'):
    st.session_state['authenticated'] = True

if not st.session_state['authenticated']:
    st.title("🔒 30 Minutes Phone Fix CRM - Locked / Låst")
    st.info("Please enter the system PIN in the sidebar to log in. / Ange PIN-kod i sidofältet för att logga in.")
    st.stop()

st.sidebar.success("✅ Logged In / Inloggad")
if st.sidebar.button("🔒 Log Out / Logga ut"):
    st.session_state['authenticated'] = False
    st.session_state['remember_me'] = False
    st.rerun()

menu = st.sidebar.radio("Navigation / القائمة الرئيسية", [
    t["menu_dashboard"],
    t["menu_repair"], 
    t["menu_quote"], 
    t["menu_invoice"], 
    t["menu_preorder"], 
    t["menu_sub"],
    t["menu_inventory"],
    t["menu_history"],
    t["menu_datacenter"]
])

def display_pdf_preview(pdf_buffer, file_name="document.pdf"):
    pdf_buffer.seek(0)
    pdf_bytes = pdf_buffer.read()
    b64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
    
    st.success("✅ Dokumentet är redo! / Document ready!")
    
    st.download_button(
        label="📥 Ladda ner PDF / Save PDF",
        data=pdf_bytes,
        file_name=file_name,
        mime="application/pdf",
        type="primary"
    )
    
    st.markdown("---")
    st.markdown("### 👁️ Förhandsgranskning & Utskrift / Preview")
    
    pdf_display = f"""
    <object data="data:application/pdf;base64,{b64_pdf}" type="application/pdf" width="100%" height="600px" style="border: 1px solid #ccc; border-radius: 8px;">
        <embed src="data:application/pdf;base64,{b64_pdf}" type="application/pdf" width="100%" height="600px" />
        <p style="padding: 20px; text-align: center;">Din webbläsare stöder inte direkt inbäddad PDF-visning. Använd knappen ovan för att ladda ner filen.</p>
    </object>
    """
    st.markdown(pdf_display, unsafe_allow_html=True)

def generate_pdf_from_record(record_type, data, comp_info):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    branch = data.get('branch', 'Eskilstuna')
    comp = comp_info.get(branch, comp_info['Eskilstuna'])
    employee_name = data.get('employee', 'Ej angiven / Not specified')
    currency = data.get('currency', 'SEK')
    moms_rate_str = data.get('moms_rate', '25%')

    # Draw Logo in PDF if logo.png exists[cite: 1]
    if os.path.exists("logo.png"):
        try:
            p.drawImage("logo.png", 50, height - 75, width=90, height=50, preserveAspectRatio=True, mask='auto')
        except Exception:
            pass
            
    p.setFont("Helvetica-Bold", 14)
    p.drawString(150, height - 40, comp["name"])
    
    p.setFont("Helvetica", 9)
    p.drawString(150, height - 55, f"Adress / Address: {comp['address']}")
    p.drawString(150, height - 70, f"Tel: {comp['phone']} | Org.nr: {comp['org_nr']}")
    
    p.setLineWidth(1)
    p.line(50, height - 85, width - 50, height - 85)

    if record_type == "quote":
        p.setFont("Helvetica-Bold", 12)
        p.drawString(50, height - 110, "KOSTNADSFÖRSLAG / PRICE QUOTATION")
        
        p.setFont("Helvetica", 10)
        p.drawString(50, height - 135, f"Datum / Date: {data.get('created_at', '')}")
        p.drawString(300, height - 135, f"Handläggare / Employee: {employee_name}")
        p.drawString(50, height - 155, f"Kund / Customer: {data.get('customer_name', '')}")
        p.drawString(50, height - 175, f"Telefon / Phone: {data.get('phone', '')}")
        p.drawString(300, height - 155, f"Enhet / Device: {data.get('device', '')}")
        
        p.setFillColorRGB(0.9, 0.9, 0.9)
        p.rect(50, height - 215, width - 100, 20, fill=1, stroke=0)
        p.setFillColorRGB(0, 0, 0)
        p.setFont("Helvetica-Bold", 9)
        p.drawString(60, height - 208, "Beskrivning av reparation / Repair Description")
        p.drawString(400, height - 208, f"Belopp / Amount ({currency})")
        
        p.setFont("Helvetica", 10)
        y_pos = height - 245
        issues_text = data.get('issues', '')
        p.drawString(60, y_pos, f"- {issues_text}")
        
        total_val = data.get('total', 0)
        p.drawString(400, y_pos, f"{total_val:.2f} {currency}")
        
        p.line(50, height - 320, width - 50, height - 320)
        p.setFont("Helvetica-Bold", 11)
        p.drawString(300, height - 345, f"Att betala / Total: {total_val:.2f} {currency}")
        p.setFont("Helvetica", 8)
        p.drawString(300, height - 360, f"(Inkl. moms / Incl. VAT)")
        
        p.setFont("Helvetica-Oblique", 8)
        p.drawString(50, height - 420, "* Detta kostnadsförslag är giltigt i 30 dagar från utfärdandedatumet.")
        p.drawString(50, 40, f"Betalning via Swish: {comp['swish']} | Bankgiro: {comp['bankgiro']}")

    elif record_type == "invoice":
        p.setFont("Helvetica-Bold", 12)
        p.drawString(50, height - 110, "FAKTURA / INVOICE")
        
        p.setFont("Helvetica", 10)
        p.drawString(50, height - 135, f"Fakturanr / Invoice No: {data.get('invoice_no', '')}")
        p.drawString(300, height - 135, f"Datum / Date: {data.get('created_at', '')}")
        p.drawString(50, height - 155, f"Kund / Customer: {data.get('customer_name', '')}")
        p.drawString(300, height - 155, f"Handläggare / Employee: {employee_name}")
        p.drawString(50, height - 175, f"Telefon / Phone: {data.get('phone', '')}")
        
        p.setFillColorRGB(0.9, 0.9, 0.9)
        p.rect(50, height - 215, width - 100, 20, fill=1, stroke=0)
        p.setFillColorRGB(0, 0, 0)
        p.setFont("Helvetica-Bold", 9)
        p.drawString(60, height - 208, "Beskrivning / Description")
        p.drawString(400, height - 208, f"Belopp / Amount ({currency})")
        
        y_pos = height - 245
        amount_val = data.get('amount', 0)
        moms_val = data.get('moms', 0)
        netto_val = amount_val - moms_val
        
        p.setFont("Helvetica", 10)
        p.drawString(60, y_pos, f"{data.get('item_desc', 'Reparation och reservdelar / Repair & Parts')}")
        p.drawString(400, y_pos, f"{netto_val:.2f} {currency}")
        
        p.line(50, height - 320, width - 50, height - 320)
        p.setFont("Helvetica", 9)
        p.drawString(300, height - 340, f"Netto / Net: {netto_val:.2f} {currency}")
        p.drawString(300, height - 360, f"Moms / VAT ({moms_rate_str}): {moms_val:.2f} {currency}")
        p.setFont("Helvetica-Bold", 11)
        p.drawString(300, height - 385, f"Att betala / Total: {amount_val:.2f} {currency}")
        
        p.setFont("Helvetica", 9)
        p.drawString(50, 60, f"Betalning sker via Swish: {comp['swish']} eller Bankgiro: {comp['bankgiro']}")
        p.drawString(50, 40, f"Företaget är godkänt för F-skatt | Org.nr: {comp['org_nr']}")

    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

# --- 0. DASHBOARD & ANALYTICS ---
if menu == t["menu_dashboard"]:
    st.header(t["dash_header"])
    branch_filter = st.selectbox("اختر الفرع / Select Branch", ["Alla / All", "Eskilstuna", "Västerås"])
    
    conn, db_type = get_db_connection()
    try:
        if db_type == "turso":
            rep_count = conn.execute("SELECT COUNT(*) FROM repairs").fetchone()[0]
            quote_count = conn.execute("SELECT COUNT(*) FROM quotes").fetchone()[0]
            inv_count = conn.execute("SELECT COUNT(*) FROM invoices").fetchone()[0]
            total_prof = conn.execute("SELECT SUM(profit) FROM quotes").fetchone()[0] or 0.0
        else:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM repairs")
            rep_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM quotes")
            quote_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM invoices")
            inv_count = cursor.fetchone()[0]
            cursor.execute("SELECT SUM(profit) FROM quotes")
            total_prof = cursor.fetchone()[0] or 0.0
    except Exception:
        rep_count, quote_count, inv_count, total_prof = 0, 0, 0, 0.0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📝 الإصلاحات", rep_count)
    col2.metric("💡 الأسعار", quote_count)
    col3.metric("📄 الفواتير", inv_count)
    col4.metric("📈 الأرباح", f"{total_prof:.2f} Kr")

    st.markdown("---")
    st.subheader("🛠️ إدارة حالة الأجهزة السريعة / Quick Repair Status Update")
    
    try:
        if db_type == "turso":
            active_repairs = conn.execute("SELECT id, customer_name, device, status, employee FROM repairs ORDER BY id DESC LIMIT 10").fetchall()
        else:
            cursor = conn.cursor()
            cursor.execute("SELECT id, customer_name, device, status, employee FROM repairs ORDER BY id DESC LIMIT 10")
            active_repairs = cursor.fetchall()
            
        if active_repairs:
            for rep in active_repairs:
                r_id, r_cust, r_dev, r_status, r_emp = rep
                st.markdown(f"**ID: {r_id}** | 👤 {r_cust} ({r_dev}) [الموظف: {r_emp or '-'}]")
                col_a, col_b = st.columns([2, 1])
                new_st = col_a.selectbox(f"الحالة #{r_id}", ["Under behandling / In Progress", "Väntar på reservdel / Waiting Part", "Klar att hämta / Ready", "Avslutad / Completed"], key=f"st_{r_id}")
                if col_b.button("تحديث", key=f"btn_st_{r_id}"):
                    if db_type == "turso":
                        conn.execute("UPDATE repairs SET status = ? WHERE id = ?", (new_st, r_id))
                    else:
                        cursor = conn.cursor()
                        cursor.execute("UPDATE repairs SET status = ? WHERE id = ?", (new_st, r_id))
                        conn.commit()
                    st.success(f"تم التحديث #{r_id}!")
                    st.rerun()
                st.markdown("---")
        else:
            st.info("لا توجد إصلاحات مسجلة حالياً.")
    except Exception as e:
        st.error(f"خطأ في تحميل الإصلاحات: {e}")

# --- 1. NYTT ÄRENDE / NEW REPAIR ---
elif menu == t["menu_repair"]:
    st.header(t["menu_repair"])
    branch = st.selectbox(t["branch_select"], ["Eskilstuna", "Västerås"])
    
    employee_name = st.text_input(t["employee"])
    c_phone = st.text_input(t["phone"])
    
    auto_name, auto_email = "", ""
    if c_phone and len(c_phone) > 5:
        conn, db_type = get_db_connection()
        try:
            if db_type == "turso":
                res = conn.execute("SELECT customer_name, email FROM repairs WHERE phone = ? LIMIT 1", (c_phone,)).fetchone()
            else:
                cursor = conn.cursor()
                cursor.execute("SELECT customer_name, email FROM repairs WHERE phone = ? LIMIT 1", (c_phone,))
                res = cursor.fetchone()
            if res:
                auto_name, auto_email = res[0], res[1] or ""
                st.info(f"💡 Tidigare kund hittad! **{auto_name}**")
        except Exception:
            pass

    c_name = st.text_input(t["customer_name"], value=auto_name)
    c_email = st.text_input(t["email"], value=auto_email)
    device = st.text_input(t["device"])
    imei = st.text_input(t["imei"])
    
    st.markdown("⚡ **قوالب الأعطال السريعة المتعددة / Multi-Issue Quick Templates:**")
    
    selected_issues = []
    if st.checkbox("📱 تغيير شاشة أصلي (Screen Replacement)"):
        selected_issues.append("Skärmbyte / Screen Replacement")
    if st.checkbox("🔋 استبدال بطارية جديدة (Battery Replacement)"):
        selected_issues.append("Batteribyte / Battery Replacement")
    if st.checkbox("🔌 إصلاح / تغيير منفذ الشحن (Charging Port)"):
        selected_issues.append("Laddport / Charging Port Repair")
    if st.checkbox("📷 إصلاح الكاميرا الأمامية/الخلفية (Camera)"):
        selected_issues.append("Kamera / Camera Repair")
    if st.checkbox("💧 معالجة أضرار المياه والسوائل (Water Damage)"):
        selected_issues.append("Vattenskada / Water Damage Service")
    if st.checkbox("🔊 إصلاح السماعة أو الميكروفون (Speaker/Mic)"):
        selected_issues.append("Ljud / Speaker & Mic Repair")
    if st.checkbox("🪟 تغيير الزجاج الخلفي (Back Glass Damaged)"):
        selected_issues.append("Baksida kraschad / Back Glass Damaged")

    combined_template_str = ", ".join(selected_issues)

    price = st.number_input(t["price"], min_value=0.0, step=50.0)
    issue = st.text_area(t["issue"], value=combined_template_str)
    
    if st.button(t["save_repair"], type="primary"):
        if c_name and c_phone and device and employee_name:
            conn, db_type = get_db_connection()
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            status = "Under behandling / In Progress"
            
            try:
                if db_type == "turso":
                    try:
                        conn.execute(
                            "INSERT INTO repairs (branch, customer_name, phone, email, device, imei, issue, price, status, employee, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (branch, c_name, c_phone, c_email, device, imei, issue, price, status, employee_name, created_at)
                        )
                    except Exception:
                        local_conn = sqlite3.connect("local_crm.db", check_same_thread=False)
                        local_cursor = local_conn.cursor()
                        local_cursor.execute(
                            "INSERT INTO repairs (branch, customer_name, phone, email, device, imei, issue, price, status, employee, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (branch, c_name, c_phone, c_email, device, imei, issue, price, status, employee_name, created_at)
                        )
                        local_conn.commit()
                        local_conn.close()
                else:
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO repairs (branch, customer_name, phone, email, device, imei, issue, price, status, employee, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (branch, c_name, c_phone, c_email, device, imei, issue, price, status, employee_name, created_at)
                    )
                    conn.commit()
                    conn.close()
                st.success(t["success_repair"])
            except Exception as e:
                st.error(f"❌ Fel vid sparande / Error: {e}")
        else:
            st.warning("⚠️ يرجى تعبئة الحقول الأساسية بما فيها اسم الموظف. / Please fill required fields including Employee name.")

# --- 2. KOSTNADSFÖRSLAG / QUOTE ---
elif menu == t["menu_quote"]:
    st.header(t["quote_header"])
    branch = st.selectbox(t["branch_select"], ["Eskilstuna", "Västerås"])
    comp = COMPANY_INFO[branch]
    
    employee_name = st.text_input(t["employee"])
    c_name = st.text_input(t["customer_name"])
    c_phone = st.text_input(t["phone"])
    device = st.text_input(t["device"])
    imei = st.text_input(t["imei"])

    st.markdown("---")
    st.subheader("🛠️ Välj Fel / Reparationer")
    
    issues_list = []
    total_price = 0.0
    total_cost = 0.0

    has_screen = st.checkbox("📱 Skärmbyte / Damaged Screen", key="chk_scr")
    if has_screen:
        p_screen = st.number_input("Pris: Skärmbyte", min_value=0.0, step=50.0, value=0.0, key="p_scr")
        c_screen = st.number_input("Inköpskostnad del / Part Cost", min_value=0.0, step=10.0, value=0.0, key="c_scr")
        issues_list.append(f"Skärmbyte / Screen: {p_screen}")
        total_price += p_screen
        total_cost += c_screen

    has_battery = st.checkbox("🔋 Batteribyte / Battery Replacement", key="chk_bat")
    if has_battery:
        p_bat = st.number_input("Pris: Batteri", min_value=0.0, step=50.0, value=0.0, key="p_bat")
        c_bat = st.number_input("Inköpskostnad del / Part Cost", min_value=0.0, step=10.0, value=0.0, key="c_bat")
        issues_list.append(f"Batteribyte / Battery: {p_bat}")
        total_price += p_bat
        total_cost += c_bat

    has_charging = st.checkbox("🔌 Laddport / Charging Port", key="chk_chg")
    if has_charging:
        p_chg = st.number_input("Pris: Laddport", min_value=0.0, step=50.0, value=0.0, key="p_chg")
        c_chg = st.number_input("Inköpskostnad del / Part Cost", min_value=0.0, step=10.0, value=0.0, key="c_chg")
        issues_list.append(f"Laddport / Charging Port: {p_chg}")
        total_price += p_chg
        total_cost += c_chg

    custom_issue = st.text_input("Övrigt fel / Custom Issue")
    if custom_issue:
        p_cust = st.number_input("Pris för övrigt", min_value=0.0, step=50.0, value=0.0, key="p_cust")
        c_cust = st.number_input("Inköpskostnad del", min_value=0.0, step=10.0, value=0.0, key="c_cust")
        issues_list.append(f"{custom_issue}: {p_cust}")
        total_price += p_cust
        total_cost += c_cust

    net_profit = total_price - total_cost

    st.markdown("---")
    st.markdown(f"### 💰 **Total Summa: {total_price:.2f} SEK**")
    st.markdown(f"📈 **Beräknad Vinst: {net_profit:.2f} SEK**")

    if st.button("Spara & Generera Kostnadsförslag PDF", type="primary"):
        if c_name and device and issues_list and employee_name:
            conn, db_type = get_db_connection()
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            issues_str = ", ".join(issues_list)
            
            try:
                if db_type == "turso":
                    try:
                        conn.execute(
                            "INSERT INTO quotes (branch, customer_name, phone, email, device, issues, total, profit, employee, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (branch, c_name, c_phone, "", device, issues_str, total_price, net_profit, employee_name, created_at)
                        )
                    except Exception:
                        local_conn = sqlite3.connect("local_crm.db", check_same_thread=False)
                        local_cursor = local_conn.cursor()
                        local_cursor.execute(
                            "INSERT INTO quotes (branch, customer_name, phone, email, device, issues, total, profit, employee, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (branch, c_name, c_phone, "", device, issues_str, total_price, net_profit, employee_name, created_at)
                        )
                        local_conn.commit()
                        local_conn.close()
                else:
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO quotes (branch, customer_name, phone, email, device, issues, total, profit, employee, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (branch, c_name, c_phone, "", device, issues_str, total_price, net_profit, employee_name, created_at)
                    )
                    conn.commit()
                    conn.close()
                st.success("✅ Kostnadsförslag sparat i databasen!")
            except Exception as e:
                st.error(f"❌ Fel vid sparande / Error: {e}")

            record_data = {
                "branch": branch,
                "customer_name": c_name,
                "phone": c_phone,
                "device": device,
                "issues": issues_str,
                "total": total_price,
                "currency": "SEK",
                "employee": employee_name,
                "created_at": date.today().strftime('%Y-%m-%d')
            }
            pdf_buf = generate_pdf_from_record("quote", record_data, COMPANY_INFO)
            st.session_state['last_quote_pdf'] = pdf_buf
            safe_dev = device.replace(' ', '_')
            safe_cust = c_name.replace(' ', '_')
            st.session_state['last_quote_filename'] = f"Kostnadsförslag_{safe_dev}_-_{safe_cust}.pdf"
            st.success("✅ PDF skapades!")

    if 'last_quote_pdf' in st.session_state:
        st.markdown("---")
        st.subheader("👀 Förhandsgranska och Skriv ut")
        display_pdf_preview(st.session_state['last_quote_pdf'], file_name=st.session_state.get('last_quote_filename', 'kostnadsforslag.pdf'))

# --- 3. FAKTURA / INVOICE ---
elif menu == t["menu_invoice"]:
    st.header(t["invoice_header"])
    branch = st.selectbox(t["branch_select"], ["Eskilstuna", "Västerås"])
    comp = COMPANY_INFO[branch]
    
    currency_choice = st.selectbox("💱 Valuta", ["SEK", "EUR"])
    moms_choice = st.selectbox("📊 Moms", ["25%", "12%", "6%", "0%"])
    employee_name = st.text_input(t["employee"])
    invoice_no = st.text_input("Fakturanummer", value="FAK-2026-001")

    f_name = st.text_input("Kundens namn / Företag")
    f_phone_inv = st.text_input("Telefonnummer")
    invoice_date = st.date_input("Fakturadatum", value=date.today())

    item_desc = st.text_input("Beskrivning", value="Reparation och reservdelar")
    item_qty = st.number_input("Antal", min_value=1, value=1)
    item_price = st.number_input("Pris inkl. moms", min_value=0.0, step=50.0)
    
    total_amount = item_qty * item_price
    moms_rate_val = 0.25 if "25%" in moms_choice else (0.12 if "12%" in moms_choice else (0.06 if "6%" in moms_choice else 0.0))
    moms_div = 1.25 if "25%" in moms_choice else (1.12 if "12%" in moms_choice else (1.06 if "6%" in moms_choice else 1.0))
    
    netto = total_amount / moms_div if moms_div > 1 else total_amount
    moms = total_amount - netto

    st.markdown(f"**Att betala:** {total_amount:.2f} {currency_choice}")
    
    if st.button("Spara & Skapa Faktura PDF", type="primary"):
        if f_name and employee_name:
            conn, db_type = get_db_connection()
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            try:
                if db_type == "turso":
                    try:
                        conn.execute(
                            "INSERT INTO invoices (branch, customer_name, phone, invoice_no, amount, moms, currency, moms_rate, employee, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (branch, f_name, f_phone_inv, invoice_no, total_amount, moms, currency_choice, moms_choice, employee_name, created_at)
                        )
                    except Exception:
                        local_conn = sqlite3.connect("local_crm.db", check_same_thread=False)
                        local_cursor = local_conn.cursor()
                        local_cursor.execute(
                            "INSERT INTO invoices (branch, customer_name, phone, invoice_no, amount, moms, currency, moms_rate, employee, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (branch, f_name, f_phone_inv, invoice_no, total_amount, moms, currency_choice, moms_choice, employee_name, created_at)
                        )
                        local_conn.commit()
                        local_conn.close()
                else:
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO invoices (branch, customer_name, phone, invoice_no, amount, moms, currency, moms_rate, employee, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (branch, f_name, f_phone_inv, invoice_no, total_amount, moms, currency_choice, moms_choice, employee_name, created_at)
                    )
                    conn.commit()
                    conn.close()
                st.success("✅ Faktura sparad!")
            except Exception as e:
                st.error(f"❌ Fel: {e}")

            record_data = {
                "branch": branch,
                "customer_name": f_name,
                "phone": f_phone_inv,
                "invoice_no": invoice_no,
                "amount": total_amount,
                "moms": moms,
                "currency": currency_choice,
                "moms_rate": moms_choice,
                "item_desc": item_desc,
                "employee": employee_name,
                "created_at": invoice_date.strftime('%Y-%m-%d')
            }
            pdf_buf = generate_pdf_from_record("invoice", record_data, COMPANY_INFO)
            st.session_state['last_invoice_pdf'] = pdf_buf
            safe_cust = f_name.replace(' ', '_')
            st.session_state['last_invoice_filename'] = f"Faktura_{invoice_no}_-_{safe_cust}.pdf"
            st.success("✅ Faktura PDF skapades!")

    if 'last_invoice_pdf' in st.session_state:
        st.markdown("---")
        display_pdf_preview(st.session_state['last_invoice_pdf'], file_name=st.session_state.get('last_invoice_filename', 'faktura.pdf'))

# --- 4. FÖRBÄLLNING / PRE-ORDER ---
elif menu == t["menu_preorder"]:
    st.header(t["preorder_header"])
    branch = st.selectbox(t["branch_select"], ["Eskilstuna", "Västerås"])
    employee_name = st.text_input(t["employee"])
    fb_name = st.text_input(t["customer_name"])
    fb_phone = st.text_input(t["phone"])
    fb_details = st.text_area("Artikel / Delar detaljer")
    fb_deposit = st.number_input("Handpenning", min_value=0.0, step=50.0)
    
    if st.button("Spara Förbeställning", type="primary"):
        if fb_name and fb_phone and employee_name:
            conn, db_type = get_db_connection()
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            try:
                if db_type == "turso":
                    try:
                        conn.execute(
                            "INSERT INTO preorders (branch, customer_name, phone, item_details, deposit, employee, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                            (branch, fb_name, fb_phone, fb_details, fb_deposit, employee_name, created_at)
                        )
                    except Exception:
                        local_conn = sqlite3.connect("local_crm.db", check_same_thread=False)
                        local_cursor = local_conn.cursor()
                        local_cursor.execute(
                            "INSERT INTO preorders (branch, customer_name, phone, item_details, deposit, employee, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                            (branch, fb_name, fb_phone, fb_details, fb_deposit, employee_name, created_at)
                        )
                        local_conn.commit()
                        local_conn.close()
                else:
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO preorders (branch, customer_name, phone, item_details, deposit, employee, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (branch, fb_name, fb_phone, fb_details, fb_deposit, employee_name, created_at)
                    )
                    conn.commit()
                    conn.close()
                st.success("✅ Förbeställning sparad!")
            except Exception as e:
                st.error(f"❌ Fel: {e}")
        else:
            st.warning("⚠️ يرجى تعبئة الحقول المطلوبة.")

# --- 5. ABONNEMANG / SUBSCRIPTIONS ---
elif menu == t["menu_sub"]:
    st.header(t["sub_header"])
    
    employee_name = st.text_input(t["employee"])
    sub_imei = st.text_input(t["imei"])
    sub_device = st.text_input(t["device"])
    branch = st.selectbox(t["branch_select"], ["Eskilstuna", "Västerås"])
    sub_name = st.text_input(t["customer_name"])
    sub_phone = st.text_input(t["phone"])

    plan_choice = st.selectbox("Välj Plan", [
        "Glass Protection Abonnemang (99 SEK/mån)",
        "Case / Cover Abonnemang (399 SEK start + 99 SEK/mån)",
        "Teknik, Mjukvara & Virus Help (99 SEK/mån)",
        "Phone Shield Total Club (149 SEK/mån)"
    ])
    
    sub_price = 149.0 if "Phone Shield Total Club" in plan_choice else 99.0
    agree_terms = st.checkbox("Kunden godkänner avtalsvillkoren & IMEI-regler")

    if st.button("Spara Abonnemang", type="primary"):
        if sub_imei and sub_name and agree_terms and employee_name:
            conn, db_type = get_db_connection()
            start_date = datetime.now().strftime("%Y-%m-%d")
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            try:
                if db_type == "turso":
                    try:
                        conn.execute(
                            "INSERT INTO subscriptions (branch, customer_name, phone, device, imei, plan_type, price, employee, start_date, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (branch, sub_name, sub_phone, sub_device, sub_imei, plan_choice, sub_price, employee_name, start_date, created_at)
                        )
                    except Exception:
                        local_conn = sqlite3.connect("local_crm.db", check_same_thread=False)
                        local_cursor = local_conn.cursor()
                        local_cursor.execute(
                            "INSERT INTO subscriptions (branch, customer_name, phone, device, imei, plan_type, price, employee, start_date, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (branch, sub_name, sub_phone, sub_device, sub_imei, plan_choice, sub_price, employee_name, start_date, created_at)
                        )
                        local_conn.commit()
                        local_conn.close()
                else:
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO subscriptions (branch, customer_name, phone, device, imei, plan_type, price, employee, start_date, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (branch, sub_name, sub_phone, sub_device, sub_imei, plan_choice, sub_price, employee_name, start_date, created_at)
                    )
                    conn.commit()
                    conn.close()
                st.success("✅ Abonnemang sparat!")
            except Exception as e:
                st.error(f"❌ Fel: {e}")
        else:
            st.warning("⚠️ يرجى التأكد من تعبئة كافة الحقول والموافقة على الشروط.")

# --- 6. LAGER & RESERVDELAR / INVENTORY ---
elif menu == t["menu_inventory"]:
    st.header(t["inv_header"])
    branch = st.selectbox(t["branch_select"], ["Eskilstuna", "Västerås"])
    
    conn, db_type = get_db_connection()
    
    st.subheader("➕ Lägg till ny reservdel")
    new_part_name = st.text_input("Artikelnamn (t.ex. iPhone 15 Skärm)")
    new_part_qty = st.number_input("Antal i lager", min_value=0, step=1, value=5)
    new_part_min = st.number_input("Varningsgräns", min_value=0, step=1, value=2)
    
    if st.button("Spara till lager", type="primary"):
        if new_part_name:
            try:
                if db_type == "turso":
                    try:
                        conn.execute("INSERT INTO inventory (part_name, stock_qty, min_limit, branch) VALUES (?, ?, ?, ?)", (new_part_name, new_part_qty, new_part_min, branch))
                    except Exception:
                        local_conn = sqlite3.connect("local_crm.db", check_same_thread=False)
                        local_cursor = local_conn.cursor()
                        local_cursor.execute("INSERT INTO inventory (part_name, stock_qty, min_limit, branch) VALUES (?, ?, ?, ?)", (new_part_name, new_part_qty, new_part_min, branch))
                        local_conn.commit()
                        local_conn.close()
                else:
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO inventory (part_name, stock_qty, min_limit, branch) VALUES (?, ?, ?, ?)", (new_part_name, new_part_qty, new_part_min, branch))
                    conn.commit()
                    conn.close()
                st.success("✅ تم إضافة القطعة!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Fel: {e}")
        else:
            st.warning("⚠️ أدخل اسم القطعة.")

# --- 7. DOKUMENT & HISTORIK / PRINT HUB ---
elif menu == t["menu_history"]:
    st.header(t["history_header"])
    
    category = st.selectbox("Välj Kategori", ["💡 Kostnadsförslag / Quotes", "📄 Fakturor / Invoices"])
    conn, db_type = get_db_connection()
    table_name = "quotes" if "Quotes" in category else "invoices"
    record_type = "quote" if "Quotes" in category else "invoice"
    
    try:
        if db_type == "turso":
            try:
                rows = conn.execute(f"SELECT * FROM {table_name} ORDER BY id DESC LIMIT 20").fetchall()
                columns_res = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
                col_names = [c[1] for c in columns_res]
                df = pd.DataFrame(rows, columns=col_names) if rows else pd.DataFrame()
            except Exception:
                local_conn = sqlite3.connect("local_crm.db", check_same_thread=False)
                df = pd.read_sql_query(f"SELECT * FROM {table_name} ORDER BY id DESC LIMIT 20", local_conn)
                local_conn.close()
        else:
            cursor = conn.cursor()
            cursor.execute(f"SELECT * FROM {table_name} ORDER BY id DESC LIMIT 20")
            rows = cursor.fetchall()
            col_names = [d[0] for d in cursor.description]
            df = pd.DataFrame(rows, columns=col_names) if rows else pd.DataFrame()
    except Exception:
        df = pd.DataFrame()
        
    if not df.empty:
        selected_record_to_print = None
        for _, row in df.iterrows():
            r_id = row['id']
            c_name = row.get('customer_name', 'Okänd')
            device_name = row.get('device', row.get('invoice_no', 'Doc'))
            total_val = row.get('total', row.get('amount', 0))
            
            checkbox_label = f"📱 {device_name} | {c_name} | {total_val} SEK"
            if st.checkbox(checkbox_label, key=f"chk_print_{r_id}"):
                selected_record_to_print = row.to_dict()

        if st.button("🖨️ طباعة الملف المختار", type="primary"):
            if selected_record_to_print:
                pdf_buf = generate_pdf_from_record(record_type, selected_record_to_print, COMPANY_INFO)
                st.session_state['hub_pdf'] = pdf_buf
                file_desc = "Kostnadsförslag" if record_type == "quote" else "Faktura"
                dev_title = str(selected_record_to_print.get('device', selected_record_to_print.get('invoice_no', 'doc'))).replace(' ', '_')
                cust_title = str(selected_record_to_print.get('customer_name', 'kund')).replace(' ', '_')
                st.session_state['hub_pdf_name'] = f"{file_desc}_{dev_title}_-_{cust_title}.pdf"
                st.rerun()
            else:
                st.warning("⚠️ اختر ملفاً أولاً.")

        if 'hub_pdf' in st.session_state:
            st.markdown("---")
            display_pdf_preview(st.session_state['hub_pdf'], file_name=st.session_state.get('hub_pdf_name', 'dokument.pdf'))
    else:
        st.info("ℹ️ لا توجد مستندات مسجلة.")

# --- 8. DATA CENTER & SÖK ---
elif menu == t["menu_datacenter"]:
    st.header(t["datacenter_header"])
    
    search_category = st.selectbox("Välj Kategori", ["📝 Reparationer", "💳 Abonnemang", "🛒 Förbeställningar", "💡 Kostnadsförslag", "📄 Fakturor", "📦 Lager"])
    search_term = st.text_input("🔎 بحث بالاسم أو الهاتف أو الـ IMEI", "").lower()
    
    conn, db_type = get_db_connection()
    table_map = {
        "📝 Reparationer": "repairs",
        "💳 Abonnemang": "subscriptions",
        "🛒 Förbeställningar": "preorders",
        "💡 Kostnadsförslag": "quotes",
        "📄 Fakturor": "invoices",
        "📦 Lager": "inventory"
    }
    current_table = table_map[search_category]
    
    try:
        if db_type == "turso":
            try:
                res = conn.execute(f"SELECT * FROM {current_table} ORDER BY id DESC")
                rows = res.fetchall()
                columns_res = conn.execute(f"PRAGMA table_info({current_table})").fetchall()
                col_names = [c[1] for c in columns_res]
                df = pd.DataFrame(rows, columns=col_names) if rows else pd.DataFrame()
            except Exception:
                local_conn = sqlite3.connect("local_crm.db", check_same_thread=False)
                df = pd.read_sql_query(f"SELECT * FROM {current_table} ORDER BY id DESC", local_conn)
                local_conn.close()
        else:
            cursor = conn.cursor()
            cursor.execute(f"SELECT * FROM {current_table} ORDER BY id DESC")
            rows = cursor.fetchall()
            col_names = [description[0] for description in cursor.description]
            df = pd.DataFrame(rows, columns=col_names) if rows else pd.DataFrame()
    except Exception:
        df = pd.DataFrame()
        
    if not df.empty:
        if search_term:
            mask = df.astype(str).apply(lambda x: x.str.lower().str.contains(search_term)).any(axis=1)
            filtered_df = df[mask]
        else:
            filtered_df = df
            
        st.dataframe(filtered_df, use_container_width=True)

        st.markdown("---")
        st.subheader("🗑️ حذف بند من النظام")
        del_options = [f"ID: {r['id']} | 👤 {r.get('customer_name', 'Okänd')}" for _, r in df.iterrows()]
        selected_del = st.selectbox("اختر البند للحذف", del_options)
        
        if st.button("Radera permanent", type="secondary"):
            if selected_del:
                del_id = int(selected_del.split("|")[0].replace("ID:", "").strip())
                try:
                    if db_type == "turso":
                        try:
                            conn.execute(f"DELETE FROM {current_table} WHERE id = ?", (del_id,))
                        except Exception:
                            local_conn = sqlite3.connect("local_crm.db", check_same_thread=False)
                            local_cursor = local_conn.cursor()
                            local_cursor.execute(f"DELETE FROM {current_table} WHERE id = ?", (del_id,))
                            local_conn.commit()
                            local_conn.close()
                    else:
                        cursor = conn.cursor()
                        cursor.execute(f"DELETE FROM {current_table} WHERE id = ?", (del_id,))
                        conn.commit()
                        conn.close()
                    st.success(f"✅ تم حذف البند #{del_id} بنجاح!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ خطأ في الحذف: {e}")
    else:
        st.info("ℹ️ لا توجد بيانات مسجلة.")
