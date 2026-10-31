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
            status TEXT, employee TEXT, created_at TEXT, signature TEXT
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
            device TEXT, imei TEXT, purchase_price REAL, employee TEXT, created_at TEXT, signature TEXT
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

    try:
        cursor.execute("ALTER TABLE repairs ADD COLUMN signature TEXT")
    except Exception:
        pass

    try:
        cursor.execute("ALTER TABLE buybacks ADD COLUMN signature TEXT")
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

# --- Secure Authentication Login & Remember Device ---
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

if not st.session_state['authenticated'] and st.session_state.get('remember_device', False):
    st.session_state['authenticated'] = True

if not st.session_state['authenticated']:
    st.markdown("<div class='login-container'>", unsafe_allow_html=True)
    st.markdown("### 🔒 System Login / Inloggning")
    st.markdown("Ange PIN-kod för att fortsätta / الرجاء إدخال رمز المرور:")
    
    login_pin = st.text_input("🔑 PIN Code / رمز المرور", type="password", key="login_pin_input")
    remember_me = st.checkbox("💾 Spara inloggning på denna enhet / تذكرني على هذا الجهاز", key="remember_device_chk")
    
    if login_pin:
        if login_pin.strip() == "Tunapark":
            st.session_state['authenticated'] = True
            st.session_state['remember_device'] = remember_me
            st.success("✅ Logged in successfully! / تم تسجيل الدخول بنجاح!")
            st.rerun()
        else:
            st.error("❌ Fel PIN-kod! / رمز المرور غير صحيح!")
            
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

if st.sidebar.button("🔒 Log Out / Logga ut / تسجيل خروج"):
    st.session_state['authenticated'] = False
    st.session_state['remember_device'] = False
    st.rerun()

def render_signature_pad(key_suffix="repair"):
    st.markdown(f"**✍️ توقيع العميل (Digital Customer Signature - iPad / Touch supported):**")
    sig_html = f"""
    <div style="border: 2px dashed #3498db; border-radius: 8px; background: #fff; padding: 5px; width: 100%; max-width: 500px;">
        <canvas id="sigCanvas_{key_suffix}" width="480" height="180" style="touch-action: none; background: #ffffff; width: 100%; height: 160px; cursor: crosshair;"></canvas>
        <div style="display: flex; justify-content: space-between; margin-top: 5px;">
            <button type="button" onclick="clearSig_{key_suffix}()" style="background: #e74c3c; color: white; border: none; padding: 5px 15px; border-radius: 5px; font-weight: bold; cursor: pointer;">مسح التوقيع (Clear)</button>
            <span style="font-size: 11px; color: #7f8c8d; align-self: center;">قم بالتوقيع بالأصبع أو القلم</span>
        </div>
    </div>
    <input type="hidden" id="sigData_{key_suffix}" name="sigData_{key_suffix}">
    <script>
    (function() {{
        var canvas = document.getElementById('sigCanvas_{key_suffix}');
        if (!canvas) return;
        var ctx = canvas.getContext('2d');
        var drawing = false;
        var lastX = 0;
        var lastY = 0;

        function getPos(e) {{
            var rect = canvas.getBoundingClientRect();
            var clientX = e.clientX;
            var clientY = e.clientY;
            if (e.touches && e.touches.length > 0) {{
                clientX = e.touches[0].clientX;
                clientY = e.touches[0].clientY;
            }}
            return {{
                x: (clientX - rect.left) * (canvas.width / rect.width),
                y: (clientY - rect.top) * (canvas.height / rect.height)
            }};
        }}

        function startDraw(e) {{
            drawing = true;
            var pos = getPos(e);
            lastX = pos.x;
            lastY = pos.y;
            e.preventDefault();
        }}

        function draw(e) {{
            if (!drawing) return;
            var pos = getPos(e);
            ctx.beginPath();
            ctx.moveTo(lastX, lastY);
            ctx.lineTo(pos.x, pos.y);
            ctx.strokeStyle = '#000';
            ctx.lineWidth = 2.5;
            ctx.lineCap = 'round';
            ctx.stroke();
            lastX = pos.x;
            lastY = pos.y;
            
            var dataURL = canvas.toDataURL('image/png');
            var input = document.getElementById('sigData_{key_suffix}');
            if (input) {{
                input.value = dataURL;
                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
            }}
            e.preventDefault();
        }}

        function stopDraw(e) {{
            if (!drawing) return;
            drawing = false;
            var dataURL = canvas.toDataURL('image/png');
            var input = document.getElementById('sigData_{key_suffix}');
            if (input) {{
                input.value = dataURL;
                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
            }}
            e.preventDefault();
        }}

        canvas.addEventListener('mousedown', startDraw);
        canvas.addEventListener('mousemove', draw);
        canvas.addEventListener('mouseup', stopDraw);
        canvas.addEventListener('mouseleave', stopDraw);

        canvas.addEventListener('touchstart', startDraw, {{passive: false}});
        canvas.addEventListener('touchmove', draw, {{passive: false}});
        canvas.addEventListener('touchend', stopDraw, {{passive: false}});

        window.clearSig_{key_suffix} = function() {{
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            var input = document.getElementById('sigData_{key_suffix}');
            if (input) {{
                input.value = '';
                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
            }}
        }};
    }})();
    </script>
    """
    st.markdown(sig_html, unsafe_allow_html=True)
    sig_val = st.text_input("Hidden Sig Data", key=f"hidden_sig_{key_suffix}", label_visibility="collapsed")
    return sig_val

