import streamlit as st
import streamlit_authenticator as stauth
import pandas as pd
import sqlite3
from datetime import date, timedelta
import io
import base64

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="30 Minutes Phone Fix CRM",
    page_icon="📱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- AUTHENTICATION SETUP (TUNAPARK LOGIN) ---
credentials = {
    'usernames': {
        'tunapark': {
            'name': 'Tunapark Admin',
            'password': stauth.Hasher.hash('tuna123')
        }
    }
}

authenticator = stauth.Authenticate(
    credentials,
    cookie_name='tunapark_crm_cookie',
    key='tunapark_signature_key',
    cookie_expiry_days=30
)

try:
    # تم إخفاء كلمة المرور تلقائياً عبر واجهة تسجيل الدخول الآمنة
    authenticator.login('main')
    authentication_status = st.session_state.get('authentication_status')
    name = st.session_state.get('name')
    username = st.session_state.get('username')
except Exception as e:
    name, authentication_status, username = authenticator.login('تسجيل الدخول / Login', 'main')

if authentication_status == False:
    st.error('اسم المستخدم أو كلمة المرور غير صحيحة / Felaktigt användarnamn eller lösenord')
elif authentication_status == None:
    st.warning('الرجاء إدخال اسم المستخدم (tunapark) وكلمة المرور (tuna123) / Vänligen logga in')
