# -*- coding: utf-8 -*-
import os
import io
import html
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components

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
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle
from reportlab.lib.units import mm

# Turso (libsql) Client Check
try:
    import libsql_client
except ImportError:
    libsql_client = None

# Company Setup & Constants
COMPANY_NAME = "30 MINUTES FIX AB"
COMPANY_TAGLINE = "Faktura • Mobilreparationer och tillbehör"
COMPANY_ADDRESS = "Gunborg Nymans Väg 2, 63222 Eskilstuna"
COMPANY_PHONE = "0700122444"
COMPANY_EMAIL = "info@30minutesphonefix.se"
COMPANY_WEB = "www.30minutesphonefix.se"
ORG_NR = "5593708034"
VAT_NR = "SE559370803401"
BANKGIRO = "5837-0354"
SWISH = "1230435420"

# Secure PINs configuration
try:
    DELETE_PIN = st.secrets.get("DELETE_PIN", os.getenv("DELETE_PIN", "tunapark"))
    DELETE_ACTION_PIN = st.secrets.get("DELETE_ACTION_PIN", os.getenv("DELETE_ACTION_PIN", "admin123"))
except Exception:
    DELETE_PIN = os.getenv("DELETE_PIN", "tunapark")
    DELETE_ACTION_PIN = os.getenv("DELETE_ACTION_PIN", "admin123")

# Direct Print Helper for Staff
def employee_print_button():
    print_js = """
    <script>
    function triggerPrint() {
        window.print();
    }
    </script>
    <button onclick="triggerPrint()" style="background-color: #003366; color: white; padding: 10px 20px; border: none; border-radius: 5px; font-weight: bold; cursor: pointer; font-size: 14px; margin-top: 10px;">
        🖨️ Skriv ut (Direct Print - Staff Only)
    </button>
    """
    components.html(print_js, height=60)