def display_pdf_preview(pdf_buffer, file_name="document.pdf", key_suffix="doc"):
    pdf_buffer.seek(0)
    pdf_bytes = pdf_buffer.read()
    b64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
    st.success("✅ Dokumentet är redo! / Document is ready!")
    
    b_col1, b_col2, b_col3 = st.columns(3)
    with b_col1:
        st.download_button("📥 Ladda ner PDF", data=pdf_bytes, file_name=file_name, mime="application/pdf", type="primary", key=f"dl_{key_suffix}")
    with b_col2:
        pdf_data_uri = f"data:application/pdf;base64,{b64_pdf}"
        st.markdown(f'<a href="{pdf_data_uri}" target="_blank" style="display:inline-block; background-color:#2980b9; color:white; padding:0.6rem 1.2rem; border-radius:8px; font-weight:600; text-align:center; text-decoration:none; width:100%;">🌐 Öppna i ny flik</a>', unsafe_allow_html=True)
    with b_col3:
        print_html = f"""
        <script>
        function printPDF_{key_suffix}() {{
            var iframe = document.createElement('iframe');
            iframe.style.display = 'none';
            iframe.src = "data:application/pdf;base64,{b64_pdf}";
            document.body.appendChild(iframe);
            iframe.contentWindow.print();
        }}
        </script>
        <button onclick="printPDF_{key_suffix}()" style="background-color: #2ecc71; color: white; padding: 0.6rem 1.2rem; border: none; border-radius: 8px; font-weight: 600; width: 100%; cursor: pointer;">
            🖨️ Skriv ut
        </button>
        """
        st.markdown(print_html, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 👁️ Förhandsgranskning / Preview")
    
    pdf_display = f"""
    <div style="text-align: center; border: 1px solid #dcdde1; border-radius: 8px; padding: 10px; background: #fff;">
        <object data="data:application/pdf;base64,{b64_pdf}" type="application/pdf" width="100%" height="550px">
            <embed src="data:application/pdf;base64,{b64_pdf}" type="application/pdf" width="100%" height="550px" />
            <p style="padding: 20px;">متصفح هاتفك لا يدعم المعاينة المباشرة. يرجى الضغط على زر <b>"Öppna i ny flik"</b> أعلاه.</p>
        </object>
    </div>
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
    signature_data = data.get('signature', None)

    if record_type == "repair_receipt_dual":
        def draw_repair_section(start_y, copy_title):
            p.setFont("Helvetica-Bold", 8.5)
            p.drawString(40, start_y, f"{comp['name']} ({copy_title}) - Butik: {branch}")
            p.setFont("Helvetica", 7)
            p.drawString(40, start_y - 10, f"Adress: {comp['address']} | Tel: {comp['phone']} | Org.nr: {comp['org_nr']}")
            p.drawString(40, start_y - 19, f"Swish: {comp['swish']} | Bankgiro: {comp['bankgiro']}")
            
            p.setFont("Helvetica-Bold", 8.5)
            p.drawString(40, start_y - 32, f"ÄRENDEKVITTO / REPAIR RECEIPT #{data.get('repair_id', '1')}")
            p.setFont("Helvetica", 7.5)
            p.drawString(320, start_y - 32, f"Datum: {data.get('created_at', '')}")
            
            p.drawString(40, start_y - 43, f"Kund: {data.get('customer_name', '')}")
            p.drawString(320, start_y - 43, f"Handläggare: {employee_name}")
            p.drawString(40, start_y - 54, f"Tel: {data.get('phone', '')}")
            p.drawString(320, start_y - 54, f"Enhet: {data.get('device', '')}")
            p.drawString(40, start_y - 65, f"IMEI: {data.get('imei', 'Ej angivet')}")
            
            p.setFillColorRGB(0.92, 0.92, 0.92)
            p.rect(40, start_y - 82, width - 80, 12, fill=1, stroke=0)
            p.setFillColorRGB(0, 0, 0)
            p.setFont("Helvetica-Bold", 7.5)
            p.drawString(45, start_y - 79, "Beskrivning av fel / Repair Description")
            p.drawString(420, start_y - 79, f"Pris ({currency})")
            
            p.setFont("Helvetica", 7.5)
            p.drawString(45, start_y - 95, f"- {data.get('issue', '')}")
            price_val = data.get('price', 0)
            p.drawString(420, start_y - 95, f"{price_val:.2f} {currency}")
            
            p.setFont("Helvetica-Bold", 7.5)
            p.drawString(320, start_y - 108, f"Att betala / Total: {price_val:.2f} {currency} (Inkl. moms)")
            
            # Apple/Samsung style terms & conditions paragraph
            p.setFont("Helvetica-Bold", 6.5)
            p.drawString(40, start_y - 120, "VILLKOR & SERVICEVILLKOR (APPLE / SAMSUNG STANDARD):")
            p.setFont("Helvetica", 5.5)
            terms_lines = [
                "1. Enheten lämnas in för felsökning/reparation enligt angivna beskrivningar. Garanti gäller enbart utfört arbete och utbytta reservdelar i 3 månader.",
                "2. Reparation kan medföra att enhetens vattentålighet försämras eller förloras. Vinkeln ansvarar ej för dolda eller befintliga fel.",
                "3. Enheter som ej hämtas ut inom 3 månader kan komma att säljas för att täcka reparationskostnader i enlighet med lagen (1985:982)."
            ]
            ty = start_y - 128
            for t_line in terms_lines:
                p.drawString(40, ty, t_line)
                ty -= 8

            p.setFont("Helvetica", 6.5)
            p.drawString(40, ty - 6, "Godkänt av kund / Terms Accepted:")
            p.drawString(320, ty - 6, "Kundens underskrift:")
            
            if signature_data:
                try:
                    if signature_data.startswith("data:image/png;base64,"):
                        sig_bytes = base64.b64decode(signature_data.split(",")[1])
                        sig_io = io.BytesIO(sig_bytes)
                        p.drawImage(sig_io, 320, ty - 38, width=100, height=30, preserveAspectRatio=True, mask='auto')
                except Exception:
                    pass
            p.rect(320, ty - 38, 120, 30, fill=0, stroke=1)

        draw_repair_section(height - 25, "BUTIKENS KOPIA / STORE COPY")
        p.setDash(3, 3)
        p.line(30, height / 2, width - 30, height / 2)
        p.setDash()
        draw_repair_section(height / 2 - 15, "KUNDENS KOPIA / CUSTOMER COPY")

    elif record_type == "buyback_receipt":
        p.setFont("Helvetica-Bold", 12)
        p.drawString(40, height - 40, comp["name"])
        p.setFont("Helvetica", 8)
        p.drawString(40, height - 52, f"Adress: {comp['address']} | Tel: {comp['phone']} | Org.nr: {comp['org_nr']}")
        p.drawString(40, height - 64, f"Swish: {comp['swish']} | Bankgiro: {comp['bankgiro']}")

        p.setFont("Helvetica-Bold", 11)
        p.drawString(40, height - 95, "INKÖPSKVITTO - BEGAGNAD ENHET / PURCHASE RECEIPT")
        p.setFont("Helvetica", 9)
        p.drawString(40, height - 120, f"Kvitto ID: #{data.get('buyback_id', '1')}")
        p.drawString(300, height - 120, f"Datum: {data.get('created_at', '')}")
        p.drawString(40, height - 140, f"Säljare: {data.get('customer_name', '')}")
        p.drawString(300, height - 140, f"Personnummer: {data.get('person_nummer', 'Ej angivet')}")
        p.drawString(40, height - 160, f"Telefon: {data.get('phone', '')}")
        p.drawString(300, height - 160, f"Handläggare: {employee_name}")
        p.drawString(40, height - 180, f"Enhet: {data.get('device', '')}")
        p.drawString(300, height - 180, f"IMEI: {data.get('imei', '')}")
        
        price_val = data.get('purchase_price', 0)
        p.setFont("Helvetica-Bold", 11)
        p.drawString(300, height - 260, f"Utbetalat belopp / Total Paid: {price_val:.2f} {currency}")

        p.setFont("Helvetica", 8)
        p.drawString(40, height - 300, "Säljaren intygar att enheten är hens egendom och att alla konton (iCloud/Google) är raderade.")
        p.drawString(40, height - 340, "Säljarens underskrift:")
        if signature_data:
            try:
                if signature_data.startswith("data:image/png;base64,"):
                    sig_bytes = base64.b64decode(signature_data.split(",")[1])
                    sig_io = io.BytesIO(sig_bytes)
                    p.drawImage(sig_io, 180, height - 365, width=120, height=40, preserveAspectRatio=True, mask='auto')
            except Exception:
                pass
        p.rect(180, height - 365, 140, 40, fill=0, stroke=1)

        p.setFont("Helvetica", 8)
        p.drawString(40, 45, f"Företag: {comp['name']} | Org.nr: {comp['org_nr']} | Swish: {comp['swish']} | Bankgiro: {comp['bankgiro']}")

    elif record_type == "quote":
        p.setFont("Helvetica-Bold", 12)
        p.drawString(40, height - 40, comp["name"])
        p.setFont("Helvetica", 8)
        p.drawString(40, height - 52, f"Adress: {comp['address']} | Tel: {comp['phone']} | Org.nr: {comp['org_nr']}")
        p.drawString(40, height - 64, f"Swish: {comp['swish']} | Bankgiro: {comp['bankgiro']}")

        p.setFont("Helvetica-Bold", 11)
        p.drawString(40, height - 95, "KOSTNADSFÖRSLAG / PRICE QUOTATION")
        p.setFont("Helvetica", 9)
        p.drawString(40, height - 120, f"Datum: {data.get('created_at', '')}")
        p.drawString(300, height - 120, f"Handläggare: {employee_name}")
        p.drawString(40, height - 140, f"Kund: {data.get('customer_name', '')}")
        p.drawString(40, height - 160, f"Telefon: {data.get('phone', '')}")
        p.drawString(300, height - 140, f"Enhet: {data.get('device', '')}")
        
        total_val = data.get('total', 0)
        p.setFont("Helvetica-Bold", 11)
        p.drawString(300, height - 260, f"Att betala / Total: {total_val:.2f} {currency} (Inkl. moms)")

        p.setFont("Helvetica", 8)
        p.drawString(40, 45, f"Företag: {comp['name']} | Org.nr: {comp['org_nr']} | Swish: {comp['swish']} | Bankgiro: {comp['bankgiro']}")

    elif record_type == "invoice":
        p.setFont("Helvetica-Bold", 16)
        p.drawString(40, height - 45, "FAKTURA")
        
        p.setFont("Helvetica-Bold", 9)
        p.drawString(380, height - 38, comp["name"])
        p.setFont("Helvetica", 8)
        p.drawString(380, height - 50, comp["address"])
        p.drawString(380, height - 62, f"Org.nr: {comp['org_nr']} | Tel: {comp['phone']}")
        p.drawString(380, height - 74, f"Swish: {comp['swish']} | Bankgiro: {comp['bankgiro']}")

        p.setLineWidth(0.5)
        p.line(40, height - 90, width - 40, height - 90)

        p.setFont("Helvetica-Bold", 9)
        p.drawString(40, height - 110, "Fakturainformation")
        p.setFont("Helvetica", 9)
        p.drawString(40, height - 125, f"Fakturanummer: {data.get('invoice_no', '')}")
        p.drawString(40, height - 140, f"Fakturadatum: {data.get('created_at', '')}")
        p.drawString(40, height - 155, f"Förfallodatum: {data.get('due_date', '')}")
        p.drawString(40, height - 170, f"Vår referens: {employee_name}")
        p.drawString(40, height - 185, f"Er referens: {data.get('ref_no', 'Ej angiven')}")

        p.setFont("Helvetica-Bold", 9)
        p.drawString(320, height - 110, "Köpare / Kund")
        p.setFont("Helvetica", 9)
        p.drawString(320, height - 125, f"{data.get('customer_name', '')}")
        p.drawString(320, height - 140, f"{data.get('address', '')}")
        p.drawString(320, height - 155, f"Tel: {data.get('phone', '')}")

        p.setFillColorRGB(0.9, 0.9, 0.9)
        p.rect(40, height - 215, width - 80, 18, fill=1, stroke=0)
        p.setFillColorRGB(0, 0, 0)
        p.setFont("Helvetica-Bold", 8)
        p.drawString(50, height - 208, "Artikel / Beskrivning")
        p.drawString(320, height - 208, "Moms")
        p.drawString(390, height - 208, f"Pris ({currency})")
        p.drawString(470, height - 208, f"Totalt ({currency})")

        amount_val = data.get('amount', 0)
        moms_val = data.get('moms', 0)
        netto_val = amount_val - moms_val

        p.setFont("Helvetica", 9)
        p.drawString(50, height - 240, data.get('item_desc', 'Reparation och reservdelar'))
        p.drawString(320, height - 240, moms_rate_str)
        p.drawString(390, height - 240, f"{netto_val:.2f}")
        p.drawString(470, height - 240, f"{amount_val:.2f}")

        p.line(320, height - 300, width - 40, height - 300)
        p.setFont("Helvetica", 9)
        p.drawString(320, height - 315, "Netto / Exkl. moms:")
        p.drawString(470, height - 315, f"{netto_val:.2f} {currency}")
        
        p.drawString(320, height - 332, f"Moms ({moms_rate_str}):")
        p.drawString(470, height - 332, f"{moms_val:.2f} {currency}")

        p.setFont("Helvetica-Bold", 11)
        p.drawString(320, height - 355, "Att betala / Total:")
        p.drawString(470, height - 355, f"{amount_val:.2f} {currency}")

        p.setFont("Helvetica-Bold", 8)
        p.drawString(40, 45, f"{comp['name']} | Adress: {comp['address']} | Org.nr: {comp['org_nr']}")
        p.drawString(40, 33, f"Bankgiro: {comp['bankgiro']} | Swish: {comp['swish']} | Innehar F-skattsedel")

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

# --- TAB 2: NEW REPAIR ---
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
        <b>⚠️ شروط الخدمة والضمان (Apple & Samsung Standard Terms):</b><br>
        • الضمان يغطي فقط الإصلاح أو القطعة التي تم استبدالها لمدة 3 أشهر.<br>
        • لا تتحمل الورشة مسؤولية ضياع البيانات أو انخفاض مقاومة الماء بعد الفتح.
    </div>
    """, unsafe_allow_html=True)
    
    terms_accepted = st.checkbox("✅ أوافق على شروط الخدمة والإصلاح (Accept Terms & Conditions)", key="rep_terms_chk")
    customer_signature = render_signature_pad(key_suffix="repair")

    if st.button(t["save_repair"], type="primary", key="btn_save_rep"):
        if not terms_accepted:
            st.error("❌ يجب الموافقة على شروط الخدمة أولاً لحفظ Ärende!")
        elif c_name and c_phone and device and employee_name:
            conn = get_db_connection()
            cursor = conn.cursor()
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(
                "INSERT INTO repairs (branch, customer_name, phone, email, device, imei, issue, price, status, employee, created_at, signature) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (global_branch, c_name, c_phone, c_email, device, imei, issue, price, "Under behandling", employee_name, created_at, customer_signature)
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
                "price": price, "employee": employee_name, "created_at": date.today().strftime('%Y-%m-%d'),
                "signature": customer_signature
            }
            st.session_state['rep_receipt_pdf'] = generate_pdf_from_record("repair_receipt_dual", rec_data, COMPANY_INFO)
        else:
            st.warning("⚠️ يرجى تعبئة الحقول الأساسية واسم الموظف.")

    if c_phone:
        rep_wa_text = f"Hej {c_name or 'Kunden'}! Ditt ärende för {device or 'enhet'} hos 30 Minutes Phone Fix ({global_branch}) har registrerats. Pris: {price} SEK. Välkommen!"
        st.markdown(f'<a href="{get_whatsapp_link(c_phone, rep_wa_text)}" target="_blank" class="whatsapp-btn">💬 إرسال تفاصيل الإصلاح عبر WhatsApp للعميل</a>', unsafe_allow_html=True)

    if 'rep_receipt_pdf' in st.session_state:
        st.markdown("---")
        display_pdf_preview(st.session_state['rep_receipt_pdf'], file_name="Inlamningskvitto_Dual.pdf", key_suffix="repair")
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
        display_pdf_preview(st.session_state['q_pdf'], file_name="quote.pdf", key_suffix="qu")
    st.markdown("</div>", unsafe_allow_html=True)

