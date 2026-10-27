import streamlit as st
import sqlite3
import os
from datetime import datetime, date
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import io

# --- Turso Cloud Database Connection ---
import libsql_client

def get_db_connection():
    url = st.secrets.get("TURSO_DATABASE_URL")
    token = st.secrets.get("TURSO_AUTH_TOKEN")
    
    if url and token:
        try:
            conn = libsql_client.connect(url=url, auth_token=token)
            return conn, "turso"
        except Exception as e:
            st.error(f"⚠️ Turso DB Connection Error: {e}")
    
    conn = sqlite3.connect("local_crm.db", check_same_thread=False)
    return conn, "sqlite"

def init_db():
    conn, db_type = get_db_connection()
    if db_type == "turso":
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
    else:
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
        conn.commit()
        conn.close()

init_db()

# Page Configuration
st.set_page_config(page_title="30 Minutes Fix CRM", layout="wide", page_icon="📱")

st.sidebar.title("30 MINUTES FIX AB")
st.sidebar.markdown("**Eskilstuna & Västerås**")
st.sidebar.markdown("---")
menu = st.sidebar.radio("Navigation / القائمة", [
    "📝 Nytt Ärende / New Repair", 
    "💡 Kostnadsförslag / Quote", 
    "📄 Faktura / Invoice", 
    "🔍 Sök Ärenden / Search", 
    "🛒 Förbeställning / Pre-order", 
    "💳 Abonnemang / Subscriptions"
])

# --- 1. NYTT ÄRENDE / NEW REPAIR ---
if menu == "📝 Nytt Ärende / New Repair":
    st.header("📝 Registrera nytt ärende / Register New Repair")
    
    branch = st.selectbox("Välj Butik / Select Branch", ["Eskilstuna", "Västerås"])
    
    col1, col2 = st.columns(2)
    with col1:
        c_name = st.text_input("Kundens namn / Customer Name")
        c_phone = st.text_input("Telefonnummer / Phone Number")
        c_email = st.text_input("E-post / Email (Optional)")
    with col2:
        device = st.text_input("Enhet / Modell / Device Model")
        imei = st.text_input("IMEI / Serienummer / IMEI Number")
        price = st.number_input("Pris (Kr) / Price", min_value=0.0, step=50.0)

    issue = st.text_area("Beskrivning av fel / Issue Description")
    
    if st.button("Spara Ärende / Save Repair (Cloud)", type="primary"):
        if c_name and c_phone and device:
            conn, db_type = get_db_connection()
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            status = "Under behandling / In Progress"
            
            try:
                if db_type == "turso":
                    conn.execute(
                        "INSERT INTO repairs (branch, customer_name, phone, email, device, imei, issue, price, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (branch, c_name, c_phone, c_email, device, imei, issue, price, status, created_at)
                    )
                else:
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO repairs (branch, customer_name, phone, email, device, imei, issue, price, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (branch, c_name, c_phone, c_email, device, imei, issue, price, status, created_at)
                    )
                    conn.commit()
                    conn.close()
                st.success("✅ Ärendet har sparats i molndatabasen! / Saved successfully to Cloud!")
            except Exception as e:
                st.error(f"❌ Fel vid sparande / Error: {e}")
        else:
            st.warning("⚠️ Fyll i obligatoriska fält (Namn, Telefon, Enhet). / Please fill required fields.")

# --- 2. KOSTNADSFÖRSLAG / QUOTE ---
elif menu == "💡 Kostnadsförslag / Quote":
    st.header("💡 Kostnadsförslag / Price Quotation")
    c_name = st.text_input("Kundens namn / Customer Name")
    device = st.text_input("Enhet / Modell / Device")
    repair_type = st.text_input("Typ av reparation / Repair Type")
    cost = st.number_input("Uppskattad kostnad (Kr) / Estimated Cost", min_value=0.0, step=50.0)
    
    if st.button("Generera PDF Kostnadsförslag / Generate PDF Quote"):
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)
        p.drawString(100, 800, "30 MINUTES FIX AB - KOSTNADSFÖRSLAG")
        p.drawString(100, 770, f"Kund / Customer: {c_name}")
        p.drawString(100, 740, f"Enhet / Device: {device}")
        p.drawString(100, 710, f"Reparation / Repair: {repair_type}")
        p.drawString(100, 680, f"Kostnad / Cost: {cost} Kr")
        p.showPage()
        p.save()
        buffer.seek(0)
        st.success("✅ Kostnadsförslag PDF skapats! / Quote PDF generated!")
        st.download_button("📥 Ladda ner PDF / Download PDF", buffer, file_name="kostnadsforslag.pdf", mime="application/pdf")

# --- 3. FAKTURA / INVOICE ---
elif menu == "📄 Faktura / Invoice":
    st.header("📄 Skapa Faktura / Create Invoice")
    f_name = st.text_input("Företag / Kundens namn / Company / Customer Name")
    amount = st.number_input("Belopp inkl. moms (Kr) / Amount incl. VAT", min_value=0.0, step=100.0)
    moms = amount * 0.20
    netto = amount - moms
    st.info(f"💡 Moms (25%): {moms:.2f} Kr | Netto: {netto:.2f} Kr")
    
    if st.button("Skapa Faktura PDF / Create Invoice PDF"):
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)
        p.drawString(100, 800, "30 MINUTES FIX AB - FAKTURA")
        p.drawString(100, 770, f"Kund / Customer: {f_name}")
        p.drawString(100, 740, f"Total inkl. moms: {amount} Kr")
        p.drawString(100, 710, f"Swish: 123-XXX XXXX | Bankgiro: XXX-XXXX")
        p.showPage()
        p.save()
        buffer.seek(0)
        st.success("✅ Faktura PDF skapad! / Invoice PDF generated!")
        st.download_button("📥 Ladda ner Faktura PDF / Download Invoice PDF", buffer, file_name="faktura.pdf", mime="application/pdf")

