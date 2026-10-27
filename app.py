import streamlit as st
import sqlite3
import os
from datetime import datetime, date
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import io
import pandas as pd

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
        conn.execute("""
            CREATE TABLE IF NOT EXISTS quotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                branch TEXT, customer_name TEXT, phone TEXT,
                device TEXT, issues TEXT, total REAL, created_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                branch TEXT, customer_name TEXT, invoice_no TEXT,
                amount REAL, moms REAL, created_at TEXT
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
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                branch TEXT, customer_name TEXT, phone TEXT,
                device TEXT, issues TEXT, total REAL, created_at TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                branch TEXT, customer_name TEXT, invoice_no TEXT,
                amount REAL, moms REAL, created_at TEXT
            )
        """)
        conn.commit()
        conn.close()

init_db()

# Page Configuration & Mobile UI Setup
st.set_page_config(page_title="30 Minutes Fix CRM", layout="wide", page_icon="📱")

COMPANY_INFO = {
    "Eskilstuna": {
        "name": "30 MINUTES FIX AB",
        "address": "Gunborg Nymans Väg 2, Eskilstuna",
        "phone": "0700122444",
        "org_nr": "5593708034",
        "swish": "123 407 16 76",
        "bankgiro": "5837-0354"
    },
    "Västerås": {
        "name": "30 MINUTES FIX AB",
        "address": "Västerås",
        "phone": "0700122444",
        "org_nr": "559537-1724",
        "swish": "123 339 15 47",
        "bankgiro": "5837-0354"
    }
}

st.sidebar.title("30 MINUTES FIX AB")
st.sidebar.markdown("**Eskilstuna & Västerås**")
st.sidebar.markdown("---")

# Persistent Session Login State
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

if not st.session_state['authenticated']:
    sidebar_pin = st.sidebar.text_input("🔑 System Login / Inloggning", type="password")
    if sidebar_pin == st.secrets.get("DELETE_PIN", "tunapark"):
        st.session_state['authenticated'] = True
        st.sidebar.success("✅ System Unlocked / Systemet upplåst")
        st.rerun()
    elif sidebar_pin:
        st.sidebar.error("❌ Fel PIN-kod / Incorrect PIN")

if not st.session_state['authenticated']:
    st.title("🔒 30 Minutes Fix CRM - Locked")
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
    "📊 Data Center & Sök / All Saved Data"
])

# --- 1. NYTT ÄRENDE / NEW REPAIR ---
if menu == "📝 Nytt Ärende / New Repair":
    st.header("📝 Registrera nytt ärende / Register Repair")
    branch = st.selectbox("Välj Butik / Select Branch", ["Eskilstuna", "Västerås"])
    
    c_name = st.text_input("Kundens namn / Customer Name")
    c_phone = st.text_input("Telefonnummer / Phone Number")
    c_email = st.text_input("E-post / Email (Optional)")
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
                st.success("✅ Ärendet har sparats i molnet! / Saved to cloud!")
            except Exception as e:
                st.error(f"❌ Fel: {e}")
        else:
            st.warning("⚠️ Fyll i obligatoriska fält. / Fill required fields.")

