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

# --- Optimized Responsive Digital Signature Pad Component (Tailored for iPads & Mobile) ---
def render_signature_pad(key_prefix="sig"):
    html_code = f"""
    <div style="background-color: #ffffff; padding: 15px; border-radius: 8px; border: 1px solid #cbd5e1; margin-bottom: 10px;">
        <p style="margin: 0 0 8px 0; font-size: 14px; font-weight: 600; color: #1e293b;">✍️ توقع هنا بإصبعك أو بالقلم (Customer Digital Signature - Touch / Pen / Mouse)</p>
        <canvas id="canvas_{key_prefix}" width="500" height="150" style="border: 2px dashed #94a3b8; border-radius: 6px; background-color: #f8fafc; cursor: crosshair; width: 100%; max-width: 500px; touch-action: none;"></canvas>
        <div style="margin-top: 8px; display: flex; justify-content: space-between; align-items: center;">
            <button type="button" onclick="clearCanvas_{key_prefix}()" style="background-color: #ef4444; color: white; border: none; padding: 6px 12px; border-radius: 4px; font-size: 12px; cursor: pointer; font-weight: 600;">🗑️ مسح التوقيع / Clear</button>
            <span id="status_{key_prefix}" style="font-size: 12px; color: #16a34a; font-weight: 600;"></span>
        </div>
    </div>
    <script>
        var canvas_{key_prefix} = document.getElementById('canvas_{key_prefix}');
        var ctx_{key_prefix} = canvas_{key_prefix}.getContext('2d');
        var drawing = false;

        ctx_{key_prefix}.lineWidth = 2.5;
        ctx_{key_prefix}.lineCap = 'round';
        ctx_{key_prefix}.lineJoin = 'round';
        ctx_{key_prefix}.strokeStyle = "#0f172a";

        function getPos(e) {
            var rect = canvas_{key_prefix}.getBoundingClientRect();
            var clientX = e.clientX || (e.touches && e.touches[0].clientX);
            var clientY = e.clientY || (e.touches && e.touches[0].clientY);
            return {
                x: clientX - rect.left,
                y: clientY - rect.top
            };
        }

        function startDraw(e) {
            drawing = true;
            var p = getPos(e);
            ctx_{key_prefix}.beginPath();
            ctx_{key_prefix}.moveTo(p.x, p.y);
            if (e.type === 'touchstart') e.preventDefault();
        }

        function draw(e) {
            if (!drawing) return;
            var p = getPos(e);
            ctx_{key_prefix}.lineTo(p.x, p.y);
            ctx_{key_prefix}.stroke();
            if (e.type === 'touchmove') e.preventDefault();
        }

        function stopDraw(e) {
            if (!drawing) return;
            drawing = false;
            var dataURL = canvas_{key_prefix}.toDataURL("image/png");
            
            // Push data URL to Streamlit session via hidden mechanism or element storage
            window.parent.document.dispatchEvent(new CustomEvent('streamlit:set_signature', {{ detail: {{ key: '{key_prefix}', data: dataURL }} }}));
            document.getElementById('status_{key_prefix}').innerText = "✅ تم التقاط وتأكيد التوقيع بنجاح";
        }

        canvas_{key_prefix}.addEventListener('mousedown', startDraw);
        canvas_{key_prefix}.addEventListener('mousemove', draw);
        canvas_{key_prefix}.addEventListener('mouseup', stopDraw);
        canvas_{key_prefix}.addEventListener('mouseleave', stopDraw);

        canvas_{key_prefix}.addEventListener('touchstart', startDraw, {{passive: false}});
        canvas_{key_prefix}.addEventListener('touchmove', draw, {{passive: false}});
        canvas_{key_prefix}.addEventListener('touchend', stopDraw);

        function clearCanvas_{key_prefix}() {
            ctx_{key_prefix}.clearRect(0, 0, canvas_{key_prefix}.width, canvas_{key_prefix}.height);
            document.getElementById('status_{key_prefix}').innerText = "";
        }
    </script>
    """
    return html_code

# --- Database Setup & Migration ---
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