elif authentication_status == True:

    authenticator.logout('تسجيل الخروج / Logga ut', 'sidebar', key='logout_btn')
    
    # --- LANGUAGE SELECTOR ---
    lang = st.sidebar.radio("🌐 Language / اللغة", ["Svenska", "العربية"])

    # --- LOCALIZATION DICTIONARY ---
    if lang == "Svenska":
        txt = {
            "welcome": "Välkommen",
            "branch": "Välj butik / Branch",
            "tab_dash": "📊 Dashboard",
            "tab_repair": "🛠️ Inlämning / Reparationer",
            "tab_quote": "💡 Kostnadsförslag",
            "tab_invoice": "📄 Företagsfakturor",
            "tab_sub": "📦 Prenumerationer",
            "tab_buyback": "🔄 Uppköp / Buyback",
            "tab_campaign": "🎯 Kampanjer",
            "tab_preorder": "📋 Förbeställningar",
            "tab_stock": "📦 Lagerhantering",
            "tab_search": "🔍 Sök & Arkiv",
            "reset": "🔄 Återställ session",
            "comp_name": "Företagsnamn / Kund",
            "org_nr_cust": "Org.nr / VAT-nr",
            "phone": "Telefonnummer",
            "address": "Adress",
            "device": "Enhet / Modell",
            "issue": "Felbeskrivning / Åtgärd",
            "price": "Pris / Belopp (SEK)",
            "employee": "Handläggare / Anställd",
            "save_repair": "Spara inlämningskvitto",
            "success_repair": "Inlämnandet har sparats!",
            "preview": "Dokumentförhandsgranskning",
            "back_app": "Tillbaka till appen",
            "download_web": "Ladda ner som webbsida",
            "inv_no": "Fakturarummer",
            "total_amt": "Totalt belopp (SEK)",
            "inv_type": "Fakturatyp (B2B)",
            "create_inv": "Skapa och förhandsgranska faktura",
            "success_inv": "Fakturan har sparats!",
            "search_q": "Sök på namn, org.nr, enhet eller nummer...",
            "select_item_print": "Välj ID för att skriva ut eller visa:",
            "service_header": "⚙️ Välj fel och specifika reparationer (Pris per del)",
            "sub_plan": "Prenumerationstyp / Plan",
            "buy_model": "Enhet / Skick (Gradering A/B/C)",
            "camp_name": "Kampanjnamn / Rabatt",
            "pre_item": "Förbeställd produkt / Reservdel",
            "stock_part": "Artikelnamn / Reservdel",
            "stock_qty": "Antal i lager",
            "save": "Spara uppgifter",
            "saved_success": "Sparat framgångsrikt!"
        }
    else:
        txt = {
            "welcome": "مرحباً بك",
            "branch": "اختر الفرع",
            "tab_dash": "📊 لوحة التحكم",
            "tab_repair": "🛠️ الإصلاحات",
            "tab_quote": "💡 عرض سعر",
            "tab_invoice": "📄 فواتير الشركات (B2B)",
            "tab_sub": "📦 الاشتراكات",
            "tab_buyback": "🔄 شراء الأجهزة",
            "tab_campaign": "🎯 الحملات",
            "tab_preorder": "📋 الطلبات المسبقة",
            "tab_stock": "📦 المخزون",
            "tab_search": "🔍 البحث والأرشيف",
            "reset": "🔄 إعادة ضبط العرض",
            "comp_name": "اسم الشركة / العميل",
            "org_nr_cust": "رقم تسجيل الشركة Org.nr",
            "phone": "رقم الهاتف",
            "address": "العنوان",
            "device": "نوع الجهاز / الموديل",
            "issue": "وصف العطل / الإجراء",
            "price": "السعر / المبلغ (SEK)",
            "employee": "اسم الموظف / المسؤول",
            "save_repair": "حفظ إيصال الإصلاح",
            "success_repair": "تم حفظ الإصلاح بنجاح!",
            "preview": "معاينة المستند",
            "back_app": "العودة إلى التطبيق",
            "download_web": "تحميل كملف ويب",
            "inv_no": "رقم الفاتورة",
            "total_amt": "المبلغ الإجمالي (SEK)",
            "inv_type": "نوع الفاتورة (B2B)",
            "create_inv": "إصدار ومعاينة الفاتورة",
            "success_inv": "تم إصدار الفاتورة بنجاح!",
            "search_q": "بحث بالاسم، رقم التسجيل، الجهاز أو الرقم...",
            "select_item_print": "اختر المعرف (ID) لطباعة أو عرض المستند:",
            "service_header": "⚙️ تحديد الأعطال وتكلفة كل قطعة منفصلة",
            "sub_plan": "نوع الاشتراكات / الخطة",
            "buy_model": "الجهاز المراد شراؤه / الحالة",
            "camp_name": "اسم الحملة التسويقية / العرض",
            "pre_item": "المنتج أو القطعة المطلوبة مسبقاً",
            "stock_part": "اسم القطعة أو المنتج بالمخزون",
            "stock_qty": "الكمية المتوفرة",
            "save": "حفظ البيانات",
            "saved_success": "تم الحفظ بنجاح!"
        }

    st.sidebar.markdown(f"**{txt['welcome']}:** {name}")

    # --- GLOBAL BRANCH & CONFIG ---
    global_branch = st.sidebar.selectbox(txt["branch"], ["Eskilstuna", "Västerås"])

    COMPANY_INFO = {
        "Eskilstuna": {
            "name": "30 Minutes Phone Fix Eskilstuna", 
            "address": "Gunborg Nymans Väg 2, 632 22 Eskilstuna", 
            "phone": "0700122444",
            "org_nr": "559370-8034",
            "moms_reg": "SE559370803401",
            "bankgiro": "123-4567"
        },
        "Västerås": {
            "name": "30 Minutes Phone Fix Västerås AB", 
            "address": "Gunborg Nymans Väg 2, 632 22 Eskilstuna", 
            "phone": "0700122444",
            "org_nr": "559537-1724",
            "moms_reg": "SE559537172401",
            "bankgiro": "765-4321"
        }
    }

    LOGO_PATH = "logo.png"

    def get_image_base64(path):
        try:
            with open(path, "rb") as img_file:
                return base64.b64encode(img_file.read()).decode('utf-8')
        except Exception:
            return ""

    logo_base64 = get_image_base64(LOGO_PATH)

    # --- DATABASE SETUP ---
    def get_db_connection():
        conn = sqlite3.connect("phoneshop_crm.db", check_same_thread=False)
        return conn

    def init_db():
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS repairs (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            branch TEXT, customer_name TEXT, phone TEXT, 
                            device TEXT, issue TEXT, price REAL, status TEXT, 
                            employee TEXT, created_at TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS invoices (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            branch TEXT, invoice_no TEXT, customer_name TEXT, 
                            customer_org TEXT, phone TEXT, address TEXT, amount REAL, moms REAL, 
                            invoice_type TEXT, employee TEXT, created_at TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS quotes (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            branch TEXT, customer_name TEXT, phone TEXT, 
                            device TEXT, issues TEXT, total REAL, profit REAL, 
                            employee TEXT, created_at TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS subscriptions (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            branch TEXT, customer_name TEXT, phone TEXT, 
                            plan TEXT, price REAL, employee TEXT, created_at TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS buyback (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            branch TEXT, customer_name TEXT, phone TEXT, 
                            device TEXT, payout REAL, employee TEXT, created_at TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS campaigns (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            branch TEXT, campaign_name TEXT, discount TEXT, 
                            start_date TEXT, end_date TEXT, employee TEXT, created_at TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS preorders (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            branch TEXT, customer_name TEXT, phone TEXT, 
                            item TEXT, deposit REAL, employee TEXT, created_at TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS stock (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            branch TEXT, part_name TEXT, category TEXT, 
                            quantity INTEGER, price REAL, employee TEXT, created_at TEXT)''')

        for table, col, col_type in [
            ("invoices", "invoice_type", "TEXT"), 
            ("invoices", "customer_org", "TEXT")
        ]:
            try:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")
            except sqlite3.OperationalError:
                pass

        conn.commit()
        conn.close()

    init_db()

    def format_price(val):
        try:
            f_val = float(val)
            return str(int(f_val))
        except:
            return str(val)

    # --- DOCUMENT GENERATOR WITH ITEMIZED COSTS AND TOTAL SUM ---
    def generate_html_document(doc_type, data, company_info):
        branch_info = company_info.get(data['branch'], company_info["Eskilstuna"])
        raw_amount = data.get('price', data.get('amount', data.get('total', data.get('payout', data.get('deposit', 0)))))
        formatted_total = format_price(raw_amount)
        uniq_id = data.get('repair_id', data.get('invoice_no', data.get('id', '30MIN-001')))
        cust_org_display = f"<br><strong>Org.nr / VAT:</strong> {data.get('customer_org', 'N/A')}" if doc_type == 'Faktura' and data.get('customer_org') else ""
        
        items = data.get('items_breakdown', [])
        if items:
            rows_html = "".join([f"<tr><td>{item['name']}</td><td style='text-align: right;'>{format_price(item['price'])} SEK</td></tr>" for item in items])
        else:
            issue_desc = data.get('issue', data.get('issues', data.get('plan', data.get('item', data.get('campaign_name', 'Service')))))
            rows_html = f"<tr><td>{issue_desc}</td><td style='text-align: right;'>{formatted_total} SEK</td></tr>"

        terms_html = """
        <div class="terms">
            <strong>Villkor & Apple Service Villkor (Repair Terms & Conditions):</strong><br>
            1. Enheten lämnas in på egen risk. Kunden ansvarar för att säkerhetskopiera data (Backup) innan reparation.<br>
            2. 30 Minutes Phone Fix lämnar 3 månaders garanti på utbytta reservdelar (gäller ej fuktskadade eller handhavandeskadade enheter).<br>
            3. Vid Apple-enheter (iPhone/iPad/Mac) rekommenderas att "Hitta min iPhone" (Find My) stängs av före inlämning.<br>
            4. Ej uthämtade enheter efter 90 dagar tillfaller verkstaden enligt svensk lag om kvarglömd egendom.
        </div>
        """

        signature_block = f"""
        <table class="sig-table">
            <tr>
                <td>Kundens undersökningsgodkännande / Signatur:<br><br>________________________________________</td>
                <td>Handläggares signatur ({data.get('employee', 'Admin')}):<br><br>________________________________________</td>
            </tr>
        </table>
        """

        single_receipt_content = f"""
            <table class="header-table">
                <tr>
                    <td>
                        <img src="data:image/png;base64,{logo_base64}" alt="Logo" class="logo">
                        <p class="company-title">30 Minutes Phone Fix</p>
                        <p style="margin: 4px 0; font-size: 13px;"><strong>{branch_info['name']}</strong></p>
                        <p style="margin: 2px 0; font-size: 11px; color: #555;">
                            Adress: {branch_info['address']}<br>
                            Org.nr: {branch_info['org_nr']} | Momsreg: {branch_info['moms_reg']}<br>
                            Tel: {branch_info['phone']} | Bankgiro: {branch_info['bankgiro']}
                        </p>
                    </td>
                    <td style="text-align: right;">
                        <p class="invoice-title">{doc_type.upper()}</p>
                        <p style="margin: 4px 0; font-size: 13px; color: #d9534f;"><strong>ID / Ref:</strong> {uniq_id}</p>
                        <p style="margin: 2px 0; font-size: 12px;"><strong>Datum:</strong> {data.get('created_at', date.today())}</p>
                    </td>
                </tr>
            </table>

            <div class="meta-box">
                <table>
                    <tr>
                        <td><strong>Kund / Företag:</strong> {data.get('customer_name', 'N/A')} {cust_org_display}</td>
                        <td><strong>Telefon:</strong> {data.get('phone', 'N/A')}</td>
                    </tr>
                    <tr>
                        <td colspan="2"><strong>Enhet / Modell:</strong> {data.get('device', data.get('item', data.get('address', 'N/A')))}</td>
                    </tr>
                </table>
            </div>

            <table class="details-table">
                <thead>
                    <tr>
                        <th>Åtgärd / Beskrivning (Service & Parts)</th>
                        <th style="text-align: right;">Pris (SEK inkl. moms)</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                    <tr style="background-color: #f8f9fa;">
                        <td><strong>Totalt belopp (Total Summa):</strong></td>
                        <td style="text-align: right;"><strong>{formatted_total} SEK</strong></td>
                    </tr>
                </tbody>
            </table>

            {terms_html}
            {signature_block}
        """

        html_content = f"""
        <!DOCTYPE html>
        <html lang="sv">
        <head>
            <meta charset="UTF-8">
            <title>{doc_type.upper()} - {uniq_id}</title>
            <style>
                body {{ font-family: Helvetica, Arial, sans-serif; padding: 20px; color: #222; background: #fff; margin: 0; font-size: 12px; }}
                .header-table {{ width: 100%; border-collapse: collapse; margin-bottom: 15px; border-bottom: 1.5px solid #007AFF; padding-bottom: 10px; }}
                .header-table td {{ vertical-align: top; }}
                .logo {{ max-height: 50px; max-width: 150px; margin-bottom: 8px; object-fit: contain; }}
                .company-title {{ font-size: 16px; font-weight: bold; color: #007AFF; margin: 0; }}
                .invoice-title {{ font-size: 20px; font-weight: bold; text-align: right; color: #333; margin: 0; }}
                .meta-box {{ background: #f8f9fa; padding: 10px; border-radius: 4px; margin-bottom: 15px; border: 1px solid #e9ecef; }}
                .meta-box table {{ width: 100%; border-collapse: collapse; }}
                .meta-box td {{ padding: 3px; font-size: 12px; }}
                .details-table {{ width: 100%; border-collapse: collapse; margin-bottom: 15px; }}
                .details-table th, .details-table td {{ border: 1px solid #dee2e6; padding: 8px; text-align: left; font-size: 12px; }}
                .details-table th {{ background-color: #f1f3f5; color: #333; }}
                .terms {{ font-size: 9px; color: #666; margin-bottom: 15px; line-height: 1.3; border-left: 3px solid #007AFF; padding-left: 8px; }}
                .sig-table {{ width: 100%; margin-top: 15px; border-collapse: collapse; font-size: 11px; }}
                .sig-table td {{ width: 50%; padding: 5px; vertical-align: bottom; }}
                .copy-tag {{ font-weight: bold; color: #007AFF; font-size: 11px; text-transform: uppercase; margin-bottom: 5px; }}
                .cut-line {{ border-top: 2px dashed #bbb; margin: 25px 0; position: relative; }}
                .cut-text {{ position: absolute; top: -10px; left: 50%; transform: translateX(-50%); background: #fff; padding: 0 10px; font-size: 10px; color: #777; }}
            </style>
        </head>
        <body>
            <div class="copy-tag">📱 1. KUNDENS EXEMPLAR (Customer Copy)</div>
            {single_receipt_content}

            <div class="cut-line">
                <span class="cut-text">Klipp här / Vik här (Kvitto för Butik & Kund)</span>
            </div>

            <div class="copy-tag">📂 2. BUTIKENS EXEMPLAR (Store Archive Copy)</div>
            {single_receipt_content}
        </body>
        </html>
        """
        return html_content

    def display_document_preview(html_content, file_name, key_suffix):
        st.markdown(f"### 📄 {txt['preview']}")
        col_back, col_web = st.columns([1, 1])
        with col_back:
            if st.button(f"🔙 {txt['back_app']}", type="primary", key=f"back_app_btn_{key_suffix}"):
                if 'active_doc' in st.session_state:
                    del st.session_state['active_doc']
                st.rerun()
        with col_web:
            st.download_button(
                label=f"🌐 {txt['download_web']}",
                data=html_content,
                file_name=file_name,
                mime="text/html",
                key=f"download_web_btn_{key_suffix}"
            )
        st.components.v1.html(html_content, height=650, scrolling=True)

    if st.sidebar.button(txt["reset"]):
        if 'active_doc' in st.session_state:
            del st.session_state['active_doc']
        st.rerun()

    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10 = st.tabs([
        txt["tab_dash"], txt["tab_repair"], txt["tab_quote"], txt["tab_invoice"], 
        txt["tab_sub"], txt["tab_buyback"], txt["tab_campaign"], txt["tab_preorder"], txt["tab_stock"], txt["tab_search"]
    ])

    with tab1:
        st.header(f"{txt['tab_dash']} ({global_branch})")
        conn = get_db_connection()
        rep_count = pd.read_sql_query("SELECT COUNT(*) FROM repairs WHERE branch = ?", conn, params=(global_branch,)).iloc[0,0]
        inv_count = pd.read_sql_query("SELECT COUNT(*) FROM invoices WHERE branch = ?", conn, params=(global_branch,)).iloc[0,0]
        quote_count = pd.read_sql_query("SELECT COUNT(*) FROM quotes WHERE branch = ?", conn, params=(global_branch,)).iloc[0,0]
        stock_count = pd.read_sql_query("SELECT SUM(quantity) FROM stock WHERE branch = ?", conn, params=(global_branch,)).iloc[0,0]
        conn.close()

        col_d1, col_d2, col_d3, col_d4 = st.columns(4)
        col_d1.metric("🛠️ Total Repairs", rep_count)
        col_d2.metric("📄 B2B Invoices", inv_count)
        col_d3.metric("💡 Quotes", quote_count)
        col_d4.metric("📦 Stock Items", stock_count if stock_count else 0)

    with tab2:
        st.header(f"{txt['tab_repair']} ({global_branch})")
        if 'active_doc' in st.session_state and st.session_state['active_doc'].get('key', '').startswith('rep_new_'):
            display_document_preview(st.session_state['active_doc']['html'], st.session_state['active_doc']['filename'], st.session_state['active_doc']['key'])
        else:
            with st.form("repair_form"):
                c_name = st.text_input(txt["comp_name"])
                c_phone = st.text_input(txt["phone"])
                c_device = st.text_input(txt["device"])
                
                st.markdown(f"### {txt['service_header']}")
                col1, col2 = st.columns(2)
                with col1:
                    chk_display = st.checkbox("📱 Skärmbyte (Display)")
                    p_display = st.number_input("Pris: Skärmbyte (SEK)", min_value=0.0, step=50.0, key="p_disp")
                    
                    chk_battery = st.checkbox("🔋 Batteribyte (Battery)")
                    p_battery = st.number_input("Pris: Batteribyte (SEK)", min_value=0.0, step=50.0, key="p_batt")
                    
                    chk_camera = st.checkbox("📷 Kamerabyte / Kameralins (Camera)")
                    p_camera = st.number_input("Pris: Kamerabyte (SEK)", min_value=0.0, step=50.0, key="p_cam")
                
                with col2:
                    chk_charger = st.checkbox("🔌 Laddkontakt (Charging Port)")
                    p_charger = st.number_input("Pris: Laddkontakt (SEK)", min_value=0.0, step=50.0, key="p_charg")
                    
                    chk_back = st.checkbox("🔍 Baksida glas (Back Glass)")
                    p_back = st.number_input("Pris: Baksida glas (SEK)", min_value=0.0, step=50.0, key="p_bg")
                    
                    chk_water = st.checkbox("💧 Vattenskada (Water Damage)")
                    p_water = st.number_input("Pris: Vattenskada (SEK)", min_value=0.0, step=50.0, key="p_wat")

                st.markdown("---")
                c_issue_extra = st.text_area("Övrig felbeskrivning / Extra arbete")
                p_extra = st.number_input("Pris: Övrigt arbete (SEK)", min_value=0.0, step=50.0, key="p_ext")
                c_emp = st.text_input(txt["employee"])
                
                submitted = st.form_submit_button(txt["save_repair"])
                if submitted:
                    items_breakdown = []
                    if chk_display and p_display > 0: items_breakdown.append({'name': '📱 Skärmbyte (Display)', 'price': p_display})
                    if chk_battery and p_battery > 0: items_breakdown.append({'name': '🔋 Batteribyte (Battery)', 'price': p_battery})
                    if chk_camera and p_camera > 0: items_breakdown.append({'name': '📷 Kamerabyte / Kameralins', 'price': p_camera})
                    if chk_charger and p_charger > 0: items_breakdown.append({'name': '🔌 Laddkontakt (Charging Port)', 'price': p_charger})
                    if chk_back and p_back > 0: items_breakdown.append({'name': '🔍 Baksida glas (Back Glass)', 'price': p_back})
                    if chk_water and p_water > 0: items_breakdown.append({'name': '💧 Vattenskada sanering', 'price': p_water})
                    if c_issue_extra and p_extra > 0: items_breakdown.append({'name': f"Övrigt: {c_issue_extra}", 'price': p_extra})
                    
                    total_calculated = sum(item['price'] for item in items_breakdown)
                    summary_text = " | ".join([f"{item['name']} ({format_price(item['price'])} kr)" for item in items_breakdown]) if items_breakdown else "Allmän service"

                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO repairs (branch, customer_name, phone, device, issue, price, status, employee, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                   (global_branch, c_name, c_phone, c_device, summary_text, total_calculated, "Pending", c_emp, str(date.today())))
                    conn.commit()
                    last_id = cursor.lastrowid
                    conn.close()
                    
                    rec_data = {
                        "branch": global_branch, "repair_id": f"REP-{date.today().strftime('%Y%m%d')}-{last_id:03d}",
                        "customer_name": c_name, "phone": c_phone, "device": c_device,
                        "items_breakdown": items_breakdown, "price": total_calculated, "employee": c_emp,
                        "created_at": str(date.today())
                    }
                    html_doc = generate_html_document("Inlämningskvitto", rec_data, COMPANY_INFO)
                    st.session_state['active_doc'] = {
                        'html': html_doc,
                        'filename': f"Inlamningskvitto_{last_id}.html",
                        'key': f"rep_new_{last_id}"
                    }
                    st.success(txt["success_repair"])
                    st.rerun()

    with tab3:
        st.header(f"{txt['tab_quote']} ({global_branch})")
        if 'active_doc' in st.session_state and st.session_state['active_doc'].get('key', '').startswith('quote_new_'):
            display_document_preview(st.session_state['active_doc']['html'], st.session_state['active_doc']['filename'], st.session_state['active_doc']['key'])
        else:
            with st.form("quote_form"):
                q_name = st.text_input(txt["comp_name"], key="q_name")
                q_phone = st.text_input(txt["phone"], key="q_phone")
                q_device = st.text_input(txt["device"], key="q_device")
                
                st.markdown(f"### {txt['service_header']}")
                col_q1, col_q2 = st.columns(2)
                with col_q1:
                    q_chk_display = st.checkbox("📱 Skärmbyte (Display)", key="q_chk_disp")
                    qp_display = st.number_input("Pris: Skärmbyte (SEK)", min_value=0.0, step=50.0, key="qp_disp")
                    
                    q_chk_battery = st.checkbox("🔋 Batteribyte (Battery)", key="q_chk_batt")
                    qp_battery = st.number_input("Pris: Batteribyte (SEK)", min_value=0.0, step=50.0, key="qp_batt")
                    
                    q_chk_camera = st.checkbox("📷 Kamerabyte / Kameralins", key="q_chk_cam")
                    qp_camera = st.number_input("Pris: Kamerabyte (SEK)", min_value=0.0, step=50.0, key="qp_cam")
                
                with col_q2:
                    q_chk_charger = st.checkbox("🔌 Laddkontakt (Charging Port)", key="q_chk_charg")
                    qp_charger = st.number_input("Pris: Laddkontakt (SEK)", min_value=0.0, step=50.0, key="qp_charg")
                    
                    q_chk_back = st.checkbox("🔍 Baksida glas (Back Glass)", key="q_chk_bg")
                    qp_back = st.number_input("Pris: Baksida glas (SEK)", min_value=0.0, step=50.0, key="qp_bg")
                    
                    q_chk_water = st.checkbox("💧 Vattenskada (Water Damage)", key="q_chk_wat")
                    qp_water = st.number_input("Pris: Vattenskada (SEK)", min_value=0.0, step=50.0, key="qp_wat")

                st.markdown("---")
                q_extra = st.text_area("Övriga kommentarer / Felbeskrivning", key="q_extra")
                qp_extra = st.number_input("Pris: Övrigt arbete (SEK)", min_value=0.0, step=50.0, key="qp_ext")
                q_emp = st.text_input(txt["employee"], key="q_emp")
                
                q_sub = st.form_submit_button("Spara & Förhandsgranska Kostnadsförslag")
                if q_sub:
                    items_breakdown = []
                    if q_chk_display and qp_display > 0: items_breakdown.append({'name': '📱 Skärmbyte (Display)', 'price': qp_display})
                    if q_chk_battery and qp_battery > 0: items_breakdown.append({'name': '🔋 Batteribyte (Battery)', 'price': qp_battery})
                    if q_chk_camera and qp_camera > 0: items_breakdown.append({'name': '📷 Kamerabyte / Kameralins', 'price': qp_camera})
                    if q_chk_charger and qp_charger > 0: items_breakdown.append({'name': '🔌 Laddkontakt (Charging Port)', 'price': qp_charger})
                    if q_chk_back and qp_back > 0: items_breakdown.append({'name': '🔍 Baksida glas (Back Glass)', 'price': qp_back})
                    if q_chk_water and qp_water > 0: items_breakdown.append({'name': '💧 Vattenskada sanering', 'price': qp_water})
                    if q_extra and qp_extra > 0: items_breakdown.append({'name': f"Övrigt: {q_extra}", 'price': qp_extra})
                    
                    total_calculated = sum(item['price'] for item in items_breakdown)
                    summary_text = " | ".join([f"{item['name']} ({format_price(item['price'])} kr)" for item in items_breakdown]) if items_breakdown else "Allmän undersökning"
                    
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO quotes (branch, customer_name, phone, device, issues, total, profit, employee, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                   (global_branch, q_name, q_phone, q_device, summary_text, total_calculated, total_calculated * 0.3, q_emp, str(date.today())))
                    conn.commit()
                    last_id = cursor.lastrowid
                    conn.close()
                    
                    q_data = {
                        "branch": global_branch, "repair_id": f"QUO-{date.today().strftime('%Y%m%d')}-{last_id:03d}",
                        "customer_name": q_name, "phone": q_phone, "device": q_device, "items_breakdown": items_breakdown, "total": total_calculated,
                        "employee": q_emp, "created_at": str(date.today())
                    }
                    html_doc = generate_html_document("Kostnadsförslag", q_data, COMPANY_INFO)
                    st.session_state['active_doc'] = {
                        'html': html_doc,
                        'filename': f"Kostnadsforslag_{last_id}.html",
                        'key': f"quote_new_{last_id}"
                    }
                    st.success("Kostnadsförslag har sparats!")
                    st.rerun()

    with tab4:
        st.header(f"{txt['tab_invoice']} ({global_branch})")
        if 'active_doc' in st.session_state and st.session_state['active_doc'].get('key', '').startswith('inv_new_'):
            display_document_preview(st.session_state['active_doc']['html'], st.session_state['active_doc']['filename'], st.session_state['active_doc']['key'])
        else:
            with st.form("invoice_form"):
                i_no = st.text_input(txt["inv_no"], value=f"FAKT-{date.today().strftime('%Y%m%d')}-01")
                i_name = st.text_input(txt["comp_name"])
                i_org = st.text_input(txt["org_nr_cust"])
                i_phone = st.text_input(txt["phone"])
                i_addr = st.text_input(txt["address"])
                i_type = st.selectbox(txt["inv_type"], ["Inrikes (Sverige - 25% Moms)", "EU Företag (Reverse Charge)", "Export utanför EU"])
                i_desc = st.text_area(txt["issue"], value="Företagsreparation och reservdelar")
                i_amt = st.number_input(txt["total_amt"], min_value=0.0, step=50.0, format="%d")
                i_emp = st.text_input(txt["employee"])
                i_sub = st.form_submit_button(txt["create_inv"])
                if i_sub:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO invoices (branch, invoice_no, customer_name, customer_org, phone, address, amount, moms, invoice_type, employee, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                   (global_branch, i_no, i_name, i_org, i_phone, i_addr, i_amt, i_amt * 0.2 if "25%" in i_type else 0, i_type, i_emp, str(date.today())))
                    conn.commit()
                    last_id = cursor.lastrowid
                    conn.close()
                    
                    inv_data = {
                        "branch": global_branch, "repair_id": i_no, "customer_name": i_name,
                        "customer_org": i_org, "phone": i_phone, "address": i_addr, "issue": i_desc,
                        "amount": i_amt, "invoice_type": i_type, "employee": i_emp, "created_at": str(date.today())
                    }
                    html_doc = generate_html_document("Faktura", inv_data, COMPANY_INFO)
                    st.session_state['active_doc'] = {
                        'html': html_doc,
                        'filename': f"{i_no}.html",
                        'key': f"inv_new_{last_id}"
                    }
                    st.success(txt["success_inv"])
                    st.rerun()

    with tab5:
        st.header(f"📦 {txt['tab_sub']} ({global_branch})")
        with st.form("sub_form"):
            s_name = st.text_input(txt["comp_name"])
            s_phone = st.text_input(txt["phone"])
            s_plan = st.text_input(txt["sub_plan"], value="Företagsavtal - 12 Månader")
            s_price = st.number_input(txt["price"], min_value=0.0, step=50.0, format="%d")
            s_emp = st.text_input(txt["employee"])
            if st.form_submit_button(txt["save"]):
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("INSERT INTO subscriptions (branch, customer_name, phone, plan, price, employee, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                               (global_branch, s_name, s_phone, s_plan, s_price, s_emp, str(date.today())))
                conn.commit()
                conn.close()
                st.success(txt["saved_success"])

    with tab6:
        st.header(f"🔄 {txt['tab_buyback']} ({global_branch})")
        with st.form("buyback_form"):
            b_name = st.text_input(txt["comp_name"])
            b_phone = st.text_input(txt["phone"])
            b_device = st.text_input(txt["buy_model"], value="iPhone 13 - Grade A")
            b_payout = st.number_input(txt["price"], min_value=0.0, step=50.0, format="%d")
            b_emp = st.text_input(txt["employee"])
            if st.form_submit_button(txt["save"]):
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("INSERT INTO buyback (branch, customer_name, phone, device, payout, employee, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                               (global_branch, b_name, b_phone, b_device, b_payout, b_emp, str(date.today())))
                conn.commit()
                conn.close()
                st.success(txt["saved_success"])

    with tab7:
        st.header(f"🎯 {txt['tab_campaign']} ({global_branch})")
        with st.form("campaign_form"):
            cp_name = st.text_input(txt["camp_name"], value="Sommarrea 20% Rabatt")
            cp_disc = st.text_input("Rabatt / Detaljer", value="20% på alla skärmbyten")
            cp_start = st.date_input("Startdatum", date.today())
            cp_end = st.date_input("Slutdatum", date.today() + timedelta(days=30))
            cp_emp = st.text_input(txt["employee"])
            if st.form_submit_button(txt["save"]):
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("INSERT INTO campaigns (branch, campaign_name, discount, start_date, end_date, employee, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                               (global_branch, cp_name, cp_disc, str(cp_start), str(cp_end), cp_emp, str(date.today())))
                conn.commit()
                conn.close()
                st.success(txt["saved_success"])

    with tab8:
        st.header(f"📋 {txt['tab_preorder']} ({global_branch})")
        with st.form("preorder_form"):
            p_name = st.text_input(txt["comp_name"])
            p_phone = st.text_input(txt["phone"])
            p_item = st.text_input(txt["pre_item"], value="iPhone 16 Pro Max Reservdel")
            p_dep = st.number_input("Handpenning / Deposit (SEK)", min_value=0.0, step=50.0, format="%d")
            p_emp = st.text_input(txt["employee"])
            if st.form_submit_button(txt["save"]):
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("INSERT INTO preorders (branch, customer_name, phone, item, deposit, employee, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                               (global_branch, p_name, p_phone, p_item, p_dep, p_emp, str(date.today())))
                conn.commit()
                conn.close()
                st.success(txt["saved_success"])

    with tab9:
        st.header(f"📦 {txt['tab_stock']} ({global_branch})")
        with st.form("stock_form"):
            st_part = st.text_input(txt["stock_part"], value="iPhone 14 Skärm OLED")
            st_cat = st.selectbox("Kategori", ["Skärmar (Displays)", "Batterier (Batteries)", "Laddkontakter (Charging Ports)", "Tillbehör (Accessories)"])
            st_qty = st.number_input(txt["stock_qty"], min_value=0, step=1, value=10)
            st_price = st.number_input(txt["price"], min_value=0.0, step=50.0, format="%d")
            st_emp = st.text_input(txt["employee"])
            if st.form_submit_button(txt["save"]):
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("INSERT INTO stock (branch, part_name, category, quantity, price, employee, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                               (global_branch, st_part, st_cat, st_qty, st_price, st_emp, str(date.today())))
                conn.commit()
                conn.close()
                st.success(txt["saved_success"])

    with tab10:
        st.header(f"{txt['tab_search']} ({global_branch})")
        if 'active_doc' in st.session_state and not st.session_state['active_doc'].get('key', '').startswith(('rep_new_', 'quote_new_', 'inv_new_')):
            doc_info = st.session_state['active_doc']
            if st.button(f"🔙 {txt['back_app']}", type="primary", key="top_back_nav_search"):
                del st.session_state['active_doc']
                st.rerun()
            display_document_preview(doc_info['html'], doc_info['filename'], doc_info['key'])
        else:
            search_query = st.text_input(txt["search_q"], key="global_search_input")
            conn = get_db_connection()
            q_like = f"%{search_query}%" if search_query else "%"

            st.subheader("📄 Företagsfakturor Arkiv")
            inv_res = pd.read_sql_query("SELECT id, invoice_no, customer_name, customer_org, phone, amount, invoice_type, created_at FROM invoices WHERE branch = ? AND (customer_name LIKE ? OR customer_org LIKE ? OR invoice_no LIKE ?)", conn, params=(global_branch, q_like, q_like, q_like))
            if not inv_res.empty:
                st.dataframe(inv_res, use_container_width=True)
                sel_inv = st.selectbox("🖨️ Välj Faktura ID:", inv_res['id'].tolist(), key="sel_inv_id")
                if sel_inv and st.button("📄 Visa / Skriv ut Faktura", key=f"btn_inv_{sel_inv}"):
                    row = inv_res[inv_res['id'] == sel_inv].iloc[0]
                    doc_data = {"branch": global_branch, "repair_id": row['invoice_no'], "customer_name": row['customer_name'], "customer_org": row['customer_org'], "phone": row['phone'], "issue": "Företagsreparation", "amount": row['amount'], "created_at": str(row['created_at'])[:10]}
                    html = generate_html_document("Faktura", doc_data, COMPANY_INFO)
                    st.session_state['active_doc'] = {'html': html, 'filename': f"{row['invoice_no']}.html", 'key': f"search_inv_{sel_inv}"}
                    st.rerun()

            st.subheader("🛠️ Reparationer Arkiv")
            rep_res = pd.read_sql_query("SELECT id, customer_name, phone, device, issue, price, created_at FROM repairs WHERE branch = ? AND (customer_name LIKE ? OR device LIKE ? OR phone LIKE ?)", conn, params=(global_branch, q_like, q_like, q_like))
            if not rep_res.empty:
                st.dataframe(rep_res, use_container_width=True)
                sel_rep = st.selectbox("🖨️ Välj Inlämning ID:", rep_res['id'].tolist(), key="sel_rep_id")
                if sel_rep and st.button("📄 Visa / Skriv ut Inlämningskvitto", key=f"btn_rep_{sel_rep}"):
                    row = rep_res[rep_res['id'] == sel_rep].iloc[0]
                    doc_data = {"branch": global_branch, "repair_id": f"REP-{str(row['created_at'])[:10].replace('-','')}-{sel_rep:03d}", "customer_name": row['customer_name'], "phone": row['phone'], "device": row['device'], "issue": row['issue'], "price": row['price'], "created_at": str(row['created_at'])[:10]}
                    html = generate_html_document("Inlämningskvitto", doc_data, COMPANY_INFO)
                    st.session_state['active_doc'] = {'html': html, 'filename': f"Inlamningskvitto_{sel_rep}.html", 'key': f"search_rep_{sel_rep}"}
                    st.rerun()

            st.subheader("💡 Kostnadsförslag Arkiv")
            quote_res = pd.read_sql_query("SELECT id, customer_name, phone, device, issues, total, created_at FROM quotes WHERE branch = ? AND (customer_name LIKE ? OR device LIKE ?)", conn, params=(global_branch, q_like, q_like))
            if not quote_res.empty:
                st.dataframe(quote_res, use_container_width=True)
                sel_q = st.selectbox("🖨️ Välj Kostnadsförslag ID:", quote_res['id'].tolist(), key="sel_q_id")
                if sel_q and st.button("📄 Visa / Skriv ut Kostnadsförslag", key=f"btn_q_{sel_q}"):
                    row = quote_res[quote_res['id'] == sel_q].iloc[0]
                    doc_data = {"branch": global_branch, "repair_id": f"QUO-{str(row['created_at'])[:10].replace('-','')}-{sel_q:03d}", "customer_name": row['customer_name'], "phone": row['phone'], "device": row['device'], "issue": row['issues'], "total": row['total'], "created_at": str(row['created_at'])[:10]}
                    html = generate_html_document("Kostnadsförslag", doc_data, COMPANY_INFO)
                    st.session_state['active_doc'] = {'html': html, 'filename': f"Kostnadsforslag_{sel_q}.html", 'key': f"search_q_{sel_q}"}
                    st.rerun()

            st.subheader("📦 Lager (Stock)")
            stock_res = pd.read_sql_query("SELECT id, part_name, category, quantity, price, created_at FROM stock WHERE branch = ? AND part_name LIKE ?", conn, params=(global_branch, q_like))
            if not stock_res.empty:
                st.dataframe(stock_res, use_container_width=True)

            conn.close()