# --- 4. SÖK ÄRENDEN / SEARCH ---
elif menu == "🔍 Sök Ärenden / Search":
    st.header("🔍 Sök och Hantera Ärenden / Search Repairs")
    pin = st.text_input("Ange PIN-kod / Enter PIN code", type="password")
    
    if pin == st.secrets.get("DELETE_PIN", "tunapark"):
        st.success("✅ Åtkomst beviljad / Access Granted")
        conn, db_type = get_db_connection()
        
        if db_type == "turso":
            res = conn.execute("SELECT * FROM repairs ORDER BY id DESC")
            rows = res.fetchall()
        else:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM repairs ORDER BY id DESC")
            rows = cursor.fetchall()
            conn.close()
            
        if rows:
            for r in rows:
                st.write(f"📌 **ID:** {r[0]} | **Branch:** {r[1]} | **Kund:** {r[2]} | **Tel:** {r[3]} | **Device:** {r[5]} | **IMEI:** {r[6]} | **Status:** {r[9]}")
        else:
            st.info("Inga ärenden hittades. / No repairs found.")
    elif pin:
        st.error("❌ Fel PIN-kod! / Incorrect PIN code!")

# --- 5. FÖRBESTÄLLNING / PRE-ORDER ---
elif menu == "🛒 Förbeställning / Pre-order":
    st.header("🛒 Förbeställning av reservdelar / Spare Parts Pre-order")
    fb_name = st.text_input("Kundens namn / Customer Name")
    fb_phone = st.text_input("Telefon / Phone")
    fb_details = st.text_area("Artikel / Delar detaljer / Part Details")
    fb_deposit = st.number_input("Handpenning / Deposit (Kr)", min_value=0.0, step=50.0)
    
    if st.button("Spara Förbeställning / Save Pre-order", type="primary"):
        if fb_name and fb_phone:
            conn, db_type = get_db_connection()
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            try:
                if db_type == "turso":
                    conn.execute(
                        "INSERT INTO preorders (branch, customer_name, phone, item_details, deposit, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                        ("Eskilstuna", fb_name, fb_phone, fb_details, fb_deposit, created_at)
                    )
                else:
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO preorders (branch, customer_name, phone, item_details, deposit, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                        ("Eskilstuna", fb_name, fb_phone, fb_details, fb_deposit, created_at)
                    )
                    conn.commit()
                    conn.close()
                st.success("✅ Förbeställning sparad i molnet! / Pre-order saved to cloud!")
            except Exception as e:
                st.error(f"❌ Fel / Error: {e}")
        else:
            st.warning("⚠️ Fyll i namn och telefon. / Fill name and phone.")

# --- 6. ABONNEMANG / SUBSCRIPTIONS ---
elif menu == "💳 Abonnemang / Subscriptions":
    st.header("💳 Hantera Abonnemang / Manage Subscriptions")
    
    sub_name = st.text_input("Kundens namn / Customer Name")
    sub_phone = st.text_input("Telefonnummer / Phone Number")
    sub_device = st.text_input("Enhet / Modell / Device")
    sub_imei = st.text_input("IMEI-nummer / IMEI Number")
    plan_type = st.selectbox("Välj Plan / Select Plan", ["GlassGuard Pro", "Case Protection", "Teknik Complete"])
    sub_price = st.number_input("Månadskostnad / Pris (Kr) / Monthly Price", min_value=0.0, step=49.0)
    
    if st.button("Spara Abonnemang / Save Subscription", type="primary"):
        if sub_name and sub_imei:
            conn, db_type = get_db_connection()
            start_date = datetime.now().strftime("%Y-%m-%d")
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            try:
                if db_type == "turso":
                    conn.execute(
                        "INSERT INTO subscriptions (branch, customer_name, phone, device, imei, plan_type, price, start_date, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        ("Eskilstuna", sub_name, sub_phone, sub_device, sub_imei, plan_type, sub_price, start_date, created_at)
                    )
                else:
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO subscriptions (branch, customer_name, phone, device, imei, plan_type, price, start_date, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        ("Eskilstuna", sub_name, sub_phone, sub_device, sub_imei, plan_type, sub_price, start_date, created_at)
                    )
                    conn.commit()
                    conn.close()
                st.success("✅ Abonnemang sparades i Turso molnet! / Subscription saved to Turso Cloud!")
            except Exception as e:
                st.error(f"❌ Fel / Error: {e}")
        else:
            st.warning("⚠️ Ange namn och IMEI. / Enter customer name and IMEI.")
            
    st.markdown("---")
    st.subheader("📋 Aktiva Abonnemang / Active Subscriptions")
    try:
        conn, db_type = get_db_connection()
        if db_type == "turso":
            res = conn.execute("SELECT * FROM subscriptions ORDER BY id DESC")
            sub_rows = res.fetchall()
        else:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM subscriptions ORDER BY id DESC")
            sub_rows = cursor.fetchall()
            conn.close()
            
        if sub_rows:
            for s in sub_rows:
                st.write(f"💳 **Kund:** {s[2]} | **Device:** {s[4]} | **IMEI:** {s[5]} | **Plan:** {s[6]} | **Pris:** {s[7]} Kr | **Datum:** {s[8]}")
        else:
            st.info("Inga aktiva abonnemang. / No active subscriptions found.")
    except Exception as e:
        st.warning(f"Laddar... / Loading...")
