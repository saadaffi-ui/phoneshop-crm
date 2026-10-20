# -*- coding: utf-8 -*-
import os
import io
import html
import sqlite3
from datetime import datetime
from pathlib import Path
import streamlit as st

# Streamlit Page Config
st.set_page_config(
    page_title="30 Minutes Phone Fix — CRM",
    page_icon="📱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ReportLab for PDF generation
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.units import mm

try:
    from supabase import create_client
except ImportError:
    create_client = None

# App Setup & Environment Settings
COMPANY_NAME = os.getenv("COMPANY_NAME", "30 Minutes Phone Fix")
COMPANY_PHONE = os.getenv("COMPANY_PHONE", "016-51 01 01")
COMPANY_EMAIL = os.getenv("COMPANY_EMAIL", "info@30minutesphonefix.se")
COMPANY_WEB = os.getenv("COMPANY_WEB", "www.30minutesphonefix.se")

# Secrets Support with fallback
try:
    DELETE_PIN = st.secrets.get("DELETE_PIN", os.getenv("DELETE_PIN", "tunapark"))
except Exception:
    DELETE_PIN = os.getenv("DELETE_PIN", "tunapark")

# -----------------------------------------------------------------------------
# CRM Store (Supabase + Local SQLite Backup)
# -----------------------------------------------------------------------------
class CRMStore:
    def __init__(self):
        try:
            self.url = st.secrets.get("SUPABASE_URL", os.getenv("SUPABASE_URL", ""))
            self.key = st.secrets.get("SUPABASE_ANON_KEY", os.getenv("SUPABASE_ANON_KEY", ""))
        except Exception:
            self.url = os.getenv("SUPABASE_URL", "")
            self.key = os.getenv("SUPABASE_ANON_KEY", "")

        self.client = None
        if self.url and self.key and create_client:
            try:
                self.client = create_client(self.url, self.key)
            except Exception:
                pass

        self.local_db_path = Path("local_crm.db")
        self._init_local_db()

    def _init_local_db(self):
        with sqlite3.connect(self.local_db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS customers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    first_name TEXT, last_name TEXT, phone TEXT UNIQUE,
                    email TEXT, subscription_type TEXT, branch TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS service_cases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER, legacy_id TEXT, first_name TEXT, last_name TEXT,
                    phone TEXT, email TEXT, subscription_type TEXT, model TEXT,
                    imei_serial TEXT, issue_description TEXT, start_date TEXT,
                    end_date TEXT, status TEXT, branch TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS pre_orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    first_name TEXT, last_name TEXT, phone TEXT,
                    part_model TEXT, deposit REAL, branch TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def search_cases(self, query="", branch="Alla"):
        q = query.casefold().strip()
        rows = []
        if self.client:
            try:
                query_builder = self.client.table("service_cases").select("*").order("created_at", desc=True).limit(500)
                if branch != "Alla":
                    query_builder = query_builder.eq("branch", branch)
                result = query_builder.execute()
                rows = result.data or []
            except Exception:
                pass
        if not rows:
            with sqlite3.connect(self.local_db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                if branch != "Alla":
                    cursor.execute("SELECT * FROM service_cases WHERE branch = ? ORDER BY id DESC LIMIT 500", (branch,))
                else:
                    cursor.execute("SELECT * FROM service_cases ORDER BY id DESC LIMIT 500")
                rows = [dict(row) for row in cursor.fetchall()]

        if q:
            rows = [r for r in rows if any(q in str(r.get(k) or "").casefold()
                    for k in ("first_name", "last_name", "phone", "id", "email", "model"))]
        return rows

    def search_pre_orders(self, query="", branch="Alla"):
        q = query.casefold().strip()
        rows = []
        if self.client:
            try:
                query_builder = self.client.table("pre_orders").select("*").order("created_at", desc=True).limit(500)
                if branch != "Alla":
                    query_builder = query_builder.eq("branch", branch)
                result = query_builder.execute()
                rows = result.data or []
            except Exception:
                pass
        if not rows:
            with sqlite3.connect(self.local_db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                if branch != "Alla":
                    cursor.execute("SELECT * FROM pre_orders WHERE branch = ? ORDER BY id DESC LIMIT 500", (branch,))
                else:
                    cursor.execute("SELECT * FROM pre_orders ORDER BY id DESC LIMIT 500")
                rows = [dict(row) for row in cursor.fetchall()]

        if q:
            rows = [r for r in rows if any(q in str(r.get(k) or "").casefold()
                    for k in ("first_name", "last_name", "phone", "part_model", "id"))]
        return rows

    def upsert_customer(self, first, last, phone, email, subscription="", branch="Eskilstuna"):
        payload = {
            "first_name": first, "last_name": last, "phone": phone,
            "email": email or None, "subscription_type": subscription or None, "branch": branch
        }
        if self.client:
            try:
                found = self.client.table("customers").select("*").eq("phone", phone).limit(1).execute().data or []
                if found:
                    cid = found[0]["id"]
                    self.client.table("customers").update(payload).eq("id", cid).execute()
                    return cid
                result = self.client.table("customers").insert(payload).execute()
                return result.data[0]["id"]
            except Exception:
                pass

        with sqlite3.connect(self.local_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM customers WHERE phone = ?", (phone,))
            row = cursor.fetchone()
            if row:
                cid = row[0]
                cursor.execute("UPDATE customers SET first_name=?, last_name=?, email=?, subscription_type=?, branch=? WHERE id=?", 
                               (first, last, email or None, subscription or None, branch, cid))
                conn.commit()
                return cid
            else:
                cursor.execute("INSERT INTO customers (first_name, last_name, phone, email, subscription_type, branch) VALUES (?, ?, ?, ?, ?, ?)", 
                               (first, last, phone, email or None, subscription or None, branch))
                conn.commit()
                return cursor.lastrowid

    def create_case(self, data):
        customer_id = self.upsert_customer(
            data["first_name"], data["last_name"], data["phone"],
            data["email"], data["subscription_type"], data["branch"]
        )
        payload = {
            "customer_id": customer_id, "first_name": data["first_name"],
            "last_name": data["last_name"], "phone": data["phone"],
            "email": data["email"] or None, "subscription_type": data["subscription_type"] or None,
            "model": data["model"], "imei_serial": data["imei_serial"] or None,
            "issue_description": data["issue_description"], "start_date": data["start_date"],
            "end_date": None, "status": "Inlämnad", "branch": data["branch"]
        }

        if self.client:
            try:
                result = self.client.table("service_cases").insert(payload).execute()
                return result.data[0]
            except Exception:
                pass

        with sqlite3.connect(self.local_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO service_cases (customer_id, first_name, last_name, phone, email, subscription_type, model, imei_serial, issue_description, start_date, end_date, status, branch)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                customer_id, payload["first_name"], payload["last_name"], payload["phone"],
                payload["email"], payload["subscription_type"], payload["model"], payload["imei_serial"],
                payload["issue_description"], payload["start_date"], payload["end_date"], payload["status"], payload["branch"]
            ))
            conn.commit()
            payload["id"] = cursor.lastrowid
            return payload

    def create_pre_order(self, data):
        payload = {
            "first_name": data["first_name"], "last_name": data["last_name"],
            "phone": data["phone"], "part_model": data["part_model"],
            "deposit": data["deposit"], "branch": data["branch"]
        }
        if self.client:
            try:
                res = self.client.table("pre_orders").insert(payload).execute()
                return res.data[0]
            except Exception:
                pass

        with sqlite3.connect(self.local_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO pre_orders (first_name, last_name, phone, part_model, deposit, branch) VALUES (?, ?, ?, ?, ?, ?)", 
                           (payload["first_name"], payload["last_name"], payload["phone"], payload["part_model"], payload["deposit"], payload["branch"]))
            conn.commit()
            payload["id"] = cursor.lastrowid
            return payload

# -----------------------------------------------------------------------------
# PDF Generation Helper
# -----------------------------------------------------------------------------
def safe_para(value):
    val_str = str(value or "").strip()
    if not val_str:
        return "Ej angivet"
    return html.escape(val_str).replace("\n", "<br/>")

def generate_receipt_pdf_bytes(case):
    buffer = io.BytesIO()
    styles = getSampleStyleSheet()
    title = ParagraphStyle("ReceiptTitle", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=13, leading=16, alignment=TA_CENTER, spaceAfter=5)
    heading = ParagraphStyle("ReceiptHeading", parent=styles["Heading3"], fontSize=9.5, leading=11, spaceBefore=4, spaceAfter=3)
    body = ParagraphStyle("ReceiptBody", parent=styles["Normal"], fontSize=8.5, leading=11, spaceAfter=3)
    terms = ParagraphStyle("ReceiptTerms", parent=body, fontSize=7.2, leading=9, textColor=colors.HexColor("#444444"))
    
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=16*mm, leftMargin=16*mm, topMargin=10*mm, bottomMargin=10*mm)
    story = []
    full_name = f"{case.get('first_name', '')} {case.get('last_name', '')}".strip()
    branch = case.get('branch', 'Eskilstuna')

    for index, copy_title in enumerate(("BUTIKENS KOPIA", "KUNDENS KOPIA")):
        if index:
            story.extend([Spacer(1, 4*mm), HRFlowable(width="100%", thickness=0.8, color=colors.grey, dash=[3, 3]), 
                          Paragraph("KLIPP HAR / SAX LINJE", ParagraphStyle("Cut", parent=body, alignment=TA_CENTER, textColor=colors.grey)), Spacer(1, 3*mm)])
        
        story.append(Paragraph(safe_para(COMPANY_NAME), title))
        company_line = f"Butik: {branch} | Tel: {COMPANY_PHONE} | Webb: {COMPANY_WEB} | {COMPANY_EMAIL}"
        story.append(Paragraph(safe_para(company_line), ParagraphStyle("Company", parent=body, alignment=TA_CENTER)))
        story.append(Paragraph(f"<b>{copy_title} - INLAMNINGSKVITTO & AVTAL</b>", title))
        story.append(Paragraph(f"<b>Arendenummer:</b> {safe_para(case.get('id'))} &nbsp;&nbsp; <b>Datum:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}", body))
        story.append(Paragraph("KUND- OCH ENHETSINFORMATION", heading))
        story.append(Paragraph(f"<b>Kund:</b> {safe_para(full_name)} &nbsp;&nbsp; <b>Mobil:</b> {safe_para(case.get('phone'))}", body))
        story.append(Paragraph(f"<b>E-post:</b> {safe_para(case.get('email'))} &nbsp;&nbsp; <b>Modell:</b> {safe_para(case.get('model'))}", body))
        story.append(Paragraph(f"<b>IMEI / Serienummer:</b> {safe_para(case.get('imei_serial'))}", body))
        story.append(Paragraph(f"<b>Abonnemangstyp:</b> {safe_para(case.get('subscription_type'))} &nbsp;&nbsp; <b>Butik:</b> {safe_para(branch)}", body))
        story.append(Paragraph(f"<b>Felbeskrivning:</b> {safe_para(case.get('issue_description'))}", body))
        story.append(Paragraph("SARSKILDA AVTALSVILLKOR", heading))
        for term in [
            "1. Verkstaden ansvarar for felsokning och reparation enligt den felbeskrivning som anges ovan.",
            "2. Garanti galler endast for de delar och det arbete som uttryckligen omfattas av verkstadens garanti.",
            "3. Kunden bor sakerhetskopiera enheten. Verkstaden kan inte garantera data bevaras vid reparation."
        ]:
            story.append(Paragraph(safe_para(term), terms))
        story.append(Spacer(1, 5*mm))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

def generate_quote_pdf_bytes(quote_data):
    buffer = io.BytesIO()
    styles = getSampleStyleSheet()
    title = ParagraphStyle("QuoteTitle", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=14, leading=17, alignment=TA_CENTER, spaceAfter=6)
    heading = ParagraphStyle("QuoteHeading", parent=styles["Heading3"], fontSize=10, leading=12, spaceBefore=6, spaceAfter=4)
    body = ParagraphStyle("QuoteBody", parent=styles["Normal"], fontSize=9, leading=12, spaceAfter=4)
    
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=16*mm, leftMargin=16*mm, topMargin=12*mm, bottomMargin=12*mm)
    story = []
    branch = quote_data.get('branch', 'Eskilstuna')
    
    story.append(Paragraph(safe_para(COMPANY_NAME), title))
    company_line = f"Butik: {branch} | Tel: {COMPANY_PHONE} | Webb: {COMPANY_WEB}"
    story.append(Paragraph(safe_para(company_line), ParagraphStyle("Company", parent=body, alignment=TA_CENTER)))
    story.append(Paragraph("<b>KOSTNADSFORSLAG (PRICE QUOTE)</b>", title))
    story.append(Paragraph(f"<b>Datum:</b> {datetime.now().strftime('%Y-%m-%d')} &nbsp;&nbsp; <b>Giltigt i:</b> 14 dagar", body))
    
    story.append(Paragraph("KUNDINFORMATION", heading))
    story.append(Paragraph(f"<b>Kund:</b> {safe_para(quote_data['customer_name'])} &nbsp;&nbsp; <b>Telefon:</b> {safe_para(quote_data['phone'])}", body))
    story.append(Paragraph(f"<b>Enhet / Modell:</b> {safe_para(quote_data['model'])} &nbsp;&nbsp; <b>Butik:</b> {safe_para(branch)}", body))
    
    story.append(Paragraph("SPECIFIKATION AV REPARATION OCH PRIS", heading))
    story.append(Paragraph(f"<b>Utfort arbete / Beskrivning:</b><br/>{safe_para(quote_data['description'])}", body))
    story.append(Spacer(1, 4*mm))
    story.append(Paragraph(f"<b>Att betala totalt inkl. moms:</b> <font size=12><b>{quote_data['total_price']} SEK</b></font>", ParagraphStyle("Total", parent=body, fontSize=11, textColor=colors.HexColor("#003366"))))
    story.append(Spacer(1, 8*mm))
    
    story.append(Paragraph("Villkor: Kostnadsforslaget ar kostnadsfritt om reparationen utfors hos oss. Vid enbart felsokning kan avgift tillkomma.", ParagraphStyle("Terms", parent=body, fontSize=7.5, textColor=colors.HexColor("#555555"))))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

# -----------------------------------------------------------------------------
# Streamlit Application UI
# -----------------------------------------------------------------------------
store = CRMStore()

st.sidebar.title("📱 30 Minutes Phone Fix")
st.sidebar.subheader("Employee Login")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

pin_input = st.sidebar.text_input("Enter Access Code / PIN:", type="password")
if st.sidebar.button("Login"):
    if pin_input == DELETE_PIN:
        st.session_state.authenticated = True
        st.sidebar.success("Logged in successfully!")
    else:
        st.sidebar.error("Incorrect PIN!")

if not st.session_state.authenticated:
    st.info("🔒 Please enter the employee PIN code in the sidebar to access the CRM.")
    st.stop()

tab1, tab2, tab3, tab4 = st.tabs(["📝 Nytt Ärende", "💡 Kostnadsförslag", "🔍 Sök Ärenden", "🛒 Förbeställning"])

# TAB 1: Register New Service Case
with tab1:
    st.header("Registrera Nytt Serviceärende")
    
    selected_branch = st.selectbox("Välj Butik / Plats *", ["Eskilstuna", "Västerås"], key="t1_branch")
    
    col1, col2 = st.columns(2)
    with col1:
        first_name = st.text_input("Förnamn *", key="t1_fn")
        last_name = st.text_input("Efternamn *", key="t1_ln")
        phone = st.text_input("Telefonnummer *", key="t1_ph")
        email = st.text_input("E-post", key="t1_em")
    
    with col2:
        model = st.text_input("Enhet / Modell * (ex. iPhone 13 Pro)", key="t1_mod")
        imei_serial = st.text_input("IMEI / Serienummer", key="t1_imei")
        subscription_type = st.selectbox("Abonnemangstyp", ["Privat", "Företag", "Försäkringsärende", "Annat"], key="t1_sub")
    
    issue_description = st.text_area("Felbeskrivning (Issue Description)", key="t1_desc")

    if st.button("💾 Spara Ärende & Skapa PDF", type="primary", key="btn_t1"):
        if not first_name or not last_name or not phone or not model:
            st.warning("⚠️ Fyll i alla obligatoriska fält (Förnamn, Efternamn, Telefon, Modell).")
        else:
            case_data = {
                "first_name": first_name, "last_name": last_name, "phone": phone,
                "email": email, "model": model, "imei_serial": imei_serial,
                "subscription_type": subscription_type, "issue_description": issue_description,
                "start_date": datetime.now().date().isoformat(),
                "branch": selected_branch
            }
            saved_case = store.create_case(case_data)
            st.success(f"✅ Ärende #{saved_case.get('id')} har sparats ({selected_branch})!")
            
            pdf_bytes = generate_receipt_pdf_bytes(saved_case)
            st.download_button(
                label="📄 Ladda ner PDF-kvitto (Download Receipt)",
                data=pdf_bytes,
                file_name=f"Kvitto_{saved_case.get('id')}.pdf",
                mime="application/pdf",
                key="dl_t1"
            )

# TAB 2: Kostnadsförslag (Price Quote)
with tab2:
    st.header("Skapa Kostnadsförslag (Price Quote)")
    
    q_branch = st.selectbox("Välj Butik / Plats *", ["Eskilstuna", "Västerås"], key="q_branch")
    
    q_col1, q_col2 = st.columns(2)
    with q_col1:
        q_name = st.text_input("Kundens Namn *", key="q_name")
        q_phone = st.text_input("Telefonnummer *", key="q_phone")
    with q_col2:
        q_model = st.text_input("Enhet / Modell * (ex. iPhone 12)", key="q_model")
        q_price = st.text_input("Totalpris inkl. moms (SEK) *", key="q_price", placeholder="ex. 1290")
    
    q_desc = st.text_area("Reparationsdetaljer / Åtgärder", key="q_desc", placeholder="ex. Skärmbyte (Originaldel) inklusive arbete och garanti.")

    if st.button("📄 Generera Kostnadsförslag PDF", type="primary", key="btn_quote"):
        if not q_name or not q_phone or not q_model or not q_price:
            st.warning("⚠️ Fyll i kundens namn, telefon, modell och pris.")
        else:
            quote_data = {
                "customer_name": q_name,
                "phone": q_phone,
                "model": q_model,
                "total_price": q_price,
                "description": q_desc,
                "branch": q_branch
            }
            q_pdf_bytes = generate_quote_pdf_bytes(quote_data)
            st.success(f"✅ Kostnadsförslag skapat ({q_branch})!")
            st.download_button(
                label="📥 Ladda ner Kostnadsförslag PDF",
                data=q_pdf_bytes,
                file_name=f"Kostnadsforslag_{q_name.replace(' ', '_')}.pdf",
                mime="application/pdf",
                key="dl_quote"
            )

# TAB 3: Search Cases & View History
with tab3:
    st.header("Sök Serviceärenden")
    
    search_branch = st.selectbox("Filtrera efter Butik", ["Alla", "Eskilstuna", "Västerås"], key="t3_branch")
    search_query = st.text_input("Sök på namn, telefon, modell eller ärendenummer:", key="t3_search")
    
    cases = store.search_cases(search_query, branch=search_branch)
    if cases:
        st.dataframe(cases, use_container_width=True)
    else:
        st.info("Inga ärenden hittades.")

# TAB 4: Pre-Orders
with tab4:
    st.header("Registrera Förbeställning (Pre-Order)")
    
    po_branch = st.selectbox("Välj Butik / Plats *", ["Eskilstuna", "Västerås"], key="po_branch")
    po_fn = st.text_input("Förnamn", key="po_fn")
    po_ln = st.text_input("Efternamn", key="po_ln")
    po_phone = st.text_input("Telefonnummer", key="po_phone")
    part_model = st.text_input("Del / Modell (ex. Skärm iPhone 14)", key="po_part")
    deposit = st.number_input("Handpenning / Deposit (SEK)", min_value=0.0, step=50.0, key="po_dep")

    if st.button("💾 Spara Förbeställning", key="btn_po"):
        if po_fn and po_phone and part_model:
            store.create_pre_order({
                "first_name": po_fn, "last_name": po_ln,
                "phone": po_phone, "part_model": part_model,
                "deposit": deposit, "branch": po_branch
            })
            st.success(f"✅ Förbeställning sparad ({po_branch})!")
        else:
            st.warning("⚠️ Fyll i förnamn, telefon och del/modell.")
