import streamlit as st
import sqlite3
import os
import urllib.parse
from datetime import datetime, date, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import io
import pandas as pd
import base64

# Simple fallback signature canvas component integration using HTML5 Canvas
def render_signature_pad(key_prefix="sig"):
    html_code = f"""
    <div style="border:2px dashed #94a3b8; border-radius:10px; padding:10px; background:#f8fafc; text-align:center;">
        <p style="margin:0 0 5px 0; font-size:13px; font-weight:bold; color:#334155;">✍️ توقيع العميل إلكترونياً / Customer Digital Signature (Touch / Pen / Mouse)</p>
        <canvas id="canvas_{key_prefix}" width="400" height="130" style="border:1px solid #cbd5e1; background:#ffffff; border-radius:6px; cursor:crosshair; touch-action:none;"></canvas>
        <br/>
        <button type="button" onclick="clearCanvas_{key_prefix}()" style="margin-top:6px; padding:4px 12px; background:#ef4444; color:white; border:none; border-radius:4px; font-size:12px; cursor:pointer;">مسح التوقيع / Rensa</button>
        <input type="hidden" id="sig_data_{key_prefix}" name="sig_data_{key_prefix}">
        <script>
            var canvas_{key_prefix} = document.getElementById('canvas_{key_prefix}');
            var ctx_{key_prefix} = canvas_{key_prefix}.getContext('2d');
            var drawing = false;
            
            ctx_{key_prefix}.lineWidth = 2;
            ctx_{key_prefix}.strokeStyle = "#000000";

            function getPos(e) {{
                var rect = canvas_{key_prefix}.getBoundingClientRect();
                var clientX = e.clientX || (e.touches && e.touches[0].clientX);
                var clientY = e.clientY || (e.touches && e.touches[0].clientY);
                return {{
                    x: clientX - rect.left,
                    y: clientY - rect.top
                }};
            }}

            function startDraw(e) {{
                drawing = true;
                var p = getPos(e);
                ctx_{key_prefix}.beginPath();
                ctx_{key_prefix}.moveTo(p.x, p.y);
                if (e.type === 'touchstart') e.preventDefault();
            }}

            function draw(e) {{
                if (!drawing) return;
                var p = getPos(e);
                ctx_{key_prefix}.lineTo(p.x, p.y);
                ctx_{key_prefix}.stroke();
                if (e.type === 'touchmove') e.preventDefault();
            }}

            function stopDraw(e) {{
                drawing = false;
            }}

            canvas_{key_prefix}.addEventListener('mousedown', startDraw);
            canvas_{key_prefix}.addEventListener('mousemove', draw);
            canvas_{key_prefix}.addEventListener('mouseup', stopDraw);
            canvas_{key_prefix}.addEventListener('mouseleave', stopDraw);

            canvas_{key_prefix}.addEventListener('touchstart', startDraw, {{passive: false}});
            canvas_{key_prefix}.addEventListener('touchmove', draw, {{passive: false}});
            canvas_{key_prefix}.addEventListener('touchend', stopDraw);

            function clearCanvas_{key_prefix}() {{
                ctx_{key_prefix}.clearRect(0, 0, canvas_{key_prefix}.width, canvas_{key_prefix}.height);
            }}
        </script>
    </div>
    """
    return html_code

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
            cost_price REAL, status TEXT, employee TEXT,
            warranty_period TEXT, terms_accepted INTEGER, signature_b64 TEXT, created_at TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            branch TEXT, customer_name TEXT, phone TEXT,
            device TEXT, imei TEXT, plan_type TEXT,
            price REAL, employee TEXT, start_date TEXT, end_date TEXT, created_at TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS buybacks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            branch TEXT, customer_name TEXT, phone TEXT, person_nummer TEXT,
            id_verified INTEGER, device TEXT, imei TEXT, purchase_price REAL,
            condition_grade TEXT, employee TEXT, signature_b64 TEXT, created_at TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS preorders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            branch TEXT, customer_name TEXT, phone TEXT,
            item_details TEXT, deposit REAL, estimated_delivery TEXT,
            employee TEXT, status TEXT, created_at TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS quotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            branch TEXT, customer_name TEXT, phone TEXT, email TEXT,
            device TEXT, issues TEXT, total REAL, profit REAL,
            valid_until TEXT, employee TEXT, created_at TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            branch TEXT, customer_name TEXT, phone TEXT, address TEXT,
            org_no_cust TEXT, ref_no TEXT, invoice_no TEXT,
            item_desc TEXT, amount REAL, moms REAL, currency TEXT,
            moms_rate TEXT, payment_terms TEXT, due_date TEXT, employee TEXT, created_at TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            part_name TEXT, category TEXT, stock_qty INTEGER, min_limit INTEGER,
            purchase_cost REAL, selling_price REAL, branch TEXT
        )
    """)
    
    # Safe Migrations for schema updates
    for tbl, cols in [
        ("repairs", ["cost_price REAL", "warranty_period TEXT", "terms_accepted INTEGER", "signature_b64 TEXT"]),
        ("buybacks", ["id_verified INTEGER", "condition_grade TEXT", "signature_b64 TEXT"]),
        ("quotes", ["valid_until TEXT"]),
        ("invoices", ["org_no_cust TEXT", "payment_terms TEXT", "due_date TEXT"]),
        ("preorders", ["estimated_delivery TEXT", "status TEXT"]),
        ("inventory", ["category TEXT", "purchase_cost REAL", "selling_price REAL"])
    ]:
        for col in cols:
            try:
                cursor.execute(f"ALTER TABLE {tbl} ADD COLUMN {col}")
            except Exception:
                pass

    conn.commit()
    conn.close()

init_db()

st.set_page_config(page_title="30 Minutes Phone Fix CRM", layout="wide", page_icon="📱")

# --- Custom Responsive Styling & Mobile Optimizations ---
st.markdown("""
<style>
    .stApp { background-color: #f8fafc; color: #1e293b; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }
    h1, h2, h3 { color: #0f172a; font-weight: 700; }
    div.stButton > button { border-radius: 8px; font-weight: 600; padding: 0.6rem 1.2rem; width: 100%; transition: all 0.2s ease; }
    .dashboard-box { background-color: #ffffff; padding: 20px; border-radius: 12px; border-left: 6px solid #2563eb; box-shadow: 0 1px 3px rgba(0,0,0,0.05); margin-bottom: 15px;}
    .repair-box { background-color: #ffffff; padding: 20px; border-radius: 12px; border-left: 6px solid #0d9488; box-shadow: 0 1px 3px rgba(0,0,0,0.05); margin-bottom: 15px;}
    .quote-box { background-color: #ffffff; padding: 20px; border-radius: 12px; border-left: 6px solid #d97706; box-shadow: 0 1px 3px rgba(0,0,0,0.05); margin-bottom: 15px;}
    .invoice-box { background-color: #ffffff; padding: 20px; border-radius: 12px; border-left: 6px solid #7c3aed; box-shadow: 0 1px 3px rgba(0,0,0,0.05); margin-bottom: 15px;}
    .sub-box { background-color: #ffffff; padding: 20px; border-radius: 12px; border-left: 6px solid #ea580c; box-shadow: 0 1px 3px rgba(0,0,0,0.05); margin-bottom: 15px;}
    .buyback-box { background-color: #ffffff; padding: 20px; border-radius: 12px; border-left: 6px solid #16a34a; box-shadow: 0 1px 3px rgba(0,0,0,0.05); margin-bottom: 15px;}
    .campaign-box { background-color: #ffffff; padding: 20px; border-radius: 12px; border-left: 6px solid #ca8a04; box-shadow: 0 1px 3px rgba(0,0,0,0.05); margin-bottom: 15px;}
    .preorder-box { background-color: #ffffff; padding: 20px; border-radius: 12px; border-left: 6px solid #0891b2; box-shadow: 0 1px 3px rgba(0,0,0,0.05); margin-bottom: 15px;}
    .inventory-box { background-color: #ffffff; padding: 20px; border-radius: 12px; border-left: 6px solid #475569; box-shadow: 0 1px 3px rgba(0,0,0,0.05); margin-bottom: 15px;}
    .search-box { background-color: #ffffff; padding: 20px; border-radius: 12px; border-left: 6px solid #334155; box-shadow: 0 1px 3px rgba(0,0,0,0.05); margin-bottom: 15px;}
    .login-container { background: #ffffff; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.08); max-width: 450px; margin: auto; border-top: 5px solid #dc2626; }
    
    .whatsapp-btn {
        display: inline-block;
        background-color: #25D366;
        color: white !important;
        padding: 0.75rem 1.2rem;
        border-radius: 8px;
        font-weight: 600;
        text-align: center;
        text-decoration: none;
        width: 100%;
        margin-top: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    .whatsapp-btn:hover { background-color: #1da851; }

    .legal-notice {
        background-color: #f1f5f9;
        padding: 12px;
        border-radius: 8px;
        border-left: 4px solid #0284c7;
        font-size: 12px;
        margin-top: 10px;
        margin-bottom: 10px;
        color: #334155;
    }

    @media only screen and (max-width: 768px) {
        .stColumns { flex-direction: column !important; }
        div.stButton > button { width: 100% !important; font-size: 16px; padding: 0.8rem; }
    }
</style>
""", unsafe_allow_html=True)

COMPANY_INFO = {
    "Eskilstuna": {
        "name": "30 MINUTES PHONE FIX AB",
        "address": "Gunborg Nymans Väg 2, 632 32 Eskilstuna",
        "phone": "0700122444",
        "org_nr": "559370-8034",
        "vat_nr": "SE559370803401",
        "swish": "123 407 16 76",
        "bankgiro": "5837-0354",
        "f_skatt": "Godkänd för F-skatt",
        "email": "info@30phonefix.se"
    },
    "Västerås": {
        "name": "30 MINUTES PHONE FIX AB",
        "address": "Stora Gatan 12, 722 12 Västerås",
        "phone": "0700122444",
        "org_nr": "559537-1724",
        "vat_nr": "SE559537172401",
        "swish": "123 339 15 47",
        "bankgiro": "5837-0354",
        "f_skatt": "Godkänd för F-skatt",
        "email": "vasteras@30phonefix.se"
    }
}

TRANSLATIONS = {
    "Svenska": {
        "tab_dash": "📊 Översikt (Dashboard)", "tab_repair": "🛠️ Ny reparation (Ärende)", "tab_quote": "💡 Offert (Kostnadsförslag)",
        "tab_invoice": "📄 Faktura (Bokföring)", "tab_sub": "💳 Abonnemang & Trygghet", "tab_buyback": "📱 Inköp Begagnat (Begagnatkontroll)",
        "tab_campaign": "🎄 Kampanjer & ERB", "tab_preorder": "🛒 Förbeställning", "tab_stock": "📦 Lagerhantering", "tab_search": "🔍 Sök & Registrerade Ärenden",
        "employee": "Handläggare (Säljare)", "phone": "Telefonnummer", "customer_name": "Kundens Namn / Företag",
        "email": "E-postadress", "device": "Enhet / Modell", "imei": "IMEI / Serienummer",
        "price": "Pris inkl. moms (SEK)", "issue": "Beskrivning av fel / Utfört arbete", "save_repair": "Registrera Ärende & Skapa Kvitto (Två delar)", "success_repair": "✅ Ärendet har registrerats i enlighet med Konsumentköplagen!"
    },
    "English": {
        "tab_dash": "📊 Dashboard", "tab_repair": "🛠️ New Repair Order", "tab_quote": "💡 Price Quotation",
        "tab_invoice": "📄 Official Invoice", "tab_sub": "💳 Subscriptions", "tab_buyback": "📱 Buyback (Used Devices)",
        "tab_campaign": "🎄 Campaigns", "tab_preorder": "🛒 Pre-orders", "tab_stock": "📦 Stock Inventory", "tab_search": "🔍 Search & Archive",
        "employee": "Employee Name", "phone": "Phone Number", "customer_name": "Customer Name / Company",
        "email": "Email Address", "device": "Device Model", "imei": "IMEI / Serial Number",
        "price": "Price incl. VAT (SEK)", "issue": "Issue / Work Description", "save_repair": "Register Order & Dual Receipt", "success_repair": "✅ Service order registered successfully according to Swedish Consumer Law!"
    },
    "العربية (Arabic)": {
        "tab_dash": "📊 لوحة التحكم والإحصاءات", "tab_repair": "🛠️ تسجيل إصلاح جديد", "tab_quote": "💡 عرض سعر رسمي (Offert)",
        "tab_invoice": "📄 إنشاء فاتورة قانونية", "tab_sub": "💳 اشتراكات الصيانة والضمان", "tab_buyback": "📱 شراء المستعمل (مطابق للقانون)",
        "tab_campaign": "🎄 العروض الموسمية والتخفيضات", "tab_preorder": "🛒 الطلبات المسبقة والعربون", "tab_stock": "📦 إدارة القطع والمخزون", "tab_search": "🔍 السجلات والأرشيف القانوني",
        "employee": "اسم الموظف المسؤول", "phone": "رقم الهاتف", "customer_name": "اسم العميل / الشركة",
        "email": "البريد الإلكتروني", "device": "نوع وطراز الجهاز", "imei": "رقم الـ IMEI / التسلسلي",
        "price": "السعر شامل الضريبة 25% (SEK)", "issue": "تفاصيل العطل والخدمة المقدمة", "save_repair": "حفظ الطلب وتوليد الإيصال المزدوج (قسم للمحل وقسم للعميل)", "success_repair": "✅ تم تسجيل الطلب بنجاح مطابقاً لشروط مراكز الصيانة العالمية والقانون السويدي!"
    }
}

def get_whatsapp_link(phone, text):
    if not phone:
        return "#"
    clean_phone = phone.strip().replace(" ", "").replace("-", "")
    if clean_phone.startswith("0"):
        clean_phone = "+46" + clean_phone[1:]
    return f"https://wa.me/{clean_phone}?text={urllib.parse.quote(text)}"

# --- Top Header Bar ---
head_c1, head_c2, head_c3 = st.columns([1, 2, 2])
with head_c1:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=65)
with head_c2:
    lang_choice = st.selectbox("🌐 Language / Språk / اللغة", ["Svenska", "English", "العربية (Arabic)"], key="top_lang_bar")
with head_c3:
    global_branch = st.selectbox("🏢 Butik / Branch / الفرع", ["Eskilstuna", "Västerås"], key="top_branch_bar")

t = TRANSLATIONS[lang_choice]
comp = COMPANY_INFO[global_branch]

st.markdown(f"""
<div style="background-color: #ffffff; padding: 12px 18px; border-radius: 10px; border: 1px solid #cbd5e1; margin-bottom: 15px; font-size: 13px; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
    <b>🏢 Aktiverad Butik / Active Store:</b> {comp['name']} - {comp['address']} | <b>Tel:</b> {comp['phone']} | <b>Org.nr:</b> {comp['org_nr']} | <b>VAT:</b> {comp['vat_nr']} | <b>Swish:</b> {comp['swish']}
</div>
""", unsafe_allow_html=True)
st.markdown("---")

# --- Authentication & Remember Device System ---
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

if not st.session_state['authenticated'] and st.session_state.get('remember_device', False):
    st.session_state['authenticated'] = True

if not st.session_state['authenticated']:
    st.markdown("<div class='login-container'>", unsafe_allow_html=True)
    st.markdown("### 🔒 System Inloggning / System Login")
    st.markdown("Ange din behörighetskod för att komma åt CRM-systemet:")
    
    login_pin = st.text_input("🔑 PIN-kod / Passcode", type="password", key="login_pin_input")
    remember_me = st.checkbox("💾 Spara inloggning på denna enhet / تذكرني على هذا الجهاز", value=st.session_state.get('remember_device', False), key="remember_device_chk")
    
    if login_pin:
        if login_pin.strip() == "Tunapark":
            st.session_state['authenticated'] = True
            st.session_state['remember_device'] = remember_me
            st.success("✅ Inloggningen godkänd / Access granted!")
            st.rerun()
        else:
            st.error("❌ Felaktig PIN-kod / Invalid passcode!")
            
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

if st.sidebar.button("🔒 Logga ut (Log Out)"):
    st.session_state['authenticated'] = False
    st.session_state['remember_device'] = False
    st.rerun()

# --- PDF Viewer & Responsive Print Tool for Mobile/Tablet/PC ---
def display_pdf_preview(pdf_buffer, file_name="document.pdf", key_suffix="doc"):
    pdf_buffer.seek(0)
    pdf_bytes = pdf_buffer.read()
    b64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
    st.success("✅ Dokumentet har genererats i enlighet med Skatteverkets krav & Service-standard!")
    
    b_col1, b_col2, b_col3 = st.columns(3)
    with b_col1:
        st.download_button("📥 Ladda ner PDF", data=pdf_bytes, file_name=file_name, mime="application/pdf", type="primary", key=f"dl_{key_suffix}")
    with b_col2:
        pdf_data_uri = f"data:application/pdf;base64,{b64_pdf}"
        st.markdown(f'<a href="{pdf_data_uri}" target="_blank" style="display:inline-block; background-color:#2563eb; color:white; padding:0.65rem 1.2rem; border-radius:8px; font-weight:600; text-align:center; text-decoration:none; width:100%;">🌐 Öppna i ny flik / Visning</a>', unsafe_allow_html=True)
    with b_col3:
        print_html = f"""
        <script>
        function printPDF_{key_suffix}() {{
            var iframe = document.createElement('iframe');
            iframe.style.display = 'none';
            iframe.src = "data:application/pdf;base64,{b64_pdf}";
            document.body.appendChild(iframe);
            setTimeout(function() {{
                iframe.contentWindow.focus();
                iframe.contentWindow.print();
            }}, 300);
        }}
        </script>
        <button onclick="printPDF_{key_suffix}()" style="background-color: #16a34a; color: white; padding: 0.65rem 1.2rem; border: none; border-radius: 8px; font-weight: 600; width: 100%; cursor: pointer;">
            🖨️ Skriv ut Direct / Print (Mobil & PC)
        </button>
        """
        st.markdown(print_html, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 👁️ Förhandsgranskning / Document Preview")
    
    pdf_display = f"""
    <div style="text-align: center; border: 1px solid #cbd5e1; border-radius: 8px; padding: 10px; background: #fff;">
        <object data="data:application/pdf;base64,{b64_pdf}#toolbar=1&navpanes=0&scrollbar=1" type="application/pdf" width="100%" height="580px">
            <embed src="data:application/pdf;base64,{b64_pdf}" type="application/pdf" width="100%" height="580px" />
            <p style="padding: 20px;">📱 Mobilvisning: Klicka på knappen <b>"🖨️ Skriv ut Direct / Print"</b> eller <b>"Öppna i ny flik"</b> ovan för utskrift och visning.</p>
        </object>
    </div>
    """
    st.markdown(pdf_display, unsafe_allow_html=True)

# --- PDF ENGINE WITH DUAL RECEPT & APPLE/SAMSUNG COMPLIANT TERMS ---
def generate_pdf_from_record(record_type, data, comp_info):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    branch = data.get('branch', 'Eskilstuna')
    comp = comp_info.get(branch, comp_info['Eskilstuna'])
    employee_name = data.get('employee', 'Ej angiven')
    currency = data.get('currency', 'SEK')
    moms_rate_str = data.get('moms_rate', '25%')

    def draw_footer():
        p.setFont("Helvetica-Bold", 7.5)
        p.drawString(40, 35, f"{comp['name']} | Org.nr: {comp['org_nr']} | VAT: {comp['vat_nr']} | {comp['f_skatt']}")
        p.setFont("Helvetica", 7)
        p.drawString(40, 24, f"Adress: {comp['address']} | Tel: {comp['phone']} | Swish: {comp['swish']} | Bankgiro: {comp['bankgiro']}")

    if record_type == "repair_receipt_dual":
        def draw_repair_section(start_y, copy_title):
            p.setFont("Helvetica-Bold", 10)
            p.drawString(40, start_y, f"{comp['name']} ({copy_title})")
            p.setFont("Helvetica", 7)
            p.drawString(40, start_y - 11, f"Org.nr: {comp['org_nr']} | VAT: {comp['vat_nr']} | {comp['f_skatt']} | Tel: {comp['phone']}")
            p.drawString(40, start_y - 20, f"Adress: {comp['address']} | Swish: {comp['swish']} | Bankgiro: {comp['bankgiro']}")
            
            p.setFont("Helvetica-Bold", 9)
            p.drawString(40, start_y - 34, f"INLÄMNINGSKVITTO / REPAIR RECEIPT #{data.get('repair_id', '1')}")
            p.setFont("Helvetica", 7.5)
            p.drawString(360, start_y - 34, f"Datum: {data.get('created_at', '')}")
            
            p.drawString(40, start_y - 46, f"Kund: {data.get('customer_name', '')}")
            p.drawString(360, start_y - 46, f"Handläggare: {employee_name}")
            p.drawString(40, start_y - 56, f"Tel: {data.get('phone', '')}")
            p.drawString(360, start_y - 56, f"Enhet/Modell: {data.get('device', '')}")
            p.drawString(40, start_y - 66, f"IMEI/SN: {data.get('imei', 'Ej angivet')}")
            p.drawString(360, start_y - 66, f"Garanti: {data.get('warranty_period', '3 Månader')}")
            
            p.setFillColorRGB(0.93, 0.94, 0.96)
            p.rect(40, start_y - 84, width - 80, 13, fill=1, stroke=0)
            p.setFillColorRGB(0, 0, 0)
            p.setFont("Helvetica-Bold", 7.5)
            p.drawString(45, start_y - 80, "Beskrivning av fel & beställd reparation")
            p.drawString(440, start_y - 80, f"Pris inkl. moms")
            
            p.setFont("Helvetica", 7.5)
            p.drawString(45, start_y - 98, f"- {data.get('issue', '')}")
            price_val = data.get('price', 0.0)
            p.drawString(440, start_y - 98, f"{price_val:.2f} {currency}")
            
            moms_calc = price_val * (0.25 / 1.25)
            netto_calc = price_val - moms_calc
            p.setFont("Helvetica", 7)
            p.drawString(40, start_y - 114, f"Netto: {netto_calc:.2f} SEK | Moms (25%): {moms_calc:.2f} SEK")
            p.setFont("Helvetica-Bold", 8)
            p.drawString(340, start_y - 114, f"Totalt uppskattat pris: {price_val:.2f} {currency}")
            
            # Apple & Samsung Authorized Style Legal Standard Terms
            p.setFont("Helvetica-Bold", 6)
            p.drawString(40, start_y - 128, "SERVICEVILLKOR & KONSUMENTRÄTT (Standardiserade Servicevillkor):")
            p.setFont("Helvetica", 5.5)
            p.drawString(40, start_y - 135, "1. Inlämnad enhet genomgår inledande diagnos. Dolda fel (t.ex. fuktskador, böjt chassi eller tidigare ingrepp) ansvarar verkstaden ej för.")
            p.drawString(40, start_y - 141, "2. Garantin gäller endast utbytt del/utfört arbete i 3-12 månader. Garantin förverkas vid yttre åverkan, fall, vätska eller ingrepp av tredje part.")
            p.drawString(40, start_y - 147, "3. Ej uthämtade enheter efter 3 månader tillfaller verkstaden i enlighet med lag (1985:982) om näringsidkares rätt att sälja saker.")

            # Handle Signature (Electronic image or manual line)
            sig_b64 = data.get('signature_b64', '')
            if sig_b64 and len(sig_b64) > 100:
                try:
                    if "," in sig_b64:
                        sig_b64 = sig_b64.split(",")[1]
                    img_data = base64.b64decode(sig_b64)
                    img_buf = io.BytesIO(img_data)
                    p.drawImage(ImageReader(img_buf), 360, start_y - 175, width=120, height=30, mask='auto')
                    p.setFont("Helvetica", 6)
                    p.drawString(360, start_y - 178, "Elektroniskt signerad av kund")
                except Exception:
                    p.setFont("Helvetica", 6.5)
                    p.drawString(350, start_y - 165, "Kundens underskrift: _________________")
            else:
                p.setFont("Helvetica", 6.5)
                p.drawString(350, start_y - 165, "Kundens underskrift: _________________")

        # Top Portion: Store Copy
        draw_repair_section(height - 25, "BUTIKENS KOPIA / STORE COPY")
        
        # Divider Cut Line
        p.setDash(3, 3)
        p.setLineWidth(0.5)
        p.line(20, height / 2, width - 20, height / 2)
        p.setDash()
        p.setFont("Helvetica-Oblique", 6)
        p.drawString(width / 2 - 40, height / 2 + 3, "✂ Klipp här / Cut here")
        
        # Bottom Portion: Customer Copy
        draw_repair_section(height / 2 - 15, "KUNDENS KOPIA / CUSTOMER COPY")

    elif record_type == "buyback_receipt":
        p.setFont("Helvetica-Bold", 14)
        p.drawString(40, height - 40, comp["name"])
        p.setFont("Helvetica", 8)
        p.drawString(40, height - 52, f"Org.nr: {comp['org_nr']} | VAT: {comp['vat_nr']} | {comp['f_skatt']} | Tel: {comp['phone']}")
        p.drawString(40, height - 62, f"Adress: {comp['address']} | Swish: {comp['swish']} | Bankgiro: {comp['bankgiro']}")

        p.setFont("Helvetica-Bold", 11)
        p.drawString(40, height - 90, "INKÖPSKVITTO & ÄGARFÖRSÄKRAN (BEGAGNAD ELEKTRONIK)")
        p.setFont("Helvetica", 7.5)
        p.drawString(40, height - 100, "Upprättat i enlighet med lag (1999:158) om handel med begagnade varor och Polismyndighetens föreskrifter.")

        p.setFont("Helvetica-Bold", 9)
        p.drawString(40, height - 125, f"Kvitto Nr: BB-{data.get('buyback_id', '1')}")
        p.drawString(320, height - 125, f"Datum: {data.get('created_at', '')}")
        
        p.setFont("Helvetica", 8.5)
        p.drawString(40, height - 142, f"Säljare (Kund): {data.get('customer_name', '')}")
        p.drawString(320, height - 142, f"Personnummer: {data.get('person_nummer', '')}")
        p.drawString(40, height - 156, f"Telefon: {data.get('phone', '')}")
        p.drawString(320, height - 156, f"ID-Kontroll utförd: {'Ja (Godkänd)' if data.get('id_verified') else 'Nej'}")
        p.drawString(40, height - 170, f"Enhet/Modell: {data.get('device', '')}")
        p.drawString(320, height - 170, f"IMEI/Serienummer: {data.get('imei', '')}")
        p.drawString(40, height - 184, f"Skick/Gradering: {data.get('condition_grade', 'B-Skick')}")
        p.drawString(320, height - 184, f"Handläggare: {employee_name}")
        
        price_val = data.get('purchase_price', 0.0)
        p.setFillColorRGB(0.95, 0.95, 0.95)
        p.rect(40, height - 225, width - 80, 25, fill=1, stroke=0)
        p.setFillColorRGB(0, 0, 0)
        p.setFont("Helvetica-Bold", 10)
        p.drawString(50, height - 210, f"Utbetalt belopp till säljaren: {price_val:.2f} {currency}")

        p.setFont("Helvetica-Bold", 8)
        p.drawString(40, height - 260, "SÄLJARENS ÄGARFÖRSÄKRAN & JURIDISKA INTYGANDE:")
        p.setFont("Helvetica", 7)
        p.drawString(40, height - 272, "1. Undertecknad säljare intygar på heder och samvete att ovanstående enhet är min egna egendom och lagligt förvärvad.")
        p.drawString(40, height - 280, "2. Enheten är helt återställd, fri från avbetalningskontrakt, samt bortkopplad från iCloud/Google-konto och stöldspärrar.")
        p.drawString(40, height - 288, "3. Om enheten visar sig vara stulen eller belagd med stöldspärr kommer polisansökan omedelbart att upprättas.")

        sig_b64 = data.get('signature_b64', '')
        if sig_b64 and len(sig_b64) > 100:
            try:
                if "," in sig_b64:
                    sig_b64 = sig_b64.split(",")[1]
                img_data = base64.b64decode(sig_b64)
                img_buf = io.BytesIO(img_data)
                p.drawImage(ImageReader(img_buf), 40, height - 340, width=130, height=35, mask='auto')
                p.setFont("Helvetica", 7)
                p.drawString(40, height - 348, "Säljarens elektroniska underskrift")
            except Exception:
                p.drawString(40, height - 330, "Säljarens underskrift: ________________________")
        else:
            p.drawString(40, height - 330, "Säljarens underskrift: ________________________")

        p.drawString(320, height - 330, "Mottaget av handläggare: ________________________")
        draw_footer()

    elif record_type == "quote":
        p.setFont("Helvetica-Bold", 14)
        p.drawString(40, height - 40, comp["name"])
        p.setFont("Helvetica", 8)
        p.drawString(40, height - 52, f"Org.nr: {comp['org_nr']} | VAT: {comp['vat_nr']} | {comp['f_skatt']} | Tel: {comp['phone']}")
        p.drawString(40, height - 62, f"Adress: {comp['address']} | Swish: {comp['swish']} | Bankgiro: {comp['bankgiro']}")

        p.setFont("Helvetica-Bold", 12)
        p.drawString(40, height - 90, "OFFERT / KOSTNADSFÖRSLAG")
        p.setFont("Helvetica", 8.5)
        p.drawString(40, height - 110, f"Datum: {data.get('created_at', '')}")
        p.drawString(320, height - 110, f"Giltig till: {data.get('valid_until', '')}")
        p.drawString(40, height - 125, f"Kund: {data.get('customer_name', '')}")
        p.drawString(320, height - 125, f"Handläggare: {employee_name}")
        p.drawString(40, height - 140, f"Telefon: {data.get('phone', '')}")
        p.drawString(320, height - 140, f"Enhet: {data.get('device', '')}")
        
        p.setFillColorRGB(0.95, 0.95, 0.95)
        p.rect(40, height - 170, width - 80, 16, fill=1, stroke=0)
        p.setFillColorRGB(0, 0, 0)
        p.setFont("Helvetica-Bold", 8.5)
        p.drawString(50, height - 165, "Beskrivning av rekommenderat arbete / reservdelar")
        p.drawString(440, height - 165, "Belopp SEK")

        p.setFont("Helvetica", 8.5)
        p.drawString(50, height - 190, data.get('issues', ''))
        
        total_val = data.get('total', 0.0)
        moms_val = total_val * (0.25 / 1.25)
        netto_val = total_val - moms_val

        p.line(40, height - 230, width - 40, height - 230)
        p.setFont("Helvetica", 8.5)
        p.drawString(320, height - 245, f"Netto exkl. moms: {netto_val:.2f} SEK")
        p.drawString(320, height - 258, f"Moms (25%): {moms_val:.2f} SEK")
        p.setFont("Helvetica-Bold", 10)
        p.drawString(320, height - 275, f"Totalt inklusive moms: {total_val:.2f} SEK")

        p.setFont("Helvetica-Oblique", 7.5)
        p.drawString(40, height - 310, "Detta kostnadsförslag är ej bindande förrän det godkänts av kunden.")
        draw_footer()

    elif record_type == "invoice":
        p.setFont("Helvetica-Bold", 18)
        p.drawString(40, height - 45, "FAKTURA")
        
        p.setFont("Helvetica-Bold", 9)
        p.drawString(340, height - 35, comp["name"])
        p.setFont("Helvetica", 7.5)
        p.drawString(340, height - 46, comp["address"])
        p.drawString(340, height - 56, f"Org.nr: {comp['org_nr']} | VAT: {comp['vat_nr']}")
        p.drawString(340, height - 66, f"Tel: {comp['phone']} | E-post: {comp['email']}")
        p.drawString(340, height - 76, f"{comp['f_skatt']}")

        p.setLineWidth(0.5)
        p.line(40, height - 85, width - 40, height - 85)

        p.setFont("Helvetica-Bold", 8.5)
        p.drawString(40, height - 102, "FAKTURAUPPGIFTER")
        p.setFont("Helvetica", 8)
        p.drawString(40, height - 115, f"Fakturanummer: {data.get('invoice_no', '')}")
        p.drawString(40, height - 127, f"Fakturadatum: {data.get('created_at', '')}")
        p.drawString(40, height - 139, f"Förfallodatum: {data.get('due_date', '')}")
        p.drawString(40, height - 151, f"Betalningsvillkor: {data.get('payment_terms', '10 dagar')}")
        p.drawString(40, height - 163, f"Vår referens: {employee_name}")
        p.drawString(40, height - 175, f"Er referens: {data.get('ref_no', 'Ej angiven')}")

        p.setFont("Helvetica-Bold", 8.5)
        p.drawString(320, height - 102, "FAKTURERAS TILL (KUND)")
        p.setFont("Helvetica", 8)
        p.drawString(320, height - 115, f"Kund: {data.get('customer_name', '')}")
        p.drawString(320, height - 127, f"Org.nr / P.nr: {data.get('org_no_cust', 'Ej angivet')}")
        p.drawString(320, height - 139, f"Adress: {data.get('address', 'Ej angiven')}")
        p.drawString(320, height - 151, f"Tel: {data.get('phone', '')}")

        p.setFillColorRGB(0.92, 0.92, 0.92)
        p.rect(40, height - 200, width - 80, 16, fill=1, stroke=0)
        p.setFillColorRGB(0, 0, 0)
        p.setFont("Helvetica-Bold", 8)
        p.drawString(45, height - 194, "Beskrivning / Artikel")
        p.drawString(300, height - 194, "Moms %")
        p.drawString(370, height - 194, f"Pris exkl. moms")
        p.drawString(460, height - 194, f"Totalt SEK")

        amount_val = data.get('amount', 0.0)
        moms_val = data.get('moms', 0.0)
        netto_val = amount_val - moms_val

        p.setFont("Helvetica", 8.5)
        p.drawString(45, height - 220, data.get('item_desc', 'Reparationstjänst & reservdelar'))
        p.drawString(300, height - 220, moms_rate_str)
        p.drawString(370, height - 220, f"{netto_val:.2f}")
        p.drawString(460, height - 220, f"{amount_val:.2f}")

        p.line(300, height - 280, width - 40, height - 280)
        p.setFont("Helvetica", 8.5)
        p.drawString(300, height - 295, "Netto exkl. moms:")
        p.drawString(460, height - 295, f"{netto_val:.2f} SEK")
        
        p.drawString(300, height - 308, f"Moms ({moms_rate_str}):")
        p.drawString(460, height - 308, f"{moms_val:.2f} SEK")

        p.setFont("Helvetica-Bold", 10)
        p.drawString(300, height - 328, "ATT BETALA (SEK):")
        p.drawString(460, height - 328, f"{amount_val:.2f} SEK")

        p.setFont("Helvetica-Bold", 8)
        p.drawString(40, height - 360, f"BETALNINGSINFORMATION:")
        p.setFont("Helvetica", 8)
        p.drawString(40, height - 372, f"Bankgiro: {comp['bankgiro']} | Swish Handel: {comp['swish']}")
        p.drawString(40, height - 384, f"Ange Fakturanummer '{data.get('invoice_no', '')}' som betalningsreferens.")
        
        draw_footer()

    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

# --- TAB NAVIGATION SETUP ---
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10 = st.tabs([
    t["tab_dash"], t["tab_repair"], t["tab_quote"], t["tab_invoice"], 
    t["tab_sub"], t["tab_buyback"], t["tab_campaign"], t["tab_preorder"], t["tab_stock"], t["tab_search"]
])

# --- TAB 1: DASHBOARD ---
with tab1:
    st.markdown("<div class='dashboard-box'>", unsafe_allow_html=True)
    st.header(f"📊 Översikt & Nyckeltal / Financial Dashboard ({global_branch})")
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM repairs WHERE branch = ?", (global_branch,))
        rep_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM quotes WHERE branch = ?", (global_branch,))
        quote_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM invoices WHERE branch = ?", (global_branch,))
        inv_count = cursor.fetchone()[0]
        cursor.execute("SELECT SUM(price) FROM repairs WHERE branch = ?", (global_branch,))
        rep_revenue = cursor.fetchone()[0] or 0.0
        conn.close()
    except Exception:
        rep_count, quote_count, inv_count, rep_revenue = 0, 0, 0, 0.0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📝 Registrerade Reparationer", rep_count)
    c2.metric("💡 Utfärdade Offertförslag", quote_count)
    c3.metric("📄 Skapade Fakturor", inv_count)
    c4.metric("💰 Omsättning Reparationer", f"{rep_revenue:.2f} SEK")

    st.markdown("""
    <div class="legal-notice">
        📌 <b>Bokföring & Skatterätt (Skatteverket):</b> Alla transaktioner och rapporter i systemet beräknas med standardiserad moms (25%). Rapporterade underlag uppfyller kraven för direkt underlag till bokföring.
    </div>
    """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# --- TAB 2: REPAIR ORDER (DUAL RECEIPT + APPLE/SAMSUNG TERMS + DIGITAL SIGNATURE) ---
with tab2:
    st.markdown("<div class='repair-box'>", unsafe_allow_html=True)
    st.header(f"🛠️ Registrera Ny Reparation / Service Order ({global_branch})")
    
    rep_col1, rep_col2 = st.columns(2)
    with rep_col1:
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
                    st.info(f"💡 Befintlig kund funnen: **{auto_name}**")
            except Exception:
                pass

        c_name = st.text_input(t["customer_name"], value=auto_name, key="rep_name")
        c_email = st.text_input(t["email"], value=auto_email, key="rep_email")

    with rep_col2:
        device = st.text_input(t["device"], key="rep_device")
        imei = st.text_input(t["imei"], key="rep_imei")
        warranty_choice = st.selectbox("Garanti på reparation / Warranty", ["3 Månader (Standard)", "6 Månader", "12 Månader", "Ingen garanti (Fuktskada)"], key="rep_warranty")
        cost_price = st.number_input("Vår inköpskostnad för delar exkl. moms (SEK)", min_value=0.0, step=50.0, key="rep_cost")

    repair_issues_options = [
        "Skärmbyte (Original / OEM)", "Skärmbyte (OLED / In-Cell)", "Batteribyte (Originalkvalitet)",
        "Laddkontakt / Laddport", "Baksida / Glasbyte", "Kamera bak / Fram", "Högtalare / Samtalshögtalare",
        "Fuktsanering & Felsökning", "Mjukvaruåterställning / Software", "Moderkortsreparation"
    ]
    selected_rep_issues = st.multiselect("Välj utförda tjänster / reservdelar:", repair_issues_options, key="multi_rep_issues")
    price = st.number_input(t["price"], min_value=0.0, step=50.0, key="rep_price")
    
    auto_issues_str = ", ".join(selected_rep_issues)
    issue = st.text_area(t["issue"], value=auto_issues_str, key="rep_issue_desc")

    st.markdown("""
    <div class="legal-notice">
        <b>⚖️ APPLE & SAMSUNG AUTHORIZED SERVICE TERMS (Standardiserade Servicevillkor):</b><br>
        • <b>Diagnos & Dolda fel:</b> Verkstaden ansvarar ej för dolda skador (fuktskador, moderkortsdefekter) som upptäcks under reparation.<br>
        • <b>Garanti:</b> Omfattar endast utbytt del/utfört arbete. Garantin förverkas vid yttre skada eller vätska.<br>
        • <b>Ej uthämtade enheter:</b> Enheter ej uthämtade efter 3 månader tillfaller verkstaden i enlighet med lag (1985:982).
    </div>
    """, unsafe_allow_html=True)
    
    # Touch Screen Digital Signature Box
    st.components.v1.html(render_signature_pad("repair_sig"), height=195)
    sig_input = st.text_input("🔑 Klistra in / Bekräfta توقيع الرقمي (أو اتركه فارغاً للتوقيع الورقي):", key="repair_sig_input")

    terms_accepted = st.checkbox("✅ Kunden har godkänt villkoren & godkänner reparationen (Accept Terms)", key="rep_terms_chk")

    if st.button(t["save_repair"], type="primary", key="btn_save_rep"):
        if not terms_accepted:
            st.error("❌ Kunden måste godkänna reparationsvillkoren innan ärendet sparas!")
        elif c_name and c_phone and device and employee_name:
            conn = get_db_connection()
            cursor = conn.cursor()
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(
                "INSERT INTO repairs (branch, customer_name, phone, email, device, imei, issue, price, cost_price, status, employee, warranty_period, terms_accepted, signature_b64, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (global_branch, c_name, c_phone, c_email, device, imei, issue, price, cost_price, "Mottagen för service", employee_name, warranty_choice, 1, sig_input, created_at)
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
                "price": price, "warranty_period": warranty_choice, "employee": employee_name, 
                "signature_b64": sig_input, "created_at": date.today().strftime('%Y-%m-%d')
            }
            st.session_state['rep_receipt_pdf'] = generate_pdf_from_record("repair_receipt_dual", rec_data, COMPANY_INFO)
        else:
            st.warning("⚠️ Vänligen fyll i alla obligatoriska fält (Kundnamn, Telefon, Enhet, Handläggare).")

    if c_phone:
        rep_wa_text = f"Hej {c_name or 'Kunden'}! Ditt serviceärende för {device or 'enheten'} hos {comp['name']} ({global_branch}) har registrerats. Beräknat pris: {price} SEK inkl. moms. Välkommen!"
        st.markdown(f'<a href="{get_whatsapp_link(c_phone, rep_wa_text)}" target="_blank" class="whatsapp-btn">💬 Skicka Ärendebekräftelse via WhatsApp till kunden</a>', unsafe_allow_html=True)

    if 'rep_receipt_pdf' in st.session_state:
        st.markdown("---")
        display_pdf_preview(st.session_state['rep_receipt_pdf'], file_name=f"Inlamningskvitto_Dual_{c_name}.pdf", key_suffix="repair")
    st.markdown("</div>", unsafe_allow_html=True)

# --- TAB 3: QUOTATION (OFFERT) ---
with tab3:
    st.markdown("<div class='quote-box'>", unsafe_allow_html=True)
    st.header(f"💡 Skapa Offert & Kostnadsförslag / Price Quotation ({global_branch})")
    
    q_c1, q_c2 = st.columns(2)
    with q_c1:
        q_emp = st.text_input(t["employee"], key="q_emp")
        q_name = st.text_input(t["customer_name"], key="q_name")
        q_phone = st.text_input(t["phone"], key="q_phone")
    with q_c2:
        q_device = st.text_input(t["device"], key="q_device")
        valid_days = st.number_input("Giltighetstid i dagar / Offer Validity Days", min_value=7, max_value=60, value=14, key="q_valid_days")

    st.markdown("---")
    st.subheader("🛠️ Specifikation av rekommenderade åtgärder & kalkylerad vinst")
    
    quote_items = [
        ("Skärmbyte / Skärmmodul", "qp_s", "qc_s"),
        ("Batteribyte", "qp_b", "qc_b"),
        ("Laddkontakt & Mikrofon", "qp_l", "qc_l"),
        ("Baksida / Chassi", "qp_bk", "qc_bk"),
        ("Övrig komponent / Arbete", "qp_o", "qc_o")
    ]
    
    issues_list = []
    total_price = 0.0
    total_cost = 0.0

    for label, p_key, c_key in quote_items:
        if st.checkbox(label, key=f"chk_{p_key}"):
            col_p, col_c = st.columns(2)
            with col_p:
                p_val = st.number_input(f"Kundpris inkl. moms ({label})", min_value=0.0, step=50.0, key=p_key)
            with col_c:
                c_val = st.number_input(f"Inköpskostnad exkl. moms ({label})", min_value=0.0, step=10.0, key=c_key)
            issues_list.append(f"{label}: {p_val:.2f} SEK")
            total_price += p_val
            total_cost += c_val

    net_profit = float(total_price - total_cost)
    st.markdown(f"### 💰 Totalt kundpris: **{total_price:.2f} SEK** (inkl. moms) | 📈 Kalkylerad Nettovinst: **{net_profit:.2f} SEK**")

    if st.button("Spara & Generera Offert PDF / Save Quote PDF", type="primary", key="btn_save_q"):
        if q_name and q_device and issues_list and q_emp:
            conn = get_db_connection()
            cursor = conn.cursor()
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            valid_until_date = (date.today() + timedelta(days=valid_days)).strftime('%Y-%m-%d')
            issues_str = ", ".join(issues_list)
            cursor.execute("INSERT INTO quotes (branch, customer_name, phone, email, device, issues, total, profit, valid_until, employee, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (global_branch, q_name, q_phone, "", q_device, issues_str, total_price, net_profit, valid_until_date, q_emp, created_at))
            conn.commit()
            conn.close()
            st.success("✅ Offerten har sparats!")
            
            record_data = {
                "branch": global_branch, "customer_name": q_name, "phone": q_phone, 
                "device": q_device, "issues": issues_str, "total": total_price, 
                "currency": "SEK", "valid_until": valid_until_date, "employee": q_emp, 
                "created_at": date.today().strftime('%Y-%m-%d')
            }
            st.session_state['q_pdf'] = generate_pdf_from_record("quote", record_data, COMPANY_INFO)

    if q_phone:
        q_wa_text = f"Hej {q_name or 'Kunden'}! Här kommer kostnadsförslag på reparation av {q_device or 'enheten'} hos {comp['name']}. Totalt: {total_price:.2f} SEK inkl. moms. Offerten är giltig i {valid_days} dagar."
        st.markdown(f'<a href="{get_whatsapp_link(q_phone, q_wa_text)}" target="_blank" class="whatsapp-btn">💬 Skicka Offert via WhatsApp till kunden</a>', unsafe_allow_html=True)

    if 'q_pdf' in st.session_state:
        display_pdf_preview(st.session_state['q_pdf'], file_name="Offert_Kostnadsforslag.pdf", key_suffix="quote")
    st.markdown("</div>", unsafe_allow_html=True)

# --- TAB 4: OFFICIAL INVOICE (FAKTURA) ---
with tab4:
    st.markdown("<div class='invoice-box'>", unsafe_allow_html=True)
    st.header(f"📄 Utfärda Officiell Faktura / Swedish Standard Invoice ({global_branch})")
    
    inv_c1, inv_c2 = st.columns(2)
    with inv_c1:
        inv_emp = st.text_input(t["employee"], key="inv_emp")
        inv_no = st.text_input("Fakturanummer / Invoice No", value=f"SE-{datetime.now().strftime('%Y%m%d%H%M')}", key="inv_no")
        inv_name = st.text_input(t["customer_name"], key="inv_name")
        inv_org_no = st.text_input("Kundens Org.nr / Personnummer", key="inv_org_no")
        inv_phone = st.text_input(t["phone"], key="inv_phone")
    with inv_c2:
        inv_address = st.text_input("Faktureringsadress", key="inv_address")
        inv_ref = st.text_input("Er Referens / Märkning", key="inv_ref")
        pay_terms = st.selectbox("Betalningsvillkor / Payment Terms", ["10 Dagar", "15 Dagar", "30 Dagar", "Kontant / Direktbetalning"], key="inv_pay_terms")
        inv_desc = st.text_input("Artikelbeskrivning", value="Mobilreparation samt reservdelar i enlighet med specifikation", key="inv_desc")

    col_a1, col_a2 = st.columns(2)
    with col_a1:
        inv_amount = st.number_input("Totalt belopp inkl. moms (SEK)", min_value=0.0, step=100.0, key="inv_amount")
    with col_a2:
        moms_rate = st.selectbox("Momssats (Mervärdesskatt)", ["25%", "12%", "6%", "0% (Export/Momsbefriad)"], key="inv_moms_rate")

    rate_val = float(moms_rate.split("%")[0]) / 100.0
    moms_amount = inv_amount * (rate_val / (1.0 + rate_val)) if rate_val > 0 else 0.0

    st.markdown("""
    <div class="legal-notice">
        📌 <b>BOKFÖRINGSDRIVEN SKATTESTANDARD (Mervärdesskattelag 2023:200):</b><br>
        Fakturan innehåller obligatoriska uppgifter: F-skatt status, Organisasjonsnummer, SE-VAT nummer, samt specifierad moms.
    </div>
    """, unsafe_allow_html=True)

    if st.button("Generera & Bokföra Faktura PDF / Save Invoice", type="primary", key="btn_save_inv"):
        if inv_name and inv_amount > 0 and inv_emp:
            conn = get_db_connection()
            cursor = conn.cursor()
            created_at = datetime.now().strftime("%Y-%m-%d")
            
            days_add = 10
            if "15" in pay_terms: days_add = 15
            elif "30" in pay_terms: days_add = 30
            elif "Direkt" in pay_terms: days_add = 0
            
            due_date = (date.today() + timedelta(days=days_add)).strftime('%Y-%m-%d')
            
            cursor.execute("INSERT INTO invoices (branch, customer_name, phone, address, org_no_cust, ref_no, invoice_no, item_desc, amount, moms, currency, moms_rate, payment_terms, due_date, employee, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", 
                           (global_branch, inv_name, inv_phone, inv_address, inv_org_no, inv_ref, inv_no, inv_desc, inv_amount, moms_amount, "SEK", moms_rate, pay_terms, due_date, inv_emp, created_at))
            conn.commit()
            conn.close()
            st.success("✅ Fakturan har skapats och bokförts!")

            record_data = {
                "branch": global_branch, "invoice_no": inv_no, "customer_name": inv_name, "org_no_cust": inv_org_no,
                "address": inv_address, "phone": inv_phone, "ref_no": inv_ref, "item_desc": inv_desc, 
                "amount": inv_amount, "moms": moms_amount, "currency": "SEK", "moms_rate": moms_rate, 
                "payment_terms": pay_terms, "employee": inv_emp, "created_at": created_at, "due_date": due_date
            }
            st.session_state['inv_pdf'] = generate_pdf_from_record("invoice", record_data, COMPANY_INFO)

    if 'inv_pdf' in st.session_state:
        display_pdf_preview(st.session_state['inv_pdf'], file_name=f"Faktura_{inv_no}.pdf", key_suffix="invoice")
    st.markdown("</div>", unsafe_allow_html=True)

# --- TAB 5: SUBSCRIPTIONS & WARRANTIES ---
with tab5:
    st.markdown("<div class='sub-box'>", unsafe_allow_html=True)
    st.header(f"💳 Abonnemang & Trygghetsavtal / Subscriptions ({global_branch})")
    
    sub_c1, sub_c2 = st.columns(2)
    with sub_c1:
        sub_emp = st.text_input(t["employee"], key="sub_emp")
        sub_name = st.text_input(t["customer_name"], key="sub_name")
        sub_phone = st.text_input(t["phone"], key="sub_phone")
    with sub_c2:
        sub_device = st.text_input(t["device"], key="sub_device")
        sub_imei = st.text_input(t["imei"], key="sub_imei")
        sub_plan = st.selectbox("Abonnemangstyp / Protection Plan", ["Skärmskydd Garanti (12 Månader)", "Full Protection VIP Plan", "Årlig Service & Batteriservice"], key="sub_plan")
        sub_price = st.number_input("Årsavgift / Månadsavgift (SEK)", min_value=0.0, step=49.0, key="sub_price")

    if st.button("Teckna Abonnemang / Save Subscription", type="primary", key="btn_save_sub"):
        if sub_name and sub_phone and sub_emp:
            conn = get_db_connection()
            cursor = conn.cursor()
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            end_date = (date.today() + timedelta(days=365)).strftime('%Y-%m-%d')
            cursor.execute("INSERT INTO subscriptions (branch, customer_name, phone, device, imei, plan_type, price, employee, start_date, end_date, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (global_branch, sub_name, sub_phone, sub_device, sub_imei, sub_plan, sub_price, sub_emp, date.today().strftime('%Y-%m-%d'), end_date, created_at))
            conn.commit()
            conn.close()
            st.success("✅ Abonnemangsavtalet har tecknats och registrerats!")
    st.markdown("</div>", unsafe_allow_html=True)

# --- TAB 6: BUYBACK WITH DIGITAL SIGNATURE ---
with tab6:
    st.markdown("<div class='buyback-box'>", unsafe_allow_html=True)
    st.header(f"📱 Inköp av Begagnad Elektronik (Lag 1999:158) / Buyback ({global_branch})")
    
    bb_c1, bb_c2 = st.columns(2)
    with bb_c1:
        b_emp = st.text_input(t["employee"], key="b_emp")
        b_name = st.text_input("Säljarens Namn (Kund)", key="b_name")
        b_person_num = st.text_input("Säljarens Personnummer (YYYYMMDD-XXXX)", key="b_pnum")
        b_phone = st.text_input(t["phone"], key="b_phone")
        b_id_chk = st.checkbox("✅ Legitimation kontrollerad (Körkort / Pass / BankID)", key="b_id_chk")

    with bb_c2:
        b_device = st.text_input(t["device"], key="b_device")
        b_imei = st.text_input(t["imei"], key="b_imei")
        b_grade = st.selectbox("Enhetens Skick / Condition Grade", ["Nyskick (A-Grade)", "Gott Skick (B-Grade)", "Slitage/Repor (C-Grade)", "Defekt/Sönder"], key="b_grade")
        b_price = st.number_input("Utbetalt Belopp till Säljaren (SEK)", min_value=0.0, step=100.0, key="b_price")

    st.markdown("""
    <div class="legal-notice">
        <b>⚖️ LAG OM HANDEL MED BEGAGNADE VAROR (1999:158):</b><br>
        Säljaren måste kunna legitimera sig. Genom att godkänna intygar säljaren att enheten är fri från stöldspärrar, iCloud-lås, samt legal egendom.
    </div>
    """, unsafe_allow_html=True)

    st.components.v1.html(render_signature_pad("bb_sig"), height=195)
    bb_sig_input = st.text_input("🔑 Bekräfta توقيع الرقمي للسائع (أو اتركه فارغاً للتوقيع الورقي):", key="bb_sig_input")

    if st.button("Spara Inköp & Generera Inköpskvitto PDF", type="primary", key="btn_save_bb"):
        if not b_id_chk:
            st.error("❌ Legitimation måste kontrolleras och bockas i enligt lag!")
        elif b_name and b_person_num and b_price > 0 and b_emp:
            conn = get_db_connection()
            cursor = conn.cursor()
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("INSERT INTO buybacks (branch, customer_name, phone, person_nummer, id_verified, device, imei, purchase_price, condition_grade, employee, signature_b64, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", 
                           (global_branch, b_name, b_phone, b_person_num, 1 if b_id_chk else 0, b_device, b_imei, b_price, b_grade, b_emp, bb_sig_input, created_at))
            bb_id = cursor.lastrowid
            conn.commit()
            conn.close()
            st.success("✅ Inköpet har registrerats i enlighet med Polismyndighetens direktiv!")

            rec_data = {
                "branch": global_branch, "buyback_id": str(bb_id), "customer_name": b_name, "person_nummer": b_person_num,
                "phone": b_phone, "id_verified": b_id_chk, "device": b_device, "imei": b_imei, "condition_grade": b_grade,
                "purchase_price": b_price, "employee": b_emp, "signature_b64": bb_sig_input, "created_at": date.today().strftime('%Y-%m-%d')
            }
            st.session_state['bb_pdf'] = generate_pdf_from_record("buyback_receipt", rec_data, COMPANY_INFO)

    if 'bb_pdf' in st.session_state:
        display_pdf_preview(st.session_state['bb_pdf'], file_name="Inkopsavtal_Begagnat.pdf", key_suffix="buyback")
    st.markdown("</div>", unsafe_allow_html=True)

# --- TAB 7: CAMPAIGNS & OFFERS ---
with tab7:
    st.markdown("<div class='campaign-box'>", unsafe_allow_html=True)
    st.header(f"🎄 Kampanjer & Säsongserbjudanden / Marketing Campaigns ({global_branch})")
    st.info("💡 Aktiva marknadskampanjer och erbjudanden som kan tillämpas i butiken:")
    
    st.markdown("""
    • **Paketerbjudande Skärmbyte:** 20% rabatt på skärmskydd vid samtidigt skärmbyte.<br>
    • **Batteribyte Kampanj:** Fast pris 499 SEK för iPhone batteribyte (Gäller vy modeller upp till iPhone 12).<br>
    • **Student & Pensionärsrabatt:** 10% rabatt på utfört arbete vid uppvisande av giltigt mecenat/legitimation.
    """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# --- TAB 8: PRE-ORDERS & DEPOSITS ---
with tab8:
    st.markdown("<div class='preorder-box'>", unsafe_allow_html=True)
    st.header(f"🛒 Förbeställning & Handpenning / Pre-orders & Deposit ({global_branch})")
    
    po_c1, po_c2 = st.columns(2)
    with po_c1:
        po_emp = st.text_input(t["employee"], key="po_emp")
        po_name = st.text_input(t["customer_name"], key="po_name")
        po_phone = st.text_input(t["phone"], key="po_phone")
    with po_c2:
        po_item = st.text_input("Beställd Produkt / Reservdel", key="po_item")
        po_deposit = st.number_input("Mottagen Handpenning (SEK)", min_value=0.0, step=100.0, key="po_deposit")
        po_est_date = st.date_input("Beräknat ankomstdatum", value=date.today() + timedelta(days=3), key="po_est_date")

    if st.button("Registrera Beställning / Save Pre-order", type="primary", key="btn_save_po"):
        if po_name and po_item and po_emp:
            conn = get_db_connection()
            cursor = conn.cursor()
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("INSERT INTO preorders (branch, customer_name, phone, item_details, deposit, estimated_delivery, employee, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", 
                           (global_branch, po_name, po_phone, po_item, po_deposit, po_est_date.strftime('%Y-%m-%d'), po_emp, "Beställd från leverantör", created_at))
            conn.commit()
            conn.close()
            st.success("✅ Förbeställningen har registrerats med mottagen handpenning!")
    st.markdown("</div>", unsafe_allow_html=True)

# --- TAB 9: INVENTORY MANAGEMENT ---
with tab9:
    st.markdown("<div class='inventory-box'>", unsafe_allow_html=True)
    st.header(f"📦 Lagerhantering & Artikelregister / Inventory ({global_branch})")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, part_name, category, stock_qty, min_limit, purchase_cost, selling_price FROM inventory WHERE branch = ?", (global_branch,))
    inv_rows = cursor.fetchall()
    conn.close()

    if inv_rows:
        df_inv = pd.DataFrame(inv_rows, columns=["ID", "Artikel / Reservdel", "Kategori", "Lagerantal", "Min-Gräns", "Inköpspris (exkl. moms)", "Försäljningspris (inkl. moms)"])
        st.dataframe(df_inv, use_container_width=True)
    else:
        st.info("ℹ️ Inga artiklar är registrerade i lagret för denna butik ännu.")

    st.markdown("---")
    st.subheader("➕ Registrera Ny Artikel / Reservdel i Lagret")
    
    inv_col1, inv_col2 = st.columns(2)
    with inv_col1:
        new_part = st.text_input("Artikelnamn / Modell", key="inv_new_part")
        new_cat = st.selectbox("Kategori", ["Skärmar", "Batterier", "Laddkontakter", "Tillbehör", "Kameror/Chassi"], key="inv_new_cat")
        new_qty = st.number_input("Antal i lager", min_value=1, step=1, key="inv_new_qty")
    with inv_col2:
        new_cost = st.number_input("Inköpspris exkl. moms (SEK)", min_value=0.0, step=10.0, key="inv_new_cost")
        new_sell = st.number_input("Försäljningspris inkl. moms (SEK)", min_value=0.0, step=50.0, key="inv_new_sell")
        new_min = st.number_input("Minsta larmgräns för lager", min_value=1, value=2, key="inv_new_min")

    if st.button("Spara Artikel i Lagret / Add Stock", key="btn_add_inv"):
        if new_part:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO inventory (part_name, category, stock_qty, min_limit, purchase_cost, selling_price, branch) VALUES (?, ?, ?, ?, ?, ?, ?)", 
                           (new_part, new_cat, new_qty, new_min, new_cost, new_sell, global_branch))
            conn.commit()
            conn.close()
            st.success("✅ Artikeln har lagts till i artikelregistret!")
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# --- TAB 10: SEARCH & RECORDS ARCHIVE ---
with tab10:
    st.markdown("<div class='search-box'>", unsafe_allow_html=True)
    st.header(f"🔍 Sök Registrerade Ärenden & Historik / Search Archive ({global_branch})")
    
    search_q = st.text_input("🔍 Sök på Kundnamn, Telefonnummer, IMEI eller Ärende ID", key="search_query")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    if search_q:
        q_term = f"%{search_q}%"
        cursor.execute("SELECT id, customer_name, phone, device, issue, price, status, warranty_period, created_at, employee FROM repairs WHERE branch = ? AND (customer_name LIKE ? OR phone LIKE ? OR imei LIKE ? OR id LIKE ?)", 
                       (global_branch, q_term, q_term, q_term, q_term))
    else:
        cursor.execute("SELECT id, customer_name, phone, device, issue, price, status, warranty_period, created_at, employee FROM repairs WHERE branch = ? ORDER BY id DESC LIMIT 30", (global_branch,))
    
    rep_records = cursor.fetchall()
    conn.close()

    if rep_records:
        df_rep = pd.DataFrame(rep_records, columns=["Ärende ID", "Kundnamn", "Telefon", "Enhet", "Utfört arbete", "Pris (SEK)", "Status", "Garanti", "Datum", "Handläggare"])
        st.dataframe(df_rep, use_container_width=True)
    else:
        st.warning("Inga ärenden hittades som matchar sökningen.")
    st.markdown("</div>", unsafe_allow_html=True)
