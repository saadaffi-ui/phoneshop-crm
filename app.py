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
    
    try:
        cursor.execute("ALTER TABLE subscriptions ADD COLUMN employee TEXT")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE repairs ADD COLUMN employee TEXT")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE preorders ADD COLUMN employee TEXT")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE quotes ADD COLUMN employee TEXT")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE invoices ADD COLUMN employee TEXT")
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

    # Start FastAPI in a background thread if not already running
    if 'fastapi_started' not in st.session_state:
        st.session_state['fastapi_started'] = True
        threading.Thread(target=run_fastapi, daemon=True).start()
except Exception:
    pass

# Page Configuration & Mobile UI Setup
st.set_page_config(page_title="30 Minutes Phone Fix CRM", layout="wide", page_icon="📱")

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

# --- Translations Dictionary ---
TRANSLATIONS = {
    "Svenska": {
        "title": "30 MINUTES PHONE FIX",
        "menu_dashboard": "📈 Dashboard & Statistik",
        "menu_repair": "📝 Nytt Ärende / New Repair",
        "menu_quote": "💡 Kostnadsförslag / Quote",
        "menu_invoice": "📄 Faktura / Invoice",
        "menu_preorder": "🛒 Förbeställning / Pre-order",
        "menu_sub": "💳 Abonnemang / Subscriptions",
        "menu_inventory": "📦 Lager & Reservdelar / Inventory",
        "menu_history": "🖨️ Dokument & Historik / Print Hub",
        "menu_datacenter": "📊 Data Center & Sök / Search & Data",
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
        "dash_header": "📈 Dashboard & Statistik",
        "quote_header": "💡 Kostnadsförslag & Vinstberäkning",
        "invoice_header": "📄 Professionell Faktura",
        "preorder_header": "🛒 Förbeställning av reservdelar",
        "sub_header": "💳 IMEI-kopplade Abonnemang & Villkor",
        "inv_header": "📦 Lager & Reservdelar",
        "history_header": "🖨️ Visa och Skriv ut tidigare sparade dokument",
        "datacenter_header": "📊 Data Center, Sök, Export & Hantering"
    },
    "English": {
        "title": "30 MINUTES PHONE FIX",
        "menu_dashboard": "📈 Dashboard & Analytics",
        "menu_repair": "📝 New Repair",
        "menu_quote": "💡 Quote",
        "menu_invoice": "📄 Invoice",
        "menu_preorder": "🛒 Pre-order",
        "menu_sub": "💳 Subscriptions",
        "menu_inventory": "📦 Inventory & Parts",
        "menu_history": "🖨️ Print Hub",
        "menu_datacenter": "📊 Data Center & Search",
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
        "dash_header": "📈 Dashboard & Analytics",
        "quote_header": "💡 Price Quotation & Profit",
        "invoice_header": "📄 Professional Invoice",
        "preorder_header": "🛒 Spare Parts Pre-order",
        "sub_header": "💳 IMEI Subscriptions & Terms",
        "inv_header": "📦 Inventory Management",
        "history_header": "🖨️ Print & History Hub",
        "datacenter_header": "📊 Search & Management"
    },
    "العربية (Arabic)": {
        "title": "صيانة الهواتف 30 دقيقة",
        "menu_dashboard": "📈 لوحة المؤشرات والإحصاءات العامة",
        "menu_repair": "📝 تسجيل إصلاح جديد",
        "menu_quote": "💡 عرض سعر وحساب الأرباح",
        "menu_invoice": "📄 فاتورة رسمية",
        "menu_preorder": "🛒 طلب مسبق لقطع الغيار",
        "menu_sub": "💳 الاشتراكات وضمان IMEI",
        "menu_inventory": "📦 إدارة المخزون وقطع الغيار",
        "menu_history": "🖨️ مركز الطباعة والأرشيف",
        "menu_datacenter": "📊 إدارة البيانات والبحث الشامل",
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
        "dash_header": "📈 لوحة المؤشرات والإحصاءات العامة",
        "quote_header": "💡 عرض سعر وحاسبة الأرباح",
        "invoice_header": "📄 الفاتورة الرسمية للمحل",
        "preorder_header": "🛒 طلب مسبق لقطع الغيار",
        "sub_header": "💳 الاشتراكات وضمان IMEI",
        "inv_header": "📦 إدارة المخزون وقطع الغيار",
        "history_header": "🖨️ مركز الطباعة والأرشيف",
        "datacenter_header": "📊 إدارة البيانات والبحث الشامل"
    }
}

