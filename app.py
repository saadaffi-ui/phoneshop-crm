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
                    branch TEXT, customer_name TEXT, phone TEXT, address TEXT, ref_no TEXT, invoice_no TEXT,
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
                "ALTER TABLE invoices ADD COLUMN employee TEXT",
                "ALTER TABLE invoices ADD COLUMN address TEXT",
                "ALTER TABLE invoices ADD COLUMN ref_no TEXT"
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
            branch TEXT, customer_name TEXT, phone TEXT, address TEXT, ref_no TEXT, invoice_no TEXT,
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

    for col in ["address", "ref_no"]:
        try:
            cursor.execute(f"ALTER TABLE invoices ADD COLUMN {col} TEXT")
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

st.markdown("""
<style>
    .stApp { background-color: #f4f6f9; color: #2c3e50; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    h1, h2, h3 { color: #1a252f; font-weight: 700; }
    div.stButton > button { border-radius: 8px; font-weight: 600; padding: 0.6rem 1.2rem; width: 100%; }
    .dashboard-box { background-color: #eaf2f8; padding: 20px; border-radius: 10px; border-left: 6px solid #2980b9; }
    .repair-box { background-color: #e8f8f5; padding: 20px; border-radius: 10px; border-left: 6px solid #1abc9c; }
    .quote-box { background-color: #fef9e7; padding: 20px; border-radius: 10px; border-left: 6px solid #f1c40f; }
    .invoice-box { background-color: #f5eef8; padding: 20px; border-radius: 10px; border-left: 6px solid #8e44ad; }
    .sub-box { background-color: #fbeee6; padding: 20px; border-radius: 10px; border-left: 6px solid #d35400; }
    .preorder-box { background-color: #e8f6f3; padding: 20px; border-radius: 10px; border-left: 6px solid #16a085; }
    .inventory-box { background-color: #fbfcfe; padding: 20px; border-radius: 10px; border-left: 6px solid #e67e22; }
    .search-box { background-color: #ebedef; padding: 20px; border-radius: 10px; border-left: 6px solid #34495e; }
    .login-container { background: #ffffff; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); max-width: 450px; margin: auto; border-top: 5px solid #e74c3c; }
</style>
""", unsafe_allow_html=True)

COMPANY_INFO = {
    "Eskilstuna": {
        "name": "30 MINUTES PHONE FIX",
        "address": "Gunborg Nymans Väg 2, 632 32 Eskilstuna",
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
        "tab_dash": "📊 Dashboard", "tab_repair": "🛠️ Nytt Ärende", "tab_quote": "💡 Kostnadsförslag",
        "tab_invoice": "📄 Faktura", "tab_sub": "💳 Abonnemang", "tab_preorder": "🛒 Förbeställning",
        "tab_stock": "📦 Lager", "tab_search": "🔍 Sök & Arkiv",
        "employee": "Handläggare / Säljare", "phone": "Telefonnummer", "customer_name": "Kundens namn",
        "email": "E-post (Valfritt)", "device": "Enhet / Modell", "imei": "IMEI / Serienummer",
        "price": "Pris", "issue": "Beskrivning av fel", "save_repair": "Spara Ärende", "success_repair": "✅ Ärendet har sparats!"
    },
    "English": {
        "tab_dash": "📊 Dashboard", "tab_repair": "🛠️ New Repair", "tab_quote": "💡 Quote",
        "tab_invoice": "📄 Invoice", "tab_sub": "💳 Subscriptions", "tab_preorder": "🛒 Pre-order",
        "tab_stock": "📦 Inventory", "tab_search": "🔍 Search & Archive",
        "employee": "Employee Name", "phone": "Phone Number", "customer_name": "Customer Name",
        "email": "Email (Optional)", "device": "Device Model", "imei": "IMEI / Serial Number",
        "price": "Price", "issue": "Issue Description", "save_repair": "Save Repair", "success_repair": "✅ Repair saved successfully!"
    },
    "العربية (Arabic)": {
        "tab_dash": "📊 لوحة التحكم", "tab_repair": "🛠️ إصلاح جديد", "tab_quote": "💡 عرض سعر",
        "tab_invoice": "📄 فاتورة", "tab_sub": "💳 الاشتراكات", "tab_preorder": "🛒 الطلب المسبق",
        "tab_stock": "📦 المخزون", "tab_search": "🔍 الأرشيف والبحث",
        "employee": "اسم الموظف المسؤول", "phone": "رقم الهاتف", "customer_name": "اسم العميل",
        "email": "البريد الإلكتروني (اختياري)", "device": "نوع وطراز الجهاز", "imei": "رقم الـ IMEI أو الرقم التسلسلي",
        "price": "السعر", "issue": "وصف العطل أو الإصلاح المطلوب", "save_repair": "حفظ بيانات الإصلاح", "success_repair": "✅ تم حفظ طلب الإصلاح بنجاح!"
    }
}

head_c1, head_c2, head_c3 = st.columns([1, 2, 2])
with head_c1:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=55)
with head_c2:
    lang_choice = st.selectbox("🌐 Language / Språk / اللغة", ["Svenska", "English", "العربية (Arabic)"], key="top_lang_bar")
with head_c3:
    global_branch = st.selectbox("🏢 Branch / Butik / الفرع", ["Eskilstuna", "Västerås"], key="top_branch_bar")

t = TRANSLATIONS[lang_choice]
comp = COMPANY_INFO[global_branch]

st.markdown(f"""
<div style="background-color: #ffffff; padding: 10px 15px; border-radius: 8px; border: 1px solid #dcdde1; margin-bottom: 15px; font-size: 13px;">
    <b>🏢 Active Branch / Aktiv Butik:</b> {comp['name']} - {comp['address']} | <b>Tel:</b> {comp['phone']} | <b>Org.nr:</b> {comp['org_nr']} | <b>Swish:</b> {comp['swish']}
</div>
""", unsafe_allow_html=True)
st.markdown("---")