# --- 2. KOSTNADSFÖRSLAG / QUOTE ---
elif menu == "💡 Kostnadsförslag / Quote":
    st.header("💡 Kostnadsförslag / Price Quotation")
    branch = st.selectbox("Välj Butik / Branch", ["Eskilstuna", "Västerås"])
    comp = COMPANY_INFO[branch]
    
    c_name = st.text_input("Kundens namn / Customer Name")
    c_phone = st.text_input("Telefonnummer / Phone Number")
    device = st.text_input("Enhet / Modell / Device Model (t.ex. iPhone 15, MacBook Pro)")
    imei = st.text_input("IMEI / Serienummer (Valfritt)")

    st.markdown("---")
    st.subheader("🛠️ Välj Fel / Reparationer (Mobil, Laptop & Elektronik)")
    
    issues_list = []
    total_price = 0.0

    col_q1, col_q2 = st.columns(2)
    
    with col_q1:
        st.markdown("**📱 Mobil & Plattor / Phones & Tablets**")
        has_screen = st.checkbox("📱 Skärmbyte / Damaged Screen")
        if has_screen:
            p_screen = st.number_input("Pris: Skärmbyte (Kr)", min_value=0.0, step=50.0, value=0.0, key="p_scr")
            issues_list.append(f"Skärmbyte: {p_screen} Kr")
            total_price += p_screen

        has_backglass = st.checkbox("📱 Baksida kraschad / Back Glass Damaged")
        if has_backglass:
            p_backglass = st.number_input("Pris: Baksida (Kr)", min_value=0.0, step=50.0, value=0.0, key="p_bg")
            issues_list.append(f"Baksida kraschad: {p_backglass} Kr")
            total_price += p_backglass

        has_water = st.checkbox("💧 Vattenskada / Water Damage")
        if has_water:
            p_water = st.number_input("Pris: Vattenskada (Kr)", min_value=0.0, step=50.0, value=0.0, key="p_wat")
            issues_list.append(f"Vattenskada: {p_water} Kr")
            total_price += p_water

        has_battery = st.checkbox("🔋 Batteriproblem / Battery Replacement")
        if has_battery:
            p_battery = st.number_input("Pris: Batteri (Kr)", min_value=0.0, step=50.0, value=0.0, key="p_bat")
            issues_list.append(f"Batteribyte: {p_battery} Kr")
            total_price += p_battery

        has_charging = st.checkbox("🔌 Laddport / Charging Port Issue")
        if has_charging:
            p_charging = st.number_input("Pris: Laddport (Kr)", min_value=0.0, step=50.0, value=0.0, key="p_chg")
            issues_list.append(f"Laddport reparation: {p_charging} Kr")
            total_price += p_charging

        has_cam = st.checkbox("📷 Kameraproblem / Camera Repair")
        if has_cam:
            p_cam = st.number_input("Pris: Kamera (Kr)", min_value=0.0, step=50.0, value=0.0, key="p_cam")
            issues_list.append(f"Kamerabyte/reparation: {p_cam} Kr")
            total_price += p_cam

    with col_q2:
        st.markdown("**💻 Laptop & Övrig Elektronik / Laptop & Electronics**")
        has_laptopscreen = st.checkbox("💻 Laptop Skärmbyte / Laptop Screen")
        if has_laptopscreen:
            p_lapscreen = st.number_input("Pris: Laptop Skärm (Kr)", min_value=0.0, step=50.0, value=0.0, key="p_lscr")
            issues_list.append(f"Laptop Skärmbyte: {p_lapscreen} Kr")
            total_price += p_lapscreen

        has_keyboard = st.checkbox("⌨️ Tangentbord / Keyboard Problem")
        if has_keyboard:
            p_keyboard = st.number_input("Pris: Tangentbord (Kr)", min_value=0.0, step=50.0, value=0.0, key="p_key")
            issues_list.append(f"Tangentbordbyte: {p_keyboard} Kr")
            total_price += p_keyboard

        has_software = st.checkbox("⚙️ Mjukvara & OS / Software & Virus Help")
        if has_software:
            p_software = st.number_input("Pris: Mjukvara (Kr)", min_value=0.0, step=50.0, value=0.0, key="p_sof")
            issues_list.append(f"Mjukvara / OS installation: {p_software} Kr")
            total_price += p_software

        has_cleaning = st.checkbox("🧹 Rengöring & Fläkt / Cleaning & Fan Service")
        if has_cleaning:
            p_cleaning = st.number_input("Pris: Rengöring (Kr)", min_value=0.0, step=50.0, value=0.0, key="p_cln")
            issues_list.append(f"Datorrengöring / Fläkt: {p_cleaning} Kr")
            total_price += p_cleaning

    custom_issue = st.text_input("Övrigt fel / Annan elektronik (Valfritt / Custom)")
    if custom_issue:
        p_custom = st.number_input("Pris för övrigt (Kr)", min_value=0.0, step=50.0, value=0.0, key="p_cust")
        issues_list.append(f"{custom_issue}: {p_custom} Kr")
        total_price += p_custom

    st.markdown("---")
    st.markdown(f"### 💰 **Total Summa / Final Total: {total_price:.2f} Kr (inkl. moms)**")
    st.info("📜 *Detta kostnadsförslag gäller endast i vår verkstad (This quote is valid only in our workshop).*")

    if st.button("Spara & Generera PDF Kostnadsförslag", type="primary"):
        if c_name and device and issues_list:
            conn, db_type = get_db_connection()
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            issues_str = ", ".join(issues_list)
            
            try:
                if db_type == "turso":
                    conn.execute(
                        "INSERT INTO quotes (branch, customer_name, phone, device, issues, total, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (branch, c_name, c_phone, device, issues_str, total_price, created_at)
                    )
                else:
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO quotes (branch, customer_name, phone, device, issues, total, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (branch, c_name, c_phone, device, issues_str, total_price, created_at)
                    )
                    conn.commit()
                    conn.close()
                st.success("✅ Kostnadsförslag sparat i molnet! / Saved to cloud!")
            except Exception as e:
                st.error(f"❌ Fel: {e}")

            buffer = io.BytesIO()
            p = canvas.Canvas(buffer, pagesize=A4)
            p.drawString(50, 800, comp["name"])
            p.drawString(50, 785, f"Adress: {comp['address']} | Tel: {comp['phone']}")
            p.drawString(50, 770, f"Org.nr: {comp['org_nr']}")
            p.drawString(50, 750, "--------------------------------------------------------")
            p.drawString(50, 730, "KOSTNADSFÖRSLAG / PRICE QUOTATION")
            p.drawString(50, 710, f"Datum: {date.today().strftime('%Y-%m-%d')}")
            p.drawString(50, 690, f"Kund: {c_name} | Tel: {c_phone}")
            p.drawString(50, 670, f"Enhet: {device} | IMEI/Serienr: {imei}")
            p.drawString(50, 650, "--------------------------------------------------------")
            
            y_pos = 620
            for item in issues_list:
                p.drawString(70, y_pos, f"- {item}")
                y_pos -= 25
            
            y_pos -= 20
            p.drawString(50, y_pos, f"TOTAL SUMMA / TOTAL: {total_price:.2f} Kr (inkl. moms)")
            y_pos -= 30
            p.drawString(50, y_pos, "* Detta kostnadsförslag gäller endast i vår verkstad.")
            
            p.showPage()
            p.save()
            buffer.seek(0)
            st.download_button("📥 Ladda ner PDF / Download PDF", buffer, file_name="kostnadsforslag.pdf", mime="application/pdf")
        else:
            st.warning("⚠️ Fyll i obligatoriska fält och välj minst ett fel. / Fill required fields.")

