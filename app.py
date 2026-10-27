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

# Company Info Details based on branch
COMPANY_INFO = {
    "Eskilstuna": {
        "name": "30 MINUTES FIX AB (Eskilstuna)",
        "address": "Gunborg Nymans Väg 2, 632 22 Eskilstuna",
        "phone": "016-XXX XXX",
        "org_nr": "559XXX-XXXX"
    },
    "Västerås": {
        "name": "30 MINUTES FIX AB (Västerås)",
        "address": "Västerås City / Stora Gatan",
        "phone": "021-XXX XXX",
        "org_nr": "559XXX-XXXX"
    }
}

st.sidebar.title("30 MINUTES FIX AB")
st.sidebar.markdown("**Eskilstuna & Västerås**")
st.sidebar.markdown("---")

# Global Security Login check via Sidebar PIN
sidebar_pin = st.sidebar.text_input("🔑 System Login (PIN: tunapark)", type="password")

if sidebar_pin != st.secrets.get("DELETE_PIN", "tunapark"):
    st.sidebar.warning("⚠️ Enter PIN 'tunapark' to unlock all features.")
    st.title("🔒 30 Minutes Fix CRM - Locked")
    st.info("Please enter the correct PIN code (`tunapark`) in the sidebar to access the CRM system. / Angiv PIN-kod i sidofältet för att låsa upp.")
    st.stop()

st.sidebar.success("✅ System Unlocked / Systemet upplåst")

