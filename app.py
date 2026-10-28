import streamlit as st
import sqlite3
import os
from datetime import datetime, date
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import io
import pandas as pd
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
                    branch TEXT, customer_name TEXT, phone TEXT, invoice_no TEXT,
                    amount REAL, moms REAL, created_at TEXT
                )
            """)
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
            branch TEXT, customer_name TEXT, phone TEXT, invoice_no TEXT,
            amount REAL, moms REAL, created_at TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

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
    st.sidebar.image("logo.png", use_container_width=True)[cite: 1]
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
    "🖨️ Dokument & Historik / Print & History Hub",
    "📊 Data Center & Sök / All Data & Search"
])

# Stabil hjälpfunktion för nedladdning och utskrift via ny flik (undviker webbläsarblockeringar)
def display_pdf_preview(pdf_buffer, file_name="document.pdf"):
    pdf_buffer.seek(0)
    pdf_bytes = pdf_buffer.read()
    b64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
    pdf_data_url = f"data:application/pdf;base64,{b64_pdf}"
    
    st.success("✅ Dokumentet är klart!")
    
    col_dl, col_pr = st.columns(2)
    with col_dl:
        st.download_button(
            label="📥 Ladda ner PDF / Save PDF",
            data=pdf_bytes,
            file_name=file_name,
            mime="application/pdf",
            type="primary"
        )
    with col_pr:
        st.markdown(
            f"""
            <div style="margin-top: 2px;">
                <a href="{pdf_data_url}" target="_blank" style="background-color: #008CBA; color: white; padding: 10px 20px; text-align: center; text-decoration: none; display: inline-block; border-radius: 5px; font-weight: bold;">
                    🖨️ Öppna & Skriv ut / Print PDF
                </a>
            </div>
            """,
            unsafe_allow_html=True
        )

# Generera PDF på nytt för sparade objekt vid visning/utskrift
def generate_pdf_from_record(record_type, data, comp_info):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    
    if os.path.exists("logo.png"):
        try:
            p.drawImage("logo.png", 50, 750, width=80, height=40, preserveAspectRatio=True, mask='auto')[cite: 1]
        except Exception:
            pass
            
    branch = data.get('branch', 'Eskilstuna')
    comp = comp_info.get(branch, comp_info['Eskilstuna'])

    if record_type == "quote":
        p.drawString(140, 780, comp["name"])
        p.drawString(140, 765, f"Adress: {comp['address']} | Tel: {comp['phone']}")
        p.drawString(140, 750, f"Org.nr: {comp['org_nr']}")
        p.drawString(50, 735, "------------------------------------------------------------------------------------------------")
        p.drawString(50, 715, "KOSTNADSFÖRSLAG / PRICE QUOTATION")
        p.drawString(50, 695, f"Datum / Date: {data.get('created_at', '')}")
        p.drawString(50, 675, f"Kund / Customer: {data.get('customer_name', '')} | Tel: {data.get('phone', '')}")
        p.drawString(50, 655, f"Enhet / Device: {data.get('device', '')}")
        p.drawString(50, 635, "------------------------------------------------------------------------------------------------")
        
        p.drawString(70, 605, f"- {data.get('issues', '')}")
        p.drawString(50, 570, f"TOTAL SUMMA / TOTAL: {data.get('total', 0):.2f} Kr (inkl. moms)")
        p.drawString(50, 540, "* Detta kostnadsförslag gäller endast i vår verkstad.")

    elif record_type == "invoice":
        p.drawString(140, 780, comp["name"])
        p.drawString(140, 765, f"Adress: {comp['address']}")
        p.drawString(140, 750, f"Tel: {comp['phone']} | Org.nr: {comp['org_nr']}")
        p.drawString(50, 735, "------------------------------------------------------------------------------------------------")
        p.drawString(50, 715, "FAKTURA / INVOICE")
        p.drawString(50, 695, f"Fakturanr / Invoice No: {data.get('invoice_no', '')} | Datum / Date: {data.get('created_at', '')}")
        p.drawString(50, 675, f"Kund / Customer: {data.get('customer_name', '')} | Tel: {data.get('phone', '')}")
        p.drawString(50, 655, "------------------------------------------------------------------------------------------------")
        p.drawString(50, 625, f"Att betala Totalt / Total: {data.get('amount', 0):.2f} Kr (inkl. moms)")
        p.drawString(50, 595, f"Moms (25%): {data.get('moms', 0):.2f} Kr")
        p.drawString(50, 555, f"Betalning via Swish: {comp['swish']} eller Bankgiro: {comp['bankgiro']}")

    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

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
                            "INSERT INTO repairs (branch, customer_name, phone, email, device, imei, issue, price, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (branch, c_name, c_phone, c_email, device, imei, issue, price, status, created_at)
                        )
                        local_conn.commit()
                        local_conn.close()
                else:
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO repairs (branch, customer_name, phone, email, device, imei, issue, price, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (branch, c_name, c_phone, c_email, device, imei, issue, price, status, created_at)
                    )
                    conn.commit()
                    conn.close()
                st.success("✅ Ärendet har sparats! / Repair saved successfully!")
            except Exception as e:
                st.error(f"❌ Fel vid sparande / Error: {e}")
        else:
            st.warning("⚠️ Fyll i obligatoriska fält (Namn, Telefon, Enhet). / Please fill required fields.")

# --- 2. KOSTNADSFÖRSLAG / QUOTE ---
elif menu == "💡 Kostnadsförslag / Quote":
    st.header("💡 Kostnadsförslag / Price Quotation")
    branch = st.selectbox("Välj Butik / Branch", ["Eskilstuna", "Västerås"])
    comp = COMPANY_INFO[branch]
    
    c_name = st.text_input("Kundens namn / Customer Name")
    c_phone = st.text_input("Telefonnummer / Phone Number")
    device = st.text_input("Enhet / Modell / Device Model (t.ex. iPhone 15, MacBook Pro)")
    imei = st.text_input("IMEI / Serienummer (Valfritt / Optional)")

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
            issues_list.append(f"Skärmbyte / Screen: {p_screen} Kr")
            total_price += p_screen

        has_backglass = st.checkbox("📱 Baksida kraschad / Back Glass Damaged")
        if has_backglass:
            p_backglass = st.number_input("Pris: Baksida (Kr)", min_value=0.0, step=50.0, value=0.0, key="p_bg")
            issues_list.append(f"Baksida kraschad / Back Glass: {p_backglass} Kr")
            total_price += p_backglass

        has_water = st.checkbox("💧 Vattenskada / Water Damage")
        if has_water:
            p_water = st.number_input("Pris: Vattenskada (Kr)", min_value=0.0, step=50.0, value=0.0, key="p_wat")
            issues_list.append(f"Vattenskada / Water Damage: {p_water} Kr")
            total_price += p_water

        has_battery = st.checkbox("🔋 Batteriproblem / Battery Replacement")
        if has_battery:
            p_battery = st.number_input("Pris: Batteri (Kr)", min_value=0.0, step=50.0, value=0.0, key="p_bat")
            issues_list.append(f"Batteribyte / Battery: {p_battery} Kr")
            total_price += p_battery

        has_charging = st.checkbox("🔌 Laddport / Charging Port Issue")
        if has_charging:
            p_charging = st.number_input("Pris: Laddport (Kr)", min_value=0.0, step=50.0, value=0.0, key="p_chg")
            issues_list.append(f"Laddport / Charging Port: {p_charging} Kr")
            total_price += p_charging

        has_cam = st.checkbox("📷 Kameraproblem / Camera Repair")
        if has_cam:
            p_cam = st.number_input("Pris: Kamera (Kr)", min_value=0.0, step=50.0, value=0.0, key="p_cam")
            issues_list.append(f"Kamera / Camera: {p_cam} Kr")
            total_price += p_cam

    with col_q2:
        st.markdown("**💻 Laptop & Övrig Elektronik / Laptop & Electronics**")
        has_laptopscreen = st.checkbox("💻 Laptop Skärmbyte / Laptop Screen")
        if has_laptopscreen:
            p_lapscreen = st.number_input("Pris: Laptop Skärm (Kr)", min_value=0.0, step=50.0, value=0.0, key="p_lscr")
            issues_list.append(f"Laptop Skärm / Screen: {p_lapscreen} Kr")
            total_price += p_lapscreen

        has_keyboard = st.checkbox("⌨️ Tangentbord / Keyboard Problem")
        if has_keyboard:
            p_keyboard = st.number_input("Pris: Tangentbord (Kr)", min_value=0.0, step=50.0, value=0.0, key="p_key")
            issues_list.append(f"Tangentbord / Keyboard: {p_keyboard} Kr")
            total_price += p_keyboard

        has_software = st.checkbox("⚙️ Mjukvara & OS / Software & Virus Help")
        if has_software:
            p_software = st.number_input("Pris: Mjukvara (Kr)", min_value=0.0, step=50.0, value=0.0, key="p_sof")
            issues_list.append(f"Mjukvara / Software: {p_software} Kr")
            total_price += p_software

        has_cleaning = st.checkbox("🧹 Rengöring & Fläkt / Cleaning & Fan Service")
        if has_cleaning:
            p_cleaning = st.number_input("Pris: Rengöring (Kr)", min_value=0.0, step=50.0, value=0.0, key="p_cln")
            issues_list.append(f"Rengöring & Fläkt / Cleaning: {p_cleaning} Kr")
            total_price += p_cleaning

    custom_issue = st.text_input("Övrigt fel / Annan elektronik (Valfritt / Custom Issue)")
    if custom_issue:
        p_custom = st.number_input("Pris för övrigt (Kr)", min_value=0.0, step=50.0, value=0.0, key="p_cust")
        issues_list.append(f"{custom_issue}: {p_custom} Kr")
        total_price += p_custom

    st.markdown("---")
    st.markdown(f"### 💰 **Total Summa / Final Total: {total_price:.2f} Kr (inkl. moms / incl. VAT)**")
    st.info("📜 *Detta kostnadsförslag gäller endast i vår verkstad / This quote is valid only in our workshop.*")

    if st.button("Spara & Generera Kostnadsförslag PDF / Save & Generate Quote PDF", type="primary"):
        if c_name and device and issues_list:
            conn, db_type = get_db_connection()
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            issues_str = ", ".join(issues_list)
            
            try:
                if db_type == "turso":
                    try:
                        conn.execute(
                            "INSERT INTO quotes (branch, customer_name, phone, email, device, issues, total, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                            (branch, c_name, c_phone, "", device, issues_str, total_price, created_at)
                        )
                    except Exception:
                        local_conn = sqlite3.connect("local_crm.db", check_same_thread=False)
                        local_cursor = local_conn.cursor()
                        local_cursor.execute(
                            "INSERT INTO quotes (branch, customer_name, phone, email, device, issues, total, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                            (branch, c_name, c_phone, "", device, issues_str, total_price, created_at)
                        )
                        local_conn.commit()
                        local_conn.close()
                else:
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO quotes (branch, customer_name, phone, email, device, issues, total, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (branch, c_name, c_phone, "", device, issues_str, total_price, created_at)
                    )
                    conn.commit()
                    conn.close()
                st.success("✅ Kostnadsförslag sparat i databasen! / Quote saved successfully!")
            except Exception as e:
                st.error(f"❌ Fel vid sparande / Error: {e}")

            buffer = io.BytesIO()
            p = canvas.Canvas(buffer, pagesize=A4)
            
            if os.path.exists("logo.png"):
                try:
                    p.drawImage("logo.png", 50, 750, width=80, height=40, preserveAspectRatio=True, mask='auto')[cite: 1]
                except Exception:
                    pass
            
            p.drawString(140, 780, comp["name"])
            p.drawString(140, 765, f"Adress: {comp['address']} | Tel: {comp['phone']}")
            p.drawString(140, 750, f"Org.nr: {comp['org_nr']}")
            p.drawString(50, 735, "------------------------------------------------------------------------------------------------")
            p.drawString(50, 715, "KOSTNADSFÖRSLAG / PRICE QUOTATION")
            p.drawString(50, 695, f"Datum / Date: {date.today().strftime('%Y-%m-%d')}")
            p.drawString(50, 675, f"Kund / Customer: {c_name} | Tel: {c_phone}")
            p.drawString(50, 655, f"Enhet / Device: {device} | IMEI/Serial: {imei}")
            p.drawString(50, 635, "------------------------------------------------------------------------------------------------")
            
            y_pos = 605
            for item in issues_list:
                p.drawString(70, y_pos, f"- {item}")
                y_pos -= 25
            
            y_pos -= 20
            p.drawString(50, y_pos, f"TOTAL SUMMA / TOTAL: {total_price:.2f} Kr (inkl. moms)")
            y_pos -= 30
            p.drawString(50, y_pos, "* Detta kostnadsförslag gäller endast i vår verkstad / Valid only in our workshop.")
            
            p.showPage()
            p.save()
            buffer.seek(0)
            st.session_state['last_quote_pdf'] = buffer
            st.success("✅ PDF skapades framgångsrikt! / PDF generated successfully!")

    if 'last_quote_pdf' in st.session_state:
        st.markdown("---")
        st.subheader("👀 Förhandsgranska och Skriv ut / Preview & Print")
        display_pdf_preview(st.session_state['last_quote_pdf'], file_name="kostnadsforslag.pdf")

# --- 3. FAKTURA / INVOICE ---
elif menu == "📄 Faktura / Invoice":
    st.header("📄 Professionell Faktura / Professional Invoice")
    branch = st.selectbox("Välj Företagsfilial / Select Branch", ["Eskilstuna", "Västerås"])
    comp = COMPANY_INFO[branch]
    
    st.info(f"""
    🏢 **Företagsuppgifter ({branch}) / Company Details:**
    * **Företag / Company:** {comp['name']}
    * **Adress / Address:** {comp['address']}
    * **Telefon / Phone:** {comp['phone']} | **Org.nr:** {comp['org_nr']}
    * **Swish:** {comp['swish']} | **Bankgiro:** {comp['bankgiro']}
    """)

    st.markdown("---")
    st.subheader("👤 Kunduppgifter / Customer Info")
    f_name = st.text_input("Företag / Kundens namn / Company or Customer Name")
    f_phone_inv = st.text_input("Telefonnummer / Phone Number")
    f_address = st.text_input("Adress / Address")
    invoice_no = st.text_input("Fakturanummer / Invoice No.", value="FAK-2026-001")
    invoice_date = st.date_input("Fakturadatum / Invoice Date", value=date.today())
    due_date = st.date_input("Förfallodatum / Due Date", value=date.today())

    st.markdown("---")
    st.subheader("🛒 Artikel & Pris / Item & Price")
    item_desc = st.text_input("Beskrivning / Description", value="Reparation och reservdelar / Repair & Parts")
    item_qty = st.number_input("Antal / Quantity", min_value=1, value=1)
    item_price = st.number_input("Pris per enhet inkl. moms (Kr) / Unit Price incl. VAT", min_value=0.0, step=50.0)
    
    total_amount = item_qty * item_price
    moms = total_amount * 0.20
    netto = total_amount - moms
    
    st.markdown(f"""
    ### 📊 Sammanfattning / Summary:
    * **Netto (exkl. moms) / Net (excl. VAT):** {netto:.2f} Kr
    * **Moms (25%) / VAT (25%):** {moms:.2f} Kr
    * **Att betala / Total Summa / Total:** **{total_amount:.2f} Kr**
    """)
    st.markdown(f"💳 **Betalningsmetod / Payment Method:** Swish: `{comp['swish']}` | Bankgiro: `{comp['bankgiro']}`")
    
    if st.button("Spara & Skapa Faktura PDF / Save & Create Invoice PDF", type="primary"):
        if f_name:
            conn, db_type = get_db_connection()
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            try:
                if db_type == "turso":
                    try:
                        conn.execute(
                            "INSERT INTO invoices (branch, customer_name, phone, invoice_no, amount, moms, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                            (branch, f_name, f_phone_inv, invoice_no, total_amount, moms, created_at)
                        )
                    except Exception:
                        local_conn = sqlite3.connect("local_crm.db", check_same_thread=False)
                        local_cursor = local_conn.cursor()
                        local_cursor.execute(
                            "INSERT INTO invoices (branch, customer_name, phone, invoice_no, amount, moms, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                            (branch, f_name, f_phone_inv, invoice_no, total_amount, moms, created_at)
                        )
                        local_conn.commit()
                        local_conn.close()
                else:
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO invoices (branch, customer_name, phone, invoice_no, amount, moms, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (branch, f_name, f_phone_inv, invoice_no, total_amount, moms, created_at)
                    )
                    conn.commit()
                    conn.close()
                st.success("✅ Faktura sparad i databasen! / Invoice saved successfully!")
            except Exception as e:
                st.error(f"❌ Fel vid sparande / Error: {e}")

            buffer = io.BytesIO()
            p = canvas.Canvas(buffer, pagesize=A4)
            
            if os.path.exists("logo.png"):
                try:
                    p.drawImage("logo.png", 50, 750, width=80, height=40, preserveAspectRatio=True, mask='auto')[cite: 1]
                except Exception:
                    pass
            
            p.drawString(140, 780, comp["name"])
            p.drawString(140, 765, f"Adress: {comp['address']}")
            p.drawString(140, 750, f"Tel: {comp['phone']} | Org.nr: {comp['org_nr']}")
            p.drawString(50, 735, "------------------------------------------------------------------------------------------------")
            p.drawString(50, 715, "FAKTURA / INVOICE")
            p.drawString(50, 695, f"Fakturanr / Invoice No: {invoice_no} | Datum / Date: {invoice_date} | Förfallodag / Due: {due_date}")
            p.drawString(50, 675, f"Kund / Customer: {f_name} | Adress: {f_address}")
            p.drawString(50, 655, "------------------------------------------------------------------------------------------------")
            p.drawString(50, 625, f"Beskrivning / Description: {item_desc} (Antal / Qty: {item_qty})")
            p.drawString(50, 595, f"Netto: {netto:.2f} Kr | Moms (25%): {moms:.2f} Kr")
            p.drawString(50, 565, f"Att betala Totalt / Total: {total_amount:.2f} Kr")
            p.drawString(50, 525, f"Betalning via Swish: {comp['swish']} eller Bankgiro: {comp['bankgiro']}")
            
            p.showPage()
            p.save()
            buffer.seek(0)
            st.session_state['last_invoice_pdf'] = buffer
            st.success("✅ Faktura PDF skapades! / Invoice PDF generated!")

    if 'last_invoice_pdf' in st.session_state:
        st.markdown("---")
        st.subheader("👀 Förhandsgranska och Skriv ut / Preview & Print")
        display_pdf_preview(st.session_state['last_invoice_pdf'], file_name=f"{invoice_no}.pdf")

# --- 4. FÖRBESTÄLLNING / PRE-ORDER ---
elif menu == "🛒 Förbeställning / Pre-order":
    st.header("🛒 Förbeställning av reservdelar / Spare Parts Pre-order")
    branch = st.selectbox("Välj Butik / Select Branch", ["Eskilstuna", "Västerås"])
    fb_name = st.text_input("Kundens namn / Customer Name")
    fb_phone = st.text_input("Telefonnummer / Phone Number")
    fb_details = st.text_area("Artikel / Delar detaljer / Part Details")
    fb_deposit = st.number_input("Handpenning / Deposit (Kr)", min_value=0.0, step=50.0)
    
    if st.button("Spara Förbeställning / Save Pre-order", type="primary"):
        if fb_name and fb_phone:
            conn, db_type = get_db_connection()
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            try:
                if db_type == "turso":
                    try:
                        conn.execute(
                            "INSERT INTO preorders (branch, customer_name, phone, item_details, deposit, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                            (branch, fb_name, fb_phone, fb_details, fb_deposit, created_at)
                        )
                    except Exception:
                        local_conn = sqlite3.connect("local_crm.db", check_same_thread=False)
                        local_cursor = local_conn.cursor()
                        local_cursor.execute(
                            "INSERT INTO preorders (branch, customer_name, phone, item_details, deposit, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                            (branch, fb_name, fb_phone, fb_details, fb_deposit, created_at)
                        )
                        local_conn.commit()
                        local_conn.close()
                else:
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO preorders (branch, customer_name, phone, item_details, deposit, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                        (branch, fb_name, fb_phone, fb_details, fb_deposit, created_at)
                    )
                    conn.commit()
                    conn.close()
                st.success("✅ Förbeställning sparad! / Pre-order saved successfully!")
            except Exception as e:
                st.error(f"❌ Fel vid sparande / Error: {e}")
        else:
            st.warning("⚠️ Fyll i namn och telefonnummer. / Fill name and phone number.")

# --- 5. ABONNEMANG / SUBSCRIPTIONS ---
elif menu == "💳 Abonnemang / Subscriptions":
    st.header("💳 IMEI-kopplade Abonnemang & Villkor / IMEI Subscriptions & Terms")
    
    sub_imei = st.text_input("IMEI-nummer (Unikt för enheten) / IMEI Number")
    sub_device = st.text_input("Enhet / Modell / Device Model (t.ex. iPhone 15)")
    branch = st.selectbox("Butik / Branch", ["Eskilstuna", "Västerås"])
    sub_name = st.text_input("Kundens namn / Customer Name")
    sub_phone = st.text_input("Telefonnummer / Phone Number")

    st.markdown("---")
    plan_choice = st.selectbox("Välj Plan / Plan Type", [
        "Glass Protection Abonnemang (99 SEK/mån)",
        "Case / Cover Abonnemang (399 SEK start + 99 SEK/mån)",
        "Teknik, Mjukvara & Virus Help (99 SEK/mån)"
    ])
    
    if "Glass Protection" in plan_choice:
        sub_price = 99.0
        st.info("💡 **Glass Protection Plan:** 99 Kr/mån | Byt skärmskydd upp till 2 ggr/mån utan självrisk (0 SEK självrisk).")
    elif "Case / Cover" in plan_choice:
        sub_price = 99.0
        st.info("💡 **Case / Cover Plan:** 399 Kr startavgift + 99 Kr/mån | Byt skydd 1 gång var 3:e månad utan självrisk.")
    else:
        sub_price = 99.0
        st.info("💡 **Teknik & Mjukvara Plan:** 99 Kr/mån | Fri hjälp med mjukvara och virusrensning.")

    st.markdown("---")
    st.info("""
    **Svenska (Villkor):**
    1. **IMEI-koppling:** Abonnemanget är strikt kopplat till enhetens **IMEI-nummer**, inte till en specifik privatperson.
    2. **Uppsägningstid:** 3 månaders uppsägningstid gäller. Kunden måste meddela oss senast **3 månader i förväg** vid uppsägning.
    3. **Byte av IMEI / Enhet:** Kunden kan begära byte av registrerat IMEI-nummer **efter 3 månaders bindningstid**.
    
    ---
    **English (Terms):**
    1. **IMEI Linking:** The subscription is strictly linked to the device's **IMEI number**, not to an individual.
    2. **Notice Period:** 3 months notice period required. Customer must inform us **3 months in advance** for cancellation.
    3. **IMEI / Device Change:** Customer can change the registered IMEI number **after 3 months**.
    """)
    
    agree_terms = st.checkbox("Kunden godkänner avtalsvillkoren & IMEI-regler / Customer accepts terms & IMEI rules")

    if st.button("Spara Abonnemang i Molnet / Save Subscription", type="primary"):
        if sub_imei and sub_name and agree_terms:
            conn, db_type = get_db_connection()
            start_date = datetime.now().strftime("%Y-%m-%d")
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            try:
                if db_type == "turso":
                    try:
                        conn.execute(
                            "INSERT INTO subscriptions (branch, customer_name, phone, device, imei, plan_type, price, start_date, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (branch, sub_name, sub_phone, sub_device, sub_imei, plan_choice, sub_price, start_date, created_at)
                        )
                    except Exception:
                        local_conn = sqlite3.connect("local_crm.db", check_same_thread=False)
                        local_cursor = local_conn.cursor()
                        local_cursor.execute(
                            "INSERT INTO subscriptions (branch, customer_name, phone, device, imei, plan_type, price, start_date, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (branch, sub_name, sub_phone, sub_device, sub_imei, plan_choice, sub_price, start_date, created_at)
                        )
                        local_conn.commit()
                        local_conn.close()
                else:
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO subscriptions (branch, customer_name, phone, device, imei, plan_type, price, start_date, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (branch, sub_name, sub_phone, sub_device, sub_imei, plan_choice, sub_price, start_date, created_at)
                    )
                    conn.commit()
                    conn.close()
                st.success("✅ Abonnemanget kopplat till IMEI har sparats! / Subscription saved successfully!")
            except Exception as e:
                st.error(f"❌ Fel vid sparande / Error: {e}")
        elif not sub_imei:
            st.warning("⚠️ IMEI-nummer är obligatoriskt! / IMEI number is required.")
        elif not agree_terms:
            st.warning("⚠️ Du måste bocka i att kunden godkänner villkoren. / Please confirm terms.")
        else:
            st.warning("⚠️ Fyll i kundens namn. / Enter customer name.")

# --- 6. DOKUMENT & HISTORIK / PRINT & HISTORY HUB ---
elif menu == "🖨️ Dokument & Historik / Print & History Hub":
    st.header("🖨️ Visa och Skriv ut tidigare sparade dokument")
    st.markdown("Välj kategori och ange ID för att visa eller skriva ut ett sparat dokument från databasen:")
    
    category = st.selectbox("Välj Kategori / Category", [
        "💡 Kostnadsförslag / Quotes", 
        "📄 Fakturor / Invoices"
    ])
    
    conn, db_type = get_db_connection()
    table_name = "quotes" if "Quotes" in category else "invoices"
    record_type = "quote" if "Quotes" in category else "invoice"
    
    try:
        if db_type == "turso":
            try:
                rows = conn.execute(f"SELECT * FROM {table_name} ORDER BY id DESC LIMIT 30").fetchall()
                columns_res = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
                col_names = [c[1] for c in columns_res]
                df = pd.DataFrame(rows, columns=col_names) if rows else pd.DataFrame()
            except Exception:
                local_conn = sqlite3.connect("local_crm.db", check_same_thread=False)
                df = pd.read_sql_query(f"SELECT * FROM {table_name} ORDER BY id DESC LIMIT 30", local_conn)
                local_conn.close()
        else:
            cursor = conn.cursor()
            cursor.execute(f"SELECT * FROM {table_name} ORDER BY id DESC LIMIT 30")
            rows = cursor.fetchall()
            col_names = [d[0] for d in cursor.description]
            df = pd.DataFrame(rows, columns=col_names) if rows else pd.DataFrame()
    except Exception:
        df = pd.DataFrame()
        
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        
        st.markdown("### 🔍 Välj post via ID för att Visa / Skriva ut")
        selected_id = st.number_input("Ange Post-ID (första kolumnen) / Enter Record ID", min_value=1, step=1)
        
        target_row = df[df['id'] == selected_id]
        
        if not target_row.empty:
            row_data = target_row.iloc[0].to_dict()
            st.success(f"✅ Vald post hittad: {row_data.get('customer_name', '')}")
            
            if st.button("👁️ Generera & Förhandsgranska PDF / View PDF", type="primary"):
                pdf_buf = generate_pdf_from_record(record_type, row_data, COMPANY_INFO)
                st.session_state['hub_pdf'] = pdf_buf
                st.session_state['hub_pdf_name'] = f"dokument_{selected_id}.pdf"
                st.rerun()
                
            if 'hub_pdf' in st.session_state:
                st.markdown("---")
                display_pdf_preview(st.session_state['hub_pdf'], file_name=st.session_state.get('hub_pdf_name', 'dokument.pdf'))
        else:
            st.info("ℹ️ Ange ett giltigt ID från tabellen ovan.")
    else:
        st.info("ℹ️ Inga dokument hittades.")

# --- 7. DATA CENTER & SÖK / ALL DATA & SEARCH ---
elif menu == "📊 Data Center & Sök / All Data & Search":
    st.header("📊 Data Center, Sök, Export & Hantering / Search, Export & Management")
    st.markdown("Sök, exportera, visa dokument eller radera poster från databasen:")
    
    search_category = st.selectbox("Välj Kategori / Select Category", [
        "📝 Reparationer / Repairs", 
        "💳 Abonnemang / Subscriptions", 
        "🛒 Förbeställningar / Pre-orders", 
        "💡 Kostnadsförslag / Quotes", 
        "📄 Fakturor / Invoices"
    ])
    
    search_term = st.text_input("🔎 Sök på Namn, Telefon eller IMEI / Search by Name, Phone, or IMEI", "").lower()
    
    conn, db_type = get_db_connection()
    
    table_map = {
        "📝 Reparationer / Repairs": "repairs",
        "💳 Abonnemang / Subscriptions": "subscriptions",
        "🛒 Förbeställningar / Pre-orders": "preorders",
        "💡 Kostnadsförslag / Quotes": "quotes",
        "📄 Fakturor / Invoices": "invoices"
    }
    
    current_table = table_map[search_category]
    
    try:
        if db_type == "turso":
            try:
                res = conn.execute(f"SELECT * FROM {current_table} ORDER BY id DESC")
                rows = res.fetchall()
                columns_res = conn.execute(f"PRAGMA table_info({current_table})").fetchall()
                col_names = [c[1] for c in columns_res]
                df = pd.DataFrame(rows, columns=col_names) if rows else pd.DataFrame()
            except Exception:
                local_conn = sqlite3.connect("local_crm.db", check_same_thread=False)
                df = pd.read_sql_query(f"SELECT * FROM {current_table} ORDER BY id DESC", local_conn)
                local_conn.close()
        else:
            cursor = conn.cursor()
            cursor.execute(f"SELECT * FROM {current_table} ORDER BY id DESC")
            rows = cursor.fetchall()
            col_names = [description[0] for description in cursor.description]
            df = pd.DataFrame(rows, columns=col_names) if rows else pd.DataFrame()
    except Exception:
        df = pd.DataFrame()
        
    if not df.empty:
        if search_term:
            mask = df.astype(str).apply(lambda x: x.str.lower().str.contains(search_term)).any(axis=1)
            filtered_df = df[mask]
        else:
            filtered_df = df
            
        st.dataframe(filtered_df, use_container_width=True)
        
        # Om det är Kostnadsförslag eller Fakturor kan man förhandsgranska/skriva ut direkt härifrån
        if current_table in ["quotes", "invoices"]:
            st.markdown("---")
            st.subheader("👁️ Visa och Skriv ut sparad post direkt / View & Print Record")
            doc_id = st.number_input("Ange ID för dokument som ska visas/skrivas ut", min_value=0, step=1, key="doc_view_id")
            
            if doc_id > 0:
                match_row = df[df['id'] == doc_id]
                if not match_row.empty:
                    row_dict = match_row.iloc[0].to_dict()
                    rec_type = "quote" if current_table == "quotes" else "invoice"
                    
                    if st.button("🖨️ Generera förhandsgranskning för ID", type="primary"):
                        buf = generate_pdf_from_record(rec_type, row_dict, COMPANY_INFO)
                        st.session_state['datacenter_pdf'] = buf
                        st.rerun()

            if 'datacenter_pdf' in st.session_state:
                st.markdown("---")
                display_pdf_preview(st.session_state['datacenter_pdf'], file_name="arkiv_dokument.pdf")

        st.markdown("---")
        st.subheader("🗑️ Radera post / Delete Record")
        delete_id = st.number_input("Ange ID för post som ska raderas / Enter ID to delete", min_value=0, step=1, key="del_id_input")
        
        if st.button("Radera permanent / Delete Permanently", type="secondary"):
            if delete_id > 0:
                try:
                    if db_type == "turso":
                        try:
                            conn.execute(f"DELETE FROM {current_table} WHERE id = ?", (delete_id,))
                        except Exception:
                            local_conn = sqlite3.connect("local_crm.db", check_same_thread=False)
                            local_cursor = local_conn.cursor()
                            local_cursor.execute(f"DELETE FROM {current_table} WHERE id = ?", (delete_id,))
                            local_conn.commit()
                            local_conn.close()
                    else:
                        cursor = conn.cursor()
                        cursor.execute(f"DELETE FROM {current_table} WHERE id = ?", (delete_id,))
                        conn.commit()
                        conn.close()
                    st.success(f"✅ Post med ID {delete_id} har raderats! / Record deleted successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Fel vid radering / Delete error: {e}")
            else:
                st.warning("⚠️ Ange ett giltigt ID att radera.")
    else:
        st.info("ℹ️ Inga poster hittades i databasen.")