# --- 3. FAKTURA / INVOICE ---
elif menu == "📄 Faktura / Invoice":
    st.header("📄 Professionell Faktura / Professional Invoice")
    branch = st.selectbox("Välj Företagsfilial / Select Branch", ["Eskilstuna", "Västerås"])
    comp = COMPANY_INFO[branch]
    
    st.info(f"""
    🏢 **Företagsuppgifter ({branch}):**
    * **Företag:** {comp['name']}
    * **Adress:** {comp['address']}
    * **Telefon:** {comp['phone']} | **Org.nr:** {comp['org_nr']}
    * **Swish:** {comp['swish']} | **Bankgiro:** {comp['bankgiro']}
    """)

    st.markdown("---")
    st.subheader("👤 Kunduppgifter / Customer Info")
    f_name = st.text_input("Företag / Kundens namn / Company or Customer Name")
    f_org = st.text_input("Org.nr / Personnummer (Optional)")
    f_address = st.text_input("Adress / Address")
    invoice_no = st.text_input("Fakturanummer / Invoice No.", value="FAK-2026-001")
    invoice_date = st.date_input("Fakturadatum / Invoice Date", value=date.today())
    due_date = st.date_input("Förfallodatum / Due Date", value=date.today())

    st.markdown("---")
    st.subheader("🛒 Artikel & Pris / Item & Price")
    item_desc = st.text_input("Beskrivning / Description", value="Reparation och reservdelar / Repair & Parts")
    item_qty = st.number_input("Antal / Quantity", min_value=1, value=1)
    item_price = st.number_input("Pris per enhet inkl. moms (Kr)", min_value=0.0, step=50.0)
    
    total_amount = item_qty * item_price
    moms = total_amount * 0.20
    netto = total_amount - moms
    
    st.markdown(f"""
    ### 📊 Sammanfattning / Summary:
    * **Netto (exkl. moms):** {netto:.2f} Kr
    * **Moms (25%):** {moms:.2f} Kr
    * **Att betala / Total Summa:** **{total_amount:.2f} Kr**
    """)
    st.markdown(f"💳 **Betalningsmetod:** Swish: `{comp['swish']}` | Bankgiro: `{comp['bankgiro']}`")
    
    if st.button("Spara & Skapa Faktura PDF", type="primary"):
        if f_name:
            conn, db_type = get_db_connection()
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            try:
                if db_type == "turso":
                    conn.execute(
                        "INSERT INTO invoices (branch, customer_name, invoice_no, amount, moms, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                        (branch, f_name, invoice_no, total_amount, moms, created_at)
                    )
                else:
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO invoices (branch, customer_name, invoice_no, amount, moms, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                        (branch, f_name, invoice_no, total_amount, moms, created_at)
                    )
                    conn.commit()
                    conn.close()
                st.success("✅ Faktura sparad i molnet! / Saved to cloud!")
            except Exception as e:
                st.error(f"❌ Fel: {e}")

            buffer = io.BytesIO()
            p = canvas.Canvas(buffer, pagesize=A4)
            p.drawString(50, 800, comp["name"])
            p.drawString(50, 785, f"Adress: {comp['address']}")
            p.drawString(50, 770, f"Tel: {comp['phone']} | Org.nr: {comp['org_nr']}")
            p.drawString(50, 750, "--------------------------------------------------------")
            p.drawString(50, 730, "FAKTURA / INVOICE")
            p.drawString(50, 710, f"Fakturanr: {invoice_no} | Datum: {invoice_date} | Förfallodag: {due_date}")
            p.drawString(50, 690, f"Kund: {f_name} | Adress: {f_address}")
            p.drawString(50, 670, "--------------------------------------------------------")
            p.drawString(50, 640, f"Beskrivning: {item_desc} (Antal: {item_qty})")
            p.drawString(50, 610, f"Netto: {netto:.2f} Kr | Moms (25%): {moms:.2f} Kr")
            p.drawString(50, 580, f"Att betala Totalt / Total: {total_amount:.2f} Kr")
            p.drawString(50, 540, f"Betalning via Swish: {comp['swish']} eller Bankgiro: {comp['bankgiro']}")
            
            p.showPage()
            p.save()
            buffer.seek(0)
            st.download_button("📥 Ladda ner Faktura PDF", buffer, file_name=f"{invoice_no}.pdf", mime="application/pdf")
        else:
            st.warning("⚠️ Ange kundens namn. / Enter customer name.")