# --- TAB 4: INVOICE ---
with tab4:
    st.markdown("<div class='invoice-box'>", unsafe_allow_html=True)
    st.header(f"📄 إنشاء وتوليد الفواتير الرسمية (Faktura) / Invoices ({global_branch})")
    inv_emp = st.text_input(t["employee"], key="inv_emp")
    inv_cname = st.text_input(t["customer_name"], key="inv_cname")
    inv_addr = st.text_input("عنوان الزبون / Kundadress", key="inv_addr")
    inv_phone = st.text_input(t["phone"], key="inv_phone")
    inv_ref = st.text_input("مرجع الفاتورة / Er referens", key="inv_ref")
    inv_num = st.text_input("رقم الفاتورة / Fakturanummer", value=f"FAK-{datetime.now().strftime('%Y%m%d%H%M')}", key="inv_num")
    inv_desc = st.text_area("وصف الخدمات والأصناف / Artikelbeskrivning", value="Reparation och reservdelar", key="inv_desc")
    
    col_amt, col_moms = st.columns(2)
    with col_amt:
        inv_amount = st.number_input("المبلغ الإجمالي شامل الضريبة / Totalt belopp (Inkl. moms)", min_value=0.0, step=50.0, key="inv_amount")
    with col_moms:
        moms_rate_choice = st.selectbox("نسبة الضريبة / Moms rate", ["25%", "12%", "6%", "0% (Momsfri)"], key="inv_moms_rate")

    rate_val = 0.25 if "25%" in moms_rate_choice else (0.12 if "12%" in moms_rate_choice else (0.06 if "6%" in moms_rate_choice else 0.0))
    calc_moms = float(inv_amount - (inv_amount / (1.0 + rate_val))) if rate_val > 0 else 0.0

    st.markdown(f"### 💵 الإجمالي: **{inv_amount:.2f} SEK** | 🏛️ قيمة الضريبة ({moms_rate_choice}): **{calc_moms:.2f} SEK**")

    if st.button("حفظ وتوليد الفاتورة PDF / Save & Generate Invoice PDF", type="primary", key="btn_save_inv"):
        if inv_cname and inv_amount > 0 and inv_emp:
            conn = get_db_connection()
            cursor = conn.cursor()
            created_at = datetime.now().strftime("%Y-%m-%d")
            cursor.execute("""
                INSERT INTO invoices (branch, customer_name, phone, address, ref_no, invoice_no, item_desc, amount, moms, currency, moms_rate, employee, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (global_branch, inv_cname, inv_phone, inv_addr, inv_ref, inv_num, inv_desc, inv_amount, calc_moms, "SEK", moms_rate_choice, inv_emp, created_at))
            conn.commit()
            conn.close()
            st.success("✅ تم حفظ الفاتورة بنجاح!")
            
            inv_data = {
                "branch": global_branch, "customer_name": inv_cname, "address": inv_addr, "phone": inv_phone,
                "ref_no": inv_ref, "invoice_no": inv_num, "item_desc": inv_desc, "amount": inv_amount,
                "moms": calc_moms, "currency": "SEK", "moms_rate": moms_rate_choice, "employee": inv_emp,
                "created_at": created_at, "due_date": (date.today() + timedelta(days=30)).strftime('%Y-%m-%d')
            }
            st.session_state['inv_pdf'] = generate_pdf_from_record("invoice", inv_data, COMPANY_INFO)

    if 'inv_pdf' in st.session_state:
        display_pdf_preview(st.session_state['inv_pdf'], file_name=f"{inv_num}.pdf", key_suffix="invoice")
    st.markdown("</div>", unsafe_allow_html=True)

# --- TAB 5: SUBSCRIPTIONS ---
with tab5:
    st.markdown("<div class='sub-box'>", unsafe_allow_html=True)
    st.header(f"💳 إدارة الاشتراكات وخدمات الصيانة الدورية / Subscriptions ({global_branch})")
    sub_emp = st.text_input(t["employee"], key="sub_emp")
    sub_name = st.text_input(t["customer_name"], key="sub_name")
    sub_phone = st.text_input(t["phone"], key="sub_phone")
    sub_device = st.text_input(t["device"], key="sub_device")
    sub_imei = st.text_input(t["imei"], key="sub_imei")
    
    plan_type = st.selectbox("نوع الاشتراك / Subscription Plan", ["Basic Care (149 SEK/mån)", "Pro Shield (299 SEK/mån)", "Business VIP (499 SEK/mån)"], key="sub_plan")
    sub_price = st.number_input("سعر الاشتراك الشهري / Monthly Price", min_value=0.0, value=149.0, step=10.0, key="sub_price")

    if st.button("حفظ الاشتراك / Save Subscription", type="primary", key="btn_save_sub"):
        if sub_name and sub_phone and sub_emp:
            conn = get_db_connection()
            cursor = conn.cursor()
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("""
                INSERT INTO subscriptions (branch, customer_name, phone, device, imei, plan_type, price, employee, start_date, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (global_branch, sub_name, sub_phone, sub_device, sub_imei, plan_type, sub_price, sub_emp, str(date.today()), created_at))
            conn.commit()
            conn.close()
            st.success("✅ تم تسجيل الاشتراك بنجاح!")
    st.markdown("</div>", unsafe_allow_html=True)

# --- TAB 6: BUYBACK ---
with tab6:
    st.markdown("<div class='buyback-box'>", unsafe_allow_html=True)
    st.header(f"📱 شراء الأجهزة المستعملة وإيصال الاستلام القانوني / Buyback ({global_branch})")
    bb_emp = st.text_input(t["employee"], key="bb_emp")
    bb_name = st.text_input(t["customer_name"], key="bb_name")
    bb_phone = st.text_input(t["phone"], key="bb_phone")
    bb_pnr = st.text_input("رقم الهوية / الشخصي (Personnummer / Legimation)", key="bb_pnr")
    bb_device = st.text_input(t["device"], key="bb_device")
    bb_imei = st.text_input(t["imei"], key="bb_imei")
    bb_price = st.number_input("مبلغ الشراء المدفوع للزبون / Purchase Payout Price", min_value=0.0, step=100.0, key="bb_price")

    st.markdown("""
    <div style="background-color: #eafaf1; padding: 12px; border-radius: 8px; border-left: 5px solid #27ae60; font-size: 13px; margin-top: 10px; margin-bottom: 10px;">
        <b>📜 إقرار ملكية الجهاز (Ägarförsäkran):</b><br>
        أقر أنا البائع بأن الجهاز ملكي الشخصي، وليس مسروقاً، وتم تسجيل خروج كامل الحسابات (iCloud / Google).
    </div>
    """, unsafe_allow_html=True)
    bb_terms = st.checkbox("✅ أوافق على إقرار الملكية والشروط القانونية (Approve Ownership Declaration)", key="bb_terms_chk")
    bb_signature = render_signature_pad(key_suffix="buyback")

    if st.button("حفظ وتوليد إيصال شراء مستعمل PDF / Save Buyback PDF", type="primary", key="btn_save_bb"):
        if not bb_terms:
            st.error("❌ يجب الموافقة على إقرار الملكية أولاً!")
        elif bb_name and bb_pnr and bb_device and bb_emp:
            conn = get_db_connection()
            cursor = conn.cursor()
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("""
                INSERT INTO buybacks (branch, customer_name, phone, person_nummer, device, imei, purchase_price, employee, created_at, signature)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (global_branch, bb_name, bb_phone, bb_pnr, bb_device, bb_imei, bb_price, bb_emp, created_at, bb_signature))
            bb_db_id = cursor.lastrowid
            conn.commit()
            conn.close()
            st.success("✅ تم حفظ إيصال الشراء بنجاح!")
            
            bb_data = {
                "branch": global_branch, "buyback_id": str(bb_db_id), "customer_name": bb_name,
                "phone": bb_phone, "person_nummer": bb_pnr, "device": bb_device, "imei": bb_imei,
                "purchase_price": bb_price, "currency": "SEK", "employee": bb_emp,
                "created_at": date.today().strftime('%Y-%m-%d'), "signature": bb_signature
            }
            st.session_state['bb_pdf'] = generate_pdf_from_record("buyback_receipt", bb_data, COMPANY_INFO)

    if 'bb_pdf' in st.session_state:
        display_pdf_preview(st.session_state['bb_pdf'], file_name="Inköpskvitto.pdf", key_suffix="buyback")
    st.markdown("</div>", unsafe_allow_html=True)

# --- TAB 7: CAMPAIGNS ---
with tab7:
    st.markdown("<div class='campaign-box'>", unsafe_allow_html=True)
    st.header(f"🎄 حملات وعروض الأسعار الموسمية / Campaigns ({global_branch})")
    st.markdown("أحدث العروض والتخفيضات الخاصة بالأعياد وموسم العودة للمدارس وعروض الصيانة الشاملة:")
    st.info("🎁 **عرض الشتاء المميز:** خصم 15% على جميع تبديلات الشاشات الأصلية وبطاريات الهواتف.")
    st.info("🎁 **عرض الطلاب:** فحص مجاني للجهاز مع أي عملية صيانة.")
    st.markdown("</div>", unsafe_allow_html=True)

# --- TAB 8: PRE-ORDERS ---
with tab8:
    st.markdown("<div class='preorder-box'>", unsafe_allow_html=True)
    st.header(f"🛒 الطلبات المسبقة للقطع والهواتف / Pre-orders ({global_branch})")
    pre_emp = st.text_input(t["employee"], key="pre_emp")
    pre_name = st.text_input(t["customer_name"], key="pre_name")
    pre_phone = st.text_input(t["phone"], key="pre_phone")
    pre_item = st.text_area("تفاصيل القطعة أو الجهاز المطلوب / Item Details", key="pre_item")
    pre_deposit = st.number_input("عربون / عربون الحجز (Deposit SEK)", min_value=0.0, step=50.0, key="pre_deposit")

    if st.button("حفظ الطلب المسبق / Save Pre-order", type="primary", key="btn_save_pre"):
        if pre_name and pre_phone and pre_item and pre_emp:
            conn = get_db_connection()
            cursor = conn.cursor()
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("""
                INSERT INTO preorders (branch, customer_name, phone, item_details, deposit, employee, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (global_branch, pre_name, pre_phone, pre_item, pre_deposit, pre_emp, created_at))
            conn.commit()
            conn.close()
            st.success("✅ تم حفظ الطلب المسبق بنجاح!")
    st.markdown("</div>", unsafe_allow_html=True)

# --- TAB 9: INVENTORY ---
with tab9:
    st.markdown("<div class='inventory-box'>", unsafe_allow_html=True)
    st.header(f"📦 إدارة المخزون وقطع الغيار / Inventory ({global_branch})")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, part_name, stock_qty, min_limit FROM inventory WHERE branch = ?", (global_branch,))
    inv_rows = cursor.fetchall()
    
    if not inv_rows:
        default_parts = [
            ("Skärmbyte (Original)", 10, 2),
            ("Skärmbyte (OLED / Kopia)", 15, 3),
            ("Batteribyte", 12, 3),
            ("Laddport", 8, 2),
            ("Baksida", 5, 1)
        ]
        for p_name, qty, limit in default_parts:
            cursor.execute("INSERT INTO inventory (part_name, stock_qty, min_limit, branch) VALUES (?, ?, ?, ?)", (p_name, qty, limit, global_branch))
        conn.commit()
        cursor.execute("SELECT id, part_name, stock_qty, min_limit FROM inventory WHERE branch = ?", (global_branch,))
        inv_rows = cursor.fetchall()
    
    df_inv = pd.DataFrame(inv_rows, columns=["ID", "قطعة الغيار / Part", "الكمية المتاحة / Stock", "الحد الأدنى / Min Limit"])
    st.dataframe(df_inv, use_container_width=True)
    
    st.markdown("---")
    st.subheader("➕ إضافة قطعة جديدة للمخزون / Add Stock Part")
    new_part = st.text_input("اسم القطعة / Part Name", key="inv_pname")
    new_qty = st.number_input("الكمية / Quantity", min_value=0, value=5, key="inv_pqty")
    new_limit = st.number_input("الحد الأدنى للتنبيه / Min Limit", min_value=0, value=2, key="inv_plimit")
    
    if st.button("إضافة للمخزون / Add to Inventory", type="primary", key="btn_add_inv"):
        if new_part:
            cursor.execute("INSERT INTO inventory (part_name, stock_qty, min_limit, branch) VALUES (?, ?, ?, ?)", (new_part, new_qty, new_limit, global_branch))
            conn.commit()
            st.success("✅ تم إضافة القطعة بنجاح!")
            st.rerun()
    conn.close()
    st.markdown("</div>", unsafe_allow_html=True)

# --- TAB 10: SEARCH & ARCHIVE ---
with tab10:
    st.markdown("<div class='search-box'>", unsafe_allow_html=True)
    st.header(f"🔍 الأرشيف الشامل والبحث في سجلات الزبائن / Search & Archive ({global_branch})")
    
    search_query = st.text_input("بحث سريع (اسم العميل، رقم الهاتف، الجهاز، IMEI، رقم الفاتورة...):", key="global_search_input")
    section_filter = st.selectbox("تصفية حسب القسم / Filter by Section:", ["جميع الأقسام (All Sections)", "🛠️ الإصلاحات (Repairs)", "💡 عروض الأسعار (Quotes)", "📄 الفواتير (Invoices)", "💳 الاشتراكات (Subscriptions)", "📱 الشراء المستعمل (Buybacks)", "🛒 الطلبات المسبقة (Pre-orders)"], key="search_section_sel")

    conn = get_db_connection()
    cursor = conn.cursor()

    def fetch_all_records(table_name, search_term=""):
        try:
            if search_term:
                like_term = f"%{search_term}%"
                cursor.execute(f"SELECT * FROM {table_name} WHERE branch = ? AND (customer_name LIKE ? OR phone LIKE ? OR employee LIKE ?)", (global_branch, like_term, like_term, like_term))
            else:
                cursor.execute(f"SELECT * FROM {table_name} WHERE branch = ?", (global_branch,))
            return cursor.fetchall()
        except Exception:
            return []

    st.markdown("---")
    
    # 1. Repairs
    if "جميع الأقسام" in section_filter or "الإصلاحات" in section_filter:
        st.subheader("🛠️ سجلات الإصلاحات (Repairs)")
        rep_records = fetch_all_records("repairs", search_query)
        if rep_records:
            for r in rep_records:
                with st.expander(f"إصلاح #{r['id']} - {r['customer_name']} ({r['phone']}) - {r['device']} - {r['created_at']}"):
                    st.write(f"**الموظف:** {r['employee']} | **الحالة:** {r['status']} | **السعر:** {r['price']} SEK")
                    st.write(f"**العطل:** {r['issue']} | **IMEI:** {r['imei']}")
                    if st.button(f"🖨️ طباعة إيصال الإصلاح #{r['id']}", key=f"btn_print_rep_{r['id']}"):
                        rec_data = {
                            "branch": r['branch'], "repair_id": str(r['id']), "customer_name": r['customer_name'],
                            "phone": r['phone'], "device": r['device'], "imei": r['imei'], "issue": r['issue'],
                            "price": r['price'], "employee": r['employee'], "created_at": r['created_at'][:10],
                            "signature": r.get('signature', None)
                        }
                        st.session_state[f'search_pdf_{r["id"]}'] = generate_pdf_from_record("repair_receipt_dual", rec_data, COMPANY_INFO)
                if f'search_pdf_{r["id"]}' in st.session_state:
                    display_pdf_preview(st.session_state[f'search_pdf_{r["id"]}'], file_name=f"Repair_{r['id']}.pdf", key_suffix=f"rep_{r['id']}")
        else:
            st.info("لا توجد سجلات إصلاح مطابقة.")

    # 2. Quotes
    if "جميع الأقسام" in section_filter or "عروض الأسعار" in section_filter:
        st.subheader("💡 سجلات عروض الأسعار (Quotes)")
        quote_records = fetch_all_records("quotes", search_query)
        if quote_records:
            for r in quote_records:
                with st.expander(f"عرض سعر #{r['id']} - {r['customer_name']} ({r['phone']}) - {r['device']} - {r['created_at']}"):
                    st.write(f"**الموظف:** {r['employee']} | **الإجمالي:** {r['total']} SEK | **الربح:** {r.get('profit', 0)} SEK")
                    st.write(f"**التفاصيل:** {r['issues']}")
                    if st.button(f"🖨️ طباعة عرض السعر #{r['id']}", key=f"btn_print_q_{r['id']}"):
                        rec_data = {
                            "branch": r['branch'], "customer_name": r['customer_name'], "phone": r['phone'],
                            "device": r['device'], "issues": r['issues'], "total": r['total'],
                            "currency": "SEK", "employee": r['employee'], "created_at": r['created_at'][:10]
                        }
                        st.session_state[f'search_q_pdf_{r["id"]}'] = generate_pdf_from_record("quote", rec_data, COMPANY_INFO)
                if f'search_q_pdf_{r["id"]}' in st.session_state:
                    display_pdf_preview(st.session_state[f'search_q_pdf_{r["id"]}'], file_name=f"Quote_{r['id']}.pdf", key_suffix=f"q_{r['id']}")
        else:
            st.info("لا توجد عروض أسعار مطابقة.")

    # 3. Invoices
    if "جميع الأقسام" in section_filter or "الفواتير" in section_filter:
        st.subheader("📄 سجلات الفواتير الرسمية (Invoices)")
        inv_records = fetch_all_records("invoices", search_query)
        if inv_records:
            for r in inv_records:
                with st.expander(f"فاتورة {r['invoice_no']} - {r['customer_name']} - {r['amount']} SEK - {r['created_at']}"):
                    st.write(f"**الموظف:** {r['employee']} | **العنوان:** {r['address']} | **الضريبة:** {r['moms']} SEK")
                    st.write(f"**الوصف:** {r['item_desc']}")
                    if st.button(f"🖨️ طباعة الفاتورة {r['invoice_no']}", key=f"btn_print_inv_{r['id']}"):
                        inv_data = {
                            "branch": r['branch'], "customer_name": r['customer_name'], "address": r['address'],
                            "phone": r['phone'], "ref_no": r['ref_no'], "invoice_no": r['invoice_no'],
                            "item_desc": r['item_desc'], "amount": r['amount'], "moms": r['moms'],
                            "currency": r['currency'], "moms_rate": r['moms_rate'], "employee": r['employee'],
                            "created_at": r['created_at'], "due_date": (date.today() + timedelta(days=30)).strftime('%Y-%m-%d')
                        }
                        st.session_state[f'search_inv_pdf_{r["id"]}'] = generate_pdf_from_record("invoice", inv_data, COMPANY_INFO)
                if f'search_inv_pdf_{r["id"]}' in st.session_state:
                    display_pdf_preview(st.session_state[f'search_inv_pdf_{r["id"]}'], file_name=f"Invoice_{r['invoice_no']}.pdf", key_suffix=f"inv_{r['id']}")
        else:
            st.info("لا توجد فواتير مطابقة.")

    # 4. Buybacks
    if "جميع الأقسام" in section_filter or "الشراء المستعمل" in section_filter:
        st.subheader("📱 سجلات شراء الأجهزة المستعملة (Buybacks)")
        bb_records = fetch_all_records("buybacks", search_query)
        if bb_records:
            for r in bb_records:
                with st.expander(f"شراء مستعمل #{r['id']} - {r['customer_name']} ({r['phone']}) - {r['device']} - {r['created_at']}"):
                    st.write(f"**الموظف:** {r['employee']} | **الشخصي:** {r['person_nummer']} | **المبلغ:** {r['purchase_price']} SEK")
                    st.write(f"**IMEI:** {r['imei']}")
                    if st.button(f"🖨️ طباعة إيصال الشراء #{r['id']}", key=f"btn_print_bb_{r['id']}"):
                        bb_data = {
                            "branch": r['branch'], "buyback_id": str(r['id']), "customer_name": r['customer_name'],
                            "phone": r['phone'], "person_nummer": r['person_nummer'], "device": r['device'],
                            "imei": r['imei'], "purchase_price": r['purchase_price'], "currency": "SEK",
                            "employee": r['employee'], "created_at": r['created_at'][:10], "signature": r.get('signature', None)
                        }
                        st.session_state[f'search_bb_pdf_{r["id"]}'] = generate_pdf_from_record("buyback_receipt", bb_data, COMPANY_INFO)
                if f'search_bb_pdf_{r["id"]}' in st.session_state:
                    display_pdf_preview(st.session_state[f'search_bb_pdf_{r["id"]}'], file_name=f"Buyback_{r['id']}.pdf", key_suffix=f"bb_{r['id']}")
        else:
            st.info("لا توجد سجلات شراء مستعمل مطابقة.")

    conn.close()
    st.markdown("</div>", unsafe_allow_html=True)