# --- Sidebar Branding & Language Selector ---
st.sidebar.title("30 MINUTES PHONE FIX")
if os.path.exists("logo.png"):
    st.sidebar.image("logo.png", use_container_width=True)

lang_choice = st.sidebar.selectbox("🌐 Välj Språk / Language / لغة الواجهة", ["Svenska", "English", "العربية (Arabic)"])
t = TRANSLATIONS[lang_choice]

st.sidebar.markdown("**Eskilstuna & Västerås**")
st.sidebar.markdown("---")

# Persistent Session Login State
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
    <object data="data:application/pdf;base64,{b64_pdf}" type="application/pdf" width="100%" height="700px" style="border: 1px solid #ccc; border-radius: 5px;">
        <embed src="data:application/pdf;base64,{b64_pdf}" type="application/pdf" width="100%" height="700px" />
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

    if os.path.exists("logo.png"):
        try:
            p.drawImage("logo.png", 50, height - 70, width=90, height=45, preserveAspectRatio=True, mask='auto')
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
    col1.metric("📝 إجمالي الإصلاحات / Repairs", rep_count)
    col2.metric("💡 عروض الأسعار / Quotes", quote_count)
    col3.metric("📄 الفواتير الرسمية / Invoices", inv_count)
    col4.metric("📈 إجمالي الأرباح / Est. Profit", f"{total_prof:.2f} Kr")

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
                col_a, col_b, col_c = st.columns([3, 3, 2])
                col_a.write(f"**ID: {r_id}** | {r_cust} ({r_dev}) [الموظف: {r_emp or '-'}]")
                col_b.write(f"الحالة الحالية: `{r_status}`")
                new_st = col_c.selectbox(f"تحديث #{r_id}", ["Under behandling / In Progress", "Väntar på reservdel / Waiting Part", "Klar att hämta / Ready", "Avslutad / Completed"], key=f"st_{r_id}")
                if col_c.button("تحديث / Save", key=f"btn_st_{r_id}"):
                    if db_type == "turso":
                        conn.execute("UPDATE repairs SET status = ? WHERE id = ?", (new_st, r_id))
                    else:
                        cursor = conn.cursor()
                        cursor.execute("UPDATE repairs SET status = ? WHERE id = ?", (new_st, r_id))
                        conn.commit()
                    st.success(f"تم تحديث حالة الأذن #{r_id} بنجاح!")
                    st.rerun()
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
    
    col_t1, col_t2 = st.columns(2)
    selected_issues = []
    
    with col_t1:
        if st.checkbox("📱 تغيير شاشة أصلي (Screen Replacement)"):
            selected_issues.append("Skärmbyte / Screen Replacement")
        if st.checkbox("🔋 استبدال بطارية جديدة (Battery Replacement)"):
            selected_issues.append("Batteribyte / Battery Replacement")
        if st.checkbox("🔌 إصلاح / تغيير منفذ الشحن (Charging Port)"):
            selected_issues.append("Laddport / Charging Port Repair")
        if st.checkbox("📷 إصلاح الكاميرا الأمامية/الخلفية (Camera)"):
            selected_issues.append("Kamera / Camera Repair")
            
    with col_t2:
        if st.checkbox("💧 معالجة أضرار المياه والسوائل (Water Damage)"):
            selected_issues.append("Vattenskada / Water Damage Service")
        if st.checkbox("🔊 إصلاح السماعة أو الميكروفون (Speaker/Mic)"):
            selected_issues.append("Ljud / Speaker & Mic Repair")
        if st.checkbox("🪟 تغيير الزجاج الخلفي (Back Glass Damaged)"):
            selected_issues.append("Baksida kraschad / Back Glass Damaged")
        if st.checkbox("⚙️ فحص وبرمجة الميكرو/النظام (Software/Diagnostics)"):
            selected_issues.append("Mjukvara & Felsökning / Software & Diagnostics")

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
    st.subheader("🛠️ Välj Fel / Reparationer (عدة قطع وعيوب في نفس الوقت)")
    
    issues_list = []
    total_price = 0.0
    total_cost = 0.0

    col_q1, col_q2 = st.columns(2)
    with col_q1:
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

        has_backglass = st.checkbox("🪟 Baksida kraschad / Back Glass Damaged", key="chk_bg")
        if has_backglass:
            p_bg = st.number_input("Pris: Baksida", min_value=0.0, step=50.0, value=0.0, key="p_bg")
            c_bg = st.number_input("Inköpskostnad del / Part Cost", min_value=0.0, step=10.0, value=0.0, key="c_bg")
            issues_list.append(f"Baksida kraschad / Back Glass: {p_bg}")
            total_price += p_bg
            total_cost += c_bg

    with col_q2:
        has_charging = st.checkbox("🔌 Laddport / Charging Port", key="chk_chg")
        if has_charging:
            p_chg = st.number_input("Pris: Laddport", min_value=0.0, step=50.0, value=0.0, key="p_chg")
            c_chg = st.number_input("Inköpskostnad del / Part Cost", min_value=0.0, step=10.0, value=0.0, key="c_chg")
            issues_list.append(f"Laddport / Charging Port: {p_chg}")
            total_price += p_chg
            total_cost += c_chg

        has_water = st.checkbox("💧 Vattenskada / Water Damage", key="chk_wat")
        if has_water:
            p_wat = st.number_input("Pris: Vattenskada", min_value=0.0, step=50.0, value=0.0, key="p_wat")
            c_wat = st.number_input("Inköpskostnad del / Part Cost", min_value=0.0, step=10.0, value=0.0, key="c_wat")
            issues_list.append(f"Vattenskada / Water Damage: {p_wat}")
            total_price += p_wat
            total_cost += c_wat

        has_cam = st.checkbox("📷 Kamera / Camera Repair", key="chk_cam")
        if has_cam:
            p_cam = st.number_input("Pris: Kamera", min_value=0.0, step=50.0, value=0.0, key="p_cam")
            c_cam = st.number_input("Inköpskostnad del / Part Cost", min_value=0.0, step=10.0, value=0.0, key="c_cam")
            issues_list.append(f"Kamera / Camera: {p_cam}")
            total_price += p_cam
            total_cost += c_cam

    custom_issue = st.text_input("Övrigt fel / Custom Issue (إضافات أخرى مخصصة)")
    if custom_issue:
        p_cust = st.number_input("Pris för övrigt", min_value=0.0, step=50.0, value=0.0, key="p_cust")
        c_cust = st.number_input("Inköpskostnad del", min_value=0.0, step=10.0, value=0.0, key="c_cust")
        issues_list.append(f"{custom_issue}: {p_cust}")
        total_price += p_cust
        total_cost += c_cust

    net_profit = total_price - total_cost

    st.markdown("---")
    st.markdown(f"### 💰 **Total Summa / Final Total: {total_price:.2f} SEK (inkl. moms / incl. VAT)**")
    st.markdown(f"📈 **Beräknad Vinst / Estimated Profit: {net_profit:.2f} SEK** *(Inköpskostnad / Cost: {total_cost:.2f} SEK)*")

    if st.button("Spara & Generera Kostnadsförslag PDF / Save Quote PDF", type="primary"):
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
                st.success("✅ Kostnadsförslag sparat i databasen! / Quote saved successfully!")
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
            st.success("✅ PDF skapades framgångsrikt! / PDF generated successfully!")

    if 'last_quote_pdf' in st.session_state:
        st.markdown("---")
        st.subheader("👀 Förhandsgranska och Skriv ut / Preview & Print")
        display_pdf_preview(st.session_state['last_quote_pdf'], file_name="kostnadsforslag.pdf")