# --- 4. FÖRBESTÄLLNING / PRE-ORDER ---
elif menu == "🛒 Förbeställning / Pre-order":
    st.header("🛒 Förbeställning av reservdelar / Pre-order")
    branch = st.selectbox("Välj Butik / Branch", ["Eskilstuna", "Västerås"])
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
                        (branch, fb_name, fb_phone, fb_details, fb_deposit, created_at)
                    )
                else:
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO preorders (branch, customer_name, phone, item_details, deposit, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                        (branch, fb_name, fb_phone, fb_details, fb_deposit, created_at)
                    )
                    conn.commit()
                    conn.close()
                st.success("✅ Förbeställning sparad i molnet! / Saved to cloud!")
            except Exception as e:
                st.error(f"❌ Fel: {e}")
        else:
            st.warning("⚠️ Fyll i namn och telefon. / Fill name and phone.")

# --- 5. ABONNEMANG / SUBSCRIPTIONS ---
elif menu == "💳 Abonnemang / Subscriptions":
    st.header("💳 IMEI-kopplade Abonnemang / Subscriptions")
    
    sub_imei = st.text_input("IMEI-nummer (Unikt för enheten) / IMEI Number")
    sub_device = st.text_input("Enhet / Modell / Device Model (t.ex. iPhone 15)")
    branch = st.selectbox("Butik / Branch", ["Eskilstuna", "Västerås"])
    sub_name = st.text_input("Kundens namn / Customer Name")
    sub_phone = st.text_input("Telefonnummer / Phone Number")
    sub_email = st.text_input("E-post / Email (Valfritt)")

    st.markdown("---")
    plan_choice = st.selectbox("Välj Plan / Plan Type", [
        "Glass Protection Abonnemang (99 SEK/mån)",
        "Case / Cover Abonnemang (399 SEK start + 99 SEK/mån)",
        "Teknik, Mjukvara & Virus Help (99 SEK/mån)"
    ])
    
    if "Glass Protection" in plan_choice:
        sub_price = 99.0
        st.info("💡 **Glass Protection:** 99 Kr/mån | Byt skärmskydd 2 ggr/mån utan självrisk.")
    elif "Case / Cover" in plan_choice:
        sub_price = 99.0
        st.info("💡 **Case / Cover:** 399 Kr start + 99 Kr/mån | Byt kفر/غطاء 1 gång var 3:e månad.")
    else:
        sub_price = 99.0
        st.info("💡 **Teknik & Mjukvara:** 99 Kr/mån | Fri support och virusrensning.")

    st.markdown("---")
    st.info("""
    **Villkor:**
    1. Abonnemanget är strikt kopplat till enhetens **IMEI-nummer**.
    2. 3 månaders uppsägningstid gäller.
    """)
    
    agree_terms = st.checkbox("Kunden godkänner avtalsvillkoren / Customer accepts terms")

    if st.button("Spara Abonnemang / Save Subscription", type="primary"):
        if sub_imei and sub_name and agree_terms:
            conn, db_type = get_db_connection()
            start_date = datetime.now().strftime("%Y-%m-%d")
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            try:
                if db_type == "turso":
                    conn.execute(
                        "INSERT INTO subscriptions (branch, customer_name, phone, device, imei, plan_type, price, start_date, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (branch, sub_name, sub_phone, sub_device, sub_imei, plan_choice, sub_price, start_date, created_at)
                    )
                else:
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO subscriptions (branch, customer_name, phone, device, imei, plan_type, price, start_date, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (branch, sub_name, sub_phone, sub_device, sub_imei, plan_choice, sub_price, start_date, created_at)
                    )
                    conn.commit()
                    conn.close()
                st.success("✅ Abonnemanget har sparats i molnet! / Saved to cloud!")
            except Exception as e:
                st.error(f"❌ Fel: {e}")
        elif not sub_imei:
            st.warning("⚠️ IMEI-nummer krävs. / IMEI required.")
        elif not agree_terms:
            st.warning("⚠️ Godkänn villkoren. / Accept terms.")
        else:
            st.warning("⚠️ Fyll i kundens namn. / Enter name.")

