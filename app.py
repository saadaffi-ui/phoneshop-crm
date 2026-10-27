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
    
    st.markdown("---")
    st.subheader("🛠️ Reparationsdetaljer & Kostnad / Repair Details & Cost")
    
    col_a, col_b = st.columns(2)
    with col_a:
        fault_1 = st.text_input("Beskrivning av fel 1 / Fault 1", value="Skärmbyte / Screen Replacement")
        price_1 = st.number_input("Pris 1 (Kr)", min_value=0.0, step=50.0, value=0.0)
    with col_b:
        fault_2 = st.text_input("Beskrivning av fel 2 / Fault 2 (Valfri)", value="")
        price_2 = st.number_input("Pris 2 (Kr)", min_value=0.0, step=50.0, value=0.0)
        
    total_price = price_1 + price_2
    st.markdown(f"### 💰 **Summa / Total: {total_price:.2f} Kr**")
    
    if st.button("Generera PDF Kostnadsförslag / Generate PDF Quote", type="primary"):
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)
        p.drawString(50, 800, "30 MINUTES FIX AB - KOSTNADSFÖRSLAG")
        p.drawString(50, 770, f"Kund / Customer: {c_name}")
        p.drawString(50, 740, f"Enhet / Device: {device}")
        p.drawString(50, 700, f"1. {fault_1} - {price_1} Kr")
        if fault_2:
            p.drawString(50, 670, f"2. {fault_2} - {price_2} Kr")
        p.drawString(50, 630, f"Totalt / Total Summa: {total_price} Kr (inkl. moms)")
        p.showPage()
        p.save()
        buffer.seek(0)
        st.success("✅ Kostnadsförslag PDF skapats! / Quote PDF generated!")
        st.download_button("📥 Ladda ner PDF / Download PDF", buffer, file_name="kostnadsforslag.pdf", mime="application/pdf")