# --- 3. FAKTURA / INVOICE ---
elif menu == t["menu_invoice"]:
    st.header(t["invoice_header"])
    branch = st.selectbox(t["branch_select"], ["Eskilstuna", "Västerås"])
    comp = COMPANY_INFO[branch]
    
    st.info(f"""
    🏢 **Företagsuppgifter ({branch}) / Company Details:**
    * **Företag / Company:** {comp['name']}
    * **Adress / Address:** {comp['address']}
    * **Telefon / Phone:** {comp['phone']} | **Org.nr:** {comp['org_nr']}
    * **Swish:** {comp['swish']} | **Bankgiro:** {comp['bankgiro']}
    """)

    st.markdown("---")
    st.subheader("👤 Kunduppgifter & Inställningar / Customer & Settings")
    
    col_inv1, col_inv2 = st.columns(2)
    with col_inv1:
        currency_choice = st.selectbox("💱 Välj Valuta / Currency", ["SEK", "EUR"])
        moms_choice = st.selectbox("📊 Välj Moms / VAT Rate", ["25%", "12%", "6%", "0% (Exemp / No VAT)"])
    with col_inv2:
        employee_name = st.text_input(t["employee"])
        invoice_no = st.text_input("Fakturanummer / Invoice No.", value="FAK-2026-001")

    f_name = st.text_input("Företag / Kundens namn / Company or Customer Name")
    f_phone_inv = st.text_input("Telefonnummer / Phone Number")
    f_address = st.text_input("Adress / Address")
    invoice_date = st.date_input("Fakturadatum / Invoice Date", value=date.today())
    due_date = st.date_input("Förfallodatum / Due Date", value=date.today())

    st.markdown("---")
    st.subheader("🛒 Artikel & Pris / Item & Price")
    item_desc = st.text_input("Beskrivning / Description", value="Reparation och reservdelar / Repair & Parts")
    item_qty = st.number_input("Antal / Quantity", min_value=1, value=1)
    item_price = st.number_input(f"Pris per enhet inkl. moms ({currency_choice}) / Unit Price incl. VAT", min_value=0.0, step=50.0)
    
    total_amount = item_qty * item_price
    
    if "25%" in moms_choice:
        moms_rate_val = 0.25
        moms_calc_divisor = 1.25
    elif "12%" in moms_choice:
        moms_rate_val = 0.12
        moms_calc_divisor = 1.12
    elif "6%" in moms_choice:
        moms_rate_val = 0.06
        moms_calc_divisor = 1.06
    else:
        moms_rate_val = 0.0
        moms_calc_divisor = 1.0

    if moms_rate_val > 0:
        netto = total_amount / moms_calc_divisor
        moms = total_amount - netto
    else:
        netto = total_amount
        moms = 0.0

    st.markdown(f"""
    ### 📊 Sammanfattning / Summary:
    * **Netto (exkl. moms) / Net (excl. VAT):** {netto:.2f} {currency_choice}
    * **Moms ({moms_choice}) / VAT:** {moms:.2f} {currency_choice}
    * **Att betala / Total Summa / Total:** **{total_amount:.2f} {currency_choice}**
    """)
    st.markdown(f"💳 **Betalningsmetod / Payment Method:** Swish: `{comp['swish']}` | Bankgiro: `{comp['bankgiro']}`")
    
    if st.button("Spara & Skapa Faktura PDF / Save & Create Invoice PDF", type="primary"):
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
                st.success("✅ Faktura sparad i databasen! / Invoice saved successfully!")
            except Exception as e:
                st.error(f"❌ Fel vid sparande / Error: {e}")

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
            st.success("✅ Faktura PDF skapades! / Invoice PDF generated!")

    if 'last_invoice_pdf' in st.session_state:
        st.markdown("---")
        st.subheader("👀 Förhandsgranska och Skriv ut / Preview & Print")
        display_pdf_preview(st.session_state['last_invoice_pdf'], file_name=f"{invoice_no}.pdf")