menu = st.sidebar.radio("Navigation / Meny", [
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
    st.header("💡 Professionellt Kostnadsförslag / Price Quotation")
    
    branch_choice = st.selectbox("Välj Butik / Branch", ["Eskilstuna", "Västerås"])
    comp = COMPANY_INFO[branch_choice]
    
    col_q1, col_q2 = st.columns(2)
    with col_q1:
        c_name = st.text_input("Kundens namn / Customer Name")
        c_phone = st.text_input("Telefonnummer / Phone Number")
    with col_q2:
        device = st.text_input("Enhet / Modell / Device Model")
        imei = st.text_input("IMEI / Serienummer (Valfritt) / IMEI Number")

    st.markdown("---")
    st.subheader("🛠️ Välj Fel och Pris / Select Issues & Prices")
    
    issues_list = []
    total_price = 0.0

    col_i1, col_i2 = st.columns(2)
    with col_i1:
        has_screen = st.checkbox("📱 Skärmbyte / Damaged Screen")
        if has_screen:
            p_screen = st.number_input("Pris för Skärmbyte (Kr)", min_value=0.0, step=50.0, value=0.0)
            issues_list.append(f"Skärmbyte: {p_screen} Kr")
            total_price += p_screen

        has_water = st.checkbox("💧 Vattenskada / Damaged with Water")
        if has_water:
            p_water = st.number_input("Pris för Vattenskada (Kr)", min_value=0.0, step=50.0, value=0.0)
            issues_list.append(f"Vattenskada: {p_water} Kr")
            total_price += p_water

    with col_i2:
        has_battery = st.checkbox("🔋 Batteriproblem / Battery Problem")
        if has_battery:
            p_battery = st.number_input("Pris för Batteribyte (Kr)", min_value=0.0, step=50.0, value=0.0)
            issues_list.append(f"Batteriproblem: {p_battery} Kr")
            total_price += p_battery

        has_software = st.checkbox("💻 Mjukvaruproblem / Software Problem")
        if has_software:
            p_software = st.number_input("Pris för Mjukvara (Kr)", min_value=0.0, step=50.0, value=0.0)
            issues_list.append(f"Mjukvaruproblem: {p_software} Kr")
            total_price += p_software

    custom_issue = st.text_input("Övrigt fel / Annan reparation (Valfritt)")
    if custom_issue:
        p_custom = st.number_input("Pris för övrigt (Kr)", min_value=0.0, step=50.0, value=0.0)
        issues_list.append(f"{custom_issue}: {p_custom} Kr")
        total_price += p_custom

    st.markdown("---")
    st.markdown(f"### 💰 **Total Summa / Final Total: {total_price:.2f} Kr (inkl. moms)**")
    
    st.info("""
    **📜 Villkor för Kostnadsförslag / Terms:**
    * Detta kostnadsförslag är **endast giltigt i vår verkstad** (This quote is valid only in our workshop).
    """)

    if st.button("Generera PDF Kostnadsförslag / Generate PDF Quote", type="primary"):
        if c_name and device and issues_list:
            buffer = io.BytesIO()
            p = canvas.Canvas(buffer, pagesize=A4)
            
            p.drawString(50, 800, comp["name"])
            p.drawString(50, 785, f"Adress: {comp['address']} | Tel: {comp['phone']}")
            p.drawString(50, 770, "--------------------------------------------------------")
            p.drawString(50, 750, "KOSTNADSFÖRSLAG / PRICE QUOTATION")
            p.drawString(50, 730, f"Datum: {date.today().strftime('%Y-%m-%d')}")
            p.drawString(50, 710, f"Kund: {c_name} | Tel: {c_phone}")
            p.drawString(50, 690, f"Enhet: {device} | IMEI: {imei}")
            p.drawString(50, 670, "--------------------------------------------------------")
            
            y_pos = 640
            p.drawString(50, y_pos, "Valda reparationer / Selected Issues:")
            for item in issues_list:
                y_pos -= 25
                p.drawString(70, y_pos, f"- {item}")
            
            y_pos -= 40
            p.drawString(50, y_pos, f"TOTAL SUMMA / TOTAL: {total_price:.2f} Kr (inkl. moms)")
            
            y_pos -= 40
            p.drawString(50, y_pos, "* Detta kostnadsförslag gäller endast i vår verkstad / Valid only in workshop.")
            
            p.showPage()
            p.save()
            buffer.seek(0)
            
            st.success("✅ Kostnadsförslag PDF skapats! / PDF Quote generated!")
            st.download_button("📥 Ladda ner PDF / Download PDF", buffer, file_name="kostnadsforslag.pdf", mime="application/pdf")
        else:
            st.warning("⚠️ Fyll i kundens namn, enhet och välj minst ett fel. / Please fill required fields.")

# --- 3. FAKTURA / INVOICE ---
elif menu == "📄 Faktura / Invoice":
    st.header("📄 Professionell Faktura / Professional Invoice")
    
    branch_choice = st.selectbox("Välj Företagsfilial / Select Branch", ["Eskilstuna", "Västerås"])
    comp = COMPANY_INFO[branch_choice]
    
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        st.subheader("📍 Kunduppgifter / Customer Info")
        f_name = st.text_input("Företag / Kundens namn / Company or Customer Name")
        f_org = st.text_input("Org.nr / Personnummer (Optional)")
        f_address = st.text_input("Adress / Address")
    with col_f2:
        st.subheader("🧾 Fakturadetaljer / Invoice Details")
        invoice_no = st.text_input("Fakturanummer / Invoice No.", value="FAK-2026-001")
        invoice_date = st.date_input("Fakturadatum / Invoice Date", value=date.today())
        due_date = st.date_input("Förfallodatum / Due Date", value=date.today())

    st.markdown("---")
    st.subheader("🛒 Artikel / Tjänst / Item & Price")
    item_desc = st.text_input("Beskrivning / Description", value="Mobilreparation och reservdelar / Phone Repair")
    item_qty = st.number_input("Antal / Quantity", min_value=1, value=1)
    item_price = st.number_input("Pris per enhet inkl. moms (Kr) / Unit Price incl. VAT", min_value=0.0, step=50.0)
    
    total_amount = item_qty * item_price
    moms = total_amount * 0.20
    netto = total_amount - moms
    
    st.markdown(f"""
    ### 📊 Sammanfattning / Summary:
    * **Netto (exkl. moms):** {netto:.2f} Kr
    * **Moms (25%):** {moms:.2f} Kr
    * **Att betala / Total Summa:** **{total_amount:.2f} Kr**
    """)
    
    st.markdown("💳 **Betalningsmetod / Payment Method:** Swish: `123-XXX XXXX` | Bankgiro: `XXX-XXXX`")
    
    if st.button("Skapa Professionell Faktura PDF / Create Invoice PDF", type="primary"):
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)
        
        p.drawString(50, 800, comp["name"])
        p.drawString(50, 785, f"Adress: {comp['address']} | Tel: {comp['phone']}")
        p.drawString(50, 770, f"Org.nr: {comp['org_nr']}")
        p.drawString(50, 750, "--------------------------------------------------------")
        p.drawString(50, 730, "FAKTURA / INVOICE")
        p.drawString(50, 710, f"Fakturanr: {invoice_no} | Datum: {invoice_date} | Förfallodag: {due_date}")
        p.drawString(50, 690, f"Kund: {f_name} | Adress: {f_address}")
        p.drawString(50, 670, "--------------------------------------------------------")
        p.drawString(50, 640, f"Beskrivning: {item_desc} (Antal: {item_qty})")
        p.drawString(50, 610, f"Netto: {netto:.2f} Kr | Moms (25%): {moms:.2f} Kr")
        p.drawString(50, 580, f"Att betala Totalt / Total: {total_amount:.2f} Kr")
        p.drawString(50, 540, "Betalning sker via Swish eller Bankgiro. Välkommen åter!")
        
        p.showPage()
        p.save()
        buffer.seek(0)
        
        st.success("✅ Faktura PDF skapad! / Invoice PDF generated!")
        st.download_button("📥 Ladda ner Faktura PDF / Download Invoice PDF", buffer, file_name=f"{invoice_no}.pdf", mime="application/pdf")

# --- 4. SÖK ÄRENDEN / SEARCH ---
elif menu == "🔍 Sök Ärenden / Search":
    st.header("🔍 Sök och Hantera Ärenden / Search Repairs")
    
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
    st.header("💳 IMEI-kopplade Abonnemang & Villkor / IMEI Subscriptions & Terms")
    
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        st.subheader("📱 Enhetskoppling (Krävs) / Device IMEI")
        sub_imei = st.text_input("IMEI-nummer (Unikt för enheten) / IMEI Number")
        sub_device = st.text_input("Enhet / Modell / Device Model (t.ex. iPhone 15)")
        branch = st.selectbox("Butik / Branch", ["Eskilstuna", "Västerås"])
    with col_s2:
        st.subheader("👤 Kunduppgifter / Customer Info")
        sub_name = st.text_input("Kundens namn / Customer Name")
        sub_phone = st.text_input("Telefonnummer / Phone Number")
        sub_email = st.text_input("E-post / Email (Valfritt)")

    st.markdown("---")
    st.subheader("📦 Välj Abonnemangsplan / Select Plan")
    
    plan_choice = st.selectbox("Välj Plan / Plan Type", [
        "Glass Protection Abonnemang (99 SEK/mån)",
        "Case / Cover Abonnemang (399 SEK start + 99 SEK/mån)",
        "Teknik, Mjukvara & Virus Help (99 SEK/mån)"
    ])
    
    if "Glass Protection" in plan_choice:
        sub_price = 99.0
        st.info("💡 **Glass Protection Plan:** 99 Kr/mån | Byt skärmskydd upp till **2 gånger per månad** helt utan självrisk (`0 SEK självrisk`).")
    elif "Case / Cover" in plan_choice:
        sub_price = 99.0
        st.info("💡 **Case / Cover Plan:** 399 Kr startavgift + 99 Kr/mån | Byt kفر/غطاء الهاتف **1 gång var 3:e månad** helt utan självrisk.")
    else:
        sub_price = 99.0
        st.info("💡 **Teknik & Mjukvara Plan:** 99 Kr/mån | Fri hjälp med mjukvara, virusrensning och teknisk support.")

    st.markdown("---")
    st.subheader("📜 Viktiga Avtalsvillkor (IMEI & Regler) / Terms & Conditions")
    
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
    
    agree_terms = st.checkbox("Kunden godkänner avtalsvillkoren & IMEI-regler / Customer accepts terms")

    if st.button("Spara Abonnemang i Molnet / Save Subscription", type="primary"):
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
                st.success("✅ Abonnemanget kopplat till IMEI har sparats i molnet! / Saved successfully!")
            except Exception as e:
                st.error(f"❌ Fel vid sparande / Error: {e}")
        elif not sub_imei:
            st.warning("⚠️ IMEI-nummer är obligatoriskt! Abonnemanget måste kopplas till en enhet. / IMEI is required.")
        elif not agree_terms:
            st.warning("⚠️ Du måste bocka i att kunden godkänner villkoren. / Please confirm terms.")
        else:
            st.warning("⚠️ Fyll i kundens namn. / Enter customer name.")
            
    st.markdown("---")
    st.subheader("📋 Aktiva IMEI-abonnemang i Molnet / Active Subscriptions")
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
                st.write(f"📱 **IMEI:** {s[5]} | **Kund:** {s[2]} | **Device:** {s[4]} | **Plan:** {s[6]} | **Pris:** {s[7]} Kr/mån | **Start:** {s[8]}")
        else:
            st.info("Inga aktiva abonnemang registrerade ännu. / No active subscriptions found.")
    except Exception as e:
        st.warning("Laddar abonnemang... / Loading...")
