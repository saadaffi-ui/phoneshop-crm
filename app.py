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

# --- Custom CSS Styling for Mobile Experience & Eye Comfort ---
st.markdown("""
<style>
    .stApp {
        background-color: #f7f9fa;
        color: #2c3e50;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    section[data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e1e8ed;
    }
    h1, h2, h3 {
        color: #1a252f;
        font-weight: 700;
    }
    div.stButton > button {
        border-radius: 8px;
        font-weight: 600;
        padding: 0.6rem 1.2rem;
        width: 100%;
        transition: all 0.3s ease;
    }
    div.stAlert {
        border-radius: 8px;
        border: none;
    }
    /* Mobile optimization for tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 5px;
        overflow-x: auto;
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

st.sidebar.title("📱 30 Minutes Phone Fix")
if os.path.exists("logo.png"):
    st.sidebar.image("logo.png", use_container_width=True)

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
    remember_device = st.sidebar.checkbox("💾 تذكرني على هذا الجهاز")
    
    if sidebar_pin == default_pin:
        st.session_state['authenticated'] = True
        if remember_device:
            st.session_state['remember_me'] = True
        st.sidebar.success("✅ System Unlocked")
        st.rerun()
    elif sidebar_pin:
        st.sidebar.error("❌ Fel PIN-kod")

if not st.session_state.get('authenticated') and st.session_state.get('remember_me'):
    st.session_state['authenticated'] = True

if not st.session_state['authenticated']:
    st.title("🔒 30 Minutes Phone Fix CRM - Locked")
    st.info("Please enter the system PIN in the sidebar to log in.")
    st.stop()

st.sidebar.success("✅ Logged In")
if st.sidebar.button("🔒 Log Out / تسجيل خروج"):
    st.session_state['authenticated'] = False
    st.session_state['remember_me'] = False
    st.rerun()

def display_pdf_preview(pdf_buffer, file_name="document.pdf"):
    pdf_buffer.seek(0)
    pdf_bytes = pdf_buffer.read()
    b64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
    
    st.success("✅ Dokumentet är redo!")
    st.download_button(
        label="📥 Ladda ner PDF / تحميل",
        data=pdf_bytes,
        file_name=file_name,
        mime="application/pdf",
        type="primary"
    )
    st.markdown("---")
    st.markdown("### 👁️ معاينة المستند / Preview")
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

    if record_type == "quote":
        p.setFont("Helvetica-Bold", 12)
        p.drawString(50, height - 110, "KOSTNADSFÖRSLAG / PRICE QUOTATION")
        p.setFont("Helvetica", 10)
        p.drawString(50, height - 135, f"Datum: {data.get('created_at', '')}")
        p.drawString(300, height - 135, f"Handläggare: {employee_name}")
        p.drawString(50, height - 155, f"Kund: {data.get('customer_name', '')}")
        p.drawString(50, height - 175, f"Telefon: {data.get('phone', '')}")
        p.drawString(300, height - 155, f"Enhet: {data.get('device', '')}")
        
        p.setFillColorRGB(0.9, 0.9, 0.9)
        p.rect(50, height - 215, width - 100, 20, fill=1, stroke=0)
        p.setFillColorRGB(0, 0, 0)
        p.setFont("Helvetica-Bold", 9)
        p.drawString(60, height - 208, "Beskrivning av reparation")
        p.drawString(400, height - 208, f"Belopp ({currency})")
        
        p.setFont("Helvetica", 10)
        y_pos = height - 245
        p.drawString(60, y_pos, f"- {data.get('issues', '')}")
        total_val = data.get('total', 0)
        p.drawString(400, y_pos, f"{total_val:.2f} {currency}")
        
        p.line(50, height - 320, width - 50, height - 320)
        p.setFont("Helvetica-Bold", 11)
        p.drawString(300, height - 345, f"Att betala / Total: {total_val:.2f} {currency}")
        p.setFont("Helvetica", 8)
        p.drawString(300, height - 360, "(Inkl. moms)")
        
        p.setFont("Helvetica-Oblique", 8)
        p.drawString(50, height - 420, "* Detta kostnadsförslag är giltigt i 30 dagar.")
        p.drawString(50, 40, f"Swish: {comp['swish']} | Bankgiro: {comp['bankgiro']}")

    elif record_type == "invoice":
        p.setFont("Helvetica-Bold", 12)
        p.drawString(50, height - 110, "FAKTURA / INVOICE")
        p.setFont("Helvetica", 10)
        p.drawString(50, height - 135, f"Fakturanr: {data.get('invoice_no', '')}")
        p.drawString(300, height - 135, f"Datum: {data.get('created_at', '')}")
        p.drawString(50, height - 155, f"Kund: {data.get('customer_name', '')}")
        p.drawString(300, height - 155, f"Handläggare: {employee_name}")
        p.drawString(50, height - 175, f"Telefon: {data.get('phone', '')}")
        
        p.setFillColorRGB(0.9, 0.9, 0.9)
        p.rect(50, height - 215, width - 100, 20, fill=1, stroke=0)
        p.setFillColorRGB(0, 0, 0)
        p.setFont("Helvetica-Bold", 9)
        p.drawString(60, height - 208, "Beskrivning")
        p.drawString(400, height - 208, f"Belopp ({currency})")
        
        y_pos = height - 245
        amount_val = data.get('amount', 0)
        moms_val = data.get('moms', 0)
        netto_val = amount_val - moms_val
        
        p.setFont("Helvetica", 10)
        p.drawString(60, y_pos, f"{data.get('item_desc', 'Reparation')}")
        p.drawString(400, y_pos, f"{netto_val:.2f} {currency}")
        
        p.line(50, height - 320, width - 50, height - 320)
        p.setFont("Helvetica", 9)
        p.drawString(300, height - 340, f"Netto: {netto_val:.2f} {currency}")
        p.drawString(300, height - 360, f"Moms ({moms_rate_str}): {moms_val:.2f} {currency}")
        p.setFont("Helvetica-Bold", 11)
        p.drawString(300, height - 385, f"Att betala: {amount_val:.2f} {currency}")
        
        p.setFont("Helvetica", 9)
        p.drawString(50, 60, f"Swish: {comp['swish']} | Bankgiro: {comp['bankgiro']}")
        p.drawString(50, 40, f"Org.nr: {comp['org_nr']}")

    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

# --- MAIN APP WITH MOBILE-FRIENDLY TABS (NO BACK-BUTTON NEEDED) ---
st.title("📱 30 Minutes Phone Fix - CRM")

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 لوحة التحكم", 
    "🛠️ إصلاح جديد", 
    "💡 عرض سعر", 
    "📄 فاتورة", 
    "📦 المخزون", 
    "🔍 البحث والأرشيف"
])

# --- TAB 1: DASHBOARD ---
with tab1:
    st.header("📊 لوحة المؤشرات والإحصاءات العامة")
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

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📝 الإصلاحات", rep_count)
    c2.metric("💡 الأسعار", quote_count)
    c3.metric("📄 الفواتير", inv_count)
    c4.metric("📈 الأرباح", f"{total_prof:.2f} Kr")

    st.markdown("---")
    st.subheader("⚡ تحديث حالة الأجهزة السريعة")
    try:
        if db_type == "turso":
            active_repairs = conn.execute("SELECT id, customer_name, device, status, employee FROM repairs ORDER BY id DESC LIMIT 5").fetchall()
        else:
            cursor = conn.cursor()
            cursor.execute("SELECT id, customer_name, device, status, employee FROM repairs ORDER BY id DESC LIMIT 5")
            active_repairs = cursor.fetchall()
            
        if active_repairs:
            for rep in active_repairs:
                r_id, r_cust, r_dev, r_status, r_emp = rep
                st.markdown(f"**ID: {r_id}** | 👤 {r_cust} ({r_dev}) [الموظف: {r_emp or '-'}]")
                new_st = st.selectbox(f"الحالة #{r_id}", ["Under behandling / In Progress", "Väntar på reservdel / Waiting Part", "Klar att hämta / Ready", "Avslutad / Completed"], key=f"st_{r_id}")
                if st.button("حفظ التحديث", key=f"btn_st_{r_id}"):
                    if db_type == "turso":
                        conn.execute("UPDATE repairs SET status = ? WHERE id = ?", (new_st, r_id))
                    else:
                        cursor = conn.cursor()
                        cursor.execute("UPDATE repairs SET status = ? WHERE id = ?", (new_st, r_id))
                        conn.commit()
                    st.success(f"تم تحديث الأذن #{r_id}!")
                    st.rerun()
                st.markdown("---")
        else:
            st.info("لا توجد إصلاحات مسجلة حالياً.")
    except Exception as e:
        st.error(f"خطأ: {e}")

# --- TAB 2: NEW REPAIR ---
with tab2:
    st.header("🛠️ تسجيل إصلاح جديد")
    branch = st.selectbox("اختر الفرع", ["Eskilstuna", "Västerås"], key="rep_branch")
    employee_name = st.text_input("اسم الموظف المسؤول (Employee)", key="rep_emp")
    c_phone = st.text_input("رقم الهاتف", key="rep_phone")
    
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
                st.info(f"💡 تم العثور على عميل سابق: **{auto_name}**")
        except Exception:
            pass

    c_name = st.text_input("اسم العميل", value=auto_name, key="rep_name")
    c_email = st.text_input("البريد الإلكتروني (اختياري)", value=auto_email, key="rep_email")
    device = st.text_input("نوع وطراز الجهاز", key="rep_device")
    imei = st.text_input("رقم الـ IMEI أو الرقم التسلسلي", key="rep_imei")
    
    st.markdown("⚡ **اختر الأعطال السريعة:**")
    selected_issues = []
    if st.checkbox("📱 تغيير شاشة أصلي", key="i_scr"): selected_issues.append("Skärmbyte / Screen")
    if st.checkbox("🔋 استبدال بطارية", key="i_bat"): selected_issues.append("Batteribyte / Battery")
    if st.checkbox("🔌 منفذ الشحن", key="i_chg"): selected_issues.append("Laddport / Charging Port")
    if st.checkbox("💧 أضرار السوائل والمياه", key="i_wat"): selected_issues.append("Vattenskada / Water Damage")
    
    combined_template_str = ", ".join(selected_issues)
    price = st.number_input("السعر الإجمالي (SEK)", min_value=0.0, step=50.0, key="rep_price")
    issue = st.text_area("وصف العطل التفصيلي", value=combined_template_str, key="rep_issue_desc")
    
    if st.button("حفظ طلب الإصلاح", type="primary", key="btn_save_rep"):
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
                st.success("✅ تم حفظ الإصلاح بنجاح!")
            except Exception as e:
                st.error(f"❌ خطأ: {e}")
        else:
            st.warning("⚠️ يرجى تعبئة الحقول الأساسية بما فيها اسم الموظف.")

# --- TAB 3: QUOTE / PRICE QUOTATION ---
with tab3:
    st.header("💡 عرض سعر وحساب الأرباح")
    q_branch = st.selectbox("اختر الفرع", ["Eskilstuna", "Västerås"], key="q_branch")
    comp = COMPANY_INFO[q_branch]
    
    q_emp = st.text_input("اسم الموظف المسؤول", key="q_emp")
    q_name = st.text_input("اسم العميل", key="q_name")
    q_phone = st.text_input("رقم الهاتف", key="q_phone")
    q_device = st.text_input("نوع الجهاز", key="q_device")

    st.markdown("---")
    st.subheader("🛠️ اختر قطع الغيار والإصلاحات")
    
    issues_list = []
    total_price = 0.0
    total_cost = 0.0

    if st.checkbox("📱 تغيير شاشة", key="q_chk_scr"):
        p_s = st.number_input("سعر شاشة للعميل", min_value=0.0, step=50.0, key="qp_s")
        c_s = st.number_input("تكلفة الشاشة علينا", min_value=0.0, step=10.0, key="qc_s")
        issues_list.append(f"Skärmbyte: {p_s}")
        total_price += p_s; total_cost += c_s

    if st.checkbox("🔋 استبدال بطارية", key="q_chk_bat"):
        p_b = st.number_input("سعر البطارية للعميل", min_value=0.0, step=50.0, key="qp_b")
        c_b = st.number_input("تكلفة البطارية علينا", min_value=0.0, step=10.0, key="qc_b")
        issues_list.append(f"Batteribyte: {p_b}")
        total_price += p_b; total_cost += c_b

    net_profit = total_price - total_cost
    st.markdown(f"### 💰 الإجمالي: **{total_price:.2f} SEK** | 📈 الربح: **{net_profit:.2f} SEK**")

    if st.button("حفظ وتوليد عرض سعر PDF", type="primary", key="btn_save_q"):
        if q_name and q_device and issues_list and q_emp:
            conn, db_type = get_db_connection()
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            issues_str = ", ".join(issues_list)
            try:
                if db_type == "turso":
                    try:
                        conn.execute(
                            "INSERT INTO quotes (branch, customer_name, phone, email, device, issues, total, profit, employee, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (q_branch, q_name, q_phone, "", q_device, issues_str, total_price, net_profit, q_emp, created_at)
                        )
                    except Exception:
                        local_conn = sqlite3.connect("local_crm.db", check_same_thread=False)
                        local_cursor = local_conn.cursor()
                        local_cursor.execute(
                            "INSERT INTO quotes (branch, customer_name, phone, email, device, issues, total, profit, employee, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (q_branch, q_name, q_phone, "", q_device, issues_str, total_price, net_profit, q_emp, created_at)
                        )
                        local_conn.commit()
                        local_conn.close()
                else:
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO quotes (branch, customer_name, phone, email, device, issues, total, profit, employee, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (q_branch, q_name, q_phone, "", q_device, issues_str, total_price, net_profit, q_emp, created_at)
                    )
                    conn.commit()
                    conn.close()
                st.success("✅ تم حفظ عرض السعر!")
            except Exception as e:
                st.error(f"❌ خطأ: {e}")

            record_data = {
                "branch": q_branch,
                "customer_name": q_name,
                "phone": q_phone,
                "device": q_device,
                "issues": issues_str,
                "total": total_price,
                "currency": "SEK",
                "employee": q_emp,
                "created_at": date.today().strftime('%Y-%m-%d')
            }
            pdf_buf = generate_pdf_from_record("quote", record_data, COMPANY_INFO)
            st.session_state['q_pdf'] = pdf_buf
            safe_dev = q_device.replace(' ', '_')
            safe_cust = q_name.replace(' ', '_')
            st.session_state['q_pdf_name'] = f"Kostnadsforslag_{safe_dev}_-_{safe_cust}.pdf"
            st.success("✅ تم تجهيز ملف PDF!")

    if 'q_pdf' in st.session_state:
        st.markdown("---")
        display_pdf_preview(st.session_state['q_pdf'], file_name=st.session_state.get('q_pdf_name', 'quote.pdf'))

# --- TAB 4: INVOICE ---
with tab4:
    st.header("📄 الفاتورة الرسمية")
    inv_branch = st.selectbox("اختر الفرع", ["Eskilstuna", "Västerås"], key="inv_branch")
    comp = COMPANY_INFO[inv_branch]
    
    inv_curr = st.selectbox("العملة", ["SEK", "EUR"], key="inv_curr")
    inv_moms = st.selectbox("نسبة الضريبة (Moms)", ["25%", "12%", "6%", "0%"], key="inv_moms_sel")
    inv_emp = st.text_input("اسم الموظف المسؤول", key="inv_emp")
    inv_no = st.text_input("رقم الفاتورة", value="FAK-2026-001", key="inv_no_in")

    inv_name = st.text_input("اسم العميل / الشركة", key="inv_name")
    inv_phone = st.text_input("رقم الهاتف", key="inv_phone")
    inv_date = st.date_input("تاريخ الفاتورة", value=date.today(), key="inv_date")

    item_desc = st.text_input("وصف البند أو الخدمة", value="Reparation och reservdelar", key="inv_desc")
    item_qty = st.number_input("الكمية", min_value=1, value=1, key="inv_qty")
    item_price = st.number_input("السعر الإجمالي inkl. moms", min_value=0.0, step=50.0, key="inv_price")
    
    total_amount = item_qty * item_price
    moms_div = 1.25 if "25%" in inv_moms else (1.12 if "12%" in inv_moms else (1.06 if "6%" in inv_moms else 1.0))
    netto = total_amount / moms_div if moms_div > 1 else total_amount
    moms = total_amount - netto

    st.markdown(f"**المبلغ الإجمالي Att betala:** **{total_amount:.2f} {inv_curr}**")

    if st.button("حفظ وتوليد فاتورة PDF", type="primary", key="btn_save_inv"):
        if inv_name and inv_emp:
            conn, db_type = get_db_connection()
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            try:
                if db_type == "turso":
                    try:
                        conn.execute(
                            "INSERT INTO invoices (branch, customer_name, phone, invoice_no, amount, moms, currency, moms_rate, employee, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (inv_branch, inv_name, inv_phone, inv_no, total_amount, moms, inv_curr, inv_moms, inv_emp, created_at)
                        )
                    except Exception:
                        local_conn = sqlite3.connect("local_crm.db", check_same_thread=False)
                        local_cursor = local_conn.cursor()
                        local_cursor.execute(
                            "INSERT INTO invoices (branch, customer_name, phone, invoice_no, amount, moms, currency, moms_rate, employee, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (inv_branch, inv_name, inv_phone, inv_no, total_amount, moms, inv_curr, inv_moms, inv_emp, created_at)
                        )
                        local_conn.commit()
                        local_conn.close()
                else:
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO invoices (branch, customer_name, phone, invoice_no, amount, moms, currency, moms_rate, employee, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (inv_branch, inv_name, inv_phone, inv_no, total_amount, moms, inv_curr, inv_moms, inv_emp, created_at)
                    )
                    conn.commit()
                    conn.close()
                st.success("✅ تم حفظ الفاتورة!")
            except Exception as e:
                st.error(f"❌ خطأ: {e}")

            record_data = {
                "branch": inv_branch,
                "customer_name": inv_name,
                "phone": inv_phone,
                "invoice_no": inv_no,
                "amount": total_amount,
                "moms": moms,
                "currency": inv_curr,
                "moms_rate": inv_moms,
                "item_desc": item_desc,
                "employee": inv_emp,
                "created_at": inv_date.strftime('%Y-%m-%d')
            }
            pdf_buf = generate_pdf_from_record("invoice", record_data, COMPANY_INFO)
            st.session_state['inv_pdf'] = pdf_buf
            safe_cust = inv_name.replace(' ', '_')
            st.session_state['inv_pdf_name'] = f"Faktura_{inv_no}_-_{safe_cust}.pdf"
            st.success("✅ تم تجهيز فاتورة PDF!")

    if 'inv_pdf' in st.session_state:
        st.markdown("---")
        display_pdf_preview(st.session_state['inv_pdf'], file_name=st.session_state.get('inv_pdf_name', 'invoice.pdf'))

# --- TAB 5: INVENTORY ---
with tab5:
    st.header("📦 إدارة المخزون وقطع الغيار")
    inv_b = st.selectbox("اختر الفرع", ["Eskilstuna", "Västerås"], key="stock_branch")
    conn, db_type = get_db_connection()
    
    st.subheader("➕ إضافة قطعة جديدة للمخزون")
    part_name = st.text_input("اسم القطعة (مثل: iPhone 15 Screen)")
    part_qty = st.number_input("العدد المتوفر", min_value=0, step=1, value=5)
    part_min = st.number_input("حد الإنذار الأدنى", min_value=0, step=1, value=2)
    
    if st.button("حفظ في المخزون", type="primary", key="btn_add_stock"):
        if part_name:
            try:
                if db_type == "turso":
                    try:
                        conn.execute("INSERT INTO inventory (part_name, stock_qty, min_limit, branch) VALUES (?, ?, ?, ?)", (part_name, part_qty, part_min, inv_b))
                    except Exception:
                        local_conn = sqlite3.connect("local_crm.db", check_same_thread=False)
                        local_cursor = local_conn.cursor()
                        local_cursor.execute("INSERT INTO inventory (part_name, stock_qty, min_limit, branch) VALUES (?, ?, ?, ?)", (part_name, part_qty, part_min, inv_b))
                        local_conn.commit()
                        local_conn.close()
                else:
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO inventory (part_name, stock_qty, min_limit, branch) VALUES (?, ?, ?, ?)", (part_name, part_qty, part_min, inv_b))
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
            rows = conn.execute("SELECT id, part_name, stock_qty, min_limit FROM inventory WHERE branch = ? ORDER BY id DESC", (inv_b,)).fetchall()
            df_inv = pd.DataFrame(rows, columns=["ID", "القطعة", "العدد", "الحد الأدنى"]) if rows else pd.DataFrame()
        else:
            local_conn = sqlite3.connect("local_crm.db", check_same_thread=False)
            df_inv = pd.read_sql_query("SELECT id, part_name, stock_qty, min_limit FROM inventory WHERE branch = ? ORDER BY id DESC", local_conn, params=(inv_b,))
            local_conn.close()
        if not df_inv.empty:
            st.dataframe(df_inv, use_container_width=True)
        else:
            st.info("لا توجد قطع مسجلة حالياً.")
    except Exception:
        pass

# --- TAB 6: SEARCH & ARCHIVE ---
with tab6:
    st.header("🔍 البحث والأرشيف وإدارة البيانات")
    search_cat = st.selectbox("اختر القسم", ["📝 الإصلاحات", "💡 عروض الأسعار", "📄 الفواتير", "📦 المخزون"])
    search_term = st.text_input("🔎 بحث بالاسم أو الهاتف أو الـ IMEI", "").lower()
    
    table_map = {
        "📝 الإصلاحات": "repairs",
        "💡 عروض الأسعار": "quotes",
        "📄 الفواتير": "invoices",
        "📦 المخزون": "inventory"
    }
    cur_tbl = table_map[search_cat]
    
    try:
        if db_type == "turso":
            res = conn.execute(f"SELECT * FROM {cur_tbl} ORDER BY id DESC")
            rows = res.fetchall()
            cols = [c[1] for c in conn.execute(f"PRAGMA table_info({cur_tbl})").fetchall()]
            df_search = pd.DataFrame(rows, columns=cols) if rows else pd.DataFrame()
        else:
            local_conn = sqlite3.connect("local_crm.db", check_same_thread=False)
            df_search = pd.read_sql_query(f"SELECT * FROM {cur_tbl} ORDER BY id DESC", local_conn)
            local_conn.close()
    except Exception:
        df_search = pd.DataFrame()
        
    if not df_search.empty:
        if search_term:
            mask = df_search.astype(str).apply(lambda x: x.str.lower().str.contains(search_term)).any(axis=1)
            filtered_df = df_search[mask]
        else:
            filtered_df = df_search
            
        st.dataframe(filtered_df, use_container_width=True)

        st.markdown("---")
        st.subheader("🗑️ حذف بند نهائياً")
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
                    st.success(f"✅ تم حذف البند #{d_id} بنجاح!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ خطأ: {e}")
    else:
        st.info("لا توجد بيانات مطابقة.")