# --- 4. FÖRBÄLLNING / PRE-ORDER ---
elif menu == t["menu_preorder"]:
    st.header(t["preorder_header"])
    branch = st.selectbox(t["branch_select"], ["Eskilstuna", "Västerås"])
    employee_name = st.text_input(t["employee"])
    fb_name = st.text_input(t["customer_name"])
    fb_phone = st.text_input(t["phone"])
    fb_details = st.text_area("Artikel / Delar detaljer / Part Details")
    fb_deposit = st.number_input("Handpenning / Deposit", min_value=0.0, step=50.0)
    
    if st.button("Spara Förbeställning / Save Pre-order", type="primary"):
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
                st.success("✅ Förbeställning sparad! / Pre-order saved successfully!")
            except Exception as e:
                st.error(f"❌ Fel vid sparande / Error: {e}")
        else:
            st.warning("⚠️ Fyll i namn, telefonnummer och ansvarig medarbetare.")

# --- 5. ABONNEMANG / SUBSCRIPTIONS ---
elif menu == t["menu_sub"]:
    st.header(t["sub_header"])
    
    employee_name = st.text_input(t["employee"])
    sub_imei = st.text_input(t["imei"])
    sub_device = st.text_input(t["device"])
    branch = st.selectbox(t["branch_select"], ["Eskilstuna", "Västerås"])
    sub_name = st.text_input(t["customer_name"])
    sub_phone = st.text_input(t["phone"])

    st.markdown("---")
    plan_choice = st.selectbox("Välj Plan / Plan Type", [
        "Glass Protection Abonnemang (99 SEK/mån)",
        "Case / Cover Abonnemang (399 SEK start + 99 SEK/mån)",
        "Teknik, Mjukvara & Virus Help (99 SEK/mån)",
        "Phone Shield Total Club (149 SEK/mån)"
    ])
    
    if "Glass Protection" in plan_choice:
        sub_price = 99.0
        st.info("💡 **Glass Protection Plan:** 99 SEK/mån | Byt skärmskydd upp till 2 ggr/mån utan självrisk.")
    elif "Case / Cover" in plan_choice:
        sub_price = 99.0
        st.info("💡 **Case / Cover Plan:** 399 SEK startavgift + 99 SEK/mån.")
    elif "Phone Shield Total Club" in plan_choice:
        sub_price = 149.0
        st.info("💡 **Phone Shield Total Club:** 149 SEK/mån | شاشة حماية مجانية كل شهرين + خصم 35% على الإصلاحات + صيانة دورية.")
    else:
        sub_price = 99.0
        st.info("💡 **Teknik & Mjukvara Plan:** 99 SEK/mån.")

    st.markdown("---")
    st.info("""
    **Svenska / العربية (Villkor / الشروط):**
    1. **IMEI-koppling / ربط IMEI:** Abonnemanget är strikt kopplat till enhetens IMEI-nummer.
    2. **Uppsägningstid / فترة الإلغاء:** 3 månaders uppsägningstid gäller.
    """)
    
    agree_terms = st.checkbox("Kunden godkänner avtalsvillkoren & IMEI-regler / Customer accepts terms")

    if st.button("Spara Abonnemang i Molnet / Save Subscription", type="primary"):
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
                st.success("✅ Abonnemanget kopplat till IMEI har sparats!")
            except Exception as e:
                st.error(f"❌ Fel vid sparande / Error: {e}")
        elif not sub_imei:
            st.warning("⚠️ IMEI-nummer är obligatoriskt!")
        elif not employee_name:
            st.warning("⚠️ يرجى إدخال اسم الموظف المسؤول.")
        elif not agree_terms:
            st.warning("⚠️ Du måste bocka i att kunden godkänner villkoren.")
        else:
            st.warning("⚠️ Fyll i kundens namn.")

    st.markdown("---")
    st.subheader("📄 توليد فاتورة من الاشتراكات المسجلة / Generate Invoice from Subscription")
    
    conn, db_type = get_db_connection()
    try:
        if db_type == "turso":
            subs_rows = conn.execute("SELECT id, customer_name, phone, device, imei, plan_type, price, employee, branch FROM subscriptions ORDER BY id DESC LIMIT 20").fetchall()
        else:
            cursor = conn.cursor()
            cursor.execute("SELECT id, customer_name, phone, device, imei, plan_type, price, employee, branch FROM subscriptions ORDER BY id DESC LIMIT 20")
            subs_rows = cursor.fetchall()
            
        if subs_rows:
            subs_df = pd.DataFrame(subs_rows, columns=["ID", "Kund / Customer", "Telefon", "Enhet", "IMEI", "Plan", "Pris", "الموظف", "الفرع"])
            st.dataframe(subs_df, use_container_width=True)
            
            sub_id_to_inv = st.number_input("أدخل رقم ID الاشتراك لتوليد فاتورة له / Enter Subscription ID to invoice", min_value=1, step=1)
            inv_currency = st.selectbox("عملة الفواتير / Currency", ["SEK", "EUR"], key="sub_inv_curr")
            inv_moms_rate = st.selectbox("نسبة الضريبة / VAT Rate", ["25%", "12%", "6%", "0%"], key="sub_inv_moms")
            
            if st.button("🖨️ إنشاء وتصدير فاتورة لهذا الاشتراك / Create Subscription Invoice", type="primary"):
                selected_sub = [row for row in subs_rows if row[0] == sub_id_to_inv]
                if selected_sub:
                    s_data = selected_sub[0]
                    s_id, s_cust, s_phone, s_dev, s_imei, s_plan, s_price, s_emp, s_branch = s_data
                    
                    if "25%" in inv_moms_rate:
                        moms_div = 1.25
                        moms_val = s_price - (s_price / moms_div)
                    elif "12%" in inv_moms_rate:
                        moms_div = 1.12
                        moms_val = s_price - (s_price / moms_div)
                    elif "6%" in inv_moms_rate:
                        moms_div = 1.06
                        moms_val = s_price - (s_price / moms_div)
                    else:
                        moms_val = 0.0

                    invoice_no_gen = f"SUB-{datetime.now().strftime('%Y%m%d')}-{s_id}"
                    
                    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    try:
                        if db_type == "turso":
                            conn.execute(
                                "INSERT INTO invoices (branch, customer_name, phone, invoice_no, amount, moms, currency, moms_rate, employee, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                (s_branch, s_cust, s_phone, invoice_no_gen, s_price, moms_val, inv_currency, inv_moms_rate, s_emp, created_at)
                            )
                        else:
                            cursor = conn.cursor()
                            cursor.execute(
                                "INSERT INTO invoices (branch, customer_name, phone, invoice_no, amount, moms, currency, moms_rate, employee, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                (s_branch, s_cust, s_phone, invoice_no_gen, s_price, moms_val, inv_currency, inv_moms_rate, s_emp, created_at)
                            )
                            conn.commit()
                    except Exception:
                        pass

                    inv_record_data = {
                        "branch": s_branch,
                        "customer_name": s_cust,
                        "phone": s_phone,
                        "invoice_no": invoice_no_gen,
                        "amount": s_price,
                        "moms": moms_val,
                        "currency": inv_currency,
                        "moms_rate": inv_moms_rate,
                        "item_desc": f"Abonnemang / Subscription: {s_plan} (IMEI: {s_imei})",
                        "employee": s_emp,
                        "created_at": date.today().strftime('%Y-%m-%d')
                    }
                    
                    pdf_buf = generate_pdf_from_record("invoice", inv_record_data, COMPANY_INFO)
                    st.session_state['sub_invoice_pdf'] = pdf_buf
                    st.success(f"✅ تم إنشاء الفاتورة رقم {invoice_no_gen} بنجاح!")
                else:
                    st.warning("⚠️ رقم الـ ID غير موجود في الاشتراكات.")

            if 'sub_invoice_pdf' in st.session_state:
                st.markdown("---")
                display_pdf_preview(st.session_state['sub_invoice_pdf'], file_name="abonnemang_faktura.pdf")
        else:
            st.info("ℹ️ لا توجد اشتراكات مسجلة بعد.")
    except Exception as e:
        st.error(f"خطأ في جلب الاشتراكات: {e}")

