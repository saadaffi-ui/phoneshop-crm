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

try:
    from supabase import create_client
except ImportError:
    create_client = None

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

# Secure PINs configuration (Secrets or Fallbacks)
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
# CRM Store Database Management (Supabase & Local SQLite Backup)
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
            conn.execute("""
                CREATE TABLE IF NOT EXISTS price_quotes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_name TEXT, phone TEXT, model TEXT,
                    total_price TEXT, description TEXT, branch TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS customer_subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    first_name TEXT, last_name TEXT, phone TEXT,
                    email TEXT, model TEXT, sub_type TEXT,
                    initial_paid REAL, monthly_fee REAL, status TEXT, branch TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            for col_sql in [
                "ALTER TABLE customers ADD COLUMN branch TEXT",
                "ALTER TABLE service_cases ADD COLUMN branch TEXT",
                "ALTER TABLE service_cases ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                "ALTER TABLE pre_orders ADD COLUMN branch TEXT",
                "ALTER TABLE price_quotes ADD COLUMN branch TEXT",
                "ALTER TABLE price_quotes ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
            ]:
                try:
                    conn.execute(col_sql)
                except sqlite3.OperationalError:
                    pass
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

    def search_quotes(self, query="", branch="Alla"):
        q = query.casefold().strip()
        rows = []
        if self.client:
            try:
                query_builder = self.client.table("price_quotes").select("*").order("created_at", desc=True).limit(500)
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
                    cursor.execute("SELECT * FROM price_quotes WHERE branch = ? ORDER BY id DESC LIMIT 500", (branch,))
                else:
                    cursor.execute("SELECT * FROM price_quotes ORDER BY id DESC LIMIT 500")
                rows = [dict(row) for row in cursor.fetchall()]

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
        if self.client:
            try:
                res = self.client.table("price_quotes").insert(payload).execute()
                return res.data[0]
            except Exception:
                pass

        with sqlite3.connect(self.local_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO price_quotes (customer_name, phone, model, total_price, description, branch)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (payload["customer_name"], payload["phone"], payload["model"], payload["total_price"], payload["description"], payload["branch"]))
            conn.commit()
            payload["id"] = cursor.lastrowid
            return payload

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
    t_header.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(t_header)
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#003366"), spaceAfter=6, spaceBefore=2))
    
    meta_box = [
        [
            Paragraph(f"<b>AVSÄNDARE:</b><br/>{COMPANY_NAME}<br/>Org.nr: {ORG_NR} • VAT.nr: {VAT_NR}<br/>Bankgiro: {BANKGIRO} • Swish: {SWISH}", body),
            Paragraph(f"<b>MOTTAGARE / KUND:</b><br/><b>{inv_data['customer_name']}</b><br/>{inv_data.get('customer_address', '')}<br/>Tel: {inv_data['customer_phone']}<br/>E-post: {inv_data.get('customer_email', 'Ej angivet')}", body)
        ]
    ]
    t_meta = Table(meta_box, colWidths=[90*mm, 90*mm])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F9F9F9")),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#CCCCCC")),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 5*mm))
    
    ref_data = [[
        Paragraph(f"<b>Er referens:</b> {inv_data.get('your_ref', '-')}", body),
        Paragraph(f"<b>Vår referens:</b> {inv_data.get('our_ref', '-')}", body),
        Paragraph(f"<b>Betalningsvillkor:</b> {inv_data.get('terms', '30 dagar')} dagar", body),
        Paragraph(f"<b>Ordernr:</b> {inv_data.get('order_no', '-')}", body)
    ]]
    t_ref = Table(ref_data, colWidths=[45*mm, 45*mm, 45*mm, 45*mm])
    t_ref.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#DDDDDD")),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#EEEEEE")),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
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
    t_items.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#003366")),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#DDDDDD")),
    ]))
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
    t_summary.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor("#EBF2F8")),
        ('BOX', (0,0), (-1,-1), 0.8, colors.HexColor("#003366")),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_summary)
    story.append(Spacer(1, 10*mm))
    
    pay_box = [
        [
            Paragraph(f"<b>Betalningsuppgifter:</b><br/>Bankgiro: <b>{BANKGIRO}</b> | Swish: <b>{SWISH}</b><br/><i>Ange fakturanummer ({inv_data['invoice_no']}) som meddelande vid betalning.</i>", sub)
        ]
    ]
    t_pay = Table(pay_box, colWidths=[180*mm])
    t_pay.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F4F4F4")),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#CCCCCC")),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
    ]))
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
            st.warning("⚠️ Vänligen fyll i alla obligatoriska fält (Förnamn, Efternamn, Telefonnummer, Modell, Felbeskrivning).")
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

# TAB 2: Kostnadsförslag (Interactive Checkboxes + Manual Itemized Pricing)
with tab2:
    st.header("💡 Skapa / Begär Kostnadsförslag (Price Quote)")
    st.write("Välj enhet och klicka i de reparationer som behövs samt ange pris för varje del:")
    
    q_branch = st.selectbox("Välj Butik / Plats *", ["Eskilstuna", "Västerås"], key="q_branch")
    
    q_col1, q_col2 = st.columns(2)
    with q_col1:
        q_name = st.text_input("Ditt Namn *", key="q_name")
        q_phone = st.text_input("Telefonnummer *", key="q_phone")
    with q_col2:
        q_model = st.text_input("Enhet / Modell * (ex. iPhone 12 Pro)", key="q_model")
    
    st.markdown("#### 🛠️ Välj reparationer och ange pris manuellt")
    
    repair_options = [
        "Skärmbyte (Display is cracked)",
        "Vattenskada (Water damaged - Felsökning/Rengöring)",
        "Baksida skadad (Back glass cracked)",
        "Kamera (Camera repair)",
        "Kameralins (Camera lens)",
        "Antenn / Täckningsfel (Antenna)",
        "Laddport (Chargeport / Charging port)",
        "Hemknapp (Home button)",
        "Volymknapp / Strömknapp (Volume/Power button)",
        "Batteribyte (Battery replacement)"
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

    extra_desc = st.text_area("Övriga anteckningar / Beskrivning", key="q_extra_desc", placeholder="ex. Extra detaljer om skadan...")
    
    st.markdown(f"### 💰 Beräknat Totalpris: **{total_calculated_price:.0f} SEK**")
    
    q_price = st.text_input("Totalpris inkl. moms (SEK) *", value=str(int(total_calculated_price)) if total_calculated_price > 0 else "", key="q_price")

    if st.button("📤 Skicka / Spara Förslag", type="primary", key="btn_quote"):
        if not q_name or not q_phone or not q_model or not q_price:
            st.warning("⚠️ Fyll i namn, telefonnummer, modell och pris.")
        else:
            combined_desc = f"Valda reparationer:\n- " + "\n- ".join(selected_repairs_info) if selected_repairs_info else ""
            if extra_desc:
                combined_desc += f"\n\nAnteckningar: {extra_desc}"
                
            quote_data = {
                "customer_name": q_name,
                "phone": q_phone,
                "model": q_model,
                "total_price": q_price,
                "description": combined_desc if combined_desc else (extra_desc or "Reparation"),
                "branch": q_branch
            }
            store.create_quote(quote_data)
            st.success(f"✅ Kostnadsförslag har sparats i databasen ({q_branch}) med totalpriset {q_price} SEK!")

    if st.session_state.authenticated:
        st.markdown("---")
        st.subheader("🔒 Personalvy: Sparade Kostnadsförslag i Databasen")
        q_search_branch = st.selectbox("Filtrera efter Butik", ["Alla", "Eskilstuna", "Västerås"], key="q_search_branch")
        q_query = st.text_input("Sök på namn, telefon eller modell:", key="q_search_input")
        
        saved_quotes = store.search_quotes(q_query, branch=q_search_branch)
        if saved_quotes:
            st.dataframe(saved_quotes, use_container_width=True)
            
            st.markdown("#### Skriv ut sparat förslag")
            selected_quote_id = st.selectbox("Välj Förslag ID att skriva ut", [q["id"] for q in saved_quotes], key="sel_q_id")
            chosen_q = next((q for q in saved_quotes if q["id"] == selected_quote_id), None)
            
            if chosen_q:
                q_pdf = generate_quote_pdf_bytes(chosen_q)
                st.download_button(
                    label="📥 Ladda ner PDF (Personal)",
                    data=q_pdf,
                    file_name=f"Kostnadsforslag_{chosen_q['customer_name'].replace(' ', '_')}.pdf",
                    mime="application/pdf",
                    key="dl_saved_quote"
                )
                employee_print_button()
        else:
            st.info("Inga sparade kostnadsförslag hittades.")

# TAB 3: Faktura
with tab3:
    st.header("📄 Skapa faktura")
    st.write("Fyll i fakturauppgifterna nedan för att generera och ladda ner en professionell PDF-faktura:")
    
    inv_no = st.text_input("Fakturanummer", value="1001", key="inv_no")
    inv_date = st.date_input("Fakturadatum", value=datetime.now(), key="inv_date")
    due_date = st.date_input("Förfallodatum", value=datetime.now() + timedelta(days=30), key="due_date")
    
    c1, c2 = st.columns(2)
    with c1:
        cust_name = st.text_input("Kundnamn / Företag", key="inv_cname")
        cust_addr = st.text_input("Adress", key="inv_caddr")
    with c2:
        cust_phone = st.text_input("Telefonnummer", key="inv_cphone")
        cust_email = st.text_input("E-post", key="inv_cemail")
        
    st.markdown("#### Artiklar / Produkter / Tjänster")
    item_desc = st.text_input("Beskrivning", value="Reparation och reservdel", key="inv_idesc")
    item_qty = st.number_input("Antal", min_value=1.0, value=1.0, key="inv_iqty")
    item_price = st.number_input("À-pris (SEK exkl. moms)", min_value=0.0, value=1000.0, key="inv_iprice")
    item_vat = st.selectbox("Moms %", [25.0, 12.0, 6.0, 0.0], key="inv_ivat")
    
    if st.button("📄 Generera Faktura PDF", type="primary", key="btn_inv"):
        invoice_payload = {
            "invoice_no": inv_no,
            "invoice_date": inv_date.strftime('%Y-%m-%d'),
            "due_date": due_date.strftime('%Y-%m-%d'),
            "customer_name": cust_name or "Kontantkund",
            "customer_address": cust_addr,
            "customer_phone": cust_phone,
            "customer_email": cust_email,
            "items": [{"code": "1", "desc": item_desc, "qty": item_qty, "price": item_price, "vat": item_vat}]
        }
        inv_pdf = generate_invoice_pdf_bytes(invoice_payload)
        st.download_button(
            label="📥 Ladda ner Faktura PDF",
            data=inv_pdf,
            file_name=f"Faktura_{inv_no}.pdf",
            mime="application/pdf"
        )

# TAB 4: Sök Ärenden (Protected View & Secure Delete Action)
with tab4:
    st.header("🔍 Sök Serviceärenden")
    
    if not st.session_state.get("authenticated", False):
        st.warning("🔒 Åtkomst nekad: Du måste logga in i sidomenyn till vänster med Personal-PIN för att se kundregistret.")
    else:
        search_branch_filter = st.selectbox("Filtrera efter Butik", ["Alla", "Eskilstuna", "Västerås"], key="search_branch_filter")
        search_query = st.text_input("Sök på kundnamn, telefonnummer, modell eller ärende-ID:", key="search_query_input")
        
        saved_cases = store.search_cases(search_query, branch=search_branch_filter)
        
        if saved_cases:
            st.write(f"Hittade {len(saved_cases)} ärenden:")
            for case in saved_cases:
                with st.expander(f"Ärende #{case['id']} - {case['first_name']} {case['last_name']} ({case['model']}) - Status: {case.get('status', 'Inlämnad')}"):
                    st.write(f"**Telefon:** {case.get('phone')} | **E-post:** {case.get('email', 'Ej angivet')}")
                    st.write(f"**Butik:** {case.get('branch')} | **Datum:** {case.get('created_at', 'Ej angivet')}")
                    st.write(f"**Felbeskrivning:** {case.get('issue_description')}")
                    
                    receipt_pdf = generate_receipt_pdf_bytes(case)
                    st.download_button(
                        label=f"📥 Ladda ner Kvitto PDF (Ärende #{case['id']})",
                        data=receipt_pdf,
                        file_name=f"Kvitto_Arende_{case['id']}.pdf",
                        mime="application/pdf",
                        key=f"dl_receipt_{case['id']}"
                    )
                    
                    st.markdown("---")
                    st.markdown("##### 🗑️ Radera Ärende (Kräver Raderingskod)")
                    entered_del_pin = st.text_input(f"Ange raderingskod för ärende #{case['id']}:", type="password", key=f"del_pin_{case['id']}")
                    if st.button(f"Radera Ärende #{case['id']} permanent", key=f"btn_del_{case['id']}", type="primary"):
                        if entered_del_pin == DELETE_ACTION_PIN:
                            with sqlite3.connect(store.local_db_path) as conn:
                                cursor = conn.cursor()
                                cursor.execute("DELETE FROM service_cases WHERE id = ?", (case['id'],))
                                conn.commit()
                            if store.client:
                                try:
                                    store.client.table("service_cases").delete().eq("id", case['id']).execute()
                                except Exception:
                                    pass
                            st.success(f"✅ Ärende #{case['id']} har raderats permanent!")
                            st.rerun()
                        else:
                            st.error("❌ Felaktig raderingskod!")
        else:
            st.info("Inga ärenden hittades.")

# TAB 5: Pre-Orders
with tab5:
    st.header("🛒 Gör en Förbeställning (Pre-Order)")
    st.write("Fyll i uppgifterna nedan för att förbeställa en reservdel eller tillbehör:")
    
    po_branch = st.selectbox("Välj Butik / Plats *", ["Eskilstuna", "Västerås"], key="po_branch")
    po_fn = st.text_input("Förnamn *", key="po_fn")
    po_ln = st.text_input("Efternamn *", key="po_ln")
    po_phone = st.text_input("Telefonnummer *", key="po_phone")
    part_model = st.text_input("Del / Modell / Artikel * (ex. Skärm iPhone 14)", key="po_part")
    deposit = st.number_input("Handpenning / Deposit (SEK)", min_value=0.0, step=50.0, key="po_dep")

    if st.button("💾 Skicka Förbeställning", key="btn_po", type="primary"):
        if not po_fn or not po_phone or not part_model:
            st.warning("⚠️ Fyll i förnamn, telefonnummer och del/modell.")
        else:
            store.create_pre_order({
                "first_name": po_fn, "last_name": po_ln,
                "phone": po_phone, "part_model": part_model,
                "deposit": deposit, "branch": po_branch
            })
            st.success("✅ Förbeställning har sparats i databasen och skickats till butiken!")

# TAB 6: Abonnemang & Glasskyddsavtal
with tab6:
    st.header("💳 Hantera Kundabonnemang (Service- & Glasskyddsavtal)")
    st.write("Skapa och hantera månadsprenumerationer för kunder (t.ex. skärmskydd eller återkommande reparationer till rabatterat pris).")
    
    ab_branch = st.selectbox("Välj Butik / Plats *", ["Eskilstuna", "Västerås"], key="ab_branch")
    
    col_ab1, col_ab2 = st.columns(2)
    with col_ab1:
        ab_fn = st.text_input("Förnamn *", key="ab_fn")
        ab_ln = st.text_input("Efternamn *", key="ab_ln")
        ab_phone = st.text_input("Telefonnummer * (Unikt ID)", key="ab_phone")
    with col_ab2:
        ab_email = st.text_input("E-post", key="ab_email")
        ab_model = st.text_input("Enhet / Modell (ex. iPhone 13 Pro)", key="ab_model")
        ab_type = st.selectbox("Typ av Abonnemang", [
            "Glasskyddsavtal (49 SEK/mån - Obegränsat byte vid stöt)", 
            "Service- & Reparationsabonnemang (99 SEK/mån - Specialpris på delar)"
        ], key="ab_type")

    col_p1, col_p2 = st.columns(2)
    with col_p1:
        initial_part_cost = st.number_input("Första betalning / Delkostnad (SEK)", min_value=0.0, value=1000.0, step=50.0, key="ab_init_cost")
    with col_p2:
        monthly_fee = st.number_input("Månadsavgift (SEK / månad)", min_value=0.0, value=49.0, step=10.0, key="ab_monthly_fee")

    if st.button("💾 Registrera Nytt Abonnemang", type="primary", key="btn_save_ab"):
        if not ab_fn or not ab_phone or not ab_model:
            st.warning("⚠️ Fyll i förnamn, telefonnummer och modell.")
        else:
            with sqlite3.connect(store.local_db_path) as conn:
                conn.execute("""
                    INSERT INTO customer_subscriptions (first_name, last_name, phone, email, model, sub_type, initial_paid, monthly_fee, status, branch)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (ab_fn, ab_ln, ab_phone, ab_email, ab_model, ab_type, initial_part_cost, monthly_fee, "Aktiv", ab_branch))
                conn.commit()
            st.success(f"✅ Abonnemang har registrerats för {ab_fn} {ab_ln}! Första betalning: {initial_part_cost} SEK, Månadsavgift: {monthly_fee} SEK/mån.")

    if st.session_state.get("authenticated", False):
        st.markdown("---")
        st.subheader("🔒 Personalvy: Aktiva Abonnemang i Systemet")
        try:
            with sqlite3.connect(store.local_db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM customer_subscriptions ORDER BY id DESC")
                subs = [dict(row) for row in cursor.fetchall()]
                if subs:
                    st.dataframe(subs, use_container_width=True)
                else:
                    st.info("Inga aktiva abonnemang hittades.")
        except Exception:
            st.info("Inga abonnemang registrerade än.")