# --- Custom Responsive Styling ---
st.markdown("""
<style>
    .stApp { background-color: #f1f5f9; color: #1e293b; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    h1, h2, h3 { color: #0f172a; font-weight: 700; }
    div.stButton > button { border-radius: 8px; font-weight: 600; padding: 0.6rem 1.2rem; width: 100%; }
    .dashboard-box { background-color: #ffffff; padding: 22px; border-radius: 12px; border-left: 6px solid #2563eb; box-shadow: 0 2px 10px rgba(0,0,0,0.03); margin-bottom: 15px;}
    .repair-box { background-color: #ffffff; padding: 22px; border-radius: 12px; border-left: 6px solid #0d9488; box-shadow: 0 2px 10px rgba(0,0,0,0.03); margin-bottom: 15px;}
    .quote-box { background-color: #ffffff; padding: 22px; border-radius: 12px; border-left: 6px solid #d97706; box-shadow: 0 2px 10px rgba(0,0,0,0.03); margin-bottom: 15px;}
    .invoice-box { background-color: #ffffff; padding: 22px; border-radius: 12px; border-left: 6px solid #7c3aed; box-shadow: 0 2px 10px rgba(0,0,0,0.03); margin-bottom: 15px;}
    .sub-box { background-color: #ffffff; padding: 22px; border-radius: 12px; border-left: 6px solid #ea580c; box-shadow: 0 2px 10px rgba(0,0,0,0.03); margin-bottom: 15px;}
    .buyback-box { background-color: #ffffff; padding: 22px; border-radius: 12px; border-left: 6px solid #16a34a; box-shadow: 0 2px 10px rgba(0,0,0,0.03); margin-bottom: 15px;}
    .search-box { background-color: #ffffff; padding: 22px; border-radius: 12px; border-left: 6px solid #475569; box-shadow: 0 2px 10px rgba(0,0,0,0.03); margin-bottom: 15px;}
    .login-container { background: #ffffff; padding: 35px; border-radius: 14px; box-shadow: 0 10px 25px rgba(0,0,0,0.08); max-width: 450px; margin: auto; border-top: 6px solid #dc2626; }
    
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
        "tab_dash": "📊 Översikt (Dashboard)", "tab_repair": "🛠️ Ny reparation", "tab_quote": "💡 Offert",
        "tab_invoice": "📄 Faktura", "tab_sub": "💳 Abonnemang", "tab_buyback": "📱 Inköp Begagnat",
        "tab_campaign": "🎄 Kampanjer", "tab_preorder": "🛒 Förbeställning", "tab_stock": "📦 Lagerhantering", "tab_search": "🔍 Sök Alla Kundfiler",
        "employee": "Handläggare / Säljare", "phone": "Telefonnummer", "customer_name": "Kundens Namn / Företag",
        "email": "E-postadress", "device": "Enhet / Modell", "imei": "IMEI / Serienummer",
        "price": "Pris inkl. moms (SEK)", "issue": "Beskrivning av fel / Utfört arbete", "save_repair": "Registrera Ärende & Skapa Kvitto (Två delar)", "success_repair": "✅ Ärendet har registrerats!"
    },
    "English": {
        "tab_dash": "📊 Dashboard", "tab_repair": "🛠️ New Repair", "tab_quote": "💡 Price Quotation",
        "tab_invoice": "📄 Official Invoice", "tab_sub": "💳 Subscriptions", "tab_buyback": "📱 Buyback",
        "tab_campaign": "🎄 Campaigns", "tab_preorder": "🛒 Pre-orders", "tab_stock": "📦 Stock Inventory", "tab_search": "🔍 Search All Customer Files",
        "employee": "Employee Name", "phone": "Phone Number", "customer_name": "Customer Name / Company",
        "email": "Email Address", "device": "Device Model", "imei": "IMEI / Serial Number",
        "price": "Price incl. VAT (SEK)", "issue": "Issue Description", "save_repair": "Register Order & Dual Receipt", "success_repair": "✅ Order registered successfully!"
    },
    "العربية (Arabic)": {
        "tab_dash": "📊 لوحة التحكم والإحصاءات", "tab_repair": "🛠️ تسجيل إصلاح جديد", "tab_quote": "💡 عرض سعر رسمية",
        "tab_invoice": "📄 إنشاء فاتورة قانونية", "tab_sub": "💳 اشتراكات الصيانة والضمان", "tab_buyback": "📱 شراء المستعمل",
        "tab_campaign": "🎄 العروض الموسمية", "tab_preorder": "🛒 الطلبات المسبقة", "tab_stock": "📦 إدارة القطع والمخزون", "tab_search": "🔍 البحث في كافة ملفات الزبائن",
        "employee": "اسم الموظف المسؤول", "phone": "رقم الهاتف", "customer_name": "اسم العميل / الشركة",
        "email": "البريد الإلكتروني", "device": "نوع وطراز الجهاز", "imei": "رقم الـ IMEI / التسلسلي",
        "price": "السعر شامل الضريبة 25% (SEK)", "issue": "تفاصيل العطل والخدمة", "save_repair": "حفظ الطلب وتوليد الإيصال المزدوج", "success_repair": "✅ تم تسجيل الطلب بنجاح!"
    }
}

def get_whatsapp_link(phone, text):
    if not phone:
        return "#"
    clean_phone = str(phone).strip().replace(" ", "").replace("-", "")
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
<div style="background-color: #ffffff; padding: 12px 18px; border-radius: 10px; border: 1px solid #cbd5e1; margin-bottom: 15px; font-size: 13.5px; box-shadow: 0 1px 3px rgba(0,0,0,0.02);">
    <b>🏢 Aktiv Butik:</b> {comp['name']} - {comp['address']} | <b>Tel:</b> {comp['phone']} | <b>Org.nr:</b> {comp['org_nr']} | <b>Swish:</b> {comp['swish']} | <b>{comp['f_skatt']}</b>
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
    st.markdown("Ange PIN-kod för åtkomst / أدخل رمز المرور:")
    
    login_pin = st.text_input("🔑 PIN-kod / Passcode", type="password", key="login_pin_input")
    remember_me = st.checkbox("💾 Spara inloggning på denna enhet / تذكرني على هذا الجهاز", value=st.session_state.get('remember_device', False), key="remember_device_chk")
    
    if login_pin:
        if login_pin.strip() == "Tunapark":
            st.session_state['authenticated'] = True
            st.session_state['remember_device'] = remember_me
            st.success("✅ Inloggningen godkänd!")
            st.rerun()
        else:
            st.error("❌ Felaktig PIN-kod!")
            
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

if st.sidebar.button("🔒 Logga ut (Log Out)"):
    st.session_state['authenticated'] = False
    st.session_state['remember_device'] = False
    st.rerun()

# --- Responsive PDF Preview & Direct Mobile Print Component ---
def display_pdf_preview(pdf_buffer, file_name="document.pdf", key_suffix="doc"):
    pdf_buffer.seek(0)
    pdf_bytes = pdf_buffer.read()
    b64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
    st.success("✅ Dokumentet är redo för utskrift och export!")
    
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
            <p style="padding: 20px;">📱 Mobilvisning: Klicka på knappen <b>"🖨️ Skriv ut Direct"</b> eller <b>"Öppna i ny flik"</b> ovan för utskrift.</p>
        </object>
    </div>
    """
    st.markdown(pdf_display, unsafe_allow_html=True)

# --- PDF GENERATOR (DUAL RECEIPT + APPLE/SAMSUNG TERMS & EMBEDDED SIGNATURE) ---
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
            price_val = float(data.get('price', 0.0))
            p.drawString(440, start_y - 98, f"{price_val:.2f} {currency}")
            
            moms_calc = price_val * (0.25 / 1.25)
            netto_calc = price_val - moms_calc
            p.setFont("Helvetica", 7)
            p.drawString(40, start_y - 114, f"Netto: {netto_calc:.2f} SEK | Moms (25%): {moms_calc:.2f} SEK")
            p.setFont("Helvetica-Bold", 8)
            p.drawString(340, start_y - 114, f"Totalt uppskattat pris: {price_val:.2f} {currency}")
            
            p.setFont("Helvetica-Bold", 6)
            p.drawString(40, start_y - 128, "SERVICEVILLKOR & KONSUMENTRÄTT (Apple & Samsung Standardized Terms):")
            p.setFont("Helvetica", 5.5)
            p.drawString(40, start_y - 135, "1. Inlämnad enhet genomgår inledande diagnos. Dolda fel (t.ex. fuktskador, böjt chassi) ansvarar verkstaden ej för.")
            p.drawString(40, start_y - 141, "2. Garantin gäller endast utbytt del/utfört arbete i 3-12 månader. Garantin förverkas vid yttre åverkan eller vätska.")
            p.drawString(40, start_y - 147, "3. Ej uthämtade enheter efter 3 månader tillfaller verkstaden i enlighet med lag (1985:982).")

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

        draw_repair_section(height - 25, "BUTIKENS KOPIA / STORE COPY")
        p.setDash(3, 3)
        p.setLineWidth(0.5)
        p.line(20, height / 2, width - 20, height / 2)
        p.setDash()
        p.setFont("Helvetica-Oblique", 6)
        p.drawString(width / 2 - 40, height / 2 + 3, "✂ Klipp här / Cut here")
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
        p.drawString(40, height - 100, "Upprättat i enlighet med lag (1999:158) om handel med begagnade varor.")

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
        
        price_val = float(data.get('purchase_price', 0.0))
        p.setFillColorRGB(0.95, 0.95, 0.95)
        p.rect(40, height - 225, width - 80, 25, fill=1, stroke=0)
        p.setFillColorRGB(0, 0, 0)
        p.setFont("Helvetica-Bold", 10)
        p.drawString(50, height - 210, f"Utbetalt belopp till säljaren: {price_val:.2f} {currency}")

        p.setFont("Helvetica-Bold", 8)
        p.drawString(40, height - 260, "SÄLJARENS ÄGARFÖRSÄKRAN & JURIDISKA INTYGANDE:")
        p.setFont("Helvetica", 7)
        p.drawString(40, height - 272, "1. Undertecknad säljare intygar att enheten är min egna egendom och lagligt förvärvad.")
        p.drawString(40, height - 280, "2. Enheten är återställd och fri från avbetalningskontrakt samt stöldspärrar.")

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
        
        total_val = float(data.get('total', 0.0))
        moms_val = total_val * (0.25 / 1.25)
        netto_val = total_val - moms_val

        p.line(40, height - 230, width - 40, height - 230)
        p.setFont("Helvetica", 8.5)
        p.drawString(320, height - 245, f"Netto exkl. moms: {netto_val:.2f} SEK")
        p.drawString(320, height - 258, f"Moms (25%): {moms_val:.2f} SEK")
        p.setFont("Helvetica-Bold", 10)
        p.drawString(320, height - 275, f"Totalt inklusive moms: {total_val:.2f} SEK")
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

        p.setLineWidth(0.5)
        p.line(40, height - 85, width - 40, height - 85)

        p.setFont("Helvetica-Bold", 8.5)
        p.drawString(40, height - 102, "FAKTURAUPPGIFTER")
        p.setFont("Helvetica", 8)
        p.drawString(40, height - 115, f"Fakturanummer: {data.get('invoice_no', '')}")
        p.drawString(40, height - 127, f"Fakturadatum: {data.get('created_at', '')}")
        p.drawString(40, height - 139, f"Förfallodatum: {data.get('due_date', '')}")

        p.setFont("Helvetica-Bold", 8.5)
        p.drawString(320, height - 102, "FAKTURERAS TILL (KUND)")
        p.setFont("Helvetica", 8)
        p.drawString(320, height - 115, f"Kund: {data.get('customer_name', '')}")
        p.drawString(320, height - 127, f"Org.nr / P.nr: {data.get('org_no_cust', 'Ej angivet')}")
        p.drawString(320, height - 139, f"Tel: {data.get('phone', '')}")

        p.setFillColorRGB(0.92, 0.92, 0.92)
        p.rect(40, height - 200, width - 80, 16, fill=1, stroke=0)
        p.setFillColorRGB(0, 0, 0)
        p.setFont("Helvetica-Bold", 8)
        p.drawString(45, height - 194, "Beskrivning / Artikel")
        p.drawString(300, height - 194, "Moms %")
        p.drawString(370, height - 194, f"Pris exkl. moms")
        p.drawString(460, height - 194, f"Totalt SEK")

        amount_val = float(data.get('amount', 0.0))
        moms_val = float(data.get('moms', 0.0))
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
    st.header(f"📊 Översikt & Nyckeltal / Dashboard ({global_branch})")
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
    c2.metric("💡 Offertförslag", quote_count)
    c3.metric("📄 Skapade Fakturor", inv_count)
    c4.metric("💰 Omsättning Reparationer", f"{rep_revenue:.2f} SEK")
    st.markdown("</div>", unsafe_allow_html=True)

# --- TAB 2: REPAIR ORDER ---
with tab2:
    st.markdown("<div class='repair-box'>", unsafe_allow_html=True)
    st.header(f"🛠️ Registrera Ny Reparation ({global_branch})")
    
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
        warranty_choice = st.selectbox("Garanti / Warranty", ["3 Månader (Standard)", "6 Månader", "12 Månader", "Ingen garanti"], key="rep_warranty")
        cost_price = st.number_input("Inköpskostnad exkl. moms (SEK)", min_value=0.0, step=50.0, key="rep_cost")

    repair_issues_options = [
        "Skärmbyte (Original)", "Skärmbyte (OLED / In-Cell)", "Batteribyte",
        "Laddkontakt", "Baksida / Glasbyte", "Kamera bak/fram", "Högtalare", "Fuktsanering", "Mjukvara"
    ]
    selected_rep_issues = st.multiselect("Välj utförda tjänster / reservdelar:", repair_issues_options, key="multi_rep_issues")
    price = st.number_input(t["price"], min_value=0.0, step=50.0, key="rep_price")
    
    auto_issues_str = ", ".join(selected_rep_issues)
    issue = st.text_area(t["issue"], value=auto_issues_str, key="rep_issue_desc")

    st.components.v1.html(render_signature_pad("repair_sig"), height=210)
    sig_input = st.text_input("🔑 Bekräfta signaturkod eller klistra in signaturreferens:", key="repair_sig_input")

    terms_accepted = st.checkbox("✅ Kunden har godkänt villkoren & godkänner reparationen", key="rep_terms_chk")

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

    if 'rep_receipt_pdf' in st.session_state:
        st.markdown("---")
        display_pdf_preview(st.session_state['rep_receipt_pdf'], file_name=f"Inlamningskvitto_Dual_{c_name}.pdf", key_suffix="repair")
    st.markdown("</div>", unsafe_allow_html=True)

# --- TAB 3: QUOTE ---
with tab3:
    st.markdown("<div class='quote-box'>", unsafe_allow_html=True)
    st.header(f"💡 Skapa Offert / Price Quotation ({global_branch})")
    
    q_c1, q_c2 = st.columns(2)
    with q_c1:
        q_emp = st.text_input(t["employee"], key="q_emp")
        q_name = st.text_input(t["customer_name"], key="q_name")
        q_phone = st.text_input(t["phone"], key="q_phone")
    with q_c2:
        q_device = st.text_input(t["device"], key="q_device")
        valid_days = st.number_input("Giltighetstid i dagar", min_value=7, max_value=60, value=14, key="q_valid_days")

    q_issue = st.text_area("Offertdetaljer / Tjänster & Delar", key="q_issue_desc")
    q_total = st.number_input("Totalt Offertbelopp inkl. moms (SEK)", min_value=0.0, step=100.0, key="q_total")

    if st.button("Spara & Generera Offert PDF", type="primary", key="btn_save_q"):
        if q_name and q_device and q_total > 0 and q_emp:
            conn = get_db_connection()
            cursor = conn.cursor()
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            valid_until_date = (date.today() + timedelta(days=valid_days)).strftime('%Y-%m-%d')
            cursor.execute("INSERT INTO quotes (branch, customer_name, phone, email, device, issues, total, profit, valid_until, employee, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (global_branch, q_name, q_phone, "", q_device, q_issue, q_total, q_total * 0.4, valid_until_date, q_emp, created_at))
            conn.commit()
            conn.close()
            st.success("✅ Offerten har sparats!")
            
            record_data = {
                "branch": global_branch, "customer_name": q_name, "phone": q_phone, 
                "device": q_device, "issues": q_issue, "total": q_total, 
                "currency": "SEK", "valid_until": valid_until_date, "employee": q_emp, 
                "created_at": date.today().strftime('%Y-%m-%d')
            }
            st.session_state['q_pdf'] = generate_pdf_from_record("quote", record_data, COMPANY_INFO)

    if 'q_pdf' in st.session_state:
        display_pdf_preview(st.session_state['q_pdf'], file_name="Offert_Kostnadsforslag.pdf", key_suffix="quote")
    st.markdown("</div>", unsafe_allow_html=True)

# --- TAB 4: INVOICE ---
with tab4:
    st.markdown("<div class='invoice-box'>", unsafe_allow_html=True)
    st.header(f"📄 Skapa Faktura ({global_branch})")
    
    inv_c1, inv_c2 = st.columns(2)
    with inv_c1:
        inv_emp = st.text_input(t["employee"], key="inv_emp")
        inv_no = st.text_input("Fakturanummer", value=f"SE-{datetime.now().strftime('%Y%m%d%H%M')}", key="inv_no")
        inv_name = st.text_input(t["customer_name"], key="inv_name")
        inv_org_no = st.text_input("Org.nr / Personnummer", key="inv_org_no")
        inv_phone = st.text_input(t["phone"], key="inv_phone")
    with inv_c2:
        inv_address = st.text_input("Faktureringsadress", key="inv_address")
        inv_ref = st.text_input("Er Referens", key="inv_ref")
        pay_terms = st.selectbox("Betalningsvillkor", ["10 Dagar", "15 Dagar", "30 Dagar", "Direktbetalning"], key="inv_pay_terms")
        inv_desc = st.text_input("Artikelbeskrivning", value="Reparation och reservdelar", key="inv_desc")

    inv_amount = st.number_input("Totalt belopp inkl. moms (SEK)", min_value=0.0, step=100.0, key="inv_amount")
    moms_amount = inv_amount * (0.25 / 1.25)

    if st.button("Spara & Generera Faktura PDF", type="primary", key="btn_save_inv"):
        if inv_name and inv_amount > 0 and inv_emp:
            conn = get_db_connection()
            cursor = conn.cursor()
            created_at = datetime.now().strftime("%Y-%m-%d")
            due_date = (date.today() + timedelta(days=10)).strftime('%Y-%m-%d')
            cursor.execute("INSERT INTO invoices (branch, customer_name, phone, address, org_no_cust, ref_no, invoice_no, item_desc, amount, moms, currency, moms_rate, payment_terms, due_date, employee, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", 
                           (global_branch, inv_name, inv_phone, inv_address, inv_org_no, inv_ref, inv_no, inv_desc, inv_amount, moms_amount, "SEK", "25%", pay_terms, due_date, inv_emp, created_at))
            conn.commit()
            conn.close()
            st.success("✅ Fakturan har skapats!")

            record_data = {
                "branch": global_branch, "invoice_no": inv_no, "customer_name": inv_name, "org_no_cust": inv_org_no,
                "address": inv_address, "phone": inv_phone, "ref_no": inv_ref, "item_desc": inv_desc, 
                "amount": inv_amount, "moms": moms_amount, "currency": "SEK", "moms_rate": "25%", 
                "payment_terms": pay_terms, "employee": inv_emp, "created_at": created_at, "due_date": due_date
            }
            st.session_state['inv_pdf'] = generate_pdf_from_record("invoice", record_data, COMPANY_INFO)

    if 'inv_pdf' in st.session_state:
        display_pdf_preview(st.session_state['inv_pdf'], file_name=f"Faktura_{inv_no}.pdf", key_suffix="invoice")
    st.markdown("</div>", unsafe_allow_html=True)

# --- TAB 5: SUBSCRIPTIONS ---
with tab5:
    st.markdown("<div class='sub-box'>", unsafe_allow_html=True)
    st.header(f"💳 Abonnemang & Trygghetsavtal ({global_branch})")
    
    sub_c1, sub_c2 = st.columns(2)
    with sub_c1:
        sub_emp = st.text_input(t["employee"], key="sub_emp")
        sub_name = st.text_input(t["customer_name"], key="sub_name")
        sub_phone = st.text_input(t["phone"], key="sub_phone")
    with sub_c2:
        sub_device = st.text_input(t["device"], key="sub_device")
        sub_imei = st.text_input(t["imei"], key="sub_imei")
        sub_plan = st.selectbox("Abonnemangstyp", ["Skärmskydd Garanti (12 Mån)", "Full Protection Plan"], key="sub_plan")
        sub_price = st.number_input("Årsavgift (SEK)", min_value=0.0, step=49.0, key="sub_price")

    if st.button("Teckna Abonnemang", type="primary", key="btn_save_sub"):
        if sub_name and sub_phone and sub_emp:
            conn = get_db_connection()
            cursor = conn.cursor()
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            end_date = (date.today() + timedelta(days=365)).strftime('%Y-%m-%d')
            cursor.execute("INSERT INTO subscriptions (branch, customer_name, phone, device, imei, plan_type, price, employee, start_date, end_date, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (global_branch, sub_name, sub_phone, sub_device, sub_imei, sub_plan, sub_price, sub_emp, date.today().strftime('%Y-%m-%d'), end_date, created_at))
            conn.commit()
            conn.close()
            st.success("✅ Abonnemanget har tecknats!")
    st.markdown("</div>", unsafe_allow_html=True)

# --- TAB 6: BUYBACK ---
with tab6:
    st.markdown("<div class='buyback-box'>", unsafe_allow_html=True)
    st.header(f"📱 Inköp av Begagnad Elektronik ({global_branch})")
    
    bb_c1, bb_c2 = st.columns(2)
    with bb_c1:
        b_emp = st.text_input(t["employee"], key="b_emp")
        b_name = st.text_input("Säljarens Namn", key="b_name")
        b_person_num = st.text_input("Personnummer (YYYYMMDD-XXXX)", key="b_pnum")
        b_phone = st.text_input(t["phone"], key="b_phone")
        b_id_chk = st.checkbox("✅ Legitimation kontrollerad", key="b_id_chk")
    with bb_c2:
        b_device = st.text_input(t["device"], key="b_device")
        b_imei = st.text_input(t["imei"], key="b_imei")
        b_grade = st.selectbox("Enhetens Skick", ["Nyskick (A)", "Gott Skick (B)", "Slitage (C)", "Defekt"], key="b_grade")
        b_price = st.number_input("Utbetalt Belopp (SEK)", min_value=0.0, step=100.0, key="b_price")

    st.components.v1.html(render_signature_pad("bb_sig"), height=210)
    bb_sig_input = st.text_input("🔑 Bekräfta signatur för säljare:", key="bb_sig_input")

    if st.button("Spara Inköp & Skapa Inköpskvitto PDF", type="primary", key="btn_save_bb"):
        if not b_id_chk:
            st.error("❌ Legitimation måste kontrolleras!")
        elif b_name and b_person_num and b_price > 0 and b_emp:
            conn = get_db_connection()
            cursor = conn.cursor()
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("INSERT INTO buybacks (branch, customer_name, phone, person_nummer, id_verified, device, imei, purchase_price, condition_grade, employee, signature_b64, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", 
                           (global_branch, b_name, b_phone, b_person_num, 1 if b_id_chk else 0, b_device, b_imei, b_price, b_grade, b_emp, bb_sig_input, created_at))
            bb_id = cursor.lastrowid
            conn.commit()
            conn.close()
            st.success("✅ Inköpet har registrerats!")

            rec_data = {
                "branch": global_branch, "buyback_id": str(bb_id), "customer_name": b_name, "person_nummer": b_person_num,
                "phone": b_phone, "id_verified": b_id_chk, "device": b_device, "imei": b_imei, "condition_grade": b_grade,
                "purchase_price": b_price, "employee": b_emp, "signature_b64": bb_sig_input, "created_at": date.today().strftime('%Y-%m-%d')
            }
            st.session_state['bb_pdf'] = generate_pdf_from_record("buyback_receipt", rec_data, COMPANY_INFO)

    if 'bb_pdf' in st.session_state:
        display_pdf_preview(st.session_state['bb_pdf'], file_name="Inkopsavtal_Begagnat.pdf", key_suffix="buyback")
    st.markdown("</div>", unsafe_allow_html=True)

# --- TAB 7: CAMPAIGNS ---
with tab7:
    st.markdown("### 🎄 Kampanjer & Erbjudanden")
    st.info("💡 Aktiva marknadskampanjer i butiken:")
    st.markdown("""
    • **Paketerbjudande:** 20% rabatt på skärmskydd vid skärmbyte.
    • **Batteribyte Kampanj:** Fast pris 499 SEK för valda modeller.
    • **Studentrabatt:** 10% rabatt på utfört arbete vid uppvisande av student-ID.
    """, unsafe_allow_html=True)

# --- TAB 8: PRE-ORDERS ---
with tab8:
    st.markdown("### 🛒 Förbeställning & Handpenning")
    po_c1, po_c2 = st.columns(2)
    with po_c1:
        po_emp = st.text_input(t["employee"], key="po_emp")
        po_name = st.text_input(t["customer_name"], key="po_name")
        po_phone = st.text_input(t["phone"], key="po_phone")
    with po_c2:
        po_item = st.text_input("Beställd Produkt / Del", key="po_item")
        po_deposit = st.number_input("Handpenning (SEK)", min_value=0.0, step=100.0, key="po_deposit")
        po_est_date = st.date_input("Beräknat ankomstdatum", value=date.today() + timedelta(days=3), key="po_est_date")

    if st.button("Registrera Förbeställning", type="primary", key="btn_save_po"):
        if po_name and po_item and po_emp:
            conn = get_db_connection()
            cursor = conn.cursor()
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("INSERT INTO preorders (branch, customer_name, phone, item_details, deposit, estimated_delivery, employee, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", 
                           (global_branch, po_name, po_phone, po_item, po_deposit, po_est_date.strftime('%Y-%m-%d'), po_emp, "Beställd", created_at))
            conn.commit()
            conn.close()
            st.success("✅ Förbeställningen har sparats!")

# --- TAB 9: INVENTORY ---
with tab9:
    st.markdown("### 📦 Lagerhantering")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, part_name, category, stock_qty, min_limit, purchase_cost, selling_price FROM inventory WHERE branch = ?", (global_branch,))
    inv_rows = cursor.fetchall()
    conn.close()

    if inv_rows:
        df_inv = pd.DataFrame(inv_rows, columns=["ID", "Artikel", "Kategori", "Antal", "Min-Gräns", "Inköpspris", "Försäljningspris"])
        st.dataframe(df_inv, use_container_width=True)
    else:
        st.info("ℹ️ Inga artiklar registrerade i lagret ännu.")

    st.markdown("---")
    st.subheader("➕ Registrera Ny Artikel")
    inv_col1, inv_col2 = st.columns(2)
    with inv_col1:
        new_part = st.text_input("Artikelnamn", key="inv_new_part")
        new_cat = st.selectbox("Kategori", ["Skärmar", "Batterier", "Laddkontakter", "Tillbehör"], key="inv_new_cat")
        new_qty = st.number_input("Antal i lager", min_value=1, step=1, key="inv_new_qty")
    with inv_col2:
        new_cost = st.number_input("Inköpspris exkl. moms", min_value=0.0, step=10.0, key="inv_new_cost")
        new_sell = st.number_input("Försäljningspris inkl. moms", min_value=0.0, step=50.0, key="inv_new_sell")
        new_min = st.number_input("Minsta larmgräns", min_value=1, value=2, key="inv_new_min")

    if st.button("Spara Artikel i Lagret", key="btn_add_inv"):
        if new_part:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO inventory (part_name, category, stock_qty, min_limit, purchase_cost, selling_price, branch) VALUES (?, ?, ?, ?, ?, ?, ?)", 
                           (new_part, new_cat, new_qty, new_min, new_cost, new_sell, global_branch))
            conn.commit()
            conn.close()
            st.success("✅ Artikeln har lagts till!")
            st.rerun()

# --- TAB 10: UNIFIED SEARCH & ALL CUSTOMER FILES ARCHIVE ---
with tab10:
    st.markdown("<div class='search-box'>", unsafe_allow_html=True)
    st.header(f"🔍 البحث والأرشيف الشامل لكافة ملفات الزبائن ({global_branch})")
    st.markdown("استعرض وابحث في جميع سجلات الزبائن عبر الأقسام (Repair, Quote, Invoice, Subscription, Buyback, Preorder) مع إمكانية المعاينة والطباعة الفورية.")

    s_col1, s_col2 = st.columns([3, 1])
    with s_col1:
        search_query = st.text_input("🔎 كلمة البحث (Search Query):", placeholder="ابحث باسم الزبون، رقم الهاتف، IMEI، أو رقم الفاتورة...", key="global_search_q")
    with s_col2:
        filter_module = st.selectbox("📁 القسم / Module:", [
            "الكل (All Modules)", 
            "🛠️ الإصلاحات (Repairs)", 
            "💡 عروض الأسعار (Quotes)", 
            "📄 الفواتير (Invoices)", 
            "💳 الاشتراكات (Subscriptions)", 
            "📱 شراء المستعمل (Buyback)", 
            "🛒 الطلبات المسبقة (Preorders)"
        ], key="filter_mod_sel")

    q_wild = f"%{search_query.strip()}%" if search_query else "%"

    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Repairs Section
    if filter_module in ["الكل (All Modules)", "🛠️ الإصلاحات (Repairs)"]:
        st.subheader("🛠️ سجلات الإصلاحات (Repairs Archive)")
        cursor.execute("""
            SELECT id, customer_name, phone, device, imei, issue, price, status, warranty_period, employee, created_at, signature_b64
            FROM repairs 
            WHERE branch = ? AND (customer_name LIKE ? OR phone LIKE ? OR device LIKE ? OR imei LIKE ? OR id LIKE ?)
            ORDER BY id DESC
        """, (global_branch, q_wild, q_wild, q_wild, q_wild, q_wild))
        rep_data = cursor.fetchall()

        if rep_data:
            for r in rep_data:
                r_dict = dict(r)
                with st.expander(f"🛠️ إصلاح #{r_dict['id']} | العميل: {r_dict['customer_name']} | الجهاز: {r_dict['device']} | {r_dict['created_at']}"):
                    st.write(f"**الهاتف:** {r_dict['phone']} | **IMEI:** {r_dict['imei']} | **الحالة:** {r_dict['status']}")
                    st.write(f"**العطل:** {r_dict['issue']} | **السعر:** {r_dict['price']} SEK | **الموظف:** {r_dict['employee']}")
                    
                    wa_msg = f"Hej {r_dict['customer_name']}! Angående din reparation #{r_dict['id']} ({r_dict['device']}) hos {comp['name']}. Status: {r_dict['status']}."
                    st.markdown(f'<a href="{get_whatsapp_link(r_dict["phone"], wa_msg)}" target="_blank" class="whatsapp-btn" style="width: auto; padding: 4px 10px; font-size: 12px;">💬 واتساب</a>', unsafe_allow_html=True)
                    
                    if st.button(f"🖨️ طباعة إيصال الإصلاح #{r_dict['id']}", key=f"btn_print_rep_{r_dict['id']}"):
                        rec_pdf_data = {
                            "branch": global_branch, "repair_id": str(r_dict['id']), "customer_name": r_dict['customer_name'],
                            "phone": r_dict['phone'], "device": r_dict['device'], "imei": r_dict['imei'], "issue": r_dict['issue'],
                            "price": r_dict['price'], "warranty_period": r_dict['warranty_period'], "employee": r_dict['employee'],
                            "signature_b64": r_dict['signature_b64'], "created_at": r_dict['created_at']
                        }
                        st.session_state[f'search_pdf_{r_dict["id"]}'] = generate_pdf_from_record("repair_receipt_dual", rec_pdf_data, COMPANY_INFO)

                    if f'search_pdf_{r_dict["id"]}' in st.session_state:
                        display_pdf_preview(st.session_state[f'search_pdf_{r_dict["id"]}'], file_name=f"Repair_{r_dict['id']}.pdf", key_suffix=f"rep_{r_dict['id']}")
        else:
            st.info("لا توجد سجلات إصلاح مطابقة.")

    # 2. Quotes Section
    if filter_module in ["الكل (All Modules)", "💡 عروض الأسعار (Quotes)"]:
        st.subheader("💡 عروض الأسعار (Quotes Archive)")
        cursor.execute("""
            SELECT id, customer_name, phone, device, issues, total, profit, valid_until, employee, created_at 
            FROM quotes 
            WHERE branch = ? AND (customer_name LIKE ? OR phone LIKE ? OR device LIKE ?)
            ORDER BY id DESC
        """, (global_branch, q_wild, q_wild, q_wild))
        quote_data = cursor.fetchall()

        if quote_data:
            for q in quote_data:
                q_dict = dict(q)
                with st.expander(f"💡 عرض سعر #{q_dict['id']} | العميل: {q_dict['customer_name']} | الجهاز: {q_dict['device']} | الإجمالي: {q_dict['total']} SEK"):
                    st.write(f"**التفاصيل:** {q_dict['issues']} | **صالح لغاية:** {q_dict['valid_until']} | **الموظف:** {q_dict['employee']}")
                    if st.button(f"🖨️ طباعة عرض السعر #{q_dict['id']}", key=f"btn_print_q_{q_dict['id']}"):
                        rec_pdf_data = {
                            "branch": global_branch, "customer_name": q_dict['customer_name'], "phone": q_dict['phone'],
                            "device": q_dict['device'], "issues": q_dict['issues'], "total": q_dict['total'],
                            "currency": "SEK", "valid_until": q_dict['valid_until'], "employee": q_dict['employee'],
                            "created_at": q_dict['created_at']
                        }
                        st.session_state[f'search_q_pdf_{q_dict["id"]}'] = generate_pdf_from_record("quote", rec_pdf_data, COMPANY_INFO)

                    if f'search_q_pdf_{q_dict["id"]}' in st.session_state:
                        display_pdf_preview(st.session_state[f'search_q_pdf_{q_dict["id"]}'], file_name=f"Quote_{q_dict['id']}.pdf", key_suffix=f"q_{q_dict['id']}")
        else:
            st.info("لا توجد عروض أسعار مطابقة.")

    # 3. Invoices Section
    if filter_module in ["الكل (All Modules)", "📄 الفواتير (Invoices)"]:
        st.subheader("📄 الفواتير المعتمدة (Invoices Archive)")
        cursor.execute("""
            SELECT id, invoice_no, customer_name, org_no_cust, phone, address, ref_no, item_desc, amount, moms, payment_terms, due_date, employee, created_at 
            FROM invoices 
            WHERE branch = ? AND (customer_name LIKE ? OR phone LIKE ? OR invoice_no LIKE ? OR org_no_cust LIKE ?)
            ORDER BY id DESC
        """, (global_branch, q_wild, q_wild, q_wild, q_wild))
        inv_data = cursor.fetchall()

        if inv_data:
            for inv in inv_data:
                inv_dict = dict(inv)
                with st.expander(f"📄 فاتورة رقم: {inv_dict['invoice_no']} | العميل: {inv_dict['customer_name']} | المبلغ: {inv_dict['amount']} SEK"):
                    st.write(f"**الرقم الضريبي:** {inv_dict['org_no_cust']} | **تاريخ الاستحقاق:** {inv_dict['due_date']} | **الموظف:** {inv_dict['employee']}")
                    if st.button(f"🖨️ طباعة الفاتورة #{inv_dict['invoice_no']}", key=f"btn_print_inv_{inv_dict['id']}"):
                        rec_pdf_data = {
                            "branch": global_branch, "invoice_no": inv_dict['invoice_no'], "customer_name": inv_dict['customer_name'],
                            "org_no_cust": inv_dict['org_no_cust'], "address": inv_dict['address'], "phone": inv_dict['phone'],
                            "ref_no": inv_dict['ref_no'], "item_desc": inv_dict['item_desc'], "amount": inv_dict['amount'],
                            "moms": inv_dict['moms'], "currency": "SEK", "moms_rate": "25%", "payment_terms": inv_dict['payment_terms'],
                            "employee": inv_dict['employee'], "created_at": inv_dict['created_at'], "due_date": inv_dict['due_date']
                        }
                        st.session_state[f'search_inv_pdf_{inv_dict["id"]}'] = generate_pdf_from_record("invoice", rec_pdf_data, COMPANY_INFO)

                    if f'search_inv_pdf_{inv_dict["id"]}' in st.session_state:
                        display_pdf_preview(st.session_state[f'search_inv_pdf_{inv_dict["id"]}'], file_name=f"Invoice_{inv_dict['invoice_no']}.pdf", key_suffix=f"inv_{inv_dict['id']}")
        else:
            st.info("لا توجد فواتير مطابقة.")

    # 4. Buybacks Section
    if filter_module in ["الكل (All Modules)", "📱 شراء المستعمل (Buyback)"]:
        st.subheader("📱 سجلات شراء الأجهزة المستعملة (Buyback Archive)")
        cursor.execute("""
            SELECT id, customer_name, phone, person_nummer, id_verified, device, imei, purchase_price, condition_grade, employee, signature_b64, created_at 
            FROM buybacks 
            WHERE branch = ? AND (customer_name LIKE ? OR phone LIKE ? OR person_nummer LIKE ? OR imei LIKE ?)
            ORDER BY id DESC
        """, (global_branch, q_wild, q_wild, q_wild, q_wild))
        bb_data = cursor.fetchall()

        if bb_data:
            for bb in bb_data:
                bb_dict = dict(bb)
                with st.expander(f"📱 شراء مستعمل #{bb_dict['id']} | البائع: {bb_dict['customer_name']} | الجهاز: {bb_dict['device']} | المبلغ: {bb_dict['purchase_price']} SEK"):
                    st.write(f"**Personnummer:** {bb_dict['person_nummer']} | **IMEI:** {bb_dict['imei']} | **ID التحقق:** {'نعم' if bb_dict['id_verified'] else 'لا'}")
                    if st.button(f"🖨️ طباعة عقد شراء مستعمل #{bb_dict['id']}", key=f"btn_print_bb_{bb_dict['id']}"):
                        rec_pdf_data = {
                            "branch": global_branch, "buyback_id": str(bb_dict['id']), "customer_name": bb_dict['customer_name'],
                            "person_nummer": bb_dict['person_nummer'], "phone": bb_dict['phone'], "id_verified": bb_dict['id_verified'],
                            "device": bb_dict['device'], "imei": bb_dict['imei'], "condition_grade": bb_dict['condition_grade'],
                            "purchase_price": bb_dict['purchase_price'], "employee": bb_dict['employee'],
                            "signature_b64": bb_dict['signature_b64'], "created_at": bb_dict['created_at']
                        }
                        st.session_state[f'search_bb_pdf_{bb_dict["id"]}'] = generate_pdf_from_record("buyback_receipt", rec_pdf_data, COMPANY_INFO)

                    if f'search_bb_pdf_{bb_dict["id"]}' in st.session_state:
                        display_pdf_preview(st.session_state[f'search_bb_pdf_{bb_dict["id"]}'], file_name=f"Buyback_{bb_dict['id']}.pdf", key_suffix=f"bb_{bb_dict['id']}")
        else:
            st.info("لا توجد سجلات شراء أجهزة مستعملة مطابقة.")

    # 5. Subscriptions Section
    if filter_module in ["الكل (All Modules)", "💳 الاشتراكات (Subscriptions)"]:
        st.subheader("💳 اشتراكات الضمان والخدمات (Subscriptions Archive)")
        cursor.execute("""
            SELECT id, customer_name, phone, device, imei, plan_type, price, employee, start_date, end_date 
            FROM subscriptions 
            WHERE branch = ? AND (customer_name LIKE ? OR phone LIKE ? OR device LIKE ?)
            ORDER BY id DESC
        """, (global_branch, q_wild, q_wild, q_wild))
        sub_data = cursor.fetchall()
        if sub_data:
            df_sub = pd.DataFrame(sub_data, columns=["ID", "العميل", "الهاتف", "الجهاز", "IMEI", "نوع الاشتراك", "السعر", "الموظف", "تاريخ البدء", "تاريخ الانتهاء"])
            st.dataframe(df_sub, use_container_width=True)
        else:
            st.info("لا توجد اشتراكات مطابقة.")

    # 6. Preorders Section
    if filter_module in ["الكل (All Modules)", "🛒 الطلبات المسبقة (Preorders)"]:
        st.subheader("🛒 سجلات الطلبات المسبقة (Pre-orders Archive)")
        cursor.execute("""
            SELECT id, customer_name, phone, item_details, deposit, estimated_delivery, employee, status, created_at 
            FROM preorders 
            WHERE branch = ? AND (customer_name LIKE ? OR phone LIKE ? OR item_details LIKE ?)
            ORDER BY id DESC
        """, (global_branch, q_wild, q_wild, q_wild))
        po_data = cursor.fetchall()
        if po_data:
            df_po = pd.DataFrame(po_data, columns=["ID", "العميل", "الهاتف", "المنتج المطلوب", "العربون", "التاريخ المتوقع", "الموظف", "الحالة", "تاريخ الطلب"])
            st.dataframe(df_po, use_container_width=True)
        else:
            st.info("لا توجد طلبات مسبقة مطابقة.")

    conn.close()
    st.markdown("</div>", unsafe_allow_html=True)