# --- 6. LAGER & RESERVDELAR / INVENTORY & PARTS ---
elif menu == t["menu_inventory"]:
    st.header(t["inv_header"])
    branch = st.selectbox(t["branch_select"], ["Eskilstuna", "Västerås"])
    
    conn, db_type = get_db_connection()
    
    st.subheader("➕ Lägg till ny reservdel / Add New Part")
    new_part_name = st.text_input("Reservdel / Artikelnamn (t.ex. iPhone 15 Skärm)")
    new_part_qty = st.number_input("Antal i lager / Stock Quantity", min_value=0, step=1, value=5)
    new_part_min = st.number_input("Varningsgräns (Min Limit)", min_value=0, step=1, value=2)
    
    if st.button("Spara till lager / Add to Inventory", type="primary"):
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
                st.success("✅ Reservdelen har lagts till i lagret!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Fel: {e}")
        else:
            st.warning("⚠️ Ange artikelnamn.")

    st.markdown("---")
    st.subheader(f"📋 Aktuellt lager för {branch} / Current Stock")
    
    try:
        if db_type == "turso":
            try:
                rows = conn.execute("SELECT id, part_name, stock_qty, min_limit FROM inventory WHERE branch = ? ORDER BY id DESC", (branch,)).fetchall()
                inv_df = pd.DataFrame(rows, columns=["ID", "Reservdel", "Antal", "Min Gräns"]) if rows else pd.DataFrame()
            except Exception:
                local_conn = sqlite3.connect("local_crm.db", check_same_thread=False)
                inv_df = pd.read_sql_query("SELECT id, part_name, stock_qty, min_limit FROM inventory WHERE branch = ? ORDER BY id DESC", local_conn, params=(branch,))
                local_conn.close()
        else:
            cursor = conn.cursor()
            cursor.execute("SELECT id, part_name, stock_qty, min_limit FROM inventory WHERE branch = ? ORDER BY id DESC", (branch,))
            rows = cursor.fetchall()
            inv_df = pd.DataFrame(rows, columns=["ID", "Reservdel", "Antal", "Min Gräns"]) if rows else pd.DataFrame()
    except Exception:
        inv_df = pd.DataFrame()

    if not inv_df.empty:
        low_stock = inv_df[inv_df["Antal"] <= inv_df["Min Gräns"]]
        if not low_stock.empty:
            st.warning("⚠️ **Varning! Följande reservdelar håller på att ta slut i lager:**")
            for _, row in low_stock.iterrows():
                st.error(f"- {row['Reservdel']} (Kvar i lager: {row['Antal']} st)")

        st.dataframe(inv_df, use_container_width=True)
    else:
        st.info("ℹ️ Inget lager registrerat ännu.")

