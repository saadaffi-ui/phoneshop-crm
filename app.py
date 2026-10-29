import streamlit as st
import sqlite3
import os
from datetime import datetime, date
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import io
import pandas as pd
import base64

# --- Local SQLite Database Setup ---
def get_db_connection():
    conn = sqlite3.connect("local_crm.db", check_same_thread=False)
    return conn

def init_db():
    conn = get_db_connection()
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
    
    # Check and add missing columns if upgrading from old DB
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

st.set_page_config(page_title="30 Minutes Phone Fix CRM", layout="wide", page_icon="📱")

# --- Custom Styling ---
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

# --- Top Header Bar ---
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

# --- Secure Authentication Login ---
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
    login_pin = st.text_input("🔑 PIN Code / رمز المرور", type="password", key="login_pin_input")
    
    if login_pin == default_pin:
        st.session_state['authenticated'] = True
        st.success("✅ Logged in successfully! / تم تسجيل الدخول بنجاح!")
        st.rerun()
    elif login_pin:
        st.error("❌ Fel PIN-kod! / رمز المرور غير صحيح!")
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

if st.sidebar.button("🔒 Log Out / Logga ut / تسجيل خروج"):
    st.session_state['authenticated'] = False
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
        p.drawString(50, height - 410, "- Vi ansvarar ej for forlorad data (sarskilt vid vattenskadade, doeda eller enheter med svart skaerm).")

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
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM repairs WHERE branch = ?", (global_branch,))
        rep_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM quotes WHERE branch = ?", (global_branch,))
        quote_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM invoices WHERE branch = ?", (global_branch,))
        inv_count = cursor.fetchone()[0]
        cursor.execute("SELECT SUM(profit) FROM quotes WHERE branch = ?", (global_branch,))
        total_prof = cursor.fetchone()[0] or 0.0
        conn.close()
    except Exception:
        rep_count, quote_count, inv_count, total_prof = 0, 0, 0, 0.0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📝 الإصلاحات / Repairs", rep_count)
    c2.metric("💡 عروض الأسعار / Quotes", quote_count)
    c3.metric("📄 الفواتير / Invoices", inv_count)
    c4.metric("📈 الأرباح / Profit", f"{total_prof:.2f} Kr")
    st.markdown("</div>", unsafe_allow_html=True)