# --- 6. DATA CENTER, SEARCH, EXPORT & DELETE ---
elif menu == "📊 Data Center & Sök / All Saved Data":
    st.header("📊 Data Center, Sök, Export & Hantering")
    st.markdown("Sök, exportera eller radera poster från molnet / Search, export, or delete cloud records:")
    
    search_category = st.selectbox("Välj Kategori / Select Category", [
        "📝 Reparationer / Repairs", 
        "💳 Abonnemang / Subscriptions", 
        "🛒 Förbeställningar / Pre-orders", 
        "💡 Kostnadsförslag / Quotes", 
        "📄 Fakturor / Invoices"
    ])
    
    search_term = st.text_input("🔎 Sök på Namn, Telefon eller IMEI / Search by Name, Phone, or IMEI", "").lower()
    
    conn, db_type = get_db_connection()
    
    # تحديد اسم الجدول بناءً على القئة المختارة
    table_map = {
        "📝 Reparationer / Repairs": "repairs",
        "💳 Abonnemang / Subscriptions": "subscriptions",
        "🛒 Förbeställningar / Pre-orders": "preorders",
        "💡 Kostnadsförslag / Quotes": "quotes",
        "📄 Fakturor / Invoices": "invoices"
    }
    
    current_table = table_map[search_category]
    
    if db_type == "turso":
        res = conn.execute(f"SELECT * FROM {current_table} ORDER BY id DESC")
        rows = res.fetchall()
        # تحويل النتائج إلى DataFrame لسهولة التصدير والعرض
        columns_res = conn.execute(f"PRAGMA table_info({current_table})").fetchall()
        col_names = [c[1] for c in columns_res]
        df = pd.DataFrame(rows, columns=col_names) if rows else pd.DataFrame()
    else:
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM {current_table} ORDER BY id DESC")
        rows = cursor.fetchall()
        col_names = [description[0] for description in cursor.description]
        df = pd.DataFrame(rows, columns=col_names) if rows else pd.DataFrame()
        conn.close()
        
    # فلترة النتائج حسب نص البحث
    if not df.empty and search_term:
        mask = df.astype(str).apply(lambda x: x.str.lower().str.contains(search_term).any(), axis=1)
        filtered_df = df[mask]
    else:
        filtered_df = df
        
    if not filtered_df.empty:
        st.markdown(f"### النتائج المطابقة ({len(filtered_df)} پستر):")
        st.dataframe(filtered_df, use_container_width=True)
        
        # --- خيارات التصدير (Export options) ---
        st.markdown("---")
        st.subheader("📥 Exportera Data / تصدير البيانات")
        col_ex1, col_ex2 = st.columns(2)
        
        with col_ex1:
            # تصدير كـ Excel (CSV)
            csv_data = filtered_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Ladda ner som Excel / CSV",
                data=csv_data,
                file_name=f"{current_table}_export.csv",
                mime="text/csv"
            )
            
        with col_ex2:
            # تصدير كـ PDF بسيط للجدول
            if st.button("📥 Generera PDF Export"):
                pdf_buffer = io.BytesIO()
                p = canvas.Canvas(pdf_buffer, pagesize=A4)
                p.drawString(50, 800, f"30 MINUTES FIX AB - Export: {search_category}")
                p.drawString(50, 780, f"Datum: {date.today().strftime('%Y-%m-%d')}")
                p.drawString(50, 760, "-------------------------------------------------------------------")
                
                y = 730
                for index, row in filtered_df.iterrows():
                    if y < 50:
                        p.showPage()
                        y = 800
                    row_text = f"ID: {row.iloc[0]} | Kund: {row.iloc[2] if len(row)>2 else ''} | Detalj: {row.iloc[3] if len(row)>3 else ''}"
                    p.drawString(50, y, str(row_text)[:90])
                    y -= 20
                
                p.save()
                pdf_buffer.seek(0)
                st.download_button(
                    label="📥 Ladda ner PDF Export",
                    data=pdf_buffer,
                    file_name=f"{current_table}_export.pdf",
                    mime="application/pdf"
                )

        # --- خيار الحذف (Delete option - محمي ولا يسمح بحذف Abonnemang أو Invoices) ---
        if current_table not in ["subscriptions", "invoices"]:
            st.markdown("---")
            st.subheader("🗑️ Radera Post / حذف عميل أو سجل")
            st.warning("⚠️ ملاحظة أمنية: لا يمكنك حذف الاشتراكات (Abonnemang) أو الفواتير (Fakturor) من هنا للحفاظ على العقود المالية.")
            
            del_id = st.number_input("Ange ID för posten som ska raderas / أدخل رقم الـ ID للحذف", min_value=1, step=1)
            del_pin = st.text_input("Ange PIN-kod för att radera / كلمة مرور الحذف", type="password", key="del_pin_input")
            
            if st.button("Radera permanent / حذف نهائي", type="primary"):
                if del_pin == st.secrets.get("DELETE_ACTION_PIN", "admin123"):
                    conn_del, dtype_del = get_db_connection()
                    try:
                        if dtype_del == "turso":
                            conn_del.execute(f"DELETE FROM {current_table} WHERE id = ?", (del_id,))
                        else:
                            cur_del = conn_del.cursor()
                            cur_del.execute(f"DELETE FROM {current_table} WHERE id = ?", (del_id,))
                            conn_del.commit()
                            conn_del.close()
                        st.success(f"✅ Posten med ID {del_id} har raderats! / تم حذف السجل بنجاح!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Fel vid radering: {e}")
                else:
                    st.error("❌ Fel PIN-kod för radering! / كلمة المرور غير صحيحة!")
        else:
            st.markdown("---")
            st.info("🔒 **حماية أمنية:** قسم الاشتراكات والفواتير محمي بالكامل ولا يمكن حذف سجلاته نهائياً من لوحة التحكم.")
            
    else:
        st.info("Inga poster hittades i denna kategori. / لا توجد سجلات مطابقة.")