# --- 7. DOKUMENT & HISTORIK / PRINT & HISTORY HUB ---
elif menu == t["menu_history"]:
    st.header(t["history_header"])
    st.markdown("Välj kategori och ange ID för att visa eller skriva ut ett sparat dokument från databasen:")
    
    category = st.selectbox("Välj Kategori / Category", [
        "💡 Kostnadsförslag / Quotes", 
        "📄 Fakturor / Invoices"
    ])
    
    conn, db_type = get_db_connection()
    table_name = "quotes" if "Quotes" in category else "invoices"
    record_type = "quote" if "Quotes" in category else "invoice"
    
    try:
        if db_type == "turso":
            try:
                rows = conn.execute(f"SELECT * FROM {table_name} ORDER BY id DESC LIMIT 30").fetchall()
                columns_res = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
                col_names = [c[1] for c in columns_res]
                df = pd.DataFrame(rows, columns=col_names) if rows else pd.DataFrame()
            except Exception:
                local_conn = sqlite3.connect("local_crm.db", check_same_thread=False)
                df = pd.read_sql_query(f"SELECT * FROM {table_name} ORDER BY id DESC LIMIT 30", local_conn)
                local_conn.close()
        else:
            cursor = conn.cursor()
            cursor.execute(f"SELECT * FROM {table_name} ORDER BY id DESC LIMIT 30")
            rows = cursor.fetchall()
            col_names = [d[0] for d in cursor.description]
            df = pd.DataFrame(rows, columns=col_names) if rows else pd.DataFrame()
    except Exception:
        df = pd.DataFrame()
        
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        
        st.markdown("### 🔍 Välj post via ID för att Visa / Skriva ut")
        selected_id = st.number_input("Ange Post-ID (första kolumnen) / Enter Record ID", min_value=1, step=1)
        
        target_row = df[df['id'] == selected_id]
        
        if not target_row.empty:
            row_data = target_row.iloc[0].to_dict()
            st.success(f"✅ Vald post hittad: {row_data.get('customer_name', '')}")
            
            if st.button("👁️ Generera & Förhandsgranska PDF / View PDF", type="primary"):
                pdf_buf = generate_pdf_from_record(record_type, row_data, COMPANY_INFO)
                st.session_state['hub_pdf'] = pdf_buf
                st.session_state['hub_pdf_name'] = f"dokument_{selected_id}.pdf"
                st.rerun()
                
            if 'hub_pdf' in st.session_state:
                st.markdown("---")
                display_pdf_preview(st.session_state['hub_pdf'], file_name=st.session_state.get('hub_pdf_name', 'dokument.pdf'))
        else:
            st.info("ℹ️ Ange ett giltigt ID från tabellen ovan.")
    else:
        st.info("ℹ️ Inga dokument hittades.")