# --- TAB 2: NEW REPAIR ---
with tab2:
    st.markdown("<div class='repair-box'>", unsafe_allow_html=True)
    st.header(f"🛠️ تسجيل إصلاح جديد / New Repair ({global_branch})")
    employee_name = st.text_input(t["employee"], key="rep_emp")
    c_phone = st.text_input(t["phone"], key="rep_phone")
    c_name = st.text_input(t["customer_name"], key="rep_name")
    c_email = st.text_input(t["email"], key="rep_email")
    device = st.text_input(t["device"], key="rep_device")
    imei = st.text_input(t["imei"], key="rep_imei")
    
    price = st.number_input(t["price"], min_value=0.0, step=50.0, key="rep_price")
    issue = st.text_area(t["issue"], key="rep_issue_desc")

    if st.button(t["save_repair"], type="primary", key="btn_save_rep"):
        if c_name and c_phone and device and employee_name:
            conn = get_db_connection()
            cursor = conn.cursor()
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(
                "INSERT INTO repairs (branch, customer_name, phone, email, device, imei, issue, price, status, employee, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (global_branch, c_name, c_phone, c_email, device, imei, issue, price, "Pågår", employee_name, created_at)
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
        else:
            st.warning("⚠️ يرجى تعبئة الحقول الأساسية واسم الموظف.")

    if 'rep_receipt_pdf' in st.session_state:
        st.markdown("---")
        display_pdf_preview(st.session_state['rep_receipt_pdf'], file_name="Inlamningskvitto.pdf")
    st.markdown("</div>", unsafe_allow_html=True)

# --- TAB 3: QUOTE ---
with tab3:
    st.markdown("<div class='quote-box'>", unsafe_allow_html=True)
    st.header(f"💡 عرض سعر / Quote ({global_branch})")
    q_emp = st.text_input(t["employee"], key="q_emp")
    q_name = st.text_input(t["customer_name"], key="q_name")
    q_phone = st.text_input(t["phone"], key="q_phone")
    q_device = st.text_input(t["device"], key="q_device")
    total_price = st.number_input("المبلغ الإجمالي / Total", min_value=0.0, step=50.0, key="q_tot")
    net_profit = st.number_input("الربح الصافي / Net Profit", min_value=0.0, step=10.0, key="q_prof")
    issues_str = st.text_input("تفاصيل العمل / Issues", key="q_issues")

    if st.button("حفظ وتوليد عرض سعر PDF", type="primary", key="btn_save_q"):
        if q_name and q_device and q_emp:
            conn = get_db_connection()
            cursor = conn.cursor()
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("INSERT INTO quotes (branch, customer_name, phone, email, device, issues, total, profit, employee, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (global_branch, q_name, q_phone, "", q_device, issues_str, total_price, net_profit, q_emp, created_at))
            conn.commit()
            conn.close()
            st.success("✅ تم حفظ عرض السعر!")
            
            record_data = {"branch": global_branch, "customer_name": q_name, "phone": q_phone, "device": q_device, "issues": issues_str, "total": total_price, "currency": "SEK", "employee": q_emp, "created_at": date.today().strftime('%Y-%m-%d')}
            st.session_state['q_pdf'] = generate_pdf_from_record("quote", record_data, COMPANY_INFO)

    if 'q_pdf' in st.session_state:
        display_pdf_preview(st.session_state['q_pdf'], file_name="quote.pdf")
    st.markdown("</div>", unsafe_allow_html=True)

# --- TAB 4: INVOICE WITH SHOREPAY & SWISH ---
with tab4:
    st.markdown("<div class='invoice-box'>", unsafe_allow_html=True)
    st.header(f"📄 الفاتورة وخيارات الدفع / Invoice & Payments ({global_branch})")
    inv_emp = st.text_input(t["employee"], key="inv_emp")
    inv_no = st.text_input("رقم الفاتورة", value="FAK-2026-001", key="inv_no_in")
    inv_name = st.text_input("اسم العميل", key="inv_name")
    inv_address = st.text_input("العنوان", value="Drottninggatan 1, Eskilstuna", key="inv_addr_in")
    inv_phone = st.text_input(t["phone"], key="inv_phone")
    item_price = st.number_input("المبلغ الإجمالي inkl. moms", min_value=0.0, step=50.0, key="inv_price")
    
    moms = item_price - (item_price / 1.25)
    st.markdown(f"**Att betala:** **{item_price:.2f} SEK** (Moms: {moms:.2f})")

    st.markdown("---")
    st.subheader("💳 وسائل وسداد الدفع الإلكتروني المباشر")
    pay_col1, pay_col2 = st.columns(2)
    with pay_col1:
        st.markdown(f"""
        <div style="background-color: #e8f8f5; padding: 15px; border-radius: 8px; border: 1px solid #1abc9c;">
            <b>📱 Swish Direct Pay</b><br>
            • Nummer: <b>{comp['swish']}</b><br>
            • Belopp: <b>{item_price:.2f} SEK</b>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🚀 توليد تنبيه دفع Swish", key="btn_swish_pay"):
            st.success(f"✅ أبلغ العميل بتحويل {item_price:.2f} SEK على Swish رقم: {comp['swish']}")

    with pay_col2:
        payment_url = f"https://pay.30minutesphonefix.se/checkout?amount={item_price}&ref={inv_no}"
        st.markdown(f"""
        <div style="background-color: #fef9e7; padding: 15px; border-radius: 8px; border: 1px solid #f1c40f;">
            <b>💳 Card Payment Link</b><br>
            • Belopp: <b>{item_price:.2f} SEK</b>
        </div>
        """, unsafe_allow_html=True)
        st.info(f"🔗 **رابط العميل المباشر:**\n`{payment_url}`")
        st.markdown(f"[اضغط هنا لفتح صفحة الدفع بالبطاقة]({payment_url})", unsafe_allow_html=True)

    st.markdown("---")
    if st.button("حفظ وتوليد فاتورة PDF", type="primary", key="btn_save_inv"):
        if inv_name and inv_emp:
            conn = get_db_connection()
            cursor = conn.cursor()
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("INSERT INTO invoices (branch, customer_name, phone, address, ref_no, invoice_no, amount, moms, currency, moms_rate, employee, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (global_branch, inv_name, inv_phone, inv_address, "", inv_no, item_price, moms, "SEK", "25%", inv_emp, created_at))
            conn.commit()
            conn.close()
            st.success("✅ تم حفظ الفاتورة!")
            
            record_data = {"branch": global_branch, "customer_name": inv_name, "address": inv_address, "phone": inv_phone, "ref_no": "", "invoice_no": inv_no, "amount": item_price, "moms": moms, "currency": "SEK", "moms_rate": "25%", "item_desc": "Reparation", "employee": inv_emp, "created_at": date.today().strftime('%Y-%m-%d')}
            st.session_state['inv_pdf'] = generate_pdf_from_record("invoice", record_data, COMPANY_INFO)

    if 'inv_pdf' in st.session_state:
        display_pdf_preview(st.session_state['inv_pdf'], file_name="invoice.pdf")
    st.markdown("</div>", unsafe_allow_html=True)

# --- TAB 5: SUBSCRIPTIONS ---
with tab5:
    st.markdown("<div class='sub-box'>", unsafe_allow_html=True)
    st.header(f"💳 الاشتراكات وضمان IMEI / Subscriptions ({global_branch})")
    sub_emp = st.text_input(t["employee"], key="sub_emp")
    sub_imei = st.text_input(t["imei"], key="sub_imei")
    sub_name = st.text_input(t["customer_name"], key="sub_name")
    if st.button("Spara Abonnemang", type="primary", key="btn_save_sub"):
        if sub_imei and sub_name:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO subscriptions (branch, customer_name, phone, device, imei, plan_type, price, employee, start_date, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (global_branch, sub_name, "", "", sub_imei, "Glass Protection", 99.0, sub_emp, date.today().strftime('%Y-%m-%d'), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
            conn.close()
            st.success("✅ تم حفظ الاشتراك وربطه برقم الـ IMEI!")
    st.markdown("</div>", unsafe_allow_html=True)

# --- TAB 6: PRE-ORDERS ---
with tab6:
    st.markdown("<div class='preorder-box'>", unsafe_allow_html=True)
    st.header(f"🛒 الطلب المسبق / Pre-orders ({global_branch})")
    pre_emp = st.text_input(t["employee"], key="pre_emp")
    pre_name = st.text_input(t["customer_name"], key="pre_name")
    if st.button("حفظ الطلب المسبق", type="primary", key="btn_save_pre"):
        if pre_name:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO preorders (branch, customer_name, phone, item_details, deposit, employee, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)", (global_branch, pre_name, "", "", 0.0, pre_emp, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
            conn.close()
            st.success("✅ تم حفظ الطلب المسبق!")
    st.markdown("</div>", unsafe_allow_html=True)

# --- TAB 7: INVENTORY ---
with tab7:
    st.markdown("<div class='inventory-box'>", unsafe_allow_html=True)
    st.header(f"📦 المخزون / Inventory ({global_branch})")
    part_name = st.text_input("اسم القطعة (e.g. iPhone Screen)")
    if st.button("حفظ في المخزون", type="primary", key="btn_add_stock"):
        if part_name:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO inventory (part_name, stock_qty, min_limit, branch) VALUES (?, ?, ?, ?)", (part_name, 5, 2, global_branch))
            conn.commit()
            conn.close()
            st.success("✅ تمت الإضافة للمخزون!")
    st.markdown("</div>", unsafe_allow_html=True)

# --- TAB 8: SEARCH & ARCHIVE ---
with tab8:
    st.markdown("<div class='search-box'>", unsafe_allow_html=True)
    st.header(f"🔍 الأرشيف والبحث / Search & Archive ({global_branch})")
    search_cat = st.selectbox("اختر القسم", ["repairs", "subscriptions", "preorders", "quotes", "invoices", "inventory"])
    conn = get_db_connection()
    df_search = pd.read_sql_query(f"SELECT * FROM {search_cat} WHERE branch = ? ORDER BY id DESC", conn, params=(global_branch,))
    conn.close()
    if not df_search.empty:
        st.dataframe(df_search, use_container_width=True)
    else:
        st.info("لا توجد بيانات مطابقة.")
    st.markdown("</div>", unsafe_allow_html=True)