if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

if not st.session_state['authenticated']:
    try:
        default_pin = st.secrets.get("DELETE_PIN", "tunapark")
    except Exception:
        default_pin = "tunapark"
        
    st.markdown("<div class='login-container'>", unsafe_allow_html=True)
    st.markdown("### 🔒 System Login / Inloggning")
    st.markdown("Ange PIN-kod för att fortsätta / الرجاء إدخال رمز المرور:")
    login_pin = st.text_input("🔑 PIN Code /  رمز المرور", type="password", key="login_pin_input")
    remember_me = st.session_state.get('remember_me', False)
    remember_device = st.checkbox("💾 Kom ihåg mig / تذكرني", value=remember_me)
    
    if login_pin == default_pin:
        st.session_state['authenticated'] = True
        st.session_state['remember_me'] = remember_device
        st.success("✅ Logged in successfully! / تم تسجيل الدخول بنجاح!")
        st.rerun()
    elif login_pin:
        st.error("❌ Fel PIN-kod! / رمز المرور غير صحيح!")
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

if st.sidebar.button("🔒 Log Out / Logga ut / تسجيل خروج"):
    st.session_state['authenticated'] = False
    st.session_state['remember_me'] = False
    st.rerun()

def display_pdf_preview(pdf_buffer, file_name="document.pdf"):
    pdf_buffer.seek(0)
    pdf_bytes = pdf_buffer.read()
    b64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
    st.success("✅ Dokumentet är redo! / Document is ready!")
    
    b_col1, b_col2 = st.columns(2)
    with b_col1:
        st.download_button("📥 Ladda ner PDF / Download PDF", data=pdf_bytes, file_name=file_name, mime="application/pdf", type="primary")
    with b_col2:
        print_html = f"""
        <script>
        function printPDF() {{
            var iframe = document.createElement('iframe');
            iframe.style.display = 'none';
            iframe.src = "data:application/pdf;base64,{b64_pdf}";
            document.body.appendChild(iframe);
            iframe.contentWindow.print();
        }}
        </script>
        <button onclick="printPDF()" style="background-color: #2ecc71; color: white; padding: 0.6rem 1.2rem; border: none; border-radius: 8px; font-weight: 600; width: 100%; cursor: pointer;">
            🖨️ Skriv ut / Print
        </button>
        """
        st.markdown(print_html, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 👁️ Förhandsgranskning / Preview")
    pdf_display = f"""
    <object data="data:application/pdf;base64,{b64_pdf}" type="application/pdf" width="100%" height="500px" style="border: 1px solid #ccc; border-radius: 8px;">
        <embed src="data:application/pdf;base64,{b64_pdf}" type="application/pdf" width="100%" height="500px" />
    </object>
    """
    st.markdown(pdf_display, unsafe_allow_html=True)

def generate_pdf_from_record(record_type, data, comp_info):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    branch = data.get('branch', 'Eskilstuna')
    comp = comp_info.get(branch, comp_info['Eskilstuna'])
    employee_name = data.get('employee', 'Ej angiven')
    currency = data.get('currency', 'SEK')
    moms_rate_str = data.get('moms_rate', '25%')

    if os.path.exists("logo.png"):
        try:
            p.drawImage("logo.png", 50, height - 75, width=90, height=50, preserveAspectRatio=True, mask='auto')
        except Exception:
            pass
            
    p.setFont("Helvetica-Bold", 14)
    p.drawString(150, height - 40, comp["name"])
    p.setFont("Helvetica", 9)
    p.drawString(150, height - 55, f"Adress: {comp['address']}")
    p.drawString(150, height - 70, f"Tel: {comp['phone']} | Org.nr: {comp['org_nr']}")
    
    p.setLineWidth(1)
    p.line(50, height - 85, width - 50, height - 85)

    if record_type == "repair_receipt":
        p.setFont("Helvetica-Bold", 12)
        p.drawString(50, height - 110, "INLÄMNINGSKVITTO / REPAIR RECEIPT")
        p.setFont("Helvetica", 10)
        p.drawString(50, height - 135, f"Ärende ID: #{data.get('repair_id', '1')}")
        p.drawString(300, height - 135, f"Datum / Date: {data.get('created_at', '')}")
        p.drawString(50, height - 155, f"Kund / Customer: {data.get('customer_name', '')}")
        p.drawString(300, height - 155, f"Handläggare / Agent: {employee_name}")
        p.drawString(50, height - 175, f"Telefon / Phone: {data.get('phone', '')}")
        p.drawString(300, height - 175, f"Enhet / Device: {data.get('device', '')}")
        p.drawString(50, height - 195, f"IMEI / Serial: {data.get('imei', 'Ej angivet')}")
        
        p.setFillColorRGB(0.9, 0.9, 0.9)
        p.rect(50, height - 235, width - 100, 20, fill=1, stroke=0)
        p.setFillColorRGB(0, 0, 0)
        p.setFont("Helvetica-Bold", 9)
        p.drawString(60, height - 228, "Beskrivning av fel / Repair Description")
        p.drawString(400, height - 228, f"Pris ({currency})")
        
        p.setFont("Helvetica", 10)
        y_pos = height - 265
        p.drawString(60, y_pos, f"- {data.get('issue', '')}")
        price_val = data.get('price', 0)
        p.drawString(400, y_pos, f"{price_val:.2f} {currency}")
        
        p.line(50, height - 320, width - 50, height - 320)
        p.setFont("Helvetica-Bold", 11)
        p.drawString(300, height - 335, f"Att betala / Total: {price_val:.2f} {currency}")
        p.setFont("Helvetica", 8)
        p.drawString(300, height - 350, "(Inkl. moms / Incl. VAT)")
        
        p.setFont("Helvetica-Bold", 8)
        p.drawString(50, height - 385, "Garanti & Villkor / Warranty & Terms:")
        p.setFont("Helvetica", 7.5)
        p.drawString(50, height - 398, "- Garanti ges endast for det arbete/delar som har utforts/bytts ut.")
        p.drawString(50, height - 410, "- Vi ansvarar ej for forlorad data (sarskilt vid vattenskadade, doeda eller enheter med svart skaerm),")
        p.drawString(50, height - 422, "  da datan kan ha gått forlorad redan innan inlamning.")
        p.drawString(50, height - 434, "- Detta kvitto maste uppvisas vid uthamtning. Vi ansvarar ej for ej uthamtade enheter efter 3 manader.")

        p.setFont("Helvetica-Oblique", 7.5)
        p.drawString(50, height - 455, "* Warranty applies only to the specific repair performed.")
        p.drawString(50, height - 467, "* Not responsible for data loss (especially on water-damaged, dead or black-screen devices).")

        p.drawString(50, 45, f"Swish: {comp['swish']} | Bankgiro: {comp['bankgiro']}")
        p.drawString(50, 32, f"Org.nr: {comp['org_nr']} | Butik / Branch: {branch}")

    elif record_type == "label_sticker":
        p.setLineWidth(1)
        p.rect(35, height - 165, 270, 140)
        p.setFont("Helvetica-Bold", 11)
        p.drawString(45, height - 50, f"{comp['name']}")
        p.setFont("Helvetica-Bold", 9)
        p.drawString(45, height - 70, f"Arende ID: #{data.get('repair_id')}   |   Datum: {data.get('created_at')}")
        p.setFont("Helvetica", 9)
        p.drawString(45, height - 90, f"Kund / Customer: {data.get('customer_name')}")
        p.drawString(45, height - 108, f"Enhet / Device: {data.get('device')}")
        p.drawString(45, height - 126, f"IMEI: {data.get('imei', '---')}")
        p.setFont("Helvetica-Bold", 9)
        p.drawString(45, height - 146, f"Tel: {data.get('phone')}   |   Pris: {data.get('price')} SEK")

    elif record_type == "quote":
        p.setFont("Helvetica-Bold", 12)
        p.drawString(50, height - 110, "KOSTNADSFÖRSLAG / PRICE QUOTATION")
        p.setFont("Helvetica", 10)
        p.drawString(50, height - 135, f"Datum / Date: {data.get('created_at', '')}")
        p.drawString(300, height - 135, f"Handläggare / Agent: {employee_name}")
        p.drawString(50, height - 155, f"Kund / Customer: {data.get('customer_name', '')}")
        p.drawString(50, height - 175, f"Telefon / Phone: {data.get('phone', '')}")
        p.drawString(300, height - 155, f"Enhet / Device: {data.get('device', '')}")
        
        p.setFillColorRGB(0.9, 0.9, 0.9)
        p.rect(50, height - 215, width - 100, 20, fill=1, stroke=0)
        p.setFillColorRGB(0, 0, 0)
        p.setFont("Helvetica-Bold", 9)
        p.drawString(60, height - 208, "Beskrivning av reparation / Repair description")
        p.drawString(400, height - 208, f"Belopp / Amount ({currency})")
        
        p.setFont("Helvetica", 10)
        y_pos = height - 245
        p.drawString(60, y_pos, f"- {data.get('issues', '')}")
        total_val = data.get('total', 0)
        p.drawString(400, y_pos, f"{total_val:.2f} {currency}")
        
        p.line(50, height - 320, width - 50, height - 320)
        p.setFont("Helvetica-Bold", 11)
        p.drawString(300, height - 345, f"Att betala / Total: {total_val:.2f} {currency}")
        p.setFont("Helvetica", 8)
        p.drawString(300, height - 360, "(Inkl. moms / Incl. VAT)")
        
        p.setFont("Helvetica-Oblique", 8)
        p.drawString(50, height - 420, "* Detta kostnadsförslag är giltigt i 30 dagar / Valid for 30 days.")
        p.drawString(50, 45, f"Swish: {comp['swish']} | Bankgiro: {comp['bankgiro']}")
        p.drawString(50, 32, f"Org.nr: {comp['org_nr']} | Butik / Branch: {branch}")

    elif record_type == "invoice":
        p.setFont("Helvetica-Bold", 12)
        p.drawString(50, height - 110, "FAKTURA / INVOICE")
        p.setFont("Helvetica", 10)
        p.drawString(50, height - 135, f"Fakturanr / Invoice No: {data.get('invoice_no', '')}")
        p.drawString(50, height - 150, f"Fakturadatum / Date: {data.get('created_at', '')}")
        p.drawString(50, height - 165, f"Vår referens / Our ref: {employee_name}")
        
        p.setFont("Helvetica-Bold", 10)
        p.drawString(300, height - 135, "Köpare / Buyer (Customer):")
        p.setFont("Helvetica", 10)
        p.drawString(300, height - 150, f"{data.get('customer_name', '')}")
        p.drawString(300, height - 165, f"{data.get('address', 'Ej angiven adress')}")
        p.drawString(300, height - 180, f"Tel: {data.get('phone', '')}")
        
        p.setFillColorRGB(0.9, 0.9, 0.9)
        p.rect(50, height - 225, width - 100, 20, fill=1, stroke=0)
        p.setFillColorRGB(0, 0, 0)
        p.setFont("Helvetica-Bold", 9)
        p.drawString(60, height - 218, "Beskrivning av tjänst / vara / Description")
        p.drawString(400, height - 218, f"Belopp / Amount ({currency})")
        
        y_pos = height - 255
        amount_val = data.get('amount', 0)
        moms_val = data.get('moms', 0)
        netto_val = amount_val - moms_val
        
        p.setFont("Helvetica", 10)
        p.drawString(60, y_pos, f"{data.get('item_desc', 'Reparation')}")
        if data.get('ref_no'):
            p.drawString(60, y_pos - 15, f"Referensnr / Order: {data.get('ref_no')}")
            
        p.drawString(400, y_pos, f"{netto_val:.2f} {currency}")
        
        p.line(50, height - 330, width - 50, height - 330)
        p.setFont("Helvetica", 9)
        p.drawString(300, height - 350, f"Netto / Net: {netto_val:.2f} {currency}")
        p.drawString(300, height - 368, f"Moms / VAT ({moms_rate_str}): {moms_val:.2f} {currency}")
        p.setFont("Helvetica-Bold", 11)
        p.drawString(300, height - 395, f"Att betala / Total: {amount_val:.2f} {currency}")
        
        p.setFont("Helvetica", 9)
        p.drawString(50, 65, f"Swish: {comp['swish']} | Bankgiro: {comp['bankgiro']}")
        p.drawString(50, 50, f"Org.nr: {comp['org_nr']} | Adress: {comp['address']}")
        p.drawString(50, 35, f"Butik / Branch: {branch} | Tel: {comp['phone']}")

    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    t["tab_dash"], t["tab_repair"], t["tab_quote"], t["tab_invoice"], 
    t["tab_sub"], t["tab_preorder"], t["tab_stock"], t["tab_search"]
])