# --- 8. DATA CENTER & SÖK / ALL DATA & SEARCH ---
elif menu == t["menu_datacenter"]:
    st.header(t["datacenter_header"])
    st.markdown("Sök, exportera, visa dokument eller radera poster från databasen:")
    
    search_category = st.selectbox("Välj Kategori / Select Category", [
        "📝 Reparationer / Repairs", 
        "💳 Abonnemang / Subscriptions", 
        "🛒 Förbeställningar / Pre-orders", 
        "💡 Kostnadsförslag / Quotes", 
        "📄 Fakturor / Invoices",
        "📦 Lager / Inventory"
    ])
    
    search_term = st.text_input("🔎 Sök på Namn, Telefon eller IMEI / Search by Name, Phone, or IMEI", "").lower()
    
    conn, db_type = get_db_connection()
    
    table_map = {
        "📝 Reparationer / Repairs": "repairs",
        "💳 Abonnemang / Subscriptions": "subscriptions",
        "🛒 Förbeställningar / Pre-orders": "preorders",
        "💡 Kostnadsförslag / Quotes": "quotes",
        "📄 Fakturor / Invoices": "invoices",
        "📦 Lager / Inventory": "inventory"
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
        
        if current_table in ["quotes", "invoices"]:
            st.markdown("---")
            st.subheader("👁️ Visa och Skriv ut sparad post direkt / View & Print Record")
            doc_id = st.number_input("Ange ID för dokument som ska visas/skrivas ut", min_value=0, step=1, key="doc_view_id")
            
            if doc_id > 0:
                match_row = df[df['id'] == doc_id]
                if not match_row.empty:
                    row_dict = match_row.iloc[0].to_dict()
                    rec_type = "quote" if current_table == "quotes" else "invoice"
                    
                    if st.button("🖨️ Generera förhandsgranskning för ID", type="primary"):
                        buf = generate_pdf_from_record(rec_type, row_dict, COMPANY_INFO)
                        st.session_state['datacenter_pdf'] = buf
                        st.rerun()

            if 'datacenter_pdf' in st.session_state:
                st.markdown("---")
                display_pdf_preview(st.session_state['datacenter_pdf'], file_name="arkiv_dokument.pdf")

        st.markdown("---")
        st.subheader("🗑️ Radera post / Delete Record")
        delete_id = st.number_input("Ange ID för post som ska raderas / Enter ID to delete", min_value=0, step=1, key="del_id_input")
        
        if st.button("Radera permanent / Delete Permanently", type="secondary"):
            if delete_id > 0:
                try:
                    if db_type == "turso":
                        try:
                            conn.execute(f"DELETE FROM {current_table} WHERE id = ?", (delete_id,))
                        except Exception:
                            local_conn = sqlite3.connect("local_crm.db", check_same_thread=False)
                            local_cursor = local_conn.cursor()
                            local_cursor.execute(f"DELETE FROM {current_table} WHERE id = ?", (delete_id,))
                            local_conn.commit()
                            local_conn.close()
                    else:
                        cursor = conn.cursor()
                        cursor.execute(f"DELETE FROM {current_table} WHERE id = ?", (delete_id,))
                        conn.commit()
                        conn.close()
                    st.success(f"✅ Post med ID {delete_id} har raderats!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Fel vid radering / Delete error: {e}")
            else:
                st.warning("⚠️ Ange ett giltigt ID att radera.")
    else:
        st.info("ℹ️ Inga poster hittades i databasen.")
