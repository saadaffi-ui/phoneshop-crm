import streamlit as st
import sqlite3
import os
import urllib.parse
from datetime import datetime, date, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import io
import pandas as pd
import base64

# --- Local SQLite Database Setup & Migration ---
def get_db_connection():
    conn = sqlite3.connect("local_crm.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
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
        CREATE TABLE IF NOT EXISTS buybacks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            branch TEXT, customer_name TEXT, phone TEXT, person_nummer TEXT,
            device TEXT, imei TEXT, purchase_price REAL, employee TEXT, created_at TEXT
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
            item_desc TEXT, amount REAL, moms REAL, currency TEXT, moms_rate TEXT, employee TEXT, created_at TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            part_name TEXT, stock_qty INTEGER, min_limit INTEGER, branch TEXT
        )
    """)
    
    try:
        cursor.execute("ALTER TABLE quotes ADD COLUMN profit REAL")
    except Exception:
        pass
        
    for tbl in ["subscriptions", "repairs", "preorders", "quotes", "invoices", "buybacks"]:
        try:
            cursor.execute(f"ALTER TABLE {tbl} ADD COLUMN employee TEXT")
        except Exception:
            pass

    for col in ["address", "ref_no", "item_desc", "moms", "currency", "moms_rate"]:
        try:
            cursor.execute(f"ALTER TABLE invoices ADD COLUMN {col} TEXT")
        except Exception:
            pass

    conn.commit()
    conn.close()

init_db()

st.set_page_config(page_title="30 Minutes Phone Fix CRM", layout="wide", page_icon="📱")

# --- Custom Responsive Styling ---
st.markdown("""
<style>
    .stApp { background-color: #f4f6f9; color: #2c3e50; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    h1, h2, h3 { color: #1a252f; font-weight: 700; }
    div.stButton > button { border-radius: 8px; font-weight: 600; padding: 0.6rem 1.2rem; width: 100%; }
    .dashboard-box { background-color: #eaf2f8; padding: 20px; border-radius: 10px; border-left: 6px solid #2980b9; margin-bottom: 15px;}
    .repair-box { background-color: #e8f8f5; padding: 20px; border-radius: 10px; border-left: 6px solid #1abc9c; margin-bottom: 15px;}
    .quote-box { background-color: #fef9e7; padding: 20px; border-radius: 10px; border-left: 6px solid #f1c40f; margin-bottom: 15px;}
    .invoice-box { background-color: #f5eef8; padding: 20px; border-radius: 10px; border-left: 6px solid #8e44ad; margin-bottom: 15px;}
    .sub-box { background-color: #fbeee6; padding: 20px; border-radius: 10px; border-left: 6px solid #d35400; margin-bottom: 15px;}
    .buyback-box { background-color: #eafaf1; padding: 20px; border-radius: 10px; border-left: 6px solid #27ae60; margin-bottom: 15px;}
    .campaign-box { background-color: #fcf3cf; padding: 20px; border-radius: 10px; border-left: 6px solid #f39c12; margin-bottom: 15px;}
    .preorder-box { background-color: #e8f6f3; padding: 20px; border-radius: 10px; border-left: 6px solid #16a085; margin-bottom: 15px;}
    .inventory-box { background-color: #fbfcfe; padding: 20px; border-radius: 10px; border-left: 6px solid #e67e22; margin-bottom: 15px;}
    .search-box { background-color: #ebedef; padding: 20px; border-radius: 10px; border-left: 6px solid #34495e; margin-bottom: 15px;}
    .login-container { background: #ffffff; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); max-width: 450px; margin: auto; border-top: 5px solid #e74c3c; }
    
    .whatsapp-btn {
        display: inline-block;
        background-color: #25D366;
        color: white !important;
        padding: 0.6rem 1.2rem;
        border-radius: 8px;
        font-weight: 600;
        text-align: center;
        text-decoration: none;
        width: 100%;
        margin-top: 10px;
    }
    .whatsapp-btn:hover { background-color: #20ba5a; }

    @media only screen and (max-width: 1024px) {
        .stColumns { flex-direction: column !important; }
    }
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
        "tab_invoice": "📄 Faktura", "tab_sub": "💳 Abonnemang", "tab_buyback": "📱 Köp av Begagnad",
        "tab_campaign": "🎄 Kampanjer", "tab_preorder": "🛒 Förbeställning", "tab_stock": "📦 Lager", "tab_search": "🔍 Sök & Ärenden",
        "employee": "Handläggare / Säljare", "phone": "Telefonnummer", "customer_name": "Kundens namn",
        "email": "E-post (Valfritt)", "device": "Enhet / Modell", "imei": "IMEI / Serienummer",
        "price": "Pris", "issue": "Beskrivning av fel", "save_repair": "Spara Ärende", "success_repair": "✅ Ärendet har sparats!"
    },
    "English": {
        "tab_dash": "📊 Dashboard", "tab_repair": "🛠️ New Repair", "tab_quote": "💡 Quote",
        "tab_invoice": "📄 Invoice", "tab_sub": "💳 Subscriptions", "tab_buyback": "📱 Buyback / Used",
        "tab_campaign": "🎄 Campaigns", "tab_preorder": "🛒 Pre-order", "tab_stock": "📦 Inventory", "tab_search": "🔍 Search & Repairs",
        "employee": "Employee Name", "phone": "Phone Number", "customer_name": "Customer Name",
        "email": "Email (Optional)", "device": "Device Model", "imei": "IMEI / Serial Number",
        "price": "Price", "issue": "Issue Description", "save_repair": "Save Repair", "success_repair": "✅ Repair saved successfully!"
    },
    "العربية (Arabic)": {
        "tab_dash": "📊 لوحة التحكم", "tab_repair": "🛠️ إصلاح جديد", "tab_quote": "💡 عرض سعر",
        "tab_invoice": "📄 فاتورة", "tab_sub": "💳 الاشتراكات", "tab_buyback": "📱 شراء مستعمل",
        "tab_campaign": "🎄 عروض المواسم", "tab_preorder": "🛒 الطلب المسبق", "tab_stock": "📦 المخزون", "tab_search": "🔍 الأرشيف والحالات",
        "employee": "اسم الموظف المسؤول", "phone": "رقم الهاتف", "customer_name": "اسم البائع / العميل",
        "email": "البريد الإلكتروني", "device": "نوع وطراز الجهاز", "imei": "رقم الـ IMEI أو التسلسلي",
        "price": "السعر", "issue": "وصف العطل أو الإصلاح", "save_repair": "حفظ طلب الإصلاح", "success_repair": "✅ تم الحفظ بنجاح!"
    }
}

def get_whatsapp_link(phone, text):
    if not phone:
        return "#"
    clean_phone = phone.strip()
    if clean_phone.startswith("0"):
        clean_phone = "+46" + clean_phone[1:]
    return f"https://wa.me/{clean_phone}?text={urllib.parse.quote(text)}"

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
        system_pin = st.secrets["auth"].get("SYSTEM_PIN", "30min2026")
    except Exception:
        system_pin = "30min2026"
        
    st.markdown("<div class='login-container'>", unsafe_allow_html=True)
    st.markdown("### 🔒 System Login / Inloggning")
    st.markdown("Ange PIN-kod för att fortsätta / الرجاء إدخال رمز المرور:")
    login_pin = st.text_input("🔑 PIN Code / رمز المرور", type="password", key="login_pin_input")
    
    if login_pin == system_pin:
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
    st.success("✅ Dokumentet är redo för utskrift! / Document is ready!")
    
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

# --- PDF GENERATOR (SWEDISH STANDARD INVOICE & DUAL COPY REPAIR) ---
def generate_pdf_from_record(record_type, data, comp_info):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    branch = data.get('branch', 'Eskilstuna')
    comp = comp_info.get(branch, comp_info['Eskilstuna'])
    employee_name = data.get('employee', 'Ej angiven')
    currency = data.get('currency', 'SEK')
    moms_rate_str = data.get('moms_rate', '25%')

    if record_type == "repair_receipt_dual":
        def draw_repair_section(start_y, copy_title):
            p.setFont("Helvetica-Bold", 10)
            p.drawString(50, start_y, f"{comp['name']} - {copy_title}")
            p.setFont("Helvetica", 8)
            p.drawString(50, start_y - 12, f"Adress: {comp['address']} | Tel: {comp['phone']} | Org.nr: {comp['org_nr']}")
            
            p.setFont("Helvetica-Bold", 9)
            p.drawString(50, start_y - 28, f"ÄRENDEKVITTO / REPAIR RECEIPT #{data.get('repair_id', '1')}")
            p.setFont("Helvetica", 8)
            p.drawString(320, start_y - 28, f"Datum: {data.get('created_at', '')}")
            
            p.drawString(50, start_y - 42, f"Kund: {data.get('customer_name', '')}")
            p.drawString(320, start_y - 42, f"Handläggare: {employee_name}")
            p.drawString(50, start_y - 56, f"Tel: {data.get('phone', '')}")
            p.drawString(320, start_y - 56, f"Enhet: {data.get('device', '')}")
            p.drawString(50, start_y - 70, f"IMEI: {data.get('imei', 'Ej angivet')}")
            
            p.setFillColorRGB(0.92, 0.92, 0.92)
            p.rect(50, start_y - 92, width - 100, 14, fill=1, stroke=0)
            p.setFillColorRGB(0, 0, 0)
            p.setFont("Helvetica-Bold", 8)
            p.drawString(55, start_y - 88, "Beskrivning av fel / Repair Description")
            p.drawString(420, start_y - 88, f"Pris ({currency})")
            
            p.setFont("Helvetica", 8)
            p.drawString(55, start_y - 108, f"- {data.get('issue', '')}")
            price_val = data.get('price', 0)
            p.drawString(420, start_y - 108, f"{price_val:.2f} {currency}")
            
            p.setFont("Helvetica-Bold", 8)
            p.drawString(320, start_y - 124, f"Att betala / Total: {price_val:.2f} {currency} (Inkl. moms)")
            
            p.setFont("Helvetica", 7)
            p.drawString(50, start_y - 140, "Villkor: Garanti gäller endast utfört arbete. Vi ansvarar ej för förlorad data.")
            p.drawString(50, start_y - 150, f"Godkänt av kund / Terms Accepted (Swish: {comp['swish']} | Bankgiro: {comp['bankgiro']})")
            p.drawString(320, start_y - 150, "Kundens underskrift: _________________")

        draw_repair_section(height - 40, "BUTIKENS KOPIA / STORE COPY")
        p.setDash(3, 3)
        p.line(30, height / 2, width - 30, height / 2)
        p.setDash()
        draw_repair_section(height / 2 - 20, "KUNDENS KOPIA / CUSTOMER COPY")

    elif record_type == "buyback_receipt":
        p.setFont("Helvetica-Bold", 12)
        p.drawString(50, height - 110, "INKÖPSKVITTO - BEGAGNAD ENHET / PURCHASE RECEIPT")
        p.setFont("Helvetica", 10)
        p.drawString(50, height - 135, f"Kvitto ID: #{data.get('buyback_id', '1')}")
        p.drawString(300, height - 135, f"Datum: {data.get('created_at', '')}")
        p.drawString(50, height - 155, f"Säljare: {data.get('customer_name', '')}")
        p.drawString(300, height - 155, f"Personnummer: {data.get('person_nummer', 'Ej angivet')}")
        p.drawString(50, height - 175, f"Telefon: {data.get('phone', '')}")
        p.drawString(300, height - 175, f"Handläggare: {employee_name}")
        p.drawString(50, height - 195, f"Enhet: {data.get('device', '')}")
        p.drawString(300, height - 195, f"IMEI: {data.get('imei', '')}")
        
        price_val = data.get('purchase_price', 0)
        p.setFont("Helvetica-Bold", 11)
        p.drawString(300, height - 325, f"Utbetalat belopp / Total Paid: {price_val:.2f} {currency}")
        p.drawString(50, 45, f"Swish: {comp['swish']} | Bankgiro: {comp['bankgiro']}")

    elif record_type == "quote":
        p.setFont("Helvetica-Bold", 12)
        p.drawString(50, height - 110, "KOSTNADSFÖRSLAG / PRICE QUOTATION")
        p.setFont("Helvetica", 10)
        p.drawString(50, height - 135, f"Datum: {data.get('created_at', '')}")
        p.drawString(300, height - 135, f"Handläggare: {employee_name}")
        p.drawString(50, height - 155, f"Kund: {data.get('customer_name', '')}")
        p.drawString(50, height - 175, f"Telefon: {data.get('phone', '')}")
        p.drawString(300, height - 155, f"Enhet: {data.get('device', '')}")
        
        total_val = data.get('total', 0)
        p.setFont("Helvetica-Bold", 11)
        p.drawString(300, height - 345, f"Att betala / Total: {total_val:.2f} {currency} (Inkl. moms)")
        p.drawString(50, 45, f"Swish: {comp['swish']} | Bankgiro: {comp['bankgiro']}")

    elif record_type == "invoice":
        # --- SWEDISH STANDARD INVOICE FORMAT ---
        p.setFont("Helvetica-Bold", 16)
        p.drawString(50, height - 50, "FAKTURA")
        
        p.setFont("Helvetica-Bold", 9)
        p.drawString(400, height - 40, comp["name"])
        p.setFont("Helvetica", 8)
        p.drawString(400, height - 52, comp["address"])
        p.drawString(400, height - 64, f"Org.nr: {comp['org_nr']}")
        p.drawString(400, height - 76, f"Tel: {comp['phone']}")
        p.drawString(400, height - 88, f"Swish: {comp['swish']} | Bankgiro: {comp['bankgiro']}")

        p.setLineWidth(0.5)
        p.line(50, height - 105, width - 50, height - 105)

        # Invoice metadata box
        p.setFont("Helvetica-Bold", 9)
        p.drawString(50, height - 125, "Fakturainformation")
        p.setFont("Helvetica", 9)
        p.drawString(50, height - 140, f"Fakturanummer: {data.get('invoice_no', '')}")
        p.drawString(50, height - 155, f"Fakturadatum: {data.get('created_at', '')}")
        p.drawString(50, height - 170, f"Förfallodatum: {data.get('due_date', '')}")
        p.drawString(50, height - 185, f"Vår referens: {employee_name}")
        p.drawString(50, height - 200, f"Er referens: {data.get('ref_no', 'Ej angiven')}")

        # Buyer info box
        p.setFont("Helvetica-Bold", 9)
        p.drawString(320, height - 125, "Köpare / Kund")
        p.setFont("Helvetica", 9)
        p.drawString(320, height - 140, f"{data.get('customer_name', '')}")
        p.drawString(320, height - 155, f"{data.get('address', '')}")
        p.drawString(320, height - 170, f"Tel: {data.get('phone', '')}")

        # Table Header
        p.setFillColorRGB(0.9, 0.9, 0.9)
        p.rect(50, height - 235, width - 100, 18, fill=1, stroke=0)
        p.setFillColorRGB(0, 0, 0)
        p.setFont("Helvetica-Bold", 8)
        p.drawString(60, height - 228, "Artikel / Beskrivning")
        p.drawString(320, height - 228, "Moms")
        p.drawString(390, height - 228, f"Pris ({currency})")
        p.drawString(470, height - 228, f"Totalt ({currency})")

        amount_val = data.get('amount', 0)
        moms_val = data.get('moms', 0)
        netto_val = amount_val - moms_val

        p.setFont("Helvetica", 9)
        p.drawString(60, height - 260, data.get('item_desc', 'Reparation och reservdelar'))
        p.drawString(320, height - 260, moms_rate_str)
        p.drawString(390, height - 260, f"{netto_val:.2f}")
        p.drawString(470, height - 260, f"{amount_val:.2f}")

        # Summary box at bottom right
        p.line(320, height - 330, width - 50, height - 330)
        p.setFont("Helvetica", 9)
        p.drawString(320, height - 345, "Netto / Exkl. moms:")
        p.drawString(470, height - 345, f"{netto_val:.2f} {currency}")
        
        p.drawString(320, height - 362, f"Moms ({moms_rate_str}):")
        p.drawString(470, height - 362, f"{moms_val:.2f} {currency}")

        p.setFont("Helvetica-Bold", 11)
        p.drawString(320, height - 385, "Att betala / Total:")
        p.drawString(470, height - 385, f"{amount_val:.2f} {currency}")

        # Footer payment info
        p.setFont("Helvetica-Bold", 8)
        p.drawString(50, 60, f"Betalning sker via Bankgiro: {comp['bankgiro']} eller Swish: {comp['swish']}.")
        p.drawString(50, 48, f"Innehar F-skattsedel | Org.nr: {comp['org_nr']}")

    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10 = st.tabs([
    t["tab_dash"], t["tab_repair"], t["tab_quote"], t["tab_invoice"], 
    t["tab_sub"], t["tab_buyback"], t["tab_campaign"], t["tab_preorder"], t["tab_stock"], t["tab_search"]
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

# --- TAB 2: NEW REPAIR (DUAL COPY & TERMS ACCEPTANCE) ---
with tab2:
    st.markdown("<div class='repair-box'>", unsafe_allow_html=True)
    st.header(f"🛠️ تسجيل إصلاح جديد وتوليد إيصال الاستلام (نسختان) / New Repair ({global_branch})")
    employee_name = st.text_input(t["employee"], key="rep_emp")
    c_phone = st.text_input(t["phone"], key="rep_phone")
    
    auto_name, auto_email = "", ""
    if c_phone and len(c_phone) > 5:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT customer_name, email FROM repairs WHERE phone = ? LIMIT 1", (c_phone,))
            res = cursor.fetchone()
            conn.close()
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
        <b>⚠️ شروط الضمان وإخلاء المسؤولية (Warranty & Disclaimer Terms):</b><br>
        • الضمان يغطي فقط الإصلاح أو القطعة التي تم استبدالها.<br>
        • لا تتحمل الورشة أي مسؤولية عن ضياع البيانات أو محتويات الهاتف.
    </div>
    """, unsafe_allow_html=True)
    
    terms_accepted = st.checkbox("✅ أوافق على شروط الضمان وإصلاح الجهاز (Accept Terms & Conditions)", key="rep_terms_chk")

    if st.button(t["save_repair"], type="primary", key="btn_save_rep"):
        if not terms_accepted:
            st.error("❌ يجب الموافقة على شروط الضمان أولاً لحفظ Ärende!")
        elif c_name and c_phone and device and employee_name:
            conn = get_db_connection()
            cursor = conn.cursor()
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(
                "INSERT INTO repairs (branch, customer_name, phone, email, device, imei, issue, price, status, employee, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (global_branch, c_name, c_phone, c_email, device, imei, issue, price, "Under behandling", employee_name, created_at)
            )
            repair_db_id = cursor.lastrowid

            for selected_part in selected_rep_issues:
                cursor.execute("UPDATE inventory SET stock_qty = stock_qty - 1 WHERE branch = ? AND part_name = ? AND stock_qty > 0", (global_branch, selected_part))

            conn.commit()
            conn.close()
            st.success(t["success_repair"])
            
            rec_data = {
                "branch": global_branch, "repair_id": str(repair_db_id), "customer_name": c_name,
                "phone": c_phone, "device": device, "imei": imei, "issue": issue,
                "price": price, "employee": employee_name, "created_at": date.today().strftime('%Y-%m-%d')
            }
            st.session_state['rep_receipt_pdf'] = generate_pdf_from_record("repair_receipt_dual", rec_data, COMPANY_INFO)
        else:
            st.warning("⚠️ يرجى تعبئة الحقول الأساسية واسم الموظف.")

    if c_phone:
        rep_wa_text = f"Hej {c_name or 'Kunden'}! Ditt ärende för {device or 'enhet'} hos 30 Minutes Phone Fix ({global_branch}) har registrerats. Pris: {price} SEK. Välkommen!"
        st.markdown(f'<a href="{get_whatsapp_link(c_phone, rep_wa_text)}" target="_blank" class="whatsapp-btn">💬 إرسال تفاصيل الإصلاح عبر WhatsApp للعميل</a>', unsafe_allow_html=True)

    if 'rep_receipt_pdf' in st.session_state:
        st.markdown("---")
        display_pdf_preview(st.session_state['rep_receipt_pdf'], file_name="Inlamningskvitto_Dual.pdf")
    st.markdown("</div>", unsafe_allow_html=True)

# --- TAB 3: QUOTE ---
with tab3:
    st.markdown("<div class='quote-box'>", unsafe_allow_html=True)
    st.header(f"💡 عرض سعر وحساب الأرباح / Price Quotation ({global_branch})")
    q_emp = st.text_input(t["employee"], key="q_emp")
    q_name = st.text_input(t["customer_name"], key="q_name")
    q_phone = st.text_input(t["phone"], key="q_phone")
    q_device = st.text_input(t["device"], key="q_device")

    st.markdown("---")
    st.subheader("🛠️ اختر قطع الغيار وحساب الأرباح / Select parts & calculation")
    quote_items = [
        ("Skärmbyte", "qp_s", "qc_s"),
        ("Batteribyte", "qp_b", "qc_b"),
        ("Laddport", "qp_l", "qc_l"),
        ("Baksida", "qp_bk", "qc_bk"),
        ("Övrigt / Utförande", "qp_o", "qc_o")
    ]
    
    issues_list = []
    total_price = 0.0
    total_cost = 0.0

    for label, p_key, c_key in quote_items:
        if st.checkbox(label, key=f"chk_{p_key}"):
            col_p, col_c = st.columns(2)
            with col_p:
                p_val = st.number_input(f"Kundpris / Customer price ({label})", min_value=0.0, step=50.0, key=p_key)
            with col_c:
                c_val = st.number_input(f"Vår kostnad / Our cost ({label})", min_value=0.0, step=10.0, key=c_key)
            issues_list.append(f"{label}: {p_val} SEK")
            total_price += p_val
            total_cost += c_val

    net_profit = float(total_price - total_cost)
    st.markdown(f"### 💰 الإجمالي / Total: **{total_price:.2f} SEK** | 📈 الربح / Net Profit: **{net_profit:.2f} SEK**")

    if st.button("حفظ وتوليد عرض سعر PDF / Save Quote PDF", type="primary", key="btn_save_q"):
        if q_name and q_device and issues_list and q_emp:
            conn = get_db_connection()
            cursor = conn.cursor()
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            issues_str = ", ".join(issues_list)
            cursor.execute("INSERT INTO quotes (branch, customer_name, phone, email, device, issues, total, profit, employee, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (global_branch, q_name, q_phone, "", q_device, issues_str, total_price, net_profit, q_emp, created_at))
            conn.commit()
            conn.close()
            st.success("✅ تم حفظ عرض السعر بنجاح!")
            
            record_data = {"branch": global_branch, "customer_name": q_name, "phone": q_phone, "device": q_device, "issues": issues_str, "total": total_price, "currency": "SEK", "employee": q_emp, "created_at": date.today().strftime('%Y-%m-%d')}
            st.session_state['q_pdf'] = generate_pdf_from_record("quote", record_data, COMPANY_INFO)

    if q_phone:
        q_wa_text = f"Hej {q_name or 'Kunden'}! Här är kostnadsförslag för {q_device or 'enhet'} hos 30 Minutes Phone Fix ({global_branch}). Totalt: {total_price:.2f} SEK. Välkommen!"
        st.markdown(f'<a href="{get_whatsapp_link(q_phone, q_wa_text)}" target="_blank" class="whatsapp-btn">💬 إرسال عرض السعر عبر WhatsApp للعميل</a>', unsafe_allow_html=True)

    if 'q_pdf' in st.session_state:
        display_pdf_preview(st.session_state['q_pdf'], file_name="quote.pdf")
    st.markdown("</div>", unsafe_allow_html=True)

# --- TAB 4: INVOICE (SWEDISH STANDARD) ---
with tab4:
    st.markdown("<div class='invoice-box'>", unsafe_allow_html=True)
    st.header(f"📄 فاتورة بمعيار الفوترة السويدي / Swedish Standard Invoice ({global_branch})")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM invoices WHERE branch = ?", (global_branch,))
    inv_count_db = cursor.fetchone()[0]
    conn.close()
    default_inv_no = f"FAK-{date.today().year}-{inv_count_db + 1001}"

    inv_emp = st.text_input(t["employee"], key="inv_emp")
    inv_no = st.text_input("رقم الفاتورة / Fakturanummer", value=default_inv_no, key="inv_no_in")
    ref_no = st.text_input("إشارة المرجع أو طلب العميل / Er referens", value="", key="inv_ref_in")

    st.markdown("---")
    st.subheader("👤 بيانات العميل وعنوان الإرسال / Buyer Address")
    inv_name = st.text_input("اسم العميل أو الشركة / Kund / Företag", key="inv_name")
    inv_address = st.text_input("عنوان الشارع والمدينة / Gatuadress, Postnummer Ort", value="Drottninggatan 1, 632 20 Eskilstuna", key="inv_addr_in")
    inv_phone = st.text_input(t["phone"], key="inv_phone")
    
    st.markdown("---")
    st.subheader("💰 تفاصيل المبلغ والضريبة / Amount & VAT")
    inv_item_desc = st.text_input("وصف الخدمة أو البند / Item Description", value="Reparation och reservdelar / Repair & parts", key="inv_item_desc_in")
    inv_amount = st.number_input("المبلغ الإجمالي شامل الضريبة / Total Amount (SEK)", min_value=0.0, step=50.0, key="inv_amount_in")
    moms_rate_choice = st.selectbox("نسبة ضريبة القيمة المضافة / Moms rate", ["25%", "12%", "6%", "0%"], key="inv_moms_rate_in")
    
    rate_val = float(moms_rate_choice.replace("%", "")) / 100.0
    calc_moms = inv_amount - (inv_amount / (1.0 + rate_val)) if rate_val > 0 else 0.0
    due_date_val = (date.today() + timedelta(days=30)).strftime('%Y-%m-%d')

    st.markdown(f"**المبلغ صافي بدون ضريبة (Netto):** {(inv_amount - calc_moms):.2f} SEK | **مبلغ الضريبة (Moms):** {calc_moms:.2f} SEK | **تاريخ الاستحقاق (30 يوم):** {due_date_val}")

    if st.button("حفظ وتوليد الفاتورة بالسعي السويدي PDF / Save & Generate Invoice PDF", type="primary", key="btn_save_inv"):
        if inv_name and inv_amount > 0 and inv_emp:
            conn = get_db_connection()
            cursor = conn.cursor()
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("""
                INSERT INTO invoices (branch, customer_name, phone, address, ref_no, invoice_no, item_desc, amount, moms, currency, moms_rate, employee, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (global_branch, inv_name, inv_phone, inv_address, ref_no, inv_no, inv_item_desc, inv_amount, calc_moms, "SEK", moms_rate_choice, inv_emp, created_at))
            conn.commit()
            conn.close()
            st.success("✅ تم حفظ الفاتورة بنجاح وفقاً للمعايير السويدية!")

            inv_data = {
                "branch": global_branch, "invoice_no": inv_no, "customer_name": inv_name,
                "address": inv_address, "phone": inv_phone, "item_desc": inv_item_desc,
                "amount": inv_amount, "moms": calc_moms, "currency": "SEK", "moms_rate": moms_rate_choice,
                "employee": inv_emp, "created_at": date.today().strftime('%Y-%m-%d'), "due_date": due_date_val, "ref_no": ref_no
            }
            st.session_state['inv_pdf'] = generate_pdf_from_record("invoice", inv_data, COMPANY_INFO)

    if inv_phone:
        inv_wa_text = f"Hej {inv_name or 'Kunden'}! Här är er faktura ({inv_no}) från 30 Minutes Phone Fix ({global_branch}). Att betala: {inv_amount:.2f} SEK. Förfallodatum: {due_date_val}. Tack!"
        st.markdown(f'<a href="{get_whatsapp_link(inv_phone, inv_wa_text)}" target="_blank" class="whatsapp-btn">💬 إرسال تفاصيل الفاتورة عبر WhatsApp للعميل</a>', unsafe_allow_html=True)

    if 'inv_pdf' in st.session_state:
        display_pdf_preview(st.session_state['inv_pdf'], file_name=f"{inv_no}.pdf")
    st.markdown("</div>", unsafe_allow_html=True)

# --- TAB 5: SUBSCRIPTIONS ---
with tab5:
    st.markdown("<div class='sub-box'>", unsafe_allow_html=True)
    st.header(f"💳 إدارة الاشتراكات وخدمات الحماية / Subscriptions ({global_branch})")
    sub_emp = st.text_input(t["employee"], key="sub_emp")
    sub_name = st.text_input(t["customer_name"], key="sub_name")
    sub_phone = st.text_input(t["phone"], key="sub_phone")
    sub_device = st.text_input(t["device"], key="sub_device")
    sub_imei = st.text_input(t["imei"], key="sub_imei")
    
    plan_types = ["Skärmskydd + Fodral (Månad)", "Företagsavtal / Service", "Mobilförsäkring Basic", "Mobilförsäkring Premium"]
    sub_plan = st.selectbox("نوع الاشتراك / Plan Type", plan_types, key="sub_plan_sel")
    sub_price = st.number_input("قيمة الاشتراك الشهري / Monthly Price (SEK)", min_value=0.0, step=20.0, key="sub_price_in")

    if st.button("حفظ الاشتراك / Save Subscription", type="primary", key="btn_save_sub"):
        if sub_name and sub_phone and sub_emp:
            conn = get_db_connection()
            cursor = conn.cursor()
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("""
                INSERT INTO subscriptions (branch, customer_name, phone, device, imei, plan_type, price, employee, start_date, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (global_branch, sub_name, sub_phone, sub_device, sub_imei, sub_plan, sub_price, sub_emp, date.today().strftime('%Y-%m-%d'), created_at))
            conn.commit()
            conn.close()
            st.success("✅ تم تسجيل الاشتراك بنجاح!")

    st.markdown("---")
    st.subheader("📋 قائمة الاشتراكات النشطة / Active Subscriptions")
    conn = get_db_connection()
    sub_df = pd.read_sql_query("SELECT id, customer_name, phone, device, plan_type, price, employee, start_date FROM subscriptions WHERE branch = ?", conn, params=(global_branch,))
    conn.close()
    if not sub_df.empty:
        st.dataframe(sub_df, use_container_width=True)
    else:
        st.info("لا توجد اشتراكات مسجلة بعد في هذا الفرع.")
    st.markdown("</div>", unsafe_allow_html=True)

# --- TAB 6: BUYBACK / BEGAGNAD ---
with tab6:
    st.markdown("<div class='buyback-box'>", unsafe_allow_html=True)
    st.header(f"📱 شراء الأجهزة المستعملة وإيصال الشراء / Buyback & Used Phones ({global_branch})")
    bb_emp = st.text_input(t["employee"], key="bb_emp")
    bb_name = st.text_input(t["customer_name"], key="bb_name")
    bb_phone = st.text_input(t["phone"], key="bb_phone")
    bb_person = st.text_input("الرقم الشخصي للبائع / Personnummer (YYYYMMDD-XXXX)", key="bb_person_in")
    bb_device = st.text_input(t["device"], key="bb_device")
    bb_imei = st.text_input(t["imei"], key="bb_imei")
    bb_price = st.number_input("مبلغ الشراء المدفوع للعميل / Purchase Price (SEK)", min_value=0.0, step=50.0, key="bb_price_in")

    st.markdown("""
    <div style="background-color: #e8faf1; padding: 12px; border-radius: 8px; border-left: 5px solid #27ae60; font-size: 13px; margin-top: 10px; margin-bottom: 10px;">
        <b>📜 إقرار البائع (Seller Declaration):</b><br>
        أقر أنا البائع بأن الجهاز ملكي القانوني وليس مسروقاً، وأنه تم تسجيل خروج حسابات (iCloud / Google).
    </div>
    """, unsafe_allow_html=True)

    if st.button("حفظ وتوليد إيصال الشراء PDF / Save Buyback Receipt", type="primary", key="btn_save_bb"):
        if bb_name and bb_phone and bb_person and bb_device and bb_emp:
            conn = get_db_connection()
            cursor = conn.cursor()
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("""
                INSERT INTO buybacks (branch, customer_name, phone, person_nummer, device, imei, purchase_price, employee, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (global_branch, bb_name, bb_phone, bb_person, bb_device, bb_imei, bb_price, bb_emp, created_at))
            bb_db_id = cursor.lastrowid
            conn.commit()
            conn.close()
            st.success("✅ تم حفظ عملية الشراء بنجاح!")

            bb_data = {
                "branch": global_branch, "buyback_id": str(bb_db_id), "customer_name": bb_name,
                "phone": bb_phone, "person_nummer": bb_person, "device": bb_device, "imei": bb_imei,
                "purchase_price": bb_price, "currency": "SEK", "employee": bb_emp, "created_at": date.today().strftime('%Y-%m-%d')
            }
            st.session_state['bb_pdf'] = generate_pdf_from_record("buyback_receipt", bb_data, COMPANY_INFO)

    if 'bb_pdf' in st.session_state:
        display_pdf_preview(st.session_state['bb_pdf'], file_name="Inkopskvitto.pdf")
    st.markdown("</div>", unsafe_allow_html=True)

# --- TAB 7: CAMPAIGNS ---
with tab7:
    st.markdown("<div class='campaign-box'>", unsafe_allow_html=True)
    st.header(f"🎄 عروض المواسم والحملات التسويقية / Campaigns & Promotions ({global_branch})")
    st.markdown("""
    ### 🌟 عروض الشهر الحالي (Current Active Campaigns)
    - **🎄 عروض العيد والربيع (Spring & Holiday Special):** خصم 15% على جميع خدمات استبدال الشاشات الأصلية.
    - **📱 عرض الحماية المتكاملة:** شاشة حماية مع غطاء حماية أصلي بسعر مخفض عند إصلاح هاتفك.
    - **🎓 خصم الطلاب (Student Discount):** 10% خصم إضافي لجميع الطلاب عند إبراز بطاقة الطالب.
    """)
    st.info("💡 يمكنك إبلاغ العميل بهذه العروض أثناء تسجيل الإصلاح أو عرض السعر لزيادة المبيعات!")
    st.markdown("</div>", unsafe_allow_html=True)

# --- TAB 8: PRE-ORDERS ---
with tab8:
    st.markdown("<div class='preorder-box'>", unsafe_allow_html=True)
    st.header(f"🛒 الطلبات المسبقة وحجز القطع / Pre-orders ({global_branch})")
    po_emp = st.text_input(t["employee"], key="po_emp")
    po_name = st.text_input(t["customer_name"], key="po_name")
    po_phone = st.text_input(t["phone"], key="po_phone")
    po_details = st.text_area("تفاصيل القطعة أو الجهاز المحجوز / Item Details", key="po_details_in")
    po_deposit = st.number_input("العربون المدفوع / Deposit (SEK)", min_value=0.0, step=50.0, key="po_deposit_in")

    if st.button("حفظ الطلب المسبق / Save Pre-order", type="primary", key="btn_save_po"):
        if po_name and po_phone and po_details and po_emp:
            conn = get_db_connection()
            cursor = conn.cursor()
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("""
                INSERT INTO preorders (branch, customer_name, phone, item_details, deposit, employee, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (global_branch, po_name, po_phone, po_details, po_deposit, po_emp, created_at))
            conn.commit()
            conn.close()
            st.success("✅ تم حفظ الطلب المسبق بنجاح!")

    st.markdown("---")
    st.subheader("📋 قائمة الطلبات المسبقة / Pre-orders List")
    conn = get_db_connection()
    po_df = pd.read_sql_query("SELECT id, customer_name, phone, item_details, deposit, employee, created_at FROM preorders WHERE branch = ?", conn, params=(global_branch,))
    conn.close()
    if not po_df.empty:
        st.dataframe(po_df, use_container_width=True)
    else:
        st.info("لا توجد طلبات مسبقة حالياً.")
    st.markdown("</div>", unsafe_allow_html=True)

# --- TAB 9: INVENTORY ---
with tab9:
    st.markdown("<div class='inventory-box'>", unsafe_allow_html=True)
    st.header(f"📦 إدارة المخزون وقطع الغيار / Inventory ({global_branch})")
    
    with st.form("add_inventory_form"):
        st.subheader("إضافة / تحديث قطع الغيار في المخزن")
        new_part = st.text_input("اسم القطعة أو الخدمة / Part Name", value="Skärmbyte (Original)")
        add_qty = st.number_input("الكمية المضافة / Quantity", min_value=1, value=5)
        min_lim = st.number_input("حد التنبيه الأدنى / Min Limit", min_value=1, value=2)
        submit_inv = st.form_submit_button("حفظ في المخزون / Save Inventory")
        if submit_inv and new_part:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id, stock_qty FROM inventory WHERE branch = ? AND part_name = ?", (global_branch, new_part))
            existing = cursor.fetchone()
            if existing:
                cursor.execute("UPDATE inventory SET stock_qty = stock_qty + ? WHERE id = ?", (add_qty, existing[0]))
            else:
                cursor.execute("INSERT INTO inventory (part_name, stock_qty, min_limit, branch) VALUES (?, ?, ?, ?)", (new_part, add_qty, min_lim, global_branch))
            conn.commit()
            conn.close()
            st.success(f"✅ تم تحديث مخزون {new_part} بنجاح!")

    st.markdown("---")
    st.subheader("📊 حالة المخزون الحالي / Current Stock Levels")
    conn = get_db_connection()
    inv_df = pd.read_sql_query("SELECT id, part_name, stock_qty, min_limit FROM inventory WHERE branch = ?", conn, params=(global_branch,))
    conn.close()
    if not inv_df.empty:
        st.dataframe(inv_df, use_container_width=True)
    else:
        st.info("المخزون فارغ حالياً في هذا الفرع.")
    st.markdown("</div>", unsafe_allow_html=True)

# --- TAB 10: SEARCH & ALL RECORDS ---
with tab10:
    st.markdown("<div class='search-box'>", unsafe_allow_html=True)
    st.header(f"🔍 البحث والأرشيف الشامل لكافة السجلات / Search & All Saved Records ({global_branch})")
    search_query = st.text_input("بحث بالاسم، رقم الهاتف، نوع الجهاز أو رقم الفاتورة / Search by Name, Phone, Device, Invoice No", key="global_search_input")
    
    conn = get_db_connection()
    q_like = f"%{search_query}%" if search_query else "%"
    
    st.subheader("📝 الإصلاحات (Repairs)")
    rep_res = pd.read_sql_query("SELECT id, customer_name, phone, device, issue, price, status, employee, created_at FROM repairs WHERE branch = ? AND (customer_name LIKE ? OR phone LIKE ? OR device LIKE ?)", conn, params=(global_branch, q_like, q_like, q_like))
    st.dataframe(rep_res, use_container_width=True)

    st.subheader("💡 عروض الأسعار (Quotes)")
    quote_res = pd.read_sql_query("SELECT id, customer_name, phone, device, issues, total, profit, employee, created_at FROM quotes WHERE branch = ? AND (customer_name LIKE ? OR phone LIKE ? OR device LIKE ?)", conn, params=(global_branch, q_like, q_like, q_like))
    st.dataframe(quote_res, use_container_width=True)

    st.subheader("📄 الفواتير (Invoices)")
    inv_res = pd.read_sql_query("SELECT id, invoice_no, customer_name, phone, address, amount, moms, employee, created_at FROM invoices WHERE branch = ? AND (customer_name LIKE ? OR phone LIKE ? OR invoice_no LIKE ?)", conn, params=(global_branch, q_like, q_like, q_like))
    st.dataframe(inv_res, use_container_width=True)

    st.subheader("💳 الاشتراكات (Subscriptions)")
    sub_res = pd.read_sql_query("SELECT id, customer_name, phone, device, plan_type, price, employee, start_date FROM subscriptions WHERE branch = ? AND (customer_name LIKE ? OR phone LIKE ? OR device LIKE ?)", conn, params=(global_branch, q_like, q_like, q_like))
    st.dataframe(sub_res, use_container_width=True)

    st.subheader("📱 شراء الأجهزة (Buybacks)")
    bb_res = pd.read_sql_query("SELECT id, customer_name, phone, person_nummer, device, purchase_price, employee, created_at FROM buybacks WHERE branch = ? AND (customer_name LIKE ? OR phone LIKE ? OR device LIKE ?)", conn, params=(global_branch, q_like, q_like, q_like))
    st.dataframe(bb_res, use_container_width=True)

    st.subheader("🛒 الطلبات المسبقة (Pre-orders)")
    po_res = pd.read_sql_query("SELECT id, customer_name, phone, item_details, deposit, employee, created_at FROM preorders WHERE branch = ? AND (customer_name LIKE ? OR phone LIKE ?)", conn, params=(global_branch, q_like, q_like))
    st.dataframe(po_res, use_container_width=True)

    st.subheader("📦 المخزون (Inventory)")
    inv_search = pd.read_sql_query("SELECT id, part_name, stock_qty, min_limit FROM inventory WHERE branch = ? AND part_name LIKE ?", conn, params=(global_branch, q_like))
    st.dataframe(inv_search, use_container_width=True)
    
    conn.close()
    st.markdown("</div>", unsafe_allow_html=True)