# --- TAB 1: DASHBOARD ---
with tab1:
    st.markdown("<div class='dashboard-box'>", unsafe_allow_html=True)
    st.header(f"📊 لوحة المؤشرات والإحصاءات العامة / Dashboard ({global_branch})")
    conn, db_type = get_db_connection()
    try:
        if db_type == "turso":
            rep_count = conn.execute("SELECT COUNT(*) FROM repairs WHERE branch = ?", (global_branch,)).fetchone()[0]
            quote_count = conn.execute("SELECT COUNT(*) FROM quotes WHERE branch = ?", (global_branch,)).fetchone()[0]
            inv_count = conn.execute("SELECT COUNT(*) FROM invoices WHERE branch = ?", (global_branch,)).fetchone()[0]
            total_prof = conn.execute("SELECT SUM(profit) FROM quotes WHERE branch = ?", (global_branch,)).fetchone()[0] or 0.0
        else:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM repairs WHERE branch = ?", (global_branch,))
            rep_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM quotes WHERE branch = ?", (global_branch,))
            quote_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM invoices WHERE branch = ?", (global_branch,))
            inv_count = cursor.fetchone()[0]
            cursor.execute("SELECT SUM(profit) FROM quotes WHERE branch = ?", (global_branch,))
            total_prof = cursor.fetchone()[0] or 0.0
    except Exception:
        rep_count, quote_count, inv_count, total_prof = 0, 0, 0, 0.0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📝 الإصلاحات / Repairs", rep_count)
    c2.metric("💡 عروض الأسعار / Quotes", quote_count)
    c3.metric("📄 الفواتير / Invoices", inv_count)
    c4.metric("📈 الأرباح / Profit", f"{total_prof:.2f} Kr")

    st.markdown("---")
    st.subheader("⚡ تحديث حالة الأجهزة السريعة / Quick Status Update")
    try:
        if db_type == "turso":
            active_repairs = conn.execute("SELECT id, customer_name, device, status, employee FROM repairs WHERE branch = ? ORDER BY id DESC LIMIT 5", (global_branch,)).fetchall()
        else:
            cursor = conn.cursor()
            cursor.execute("SELECT id, customer_name, device, status, employee FROM repairs WHERE branch = ? ORDER BY id DESC LIMIT 5", (global_branch,))
            active_repairs = cursor.fetchall()
            
        if active_repairs:
            for rep in active_repairs:
                r_id, r_cust, r_dev, r_status, r_emp = rep
                st.markdown(f"**ID: {r_id}** | 👤 {r_cust} ({r_dev}) [الموظف / Agent: {r_emp or '-'}]")
                new_st = st.selectbox(f"الحالة / Status #{r_id}", ["Under behandling / In Progress", "Väntar på reservdel / Waiting Part", "Klar att hämta / Ready", "Avslutad / Completed"], key=f"st_{r_id}")
                if st.button("حفظ التحديث / Save Status", key=f"btn_st_{r_id}"):
                    if db_type == "turso":
                        conn.execute("UPDATE repairs SET status = ? WHERE id = ?", (new_st, r_id))
                    else:
                        cursor = conn.cursor()
                        cursor.execute("UPDATE repairs SET status = ? WHERE id = ?", (new_st, r_id))
                        conn.commit()
                    st.success(f"تم تحديث الأذن #{r_id}! / Updated!")
                    st.rerun()
                st.markdown("---")
        else:
            st.info("لا توجد إصلاحات مسجلة لهذا الفرع حالياً. / No repairs found.")
    except Exception as e:
        st.error(f"خطأ / Error: {e}")
    st.markdown("</div>", unsafe_allow_html=True)