# -----------------------------------------------------------------------------
# CRM Store Database Management (Hybrid: Turso Cloud / Local SQLite Fallback)
# -----------------------------------------------------------------------------
class CRMStore:
    def __init__(self):
        try:
            self.db_url = st.secrets.get("TURSO_DATABASE_URL", os.getenv("TURSO_DATABASE_URL", ""))
            self.db_token = st.secrets.get("TURSO_AUTH_TOKEN", os.getenv("TURSO_AUTH_TOKEN", ""))
        except Exception:
            self.db_url = os.getenv("TURSO_DATABASE_URL", "")
            self.db_token = os.getenv("TURSO_AUTH_TOKEN", "")

        self.use_turso = bool(self.db_url and libsql_client)
        self.local_db_path = Path("local_crm.db")
        self._init_db()

    def _get_conn(self):
        if self.use_turso:
            try:
                return libsql_client.connect(url=self.db_url, auth_token=self.db_token)
            except Exception:
                pass
        return sqlite3.connect(self.local_db_path)

    def _init_db(self):
        conn = self._get_conn()
        try:
            if self.use_turso:
                with conn:
                    conn.execute("CREATE TABLE IF NOT EXISTS customers (id INTEGER PRIMARY KEY AUTOINCREMENT, first_name TEXT, last_name TEXT, phone TEXT UNIQUE, email TEXT, subscription_type TEXT, branch TEXT)")
                    conn.execute("CREATE TABLE IF NOT EXISTS service_cases (id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER, legacy_id TEXT, first_name TEXT, last_name TEXT, phone TEXT, email TEXT, subscription_type TEXT, model TEXT, imei_serial TEXT, issue_description TEXT, start_date TEXT, end_date TEXT, status TEXT, branch TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
                    conn.execute("CREATE TABLE IF NOT EXISTS pre_orders (id INTEGER PRIMARY KEY AUTOINCREMENT, first_name TEXT, last_name TEXT, phone TEXT, part_model TEXT, deposit REAL, branch TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
                    conn.execute("CREATE TABLE IF NOT EXISTS price_quotes (id INTEGER PRIMARY KEY AUTOINCREMENT, customer_name TEXT, phone TEXT, model TEXT, total_price TEXT, description TEXT, branch TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
                    conn.execute("CREATE TABLE IF NOT EXISTS customer_subscriptions (id INTEGER PRIMARY KEY AUTOINCREMENT, first_name TEXT, last_name TEXT, phone TEXT, email TEXT, model TEXT, imei_serial TEXT, sub_type TEXT, initial_paid REAL, monthly_fee REAL, next_payment_date TEXT, expiry_date TEXT, status TEXT, branch TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
            else:
                with conn:
                    conn.execute("CREATE TABLE IF NOT EXISTS customers (id INTEGER PRIMARY KEY AUTOINCREMENT, first_name TEXT, last_name TEXT, phone TEXT UNIQUE, email TEXT, subscription_type TEXT, branch TEXT)")
                    conn.execute("CREATE TABLE IF NOT EXISTS service_cases (id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER, legacy_id TEXT, first_name TEXT, last_name TEXT, phone TEXT, email TEXT, subscription_type TEXT, model TEXT, imei_serial TEXT, issue_description TEXT, start_date TEXT, end_date TEXT, status TEXT, branch TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
                    conn.execute("CREATE TABLE IF NOT EXISTS pre_orders (id INTEGER PRIMARY KEY AUTOINCREMENT, first_name TEXT, last_name TEXT, phone TEXT, part_model TEXT, deposit REAL, branch TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
                    conn.execute("CREATE TABLE IF NOT EXISTS price_quotes (id INTEGER PRIMARY KEY AUTOINCREMENT, customer_name TEXT, phone TEXT, model TEXT, total_price TEXT, description TEXT, branch TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
                    conn.execute("CREATE TABLE IF NOT EXISTS customer_subscriptions (id INTEGER PRIMARY KEY AUTOINCREMENT, first_name TEXT, last_name TEXT, phone TEXT, email TEXT, model TEXT, imei_serial TEXT, sub_type TEXT, initial_paid REAL, monthly_fee REAL, next_payment_date TEXT, expiry_date TEXT, status TEXT, branch TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
            
            # Add imei_serial column if missing in older DB versions
            try:
                conn.execute("ALTER TABLE customer_subscriptions ADD COLUMN imei_serial TEXT")
            except Exception:
                pass
            conn.commit()
        finally:
            if hasattr(conn, "close"):
                conn.close()

    def search_cases(self, query="", branch="Alla"):
        q = query.casefold().strip()
        rows = []
        conn = self._get_conn()
        try:
            if self.use_turso:
                if branch != "Alla":
                    cursor = conn.execute("SELECT * FROM service_cases WHERE branch = ? ORDER BY id DESC LIMIT 500", (branch,))
                else:
                    cursor = conn.execute("SELECT * FROM service_cases ORDER BY id DESC LIMIT 500")
                columns = [col[0] for col in cursor.description]
                rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
            else:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                if branch != "Alla":
                    cursor.execute("SELECT * FROM service_cases WHERE branch = ? ORDER BY id DESC LIMIT 500", (branch,))
                else:
                    cursor.execute("SELECT * FROM service_cases ORDER BY id DESC LIMIT 500")
                rows = [dict(row) for row in cursor.fetchall()]
        finally:
            if hasattr(conn, "close"):
                conn.close()

        if q:
            rows = [r for r in rows if any(q in str(r.get(k) or "").casefold()
                    for k in ("first_name", "last_name", "phone", "id", "email", "model"))]
        return rows

    def search_quotes(self, query="", branch="Alla"):
        q = query.casefold().strip()
        rows = []
        conn = self._get_conn()
        try:
            if self.use_turso:
                if branch != "Alla":
                    cursor = conn.execute("SELECT * FROM price_quotes WHERE branch = ? ORDER BY id DESC LIMIT 500", (branch,))
                else:
                    cursor = conn.execute("SELECT * FROM price_quotes ORDER BY id DESC LIMIT 500")
                columns = [col[0] for col in cursor.description]
                rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
            else:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                if branch != "Alla":
                    cursor.execute("SELECT * FROM price_quotes WHERE branch = ? ORDER BY id DESC LIMIT 500", (branch,))
                else:
                    cursor.execute("SELECT * FROM price_quotes ORDER BY id DESC LIMIT 500")
                rows = [dict(row) for row in cursor.fetchall()]
        finally:
            if hasattr(conn, "close"):
                conn.close()

        if q:
            rows = [r for r in rows if any(q in str(r.get(k) or "").casefold()
                    for k in ("customer_name", "phone", "model", "id", "description"))]
        return rows

    def create_quote(self, data):
        payload = {
            "customer_name": data["customer_name"],
            "phone": data["phone"],
            "model": data["model"],
            "total_price": data["total_price"],
            "description": data["description"],
            "branch": data["branch"]
        }
        conn = self._get_conn()
        try:
            cursor = conn.execute("""
                INSERT INTO price_quotes (customer_name, phone, model, total_price, description, branch)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (payload["customer_name"], payload["phone"], payload["model"], payload["total_price"], payload["description"], payload["branch"]))
            conn.commit()
            payload["id"] = cursor.lastrowid
            return payload
        finally:
            if hasattr(conn, "close"):
                conn.close()

    def upsert_customer(self, first, last, phone, email, subscription="", branch="Eskilstuna"):
        conn = self._get_conn()
        try:
            cursor = conn.execute("SELECT id FROM customers WHERE phone = ?", (phone,))
            row = cursor.fetchone()
            if row:
                cid = row[0]
                conn.execute("UPDATE customers SET first_name=?, last_name=?, email=?, subscription_type=?, branch=? WHERE id=?", 
                             (first, last, email or None, subscription or None, branch, cid))
                conn.commit()
                return cid
            else:
                cursor = conn.execute("INSERT INTO customers (first_name, last_name, phone, email, subscription_type, branch) VALUES (?, ?, ?, ?, ?, ?)", 
                             (first, last, phone, email or None, subscription or None, branch))
                conn.commit()
                return cursor.lastrowid
        finally:
            if hasattr(conn, "close"):
                conn.close()

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

        conn = self._get_conn()
        try:
            cursor = conn.execute("""
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
        finally:
            if hasattr(conn, "close"):
                conn.close()

    def create_pre_order(self, data):
        payload = {
            "first_name": data["first_name"], "last_name": data["last_name"],
            "phone": data["phone"], "part_model": data["part_model"],
            "deposit": data["deposit"], "branch": data["branch"]
        }
        conn = self._get_conn()
        try:
            cursor = conn.execute("INSERT INTO pre_orders (first_name, last_name, phone, part_model, deposit, branch) VALUES (?, ?, ?, ?, ?, ?)", 
                       (payload["first_name"], payload["last_name"], payload["phone"], payload["part_model"], payload["deposit"], payload["branch"]))
            conn.commit()
            payload["id"] = cursor.lastrowid
            return payload
        finally:
            if hasattr(conn, "close"):
                conn.close()

    def create_subscription(self, data):
        payload = {
            "first_name": data["first_name"], "last_name": data["last_name"],
            "phone": data["phone"], "email": data["email"], "model": data["model"],
            "imei_serial": data["imei_serial"], "sub_type": data["sub_type"], 
            "initial_paid": data["initial_paid"], "monthly_fee": data["monthly_fee"], 
            "next_payment_date": data["next_payment_date"], "expiry_date": data["expiry_date"], 
            "status": "Aktiv", "branch": data["branch"]
        }
        conn = self._get_conn()
        try:
            cursor = conn.execute("""
                INSERT INTO customer_subscriptions (first_name, last_name, phone, email, model, imei_serial, sub_type, initial_paid, monthly_fee, next_payment_date, expiry_date, status, branch)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                payload["first_name"], payload["last_name"], payload["phone"], payload["email"],
                payload["model"], payload["imei_serial"], payload["sub_type"], payload["initial_paid"], 
                payload["monthly_fee"], payload["next_payment_date"], payload["expiry_date"], 
                payload["status"], payload["branch"]
            ))
            conn.commit()
            payload["id"] = cursor.lastrowid
            return payload
        finally:
            if hasattr(conn, "close"):
                conn.close()

# -----------------------------------------------------------------------------
# PDF Generation Functions
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
                          Paragraph("KLIPP HÄR / SAX LINJE", ParagraphStyle("Cut", parent=body, alignment=TA_CENTER, textColor=colors.grey)), Spacer(1, 3*mm)])
        
        story.append(Paragraph(safe_para(COMPANY_NAME), title))
        company_line = f"Butik: {branch} | Tel: {COMPANY_PHONE} | Webb: {COMPANY_WEB} | {COMPANY_EMAIL}"
        story.append(Paragraph(safe_para(company_line), ParagraphStyle("Company", parent=body, alignment=TA_CENTER)))
        story.append(Paragraph(f"<b>{copy_title} - INLÄMNINGSKVITTO & AVTAL</b>", title))
        story.append(Paragraph(f"<b>Ärendenummer:</b> {safe_para(case.get('id'))} &nbsp;&nbsp; <b>Datum:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}", body))
        story.append(Paragraph("KUND- OCH ENHETSINFORMATION", heading))
        story.append(Paragraph(f"<b>Kund:</b> {safe_para(full_name)} &nbsp;&nbsp; <b>Mobil:</b> {safe_para(case.get('phone'))}", body))
        story.append(Paragraph(f"<b>E-post:</b> {safe_para(case.get('email'))} &nbsp;&nbsp; <b>Modell:</b> {safe_para(case.get('model'))}", body))
        story.append(Paragraph(f"<b>IMEI / Serienummer:</b> {safe_para(case.get('imei_serial'))}", body))
        story.append(Paragraph(f"<b>Abonnemangstyp:</b> {safe_para(case.get('subscription_type'))} &nbsp;&nbsp; <b>Butik:</b> {safe_para(branch)}", body))
        story.append(Paragraph(f"<b>Felbeskrivning:</b> {safe_para(case.get('issue_description'))}", body))
        story.append(Paragraph("SÄRSKILDA AVTALSVILLKOR", heading))
        for term in [
            "1. Verkstaden ansvarar för felsökning och reparation enligt den felbeskrivning som anges ovan.",
            "2. Garanti gäller endast för de delar och det arbete som uttryckligen omfattas av verkstadens garanti.",
            "3. Kunden ansvarar för att säkerhetskopiera enheten (om möjligt, eller begära hjälp av verkstaden). Verkstaden sparar ingen information automatiskt, men på grund av mjukvarufel eller hårdvaruskador (såsom vattenskador eller fel på moderkortet) finns det en risk för dataförlust under reparationen, och verkstaden garanterar inte att data bevaras."
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
    story.append(Paragraph("<b>KOSTNADSFÖRSLAG (PRICE QUOTE)</b>", title))
    story.append(Paragraph(f"<b>Datum:</b> {datetime.now().strftime('%Y-%m-%d')} &nbsp;&nbsp; <b>Giltigt i:</b> 14 dagar", body))
    
    story.append(Paragraph("KUNDINFORMATION", heading))
    story.append(Paragraph(f"<b>Kund:</b> {safe_para(quote_data['customer_name'])} &nbsp;&nbsp; <b>Telefon:</b> {safe_para(quote_data['phone'])}", body))
    story.append(Paragraph(f"<b>Enhet / Modell:</b> {safe_para(quote_data['model'])} &nbsp;&nbsp; <b>Butik:</b> {safe_para(branch)}", body))
    
    story.append(Paragraph("SPECIFIKATION AV REPARATION OCH PRIS", heading))
    story.append(Paragraph(f"<b>Utfört arbete / Beskrivning:</b><br/>{safe_para(quote_data['description'])}", body))
    story.append(Spacer(1, 4*mm))
    story.append(Paragraph(f"<b>Att betala totalt inkl. moms:</b> <font size=12><b>{quote_data['total_price']} SEK</b></font>", ParagraphStyle("Total", parent=body, fontSize=11, textColor=colors.HexColor("#003366"))))
    story.append(Spacer(1, 8*mm))
    
    story.append(Paragraph("Villkor: Kostnadsförslaget är kostnadsfritt om reparationen utförs hos oss. Vid enbart felsökning kan avgift tillkomma.", ParagraphStyle("Terms", parent=body, fontSize=7.5, textColor=colors.HexColor("#555555"))))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

def generate_invoice_pdf_bytes(inv_data):
    buffer = io.BytesIO()
    styles = getSampleStyleSheet()
    sub = ParagraphStyle("InvSub", parent=styles["Normal"], fontSize=8.5, leading=11, textColor=colors.HexColor("#333333"))
    body = ParagraphStyle("InvBody", parent=styles["Normal"], fontSize=8.5, leading=11)
    bold_body = ParagraphStyle("InvBoldBody", parent=body, fontName="Helvetica-Bold")
    header_right = ParagraphStyle("InvRight", parent=body, alignment=TA_RIGHT)
    
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=15*mm, leftMargin=15*mm, topMargin=12*mm, bottomMargin=12*mm)
    story = []
    
    header_data = [
        [
            Paragraph(f"<b>{COMPANY_NAME}</b><br/>{COMPANY_TAGLINE}<br/>{COMPANY_ADDRESS}<br/>Tel: {COMPANY_PHONE} | {COMPANY_EMAIL}<br/>Webb: {COMPANY_WEB}", sub),
            Paragraph(f"<b>FAKTURA</b><br/><b>Fakturanr:</b> {inv_data['invoice_no']}<br/><b>Fakturadatum:</b> {inv_data['invoice_date']}<br/><b>Förfallodatum:</b> {inv_data['due_date']}", header_right)
        ]
    ]
    t_header = Table(header_data, colWidths=[100*mm, 80*mm])
    t_header.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('BOTTOMPADDING', (0,0), (-1,-1), 10)]))
    story.append(t_header)
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#003366"), spaceAfter=6, spaceBefore=2))
    
    meta_box = [
        [
            Paragraph(f"<b>AVSÄNDARE:</b><br/>{COMPANY_NAME}<br/>Org.nr: {ORG_NR} • VAT.nr: {VAT_NR}<br/>Bankgiro: {BANKGIRO} • Swish: {SWISH}", body),
            Paragraph(f"<b>MOTTAGARE / KUND:</b><br/><b>{inv_data['customer_name']}</b><br/>{inv_data.get('customer_address', '')}<br/>Tel: {inv_data['customer_phone']}<br/>E-post: {inv_data.get('customer_email', 'Ej angivet')}", body)
        ]
    ]
    t_meta = Table(meta_box, colWidths=[90*mm, 90*mm])
    t_meta.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F9F9F9")), ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#CCCCCC")), ('VALIGN', (0,0), (-1,-1), 'TOP'), ('TOPPADDING', (0,0), (-1,-1), 6), ('BOTTOMPADDING', (0,0), (-1,-1), 6), ('LEFTPADDING', (0,0), (-1,-1), 6), ('RIGHTPADDING', (0,0), (-1,-1), 6)]))
    story.append(t_meta)
    story.append(Spacer(1, 5*mm))
    
    ref_data = [[
        Paragraph(f"<b>Er referens:</b> {inv_data.get('your_ref', '-')}", body),
        Paragraph(f"<b>Vår referens:</b> {inv_data.get('our_ref', '-')}", body),
        Paragraph(f"<b>Betalningsvillkor:</b> {inv_data.get('terms', '30 dagar')} dagar", body),
        Paragraph(f"<b>Ordernr:</b> {inv_data.get('order_no', '-')}", body)
    ]]
    t_ref = Table(ref_data, colWidths=[45*mm, 45*mm, 45*mm, 45*mm])
    t_ref.setStyle(TableStyle([('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#DDDDDD")), ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#EEEEEE")), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('TOPPADDING', (0,0), (-1,-1), 4), ('BOTTOMPADDING', (0,0), (-1,-1), 4)]))
    story.append(t_ref)
    story.append(Spacer(1, 6*mm))
    
    table_rows = [
        [Paragraph("<b>Artikel</b>", bold_body), Paragraph("<b>Benämning / beskrivning</b>", bold_body), Paragraph("<b>Antal</b>", bold_body), Paragraph("<b>À-pris (SEK)</b>", bold_body), Paragraph("<b>Moms %</b>", bold_body), Paragraph("<b>Totalt (SEK)</b>", bold_body)]
    ]
    subtotal = 0.0
    total_moms = 0.0
    
    for item in inv_data['items']:
        qty = float(item['qty'])
        price = float(item['price'])
        vat_rate = float(item['vat'])
        line_total = qty * price
        line_vat = line_total * (vat_rate / 100.0)
        subtotal += line_total
        total_moms += line_vat
        table_rows.append([
            Paragraph(str(item.get('code', '-')), body),
            Paragraph(str(item['desc']), body),
            Paragraph(str(qty), body),
            Paragraph(f"{price:.2f}", body),
            Paragraph(f"{vat_rate}%", body),
            Paragraph(f"{line_total:.2f}", body)
        ])
        
    t_items = Table(table_rows, colWidths=[20*mm, 80*mm, 15*mm, 25*mm, 15*mm, 25*mm])
    t_items.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.HexColor("#003366")), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('BOTTOMPADDING', (0,0), (-1,-1), 5), ('TOPPADDING', (0,0), (-1,-1), 5), ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#DDDDDD"))]))
    for i in range(len(table_rows[0])):
        table_rows[0][i].style.textColor = colors.white
        
    story.append(t_items)
    story.append(Spacer(1, 6*mm))
    
    grand_total = subtotal + total_moms
    summary_data = [
        [Paragraph("<b>Momsunderlag (SEK):</b>", body), Paragraph(f"{subtotal:.2f}", header_right)],
        [Paragraph("<b>Total moms (SEK):</b>", body), Paragraph(f"{total_moms:.2f}", header_right)],
        [Paragraph("<b>ATT BETALA (SEK):</b>", bold_body), Paragraph(f"<b>{grand_total:.2f} SEK</b>", header_right)]
    ]
    t_summary = Table(summary_data, colWidths=[100*mm, 80*mm])
    t_summary.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor("#EBF2F8")), ('BOX', (0,0), (-1,-1), 0.8, colors.HexColor("#003366")), ('TOPPADDING', (0,0), (-1,-1), 5), ('BOTTOMPADDING', (0,0), (-1,-1), 5)]))
    story.append(t_summary)
    story.append(Spacer(1, 10*mm))
    
    pay_box = [[Paragraph(f"<b>Betalningsuppgifter:</b><br/>Bankgiro: <b>{BANKGIRO}</b> | Swish: <b>{SWISH}</b><br/><i>Ange fakturanummer ({inv_data['invoice_no']}) som meddelande vid betalning.</i>", sub)]]
    t_pay = Table(pay_box, colWidths=[180*mm])
    t_pay.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F4F4F4")), ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#CCCCCC")), ('TOPPADDING', (0,0), (-1,-1), 6), ('BOTTOMPADDING', (0,0), (-1,-1), 6), ('LEFTPADDING', (0,0), (-1,-1), 6)]))
    story.append(t_pay)
    story.append(Spacer(1, 6*mm))
    story.append(Paragraph(f"<font size=7 color='#666666'>{COMPANY_NAME} • Org.nr {ORG_NR} • VAT {VAT_NR} • Tack för ditt förtroende!</font>", ParagraphStyle("Foot", parent=body, alignment=TA_CENTER)))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

# -----------------------------------------------------------------------------
# Streamlit Application Interface
# -----------------------------------------------------------------------------
store = CRMStore()

st.sidebar.title("📱 30 Minutes Phone Fix")
st.sidebar.subheader("🔒 Personal Inloggning")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    pin_input = st.sidebar.text_input("Ange Personal PIN / Kod:", type="password", key="login_pin")
    if st.sidebar.button("🔑 Logga in", key="btn_login"):
        if pin_input == DELETE_PIN:
            st.session_state.authenticated = True
            st.sidebar.success("✅ Inloggad som Personal")
            st.rerun()
        else:
            st.sidebar.error("❌ Felaktig PIN-kod!")
else:
    st.sidebar.success("🔒 Inloggad (Personalläge aktivt)")
    if st.sidebar.button("🚪 Logga ut"):
        st.session_state.authenticated = False
        st.rerun()

# Application Tabs Navigation
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📝 Nytt Ärende", 
    "💡 Kostnadsförslag (Public)", 
    "📄 Faktura", 
    "🔍 Sök Ärenden (Protected)", 
    "🛒 Förbeställning (Public)",
    "💳 Abonnemang"
])

# TAB 1: Nytt Ärende
with tab1:
    st.header("📝 Skapa Nytt Serviceärende")
    branch = st.selectbox("Välj Butik / Plats *", ["Eskilstuna", "Västerås"], key="new_case_branch")
    
    col1, col2 = st.columns(2)
    with col1:
        fn = st.text_input("Förnamn *", key="nc_fn")
        ln = st.text_input("Efternamn *", key="nc_ln")
        phone = st.text_input("Telefonnummer *", key="nc_phone")
    with col2:
        email = st.text_input("E-post", key="nc_email")
        model = st.text_input("Enhet / Modell *", key="nc_model")
        imei = st.text_input("IMEI / Serienummer", key="nc_imei")
        sub_type = st.selectbox("Abonnemangstyp", ["Privat", "Företag", "Försäkring"], key="nc_sub")
        
    issue_desc = st.text_area("Felbeskrivning *", key="nc_desc")
    
    if st.button("💾 Spara och Skapa Ärende", type="primary", key="btn_create_case"):
        if not fn or not ln or not phone or not model or not issue_desc:
            st.warning("⚠️ Vänligen fyll i alla obligatoriska fält.")
        else:
            case_data = {
                "first_name": fn, "last_name": ln, "phone": phone,
                "email": email, "model": model, "imei_serial": imei,
                "subscription_type": sub_type, "issue_description": issue_desc,
                "start_date": datetime.now().strftime('%Y-%m-%d'),
                "branch": branch
            }
            new_case = store.create_case(case_data)
            st.success(f"✅ Ärende #{new_case['id']} har skapats framgångsrikt!")
            
            pdf_bytes = generate_receipt_pdf_bytes(new_case)
            st.download_button(
                label="📥 Ladda ner Inlämningskvitto (PDF)",
                data=pdf_bytes,
                file_name=f"Inlaminingskvitto_Arende_{new_case['id']}.pdf",
                mime="application/pdf"
            )

# TAB 2: Kostnadsförslag (Public)
with tab2:
    st.header("💡 Skapa / Begär Kostnadsförslag (Price Quote)")
    q_branch = st.selectbox("Välj Butik / Plats *", ["Eskilstuna", "Västerås"], key="q_branch")
    q_col1, q_col2 = st.columns(2)
    with q_col1:
        q_name = st.text_input("Ditt Namn *", key="q_name")
        q_phone = st.text_input("Telefonnummer *", key="q_phone")
    with q_col2:
        q_model = st.text_input("Enhet / Modell * (ex. iPhone 12 Pro)", key="q_model")
    
    st.markdown("#### 🛠️ Välj reparationer och ange pris")
    repair_options = [
        "Skärmbyte (Display)", "Vattenskada (Water damaged)", "Baksida skadad (Back glass)",
        "Kamera (Camera)", "Kameralins (Camera lens)", "Laddport (Charging port)",
        "Hemknapp (Home button)", "Batteribyte (Battery replacement)"
    ]
    
    selected_repairs_info = []
    total_calculated_price = 0.0
    col_a, col_b = st.columns(2)
    half_len = (len(repair_options) + 1) // 2
    
    with col_a:
        for idx, rep_name in enumerate(repair_options[:half_len]):
            if st.checkbox(rep_name, key=f"rep_chk_{idx}"):
                item_price = st.number_input(f"Pris för {rep_name} (SEK)", min_value=0.0, step=50.0, value=0.0, key=f"rep_price_{idx}")
                selected_repairs_info.append(f"{rep_name}: {item_price:.0f} SEK")
                total_calculated_price += item_price
                
    with col_b:
        for idx, rep_name in enumerate(repair_options[half_len:], start=half_len):
            if st.checkbox(rep_name, key=f"rep_chk_{idx}"):
                item_price = st.number_input(f"Pris för {rep_name} (SEK)", min_value=0.0, step=50.0, value=0.0, key=f"rep_price_{idx}")
                selected_repairs_info.append(f"{rep_name}: {item_price:.0f} SEK")
                total_calculated_price += item_price

    extra_desc = st.text_area("Övriga anteckningar / Beskrivning", key="q_extra")
    
    full_description = "\n".join(selected_repairs_info)
    if extra_desc:
        full_description += f"\nExtra: {extra_desc}"
        
    st.info(f"💰 **Beräknat totalpris:** {total_calculated_price:.0f} SEK")
    
    if st.button("💾 Spara och Skapa Kostnadsförslag", type="primary", key="btn_create_quote"):
        if not q_name or not q_phone or not q_model or total_calculated_price <= 0:
            st.warning("⚠️ Vänligen fyll i namn, telefon, modell och välj minst en reparation med pris.")
        else:
            quote_data = {
                "customer_name": q_name, "phone": q_phone, "model": q_model,
                "total_price": f"{total_calculated_price:.0f}", "description": full_description, "branch": q_branch
            }
            new_q = store.create_quote(quote_data)
            st.success(f"✅ Kostnadsförslag #{new_q['id']} har skapats!")
            pdf_bytes = generate_quote_pdf_bytes(new_q)
            st.download_button(
                label="📥 Ladda ner Kostnadsförslag (PDF)",
                data=pdf_bytes,
                file_name=f"Kostnadsforslag_{new_q['id']}.pdf",
                mime="application/pdf"
            )

# TAB 3: Faktura
with tab3:
    st.header("📄 Skapa Faktura")
    if not st.session_state.authenticated:
        st.warning("🔒 Denna flik kräver personalinloggning.")
    else:
        inv_branch = st.selectbox("Butik / Plats", ["Eskilstuna", "Västerås"], key="inv_branch")
        col1, col2 = st.columns(2)
        with col1:
            inv_no = st.text_input("Fakturanummer", value=f"INV-{datetime.now().strftime('%Y%m%d%H%M')}")
            c_name = st.text_input("Kundnamn / Företag")
            c_addr = st.text_input("Adress")
            c_phone = st.text_input("Telefonnummer")
        with col2:
            c_email = st.text_input("E-post")
            inv_date = st.date_input("Fakturadatum", value=datetime.now())
            due_days = st.selectbox("Betalningsvillkor", [15, 30, 45], index=1)
            due_date = inv_date + timedelta(days=due_days)
            st.write(f"**Förfallodatum:** {due_date}")

        st.markdown("#### Artiklar")
        if "invoice_items" not in st.session_state:
            st.session_state.invoice_items = [{"code": "REPAR", "desc": "Mobilreparation", "qty": 1.0, "price": 1000.0, "vat": 25.0}]

        for idx, item in enumerate(st.session_state.invoice_items):
            cols = st.columns([1, 3, 1, 2, 1])
            item["code"] = cols[0].text_input(f"Art.nr", value=item["code"], key=f"inv_code_{idx}")
            item["desc"] = cols[1].text_input(f"Beskrivning", value=item["desc"], key=f"inv_desc_{idx}")
            item["qty"] = cols[2].number_input(f"Antal", value=item["qty"], key=f"inv_qty_{idx}")
            item["price"] = cols[3].number_input(f"À-pris", value=item["price"], key=f"inv_price_{idx}")
            item["vat"] = cols[4].selectbox(f"Moms", [25.0, 12.0, 6.0, 0.0], index=0, key=f"inv_vat_{idx}")

        if st.button("➕ Lägg till rad"):
            st.session_state.invoice_items.append({"code": "", "desc": "", "qty": 1.0, "price": 0.0, "vat": 25.0})
            st.rerun()

        if st.button("💾 Generera Faktura (PDF)", type="primary"):
            if not c_name or not c_phone:
                st.warning("⚠️ Vänligen fyll i kundnamn och telefon.")
            else:
                inv_data = {
                    "invoice_no": inv_no, "invoice_date": inv_date.strftime('%Y-%m-%d'),
                    "due_date": due_date.strftime('%Y-%m-%d'), "customer_name": c_name,
                    "customer_address": c_addr, "customer_phone": c_phone, "customer_email": c_email,
                    "items": st.session_state.invoice_items, "branch": inv_branch
                }
                pdf_bytes = generate_invoice_pdf_bytes(inv_data)
                st.download_button(
                    label="📥 Ladda ner Faktura (PDF)",
                    data=pdf_bytes,
                    file_name=f"Faktura_{inv_no}.pdf",
                    mime="application/pdf"
                )

# TAB 4: Sök Ärenden (Protected)
with tab4:
    st.header("🔍 Sök Serviceärenden")
    if not st.session_state.authenticated:
        st.warning("🔒 Denna flik kräver inloggning. Ange PIN-koden i menyn till vänster.")
    else:
        search_branch = st.selectbox("Filtrera på Butik", ["Alla", "Eskilstuna", "Västerås"], key="search_branch")
        search_query = st.text_input("Sök på namn, telefon, modell eller ärendenummer", key="search_query")
        
        cases = store.search_cases(search_query, search_branch)
        if cases:
            st.write(f"Hittade {len(cases)} ärenden:")
            for c in cases:
                with st.expander(f"Ärende #{c.get('id')} - {c.get('first_name')} {c.get('last_name')} ({c.get('model')})"):
                    st.write(f"**Telefon:** {c.get('phone')}")
                    st.write(f"**E-post:** {c.get('email')}")
                    st.write(f"**Felbeskrivning:** {c.get('issue_description')}")
                    st.write(f"**Status:** {c.get('status')} | **Butik:** {c.get('branch')}")
                    st.write(f"**Datum:** {c.get('created_at')}")
        else:
            st.info("Inga ärenden hittades.")

# TAB 5: Förbeställning (Public)
with tab5:
    st.header("🛒 Förbeställning av reservdel")
    po_branch = st.selectbox("Välj Butik / Plats", ["Eskilstuna", "Västerås"], key="po_branch")
    col1, col2 = st.columns(2)
    with col1:
        po_fn = st.text_input("Förnamn", key="po_fn")
        po_ln = st.text_input("Efternamn", key="po_ln")
        po_phone = st.text_input("Telefonnummer", key="po_phone")
    with col2:
        po_model = st.text_input("Del / Enhetsmodell (ex. iPhone 13 Skärm)", key="po_model")
        po_deposit = st.number_input("Handpenning (SEK)", min_value=0.0, step=50.0, value=100.0, key="po_deposit")

    if st.button("💾 Spara Förbeställning", type="primary", key="btn_po"):
        if not po_fn or not po_phone or not po_model:
            st.warning("⚠️ Fyll i namn, telefon och modell.")
        else:
            po_data = {
                "first_name": po_fn, "last_name": po_ln, "phone": po_phone,
                "part_model": po_model, "deposit": po_deposit, "branch": po_branch
            }
            res = store.create_pre_order(po_data)
            st.success(f"✅ Förbeställning #{res['id']} sparad!")

# TAB 6: Abonnemang
with tab6:
    st.header("💳 Abonnemang och Tjänster (Enhetsbundna)")
    
    sub_choice = st.radio("Välj Abonnemangstyp att registrera:", [
        "GlassGuard™ Pro (Skärmskyddsabonnemang)", 
        "Cover / Case Abonnemang (Mobilskal & Kantskydd)",
        "Teknik & Mjukvara (Mjukvarufel, Virus & Felsökning)"
    ], key="sub_choice_radio")
    
    sub_branch = st.selectbox("Välj Butik / Plats", ["Eskilstuna", "Västerås"], key="sub_branch_sel")
    
    if "GlassGuard" in sub_choice:
        st.markdown("""
        > **30 Minutes GlassGuard™ Pro**  
        > **Pris:** Endast **99 SEK / månad** (3 månaders bindnings-/uppsägningstid).  
        > * **Täckning:** Härdat glas till alla iPhone + 99% av Samsung & Google. MobileSkin till alla modeller.  
        > * **Villkor:** Låst till enhet via **IMEI/Serienummer**. Byt upp till 2 ggr/mån utan självrisk + 15% rabatt på reparation/tillbehör.
        """)
        def_initial = 99.0
        fee_val = 99.0
        sub_type_name = "GlassGuard™ Pro (99kr/mån)"
    elif "Cover" in sub_choice:
        st.markdown("""
        > **Cover / Case Abonnemang (Mobilskal)**  
        > **Pris:** **399 SEK** startavgift + **99 SEK / månad** (3 månaders bindnings-/uppsägningstid).  
        > * **Villkor:** Låst till enhet via **IMEI/Serienummer**. Byt skal **1 gång var 3:e månad** helt utan självrisk (0 SEK).
        """)
        def_initial = 399.0
        fee_val = 99.0
        sub_type_name = "Cover / Case Abonnemang (399kr start + 99kr/mån)"
    else:
        st.markdown("""
        > **Teknik & Mjukvara Abonnemang (Mobil & Dator)**  
        > **Pris:** Endast **99 SEK / månad** (3 månaders bindnings-/uppsägningstid).  
        > * **Villkor:** Låst till enhet via **IMEI / Serienummer**. Få fri mjukvarusupport, virusborttagning och felsökning för enheten så länge abonnemanget är aktivt. Enheten kan bytas ut i abonnemanget **1 gång var 3:e månad**.
        """)
        def_initial = 99.0
        fee_val = 99.0
        sub_type_name = "Teknik & Mjukvara Abonnemang (99kr/mån)"

    col1, col2 = st.columns(2)
    with col1:
        s_fn = st.text_input("Förnamn *", key="sub_fn")
        s_ln = st.text_input("Efternamn *", key="sub_ln")
        s_phone = st.text_input("Telefonnummer *", key="sub_phone")
    with col2:
        s_email = st.text_input("E-post", key="sub_email")
        s_model = st.text_input("Enhet / Modell * (ex. iPhone 15 Pro / MacBook)", key="sub_model")
        s_imei = st.text_input("IMEI / Serienummer (Enhetslås) *", key="sub_imei", help="Obligatoriskt för att låsa abonnemanget till enskild enhet.")
        s_initial = st.number_input("Startbelopp / Första betalning (SEK)", min_value=0.0, step=50.0, value=def_initial, key="sub_initial")

    if st.button("💾 Registrera Abonnemang (Enhetsbundet)", type="primary", key="btn_save_sub"):
        if not s_fn or not s_ln or not s_phone or not s_model or not s_imei:
            st.warning("⚠️ Vänligen fyll i alla obligatoriska fält, inklusive IMEI / Serienummer för enhetslåsning.")
        else:
            now = datetime.now()
            next_pay = (now + timedelta(days=30)).strftime('%Y-%m-%d')
            expiry = (now + timedelta(days=90)).strftime('%Y-%m-%d') # 3 månaders bindnings-/uppsägningstid
            
            sub_data = {
                "first_name": s_fn, "last_name": s_ln, "phone": s_phone,
                "email": s_email, "model": s_model, "imei_serial": s_imei,
                "sub_type": sub_type_name, "initial_paid": s_initial, "monthly_fee": fee_val,
                "next_payment_date": next_pay, "expiry_date": expiry, "branch": sub_branch
            }
            res = store.create_subscription(sub_data)
            st.success(f"✅ Abonnemang '{sub_type_name}' har skapats och låsts till enhet IMEI/Serial: {s_imei}!")
