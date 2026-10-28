import streamlit as st
import sqlite3
import os
from datetime import datetime, date
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import io
import pandas as pd
import requests
import base64

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
                    status TEXT, created_at TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    branch TEXT, customer_name TEXT, phone TEXT,
                    device TEXT, imei TEXT, plan_type TEXT,
                    price REAL, start_date TEXT, created_at TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS preorders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    branch TEXT, customer_name TEXT, phone TEXT,
                    item_details TEXT, deposit REAL, created_at TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS quotes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    branch TEXT, customer_name TEXT, phone TEXT, email TEXT,
                    device TEXT, issues TEXT, total REAL, created_at TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS invoices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    branch TEXT, customer_name TEXT, phone TEXT, email TEXT, invoice_no TEXT,
                    amount REAL, moms REAL, created_at TEXT
                )
            """)
            try:
                conn.execute("ALTER TABLE quotes ADD COLUMN email TEXT")
            except Exception:
                pass
            try:
                conn.execute("ALTER TABLE invoices ADD COLUMN email TEXT")
            except Exception:
                pass
            return
        except Exception:
            pass

    # SQLite initialization fallback & migration
    conn = sqlite3.connect("local_crm.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS repairs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            branch TEXT, customer_name TEXT, phone TEXT, email TEXT,
            device TEXT, imei TEXT, issue TEXT, price REAL,
            status TEXT, created_at TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            branch TEXT, customer_name TEXT, phone TEXT,
            device TEXT, imei TEXT, plan_type TEXT,
            price REAL, start_date TEXT, created_at TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS preorders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            branch TEXT, customer_name TEXT, phone TEXT,
            item_details TEXT, deposit REAL, created_at TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS quotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            branch TEXT, customer_name TEXT, phone TEXT, email TEXT,
            device TEXT, issues TEXT, total REAL, created_at TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            branch TEXT, customer_name TEXT, phone TEXT, email TEXT, invoice_no TEXT,
            amount REAL, moms REAL, created_at TEXT
        )
    """)
    
    try:
        cursor.execute("ALTER TABLE quotes ADD COLUMN email TEXT")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE invoices ADD COLUMN email TEXT")
    except Exception:
        pass
        
    conn.commit()
    conn.close()

init_db()

# --- Direct Email Sender via Resend API ---
def send_email_with_attachment(receiver_email, subject, body, pdf_buffer=None, filename="document.pdf"):
    api_key = "re_EUnVDsTT_3QZr3adGSQY9vEdSjTYc1b2h"
    sender_email = st.secrets.get("EMAIL_SENDER", "info@30minutesphonefix.se")
    
    try:
        url = "https://api.resend.com/emails"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "from": f"30 Minutes Phone Fix <{sender_email}>",
            "to": [receiver_email],
            "subject": subject,
            "text": body
        }
        
        if pdf_buffer is not None:
            pdf_buffer.seek(0)
            pdf_bytes = pdf_buffer.read()
            encoded_file = base64.b64encode(pdf_bytes).decode('utf-8')
            payload["attachments"] = [
                {
                    "filename": filename,
                    "content": encoded_file
                }
            ]
            
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        
        if response.status_code == 200 or response.status_code == 201:
            return True
        else:
            st.error(f"❌ E-postfel från Resend API: {response.text}")
            return False
    except requests.exceptions.Timeout:
        st.error("❌ Anslutningen till Resend API tog för lång tid (Timeout).")
        return False
    except Exception as e:
        st.error(f"❌ Fel vid direkt e-postutskick: {e}")
        return False

# Page Configuration & Mobile UI Setup
st.set_page_config(page_title="30 Minutes Phone Fix CRM", layout="wide", page_icon="📱")

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

# --- Sidebar Branding with Logo ---
st.sidebar.title("30 MINUTES PHONE FIX")
if os.path.exists("logo.png"):
    st.sidebar.image("logo.png", use_container_width=True) #[cite: 1]
st.sidebar.markdown("**Eskilstuna & Västerås**")
st.sidebar.markdown("---")

# Persistent Session Login State
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

if not st.session_state['authenticated']:
    try:
        default_pin = st.secrets.get("DELETE_PIN", "tunapark")
    except Exception:
        default_pin = "tunapark"
        
    sidebar_pin = st.sidebar.text_input("🔑 System Login / Inloggning", type="password")
    if sidebar_pin == default_pin:
        st.session_state['authenticated'] = True
        st.sidebar.success("✅ System Unlocked / Systemet upplåst")
        st.rerun()
    elif sidebar_pin:
        st.sidebar.error("❌ Fel PIN-kod / Incorrect PIN")

if not st.session_state['authenticated']:
    st.title("🔒 30 Minutes Phone Fix CRM - Locked / Låst")
    st.info("Please enter the system PIN in the sidebar to log in. / Ange PIN-kod i sidofältet för att logga in.")
    st.stop()

st.sidebar.success("✅ Logged In / Inloggad")
if st.sidebar.button("🔒 Log Out / Logga ut"):
    st.session_state['authenticated'] = False
    st.rerun()

menu = st.sidebar.radio("Navigation / Meny", [
    "📝 Nytt Ärende / New Repair", 
    "💡 Kostnadsförslag / Quote", 
    "📄 Faktura / Invoice", 
    "🛒 Förbeställning / Pre-order", 
    "💳 Abonnemang / Subscriptions",
    "📤 E-post Utskick & Historik / Email Hub & History",
    "📊 Data Center & Sök / All Data & Search"
])

# --- 1. NYTT ÄRENDE / NEW REPAIR ---
if menu == "📝 Nytt Ärende / New Repair":
    st.header("📝 Registrera nytt ärende / Register New Repair")
    branch = st.selectbox("Välj Butik / Select Branch", ["Eskilstuna", "Västerås"])
    
    c_name = st.text_input("Kundens namn / Customer Name")
    c_phone = st.text_input("Telefonnummer / Phone Number")
    c_email = st.text_input("E-post / Email (Valfritt / Optional)")
    device = st.text_input("Enhet / Modell / Device Model")
    imei = st.text_input("IMEI / Serienummer / IMEI / Serial Number")
    price = st.number_input("Pris (Kr) / Price", min_value=0.0, step=50.0)
    issue = st.text_area("Beskrivning av fel / Issue Description")
    
    if st.button("Spara Ärende / Save Repair", type="primary"):
        if c_name and c_phone and device:
            conn, db_type = get_db_connection()
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            status = "Under behandling / In Progress"
            
            try:
                if db_type == "turso":
                    try:
                        conn.execute(
                            "INSERT INTO repairs (branch, customer_name, phone, email, device, imei, issue, price, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (branch, c_name, c_phone, c_email, device, imei, issue, price, status, created_at)
                        )
                    except Exception:
                        local_conn = sqlite3.connect("local_crm.db", check_same_thread=False)
                        local_cursor = local_conn.cursor()
                        local_cursor.execute(
                            "INSERT INTO repairs (branch, customer_name, phone, email, device, imei, issue, price, status, created_at