# --- TAB 2: NEW REPAIR ---
with tab2:
    st.markdown("<div class='repair-box'>", unsafe_allow_html=True)
    st.header(f"🛠️ تسجيل إصلاح جديد وتوليد إيصال الاستلام / New Repair ({global_branch})")
    employee_name = st.text_input(t["employee"], key="rep_emp")
    c_phone = st.text_input(t["phone"], key="rep_phone")
    
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
                st.info(f"💡 تم العثور على عميل سابق / Existing customer: **{auto_name}**")
        except Exception:
            pass

    c_name = st.text_input(t["customer_name"], value=auto_name, key="rep_name")
    c_email = st.text_input(t["email"], value=auto_email, key="rep_email")
    device = st.text_input(t["device"], key="rep_device")
    imei = st.text_input(t["imei"], key="rep_imei")
    
    repair_issues_options = [
        "Skärmbyte (Original)", "Skärmbyte (OLED / Kopia)", "Batteribyte",
        "Laddport", "Baksida", "Kamera bak", "Kamera fram", "Ljud / Högtalare",
        "Vattenskada", "Mjukvara / Software", "Övrigt fel"
    ]
    selected_rep_issues = st.multiselect("قائمة الأعطال / Issue options:", repair_issues_options, key="multi_rep_issues")
    price = st.number_input(t["price"], min_value=0.0, step=50.0, key="rep_price")
    
    auto_issues_str = ", ".join(selected_rep_issues)
    issue = st.text_area(t["issue"], value=auto_issues_str, key="rep_issue_desc")

    st.markdown("""
    <div style="background-color: #fff3cd; padding: 12px; border-radius: 8px; border-left: 5px solid #ffc107; font-size: 13px; margin-top: 10px; margin-bottom: 10px;">
        <b>⚠️ شروط الضمان وإخلاء المسؤولية (Warranty & Disclaimer Terms on Receipt):</b><br>
        • الضمان يغطي فقط الإصلاح أو القطعة التي تم استبدالها.<br>
        • لا تتحمل الورشة أي مسؤولية عن ضياع البيانات في الأجهزة التالفة بسبب الماء أو الأجهزة الميتة.
    </div>
    """, unsafe_allow_html=True)
    
    if st.button(t["save_repair"], type="primary", key="btn_save_rep"):
        if c_name and c_phone and device and employee_name:
            conn, db_type = get_db_connection()
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            status = "Under behandling / In Progress"
            try:
                if db_type == "turso":
                    conn.execute(
                        "INSERT INTO repairs (branch, customer_name, phone, email, device, imei, issue, price, status, employee, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (global_branch, c_name, c_phone, c_email, device, imei, issue, price, status, employee_name, created_at)
                    )
                else:
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO repairs (branch, customer_name, phone, email, device, imei, issue, price, status, employee, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (global_branch, c_name, c_phone, c_email, device, imei, issue, price, status, employee_name, created_at)
                    )
                    conn.commit()
                    conn.close()
                st.success(t["success_repair"])
                
                rec_data = {
                    "branch": global_branch, "repair_id": "99", "customer_name": c_name,
                    "phone": c_phone, "device": device, "imei": imei, "issue": issue,
                    "price": price, "employee": employee_name, "created_at": date.today().strftime('%Y-%m-%d')
                }
                st.session_state['rep_receipt_pdf'] = generate_pdf_from_record("repair_receipt", rec_data, COMPANY_INFO)
                st.session_state['rep_label_pdf'] = generate_pdf_from_record("label_sticker", rec_data, COMPANY_INFO)
            except Exception as e:
                st.error(f"❌ خطأ / Error: {e}")
        else:
            st.warning("⚠️ يرجى تعبئة الحقول الأساسية واسم الموظف / Please fill required fields.")

    if 'rep_receipt_pdf' in st.session_state:
        st.markdown("---")
        st.subheader("📄 إيصال استلام العميل / Inlämningskvitto (Receipt)")
        display_pdf_preview(st.session_state['rep_receipt_pdf'], file_name="Inlamningskvitto.pdf")
        
    if 'rep_label_pdf' in st.session_state:
        st.markdown("---")
        st.subheader("🏷️ ملصق الجهاز والـ IMEI / IMEI Label Sticker")
        display_pdf_preview(st.session_state['rep_label_pdf'], file_name="IMEI_Label.pdf")
    st.markdown("</div>", unsafe_allow_html=True)