# --- 3. FAKTURA / INVOICE ---
elif menu == "📄 Faktura / Invoice":
    st.header("📄 Skapa Professionell Faktura / Create Professional Invoice")
    
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        st.subheader("📍 Företags-/Kunduppgifter")
        f_name = st.text_input("Företag / Kundens namn / Company or Customer Name")
        f_org = st.text_input("Org.nr / Personnummer (Optional)")
        f_address = st.text_input("Adress / Address")
    with col_f2:
        st.subheader("🧾 Fakturadetaljer")
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
    
    if st.button("Skapa Faktura PDF / Create Invoice PDF", type="primary"):
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)
        p.drawString(50, 800, "30 MINUTES FIX AB - FAKTURA")
        p.drawString(50, 770, f"Fakturanr: {invoice_no} | Datum: {invoice_date}")
        p.drawString(50, 740, f"Kund: {f_name} ({f_address})")
        p.drawString(50, 700, f"Beskrivning: {item_desc} (Antal: {item_qty})")
        p.drawString(50, 670, f"Netto: {netto:.2f} Kr | Moms (25%): {moms:.2f} Kr")
        p.drawString(50, 640, f"Att betala Totalt: {total_amount:.2f} Kr")
        p.drawString(50, 600, "Betalning via Swish eller Bankgiro.")
        p.showPage()
        p.save()
        buffer.seek(0)
        st.success("✅ Faktura PDF skapad! / Invoice PDF generated!")
        st.download_button("📥 Ladda ner Faktura PDF / Download Invoice PDF", buffer, file_name=f"{invoice_no}.pdf", mime="application/pdf")

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
    st.header("💳 Hantera Abonnemang & Villkor / Subscriptions & Terms")
    
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        st.subheader("👤 Kunduppgifter / Customer Info")
        sub_name = st.text_input("Kundens namn / Customer Name")
        sub_phone = st.text_input("Telefonnummer / Phone Number")
        sub_email = st.text_input("E-post / Email (Valfritt)")
    with col_s2:
        st.subheader("📱 Enhetsuppgifter / Device Info")
        sub_device = st.text_input("Enhet / Modell / Device Model")
        sub_imei = st.text_input("IMEI-nummer / IMEI Number")
        branch = st.selectbox("Butik / Branch", ["Eskilstuna", "Västerås"])

    st.markdown("---")
    st.subheader("📦 Välj Paket & Månadskostnad / Select Plan & Payment")
    
    plan_type = st.selectbox("Välj Abonnemangstyp / Select Plan", [
        "GlassGuard Pro (Skärmskydd + Fria Byte) - 149 Kr/mån",
        "Case & Screen Protection (Skal + Skärmskydd) - 199 Kr/mån",
        "Teknik Complete (Fullständigt skydd & service) - 299 Kr/mån"
    ])
    
    sub_price = st.number_input("Månadskostnad / Monthly Payment (Kr)", min_value=0.0, step=10.0, value=149.0)
    payment_method = st.radio("Betalningsmetod / Payment Method", ["Autogiro / Månadsvis", "Kortbetalning", "Swish Månadsvis"])

    # --- الشروط الرسمية (بما فيها شرط الـ 3 أشهر للإلغاء أو التغيير) ---
    st.markdown("---")
    st.subheader("📜 Avtalsvillkor & Regler / Subscription Terms & Rules")
    
    st.info("""
    **Svenska (Villkor):**
    1. **Bindningstid:** Abonnemanget har en minsta bindningstid på 3 månader.
    2. **Uppsägning & Byte av enhet:** Om du vill säga upp abonnemanget eller byta registrerad enhet/IMEI måste du meddela oss senast **3 månader i förväg**.
    3. **Betalning:** Månadsavgiften betalas varje månad i förskott.
    4. **Giltighet:** Skyddet och servicen gäller endast för den registrerade enheten kopplad till IMEI-numret ovan.
    
    ---
    **English (Terms):**
    1. **Binding Period:** Minimum contract period is 3 months.
    2. **Cancellation & Device Change:** To cancel the subscription or replace the registered device/IMEI, you must notify us **3 months in advance**.
    3. **Payment:** Monthly fee is paid in advance each month.
    4. **Validity:** Coverage applies strictly to the registered IMEI number listed above.
    """)
    
    agree_terms = st.checkbox("Kunden godkänner avtalsvillkoren / Customer accepts terms & conditions")

    if st.button("Spara Abonnemang / Save Subscription", type="primary"):
        if sub_name and sub_imei and agree_terms:
            conn, db_type = get_db_connection()
            start_date = datetime.now().strftime("%Y-%m-%d")
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            try:
                if db_type == "turso":
                    conn.execute(
                        "INSERT INTO subscriptions (branch, customer_name, phone, device, imei, plan_type, price, start_date, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (branch, sub_name, sub_phone, sub_device, sub_imei, plan_type, sub_price, start_date, created_at)
                    )
                else:
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO subscriptions (branch, customer_name, phone, device, imei, plan_type, price, start_date, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (branch, sub_name, sub_phone, sub_device, sub_imei, plan_type, sub_price, start_date, created_at)
                    )
                    conn.commit()
                    conn.close()
                st.success("✅ Abonnemanget har registrerats och sparats i molnet! / Saved to cloud successfully!")
            except Exception as e:
                st.error(f"❌ Fel vid sparande / Error: {e}")
        elif not agree_terms:
            st.warning("⚠️ Du måste bocka i att kunden godkänner villkoren. / Please confirm terms acceptance.")
        else:
            st.warning("⚠️ Fyll i namn och IMEI-nummer. / Enter customer name and IMEI.")
            
    st.markdown("---")
    st.subheader("📋 Aktiva Abonnemang i Molnet / Active Subscriptions")
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
                st.write(f"💳 **Kund:** {s[2]} | **Tel:** {s[3]} | **Device:** {s[4]} | **IMEI:** {s[5]} | **Paket:** {s[6]} | **Pris:** {s[7]} Kr/mån | **Start:** {s[8]}")
        else:
            st.info("Inga aktiva abonnemang registrerade ännu. / No active subscriptions found.")
    except Exception as e:
        st.warning("Laddar abonnemang... / Loading...")