# --- TAB 3: QUOTE ---
with tab3:
    st.markdown("<div class='quote-box'>", unsafe_allow_html=True)
    st.header(f"💡 عرض سعر وحساب الأرباح / Price Quotation ({global_branch})")
    q_emp = st.text_input(t["employee"], key="q_emp")
    q_name = st.text_input(t["customer_name"], key="q_name")
    q_phone = st.text_input(t["phone"], key="q_phone")
    q_device = st.text_input(t["device"], key="q_device")

    quote_items = [("Skärmbyte", "qp_s", "qc_s"), ("Batteribyte", "qp_b", "qc_b"), ("Laddport", "qp_l", "qc_l"), ("Baksida", "qp_bk", "qc_bk")]
    issues_list, total_price, total_cost = [], 0.0, 0.0

    for label, p_key, c_key in quote_items:
        if st.checkbox(label, key=f"chk_{p_key}"):
            col_p, col_c = st.columns(2)
            with col_p: p_val = st.number_input(f"Kundpris ({label})", min_value=0.0, step=50.0, key=p_key)
            with col_c: c_val = st.number_input(f"Vår kostnad ({label})", min_value=0.0, step=10.0, key=c_key)
            issues_list.append(f"{label}: {p_val} SEK")
            total_price += p_val
            total_cost += c_val

    net_profit = total_price - total_cost
    st.markdown(f"### 💰 الإجمالي / Total: **{total_price:.2f} SEK** | 📈 الربح / Net Profit: **{net_profit:.2f} SEK**")

    if st.button("حفظ وتوليد عرض سعر PDF / Save Quote PDF", type="primary", key="btn_save_q"):
        if q_name and q_device and issues_list and q_emp:
            conn, db_type = get_db_connection()
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            issues_str = ", ".join(issues_list)
            try:
                if db_type == "turso":
                    conn.execute("INSERT INTO quotes (branch, customer_name, phone, email, device, issues, total, profit, employee, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (global_branch, q_name, q_phone, "", q_device, issues_str, total_price, net_profit, q_emp, created_at))
                else:
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO quotes (branch, customer_name, phone, email, device, issues, total, profit, employee, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (global_branch, q_name, q_phone, "", q_device, issues_str, total_price, net_profit, q_emp, created_at))
                    conn.commit()
                    conn.close()
                st.success("✅ تم حفظ عرض السعر! / Saved!")
            except Exception as e:
                st.error(f"❌ خطأ / Error: {e}")

            record_data = {"branch": global_branch, "customer_name": q_name, "phone": q_phone, "device": q_device, "issues": issues_str, "total": total_price, "currency": "SEK", "employee": q_emp, "created_at": date.today().strftime('%Y-%m-%d')}
            st.session_state['q_pdf'] = generate_pdf_from_record("quote", record_data, COMPANY_INFO)
            st.session_state['q_pdf_name'] = f"Kostnadsforslag_{q_device.replace(' ', '_')}.pdf"

    if 'q_pdf' in st.session_state:
        st.markdown("---")
        display_pdf_preview(st.session_state['q_pdf'], file_name=st.session_state.get('q_pdf_name', 'quote.pdf'))
    st.markdown("</div>", unsafe_allow_html=True)

# --- TAB 4: INVOICE WITH SWISH & LINK GENERATOR ---
with tab4:
    st.markdown("<div class='invoice-box'>", unsafe_allow_html=True)
    st.header(f"📄 الفاتورة الرسمية وخيارات الدفع / Standard Invoice & Payments ({global_branch})")
    
    inv_emp = st.text_input(t["employee"], key="inv_emp")
    inv_no = st.text_input("رقم الفاتورة / Fakturanummer", value="FAK-2026-001", key="inv_no_in")
    ref_no = st.text_input("إشارة المرجع أو الطلب / Vår referens", value="", key="inv_ref_in")
    inv_name = st.text_input("اسم العميل / Kund / Företag", key="inv_name")
    inv_address = st.text_input("عنوان الشارع والمدينة / Gatuadress", value="Drottninggatan 1, Eskilstuna", key="inv_addr_in")
    inv_phone = st.text_input(t["phone"], key="inv_phone")
    
    inv_curr = st.selectbox("العملة / Currency", ["SEK", "EUR"], key="inv_curr")
    inv_moms = st.selectbox("نسبة الضريبة / Moms (VAT)", ["25%", "12%", "6%", "0%"], key="inv_moms_sel")
    item_desc = st.text_input("وصف البند / Beskrivning", value="Reparation och reservdelar", key="inv_desc")
    item_price = st.number_input("السعر الإجمالي inkl. moms / Pris", min_value=0.0, step=50.0, key="inv_price")
    
    moms_div = 1.25 if "25%" in inv_moms else (1.12 if "12%" in inv_moms else (1.06 if "6%" in inv_moms else 1.0))
    netto = item_price / moms_div if moms_div > 1 else item_price
    moms = item_price - netto

    st.markdown(f"**المبلغ الإجمالي / Att betala:** **{item_price:.2f} {inv_curr}** (Netto: {netto:.2f} | Moms: {moms:.2f})")

    st.markdown("---")
    st.subheader("💳 وسائل وسداد الدفع الإلكتروني / Direct Payment Gateways")
    pay_col1, pay_col2 = st.columns(2)
    with pay_col1:
        st.markdown(f"""
        <div style="background-color: #e8f8f5; padding: 15px; border-radius: 8px; border: 1px solid #1abc9c;">
            <b>📱 Swish Direct Pay</b><br>
            • Nummer: <b>{comp['swish']}</b><br>
            • Belopp: <b>{item_price:.2f} {inv_curr}</b>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🚀 توليد تنبيه دفع Swish", key="btn_swish_pay"):
            st.success(f"✅ أبلغ العميل بتحويل {item_price:.2f} {inv_curr} على Swish رقم: {comp['swish']}")

    with pay_col2:
        st.markdown(f"""
        <div style="background-color: #fef9e7; padding: 15px; border-radius: 8px; border: 1px solid #f1c40f;">
            <b>💳 Payment Link</b><br>
            • Belopp: <b>{item_price:.2f} {inv_curr}</b>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🔗 إنشاء رابط الدفع", key="btn_pay_link"):
            payment_url = f"https://pay.30minutesphonefix.se/checkout?amount={item_price}&ref={inv_no}"
            st.info(f"🔗 **رابط العميل:**\n`{payment_url}`")
            st.markdown(f"[اضغط هنا لفتح صفحة الدفع]({payment_url})", unsafe_allow_html=True)

    st.markdown("---")
    if st.button("حفظ وتوليد فاتورة PDF رسمية", type="primary", key="btn_save_inv"):
        if inv_name and inv_emp:
            conn, db_type = get_db_connection()
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            try:
                if db_type == "turso":
                    conn.execute("INSERT INTO invoices (branch, customer_name, phone, address, ref_no, invoice_no, amount, moms, currency, moms_rate, employee, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (global_branch, inv_name, inv_phone, inv_address, ref_no, inv_no, item_price, moms, inv_curr, inv_moms, inv_emp, created_at))
                else:
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO invoices (branch, customer_name, phone, address, ref_no, invoice_no, amount, moms, currency, moms_rate, employee, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (global_branch, inv_name, inv_phone, inv_address, ref_no, inv_no, item_price, moms, inv_curr, inv_moms, inv_emp, created_at))
                    conn.commit()
                    conn.close()
                st.success("✅ تم حفظ الفاتورة بنجاح!")
            except Exception as e:
                st.error(f"❌ خطأ: {e}")

            record_data = {"branch": global_branch, "customer_name": inv_name, "address": inv_address, "phone": inv_phone, "ref_no": ref_no, "invoice_no": inv_no, "amount": item_price, "moms": moms, "currency": inv_curr, "moms_rate": inv_moms, "item_desc": item_desc, "employee": inv_emp, "created_at": date.today().strftime('%Y-%m-%d')}
            st.session_state['inv_pdf'] = generate_pdf_from_record("invoice", record_data, COMPANY_INFO)
            st.session_state['inv_pdf_name'] = f"Faktura_{inv_no}.pdf"

    if 'inv_pdf' in st.session_state:
        st.markdown("---")
        display_pdf_preview(st.session_state['inv_pdf'], file_name=st.session_state.get('inv_pdf_name', 'invoice.pdf'))
    st.markdown("</div>", unsafe_allow_html=True)

# --- TAB 5: SUBSCRIPTIONS ---
with tab5:
    st.markdown("<div class='sub-box'>", unsafe_allow_html=True)
    st.header(f"💳 الاشتراكات وضمان IMEI / Subscriptions ({global_branch})")
    sub_emp = st.text_input(t["employee"], key="sub_emp")
    sub_imei = st.text_input(t["imei"], key="sub_imei")
    sub_device = st.text_input(t["device"], key="sub_device")
    sub_name = st.text_input(t["customer_name"], key="sub_name")
    sub_phone = st.text_input(t["phone"], key="sub_phone")
    plan_choice = st.selectbox("Välj Plan", ["Glass Protection Abonnemang (99 SEK/mån)", "Phone Shield Total Club (149 SEK/mån)"])
    sub_price = 149.0 if "Phone Shield Total Club" in plan_choice else 99.0
    agree_terms = st.checkbox("Kunden godkänner villkoren")

    if st.button("Spara Abonnemang", type="primary", key="btn_save_sub"):
        if sub_imei and sub_name and agree_terms and sub_emp:
            conn, db_type = get_db_connection()
            start_date, created_at = datetime.now().strftime("%Y-%m-%d"), datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            try:
                if db_type == "turso":
                    conn.execute("INSERT INTO subscriptions (branch, customer_name, phone, device, imei, plan_type, price, employee, start_date, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (global_branch, sub_name, sub_phone, sub_device, sub_imei, plan_choice, sub_price, sub_emp, start_date, created_at))
                else:
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO subscriptions (branch, customer_name, phone, device, imei, plan_type, price, employee, start_date, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (global_branch, sub_name, sub_phone, sub_device, sub_imei, plan_choice, sub_price, sub_emp, start_date, created_at))
                    conn.commit()
                    conn.close()
                st.success("✅ تم حفظ الاشتراك وربطه برقم الـ IMEI!")
            except Exception as e:
                st.error(f"❌ خطأ: {e}")
        else:
            st.warning("⚠️ يرجى إدخال الحقول المطلوبة والموافقة على الشروط.")
    st.markdown("</div>", unsafe_allow_html=True)

# --- TAB 6: PRE-ORDERS ---
with tab6:
    st.markdown("<div class='preorder-box'>", unsafe_allow_html=True)
    st.header(f"🛒 الطلب المسبق لقطع الغيار / Pre-orders ({global_branch})")
    pre_emp = st.text_input(t["employee"], key="pre_emp")
    pre_name = st.text_input(t["customer_name"], key="pre_name")
    pre_phone = st.text_input(t["phone"], key="pre_phone")
    pre_details = st.text_area("تفاصيل القطعة المطلوبة")
    pre_deposit = st.number_input("العربون المدفوع (SEK)", min_value=0.0, step=50.0)

    if st.button("حفظ الطلب المسبق", type="primary", key="btn_save_pre"):
        if pre_name and pre_phone and pre_emp:
            conn, db_type = get_db_connection()
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            try:
                if db_type == "turso":
                    conn.execute("INSERT INTO preorders (branch, customer_name, phone, item_details, deposit, employee, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)", (global_branch, pre_name, pre_phone, pre_details, pre_deposit, pre_emp, created_at))
                else:
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO preorders (branch, customer_name, phone, item_details, deposit, employee, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)", (global_branch, pre_name, pre_phone, pre_details, pre_deposit, pre_emp, created_at))
                    conn.commit()
                    conn.close()
                st.success("✅ تم حفظ الطلب المسبق!")
            except Exception as e:
                st.error(f"❌ خطأ: {e}")
        else:
            st.warning("⚠️ أدخل اسم الموظف والعميل ورقم الهاتف.")
    st.markdown("</div>", unsafe_allow_html=True)

# --- TAB 7: INVENTORY ---
with tab7:
    st.markdown("<div class='inventory-box'>", unsafe_allow_html=True)
    st.header(f"📦 إدارة المخزون / Inventory ({global_branch})")
    conn, db_type = get_db_connection()
    
    part_name = st.text_input("اسم القطعة (e.g. iPhone 15 Screen)")
    part_qty = st.number_input("العدد المتوفر", min_value=0, step=1, value=5)
    part_min = st.number_input("حد الإنذار الأدنى", min_value=0, step=1, value=2)
    
    if st.button("حفظ في المخزون", type="primary", key="btn_add_stock"):
        if part_name:
            try:
                if db_type == "turso":
                    conn.execute("INSERT INTO inventory (part_name, stock_qty, min_limit, branch) VALUES (?, ?, ?, ?)", (part_name, part_qty, part_min, global_branch))
                else:
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO inventory (part_name, stock_qty, min_limit, branch) VALUES (?, ?, ?, ?)", (part_name, part_qty, part_min, global_branch))
                    conn.commit()
                    conn.close()
                st.success("✅ تمت الإضافة للمخزون!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ خطأ: {e}")
        else:
            st.warning("⚠️ أدخل اسم القطعة.")

    st.markdown("---")
    try:
        if db_type == "turso":
            rows = conn.execute("SELECT id, part_name, stock_qty, min_limit FROM inventory WHERE branch = ? ORDER BY id DESC", (global_branch,)).fetchall()
            df_inv = pd.DataFrame(rows, columns=["ID", "Part Name", "Qty", "Min Limit"]) if rows else pd.DataFrame()
        else:
            local_conn = sqlite3.connect("local_crm.db", check_same_thread=False)
            df_inv = pd.read_sql_query("SELECT id, part_name, stock_qty, min_limit FROM inventory WHERE branch = ? ORDER BY id DESC", local_conn, params=(global_branch,))
            local_conn.close()
        if not df_inv.empty:
            st.dataframe(df_inv, use_container_width=True)
        else:
            st.info("لا توجد قطع مسجلة.")
    except Exception:
        pass
    st.markdown("</div>", unsafe_allow_html=True)

# --- TAB 8: SEARCH & ARCHIVE ---
with tab8:
    st.markdown("<div class='search-box'>", unsafe_allow_html=True)
    st.header(f"🔍 الأرشيف والبحث / Search & Archive ({global_branch})")
    search_cat = st.selectbox("اختر القسم", ["📝 الإصلاحات / Repairs", "💳 الاشتراكات / Subscriptions", "🛒 الطلبات / Pre-orders", "💡 عروض الأسعار / Quotes", "📄 الفواتير / Invoices", "📦 المخزون / Inventory"])
    search_term = st.text_input("🔎 بحث بالاسم أو الهاتف أو الـ IMEI", "").lower()
    
    table_map = {
        "📝 الإصلاحات / Repairs": "repairs", "💳 الاشتراكات / Subscriptions": "subscriptions",
        "🛒 الطلبات / Pre-orders": "preorders", "💡 عروض الأسعار / Quotes": "quotes",
        "📄 الفواتير / Invoices": "invoices", "📦 المخزون / Inventory": "inventory"
    }
    cur_tbl = table_map[search_cat]
    
    try:
        if db_type == "turso":
            res = conn.execute(f"SELECT * FROM {cur_tbl} WHERE branch = ? ORDER BY id DESC", (global_branch,))
            rows = res.fetchall()
            cols = [c[1] for c in conn.execute(f"PRAGMA table_info({cur_tbl})").fetchall()]
            df_search = pd.DataFrame(rows, columns=cols) if rows else pd.DataFrame()
        else:
            local_conn = sqlite3.connect("local_crm.db", check_same_thread=False)
            df_search = pd.read_sql_query(f"SELECT * FROM {cur_tbl} WHERE branch = ? ORDER BY id DESC", local_conn, params=(global_branch,))
            local_conn.close()
    except Exception:
        df_search = pd.DataFrame()
        
    if not df_search.empty:
        filtered_df = df_search[df_search.astype(str).apply(lambda x: x.str.lower().str.contains(search_term)).any(axis=1)] if search_term else df_search
        st.dataframe(filtered_df, use_container_width=True)

        if cur_tbl == "repairs":
            st.markdown("---")
            repair_opts = [f"ID: {r['id']} | 👤 {r['customer_name']} ({r['device']})" for _, r in filtered_df.iterrows()]
            selected_rep_to_print = st.selectbox("اختر الإصلاح للطباعة", repair_opts, key="sel_rep_print")
            if selected_rep_to_print:
                sel_id = int(selected_rep_to_print.split("|")[0].replace("ID:", "").strip())
                row_data = filtered_df[filtered_df['id'] == sel_id].iloc[0]
                c_pr1, c_pr2 = st.columns(2)
                with c_pr1:
                    if st.button("📄 طباعة إيصال الاستلام", key="btn_print_rec_arch"):
                        r_data = {"branch": global_branch, "repair_id": str(row_data['id']), "customer_name": row_data['customer_name'], "phone": row_data['phone'], "device": row_data['device'], "imei": row_data['imei'], "issue": row_data['issue'], "price": row_data['price'], "employee": row_data.get('employee', 'Admin'), "created_at": str(row_data['created_at'])[:10]}
                        display_pdf_preview(generate_pdf_from_record("repair_receipt", r_data, COMPANY_INFO), file_name=f"Inlamningskvitto_{sel_id}.pdf")
                with c_pr2:
                    if st.button("🏷️ طباعة ملصق IMEI", key="btn_print_lbl_arch"):
                        r_data = {"branch": global_branch, "repair_id": str(row_data['id']), "customer_name": row_data['customer_name'], "phone": row_data['phone'], "device": row_data['device'], "imei": row_data['imei'], "price": row_data['price'], "created_at": str(row_data['created_at'])[:10]}
                        display_pdf_preview(generate_pdf_from_record("label_sticker", r_data, COMPANY_INFO), file_name=f"IMEI_Label_{sel_id}.pdf")

        st.markdown("---")
        del_opts = [f"ID: {r['id']} | 👤 {r.get('customer_name', r.get('part_name', 'Okänd'))}" for _, r in filtered_df.iterrows()]
        sel_del = st.selectbox("اختر البند للحذف", del_opts, key="del_sb")
        if st.button("حذف نهائي", type="secondary"):
            if sel_del:
                d_id = int(sel_del.split("|")[0].replace("ID:", "").strip())
                try:
                    if db_type == "turso":
                        conn.execute(f"DELETE FROM {cur_tbl} WHERE id = ?", (d_id,))
                    else:
                        local_conn = sqlite3.connect("local_crm.db", check_same_thread=False)
                        local_conn.execute(f"DELETE FROM {cur_tbl} WHERE id = ?", (d_id,))
                        local_conn.commit()
                        local_conn.close()
                    st.success(f"✅ تم الحذف بنجاح!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ خطأ: {e}")
    else:
        st.info("لا توجد بيانات مطابقة.")
    st.markdown("</div>", unsafe_allow_html=True)
