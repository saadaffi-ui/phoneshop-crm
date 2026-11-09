import streamlit as st
import streamlit_authenticator as stauth
import pandas as pd
import sqlite3
from datetime import date, timedelta
import io
import base64
import json

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
    authenticator.login('main')
    authentication_status = st.session_state.get('authentication_status')
    name = st.session_state.get('name')
    username = st.session_state.get('username')
except Exception as e:
    name, authentication_status, username = authenticator.login('تسجيل الدخول / Login', 'main')

if authentication_status == False:
    st.error('اسم المستخدم أو كلمة المرور غير صحيحة / Felaktigt användarnamn eller lösenord')
elif authentication_status == None:
    st.warning('Vänligen logga in')
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
            "tab_buyback": "🔄 Uppköp / Kvittens (Buyback)",
            "tab_campaign": "🎯 Kampanjer",
            "tab_preorder": "📋 Förbeställningar",
            "tab_stock": "📦 Lagerhantering",
            "tab_schedule": "📅 Arbetsschema (Månad)",
            "tab_search": "🔍 Sök & Arkiv",
            "reset": "🔄 Återställ session",
            "comp_name": "Företagsnamn / Kund",
            "org_nr_cust": "Org.nr / VAT-nr / Personnummer",
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
            "download_web": "🌐 Öppna / Ladda ner dokument",
            "inv_no": "Fakturarummer",
            "total_amt": "Totalt belopp (SEK)",
            "inv_type": "Fakturatyp (B2B)",
            "create_inv": "Skapa och förhandsgranska faktura",
            "success_inv": "Fakturan har sparats!",
            "search_q": "Sök på namn, org.nr, personnummer, enhet eller nummer...",
            "select_item_print": "Välj ID för att skriva ut eller visa:",
            "service_header": "⚙️ Välj fel och specifika reparationer (Pris per del)",
            "sub_plan": "Prenumerationstyp / Plan",
            "buy_model": "Enhet / Skick (Gradering A/B/C) & IMEI-nr",
            "camp_name": "Kampanjnamn / Rabatt",
            "pre_item": "Förbeställd produkt / Reservdel",
            "stock_part": "Artikelnamn / Reservdel",
            "stock_qty": "Antal i lager",
            "save": "Spara uppgifter",
            "saved_success": "Sparat framgångsrikt!",
            "delete_btn": "🗑️ Radera post",
            "deleted_success": "Posten har raderats!",
            "recent_records": "Tidigare sparade poster i detta avsnitt:"
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
            "tab_buyback": "🔄 شراء الأجهزة / Kvittens (Buyback)",
            "tab_campaign": "🎯 الحملات",
            "tab_preorder": "📋 الطلبات المسبقة",
            "tab_stock": "📦 المخزون",
            "tab_schedule": "📅 جدول أوقات العمل (شهري)",
            "tab_search": "🔍 البحث والأرشيف",
            "reset": "🔄 إعادة ضبط العرض",
            "comp_name": "اسم العميل / البائع",
            "org_nr_cust": "رقم الهوية الشخصية (Personnummer) / Org.nr",
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
            "download_web": "🌐 فتح أو تحميل المستند مباشرة",
            "inv_no": "رقم الفاتورة",
            "total_amt": "المبلغ الإجمالي (SEK)",
            "inv_type": "نوع الفاتورة (B2B)",
            "create_inv": "إصدار ومعاينة الفاتورة",
            "success_inv": "تم إصدار الفاتورة بنجاح!",
            "search_q": "بحث بالاسم، رقم الهوية الشخصية، الجهاز أو الرقم...",
            "select_item_print": "اختر المعرف (ID) لطباعة أو عرض المستند:",
            "service_header": "⚙️ تحديد الأعطال وتكلفة كل قطعة منفصلة",
            "sub_plan": "نوع الاشتراكات / الخطة",
            "buy_model": "الجهاز المراد شراؤه / الحالة / رقم IMEI",
            "camp_name": "اسم الحملة التسويقية / العرض",
            "pre_item": "المنتج أو القطعة المطلوبة مسبقاً",
            "stock_part": "اسم القطعة أو المنتج بالمخزون",
            "stock_qty": "الكمية المتوفرة",
            "save": "حفظ البيانات",
            "saved_success": "تم الحفظ بنجاح!",
            "delete_btn": "🗑️ حذف السجل",
            "deleted_success": "تم حذف السجل بنجاح!",
            "recent_records": "السجلات المحفوظة حديثاً في هذا القسم:"
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

    # --- SAFE DATABASE SETUP WITH NON-DESTRUCTIVE MIGRATIONS ---
    def get_db_connection():
        conn = sqlite3.connect("phoneshop_crm.db", check_same_thread=False)
        return conn

    def delete_record_by_id(table_name, record_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(f"DELETE FROM {table_name} WHERE id = ?", (record_id,))
        conn.commit()
        conn.close()

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
                            branch TEXT, customer_name TEXT, person_nr TEXT, phone TEXT, 
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
        cursor.execute('''CREATE TABLE IF NOT EXISTS schedules (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            branch TEXT, employee_name TEXT, month_year TEXT, 
                            schedule_type TEXT, schedule_details TEXT, created_at TEXT)''')

        migrations = [
            ("invoices", "invoice_type", "TEXT"),
            ("invoices", "customer_org", "TEXT"),
            ("buyback", "person_nr", "TEXT"),
            ("schedules", "schedule_type", "TEXT")
        ]
        
        for table, col, col_type in migrations:
            cursor.execute(f"PRAGMA table_info({table})")
            existing_cols = [row[1] for row in cursor.fetchall()]
            if col not in existing_cols:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")

        conn.commit()
        conn.close()

    init_db()

    def format_price(val):
        try:
            f_val = float(val)
            return str(int(f_val))
        except:
            return str(val)

    # --- DOCUMENT GENERATOR (OPTIMIZED TO FIT EXACTLY ONE A4 PAGE) ---
    def generate_html_document(doc_type, data, company_info):
        branch_info = company_info.get(data['branch'], company_info["Eskilstuna"])
        raw_amount = data.get('price', data.get('amount', data.get('total', data.get('payout', data.get('deposit', 0)))))
        formatted_total = format_price(raw_amount)
        uniq_id = data.get('repair_id', data.get('invoice_no', data.get('id', '30MIN-001')))
        
        person_nr_display = f"<br><strong>Personnummer / ID:</strong> {data.get('person_nr', 'N/A')}" if doc_type.startswith('Kvittens') and data.get('person_nr') else ""
        cust_org_display = f"<br><strong>Org.nr / VAT:</strong> {data.get('customer_org', 'N/A')}" if doc_type == 'Faktura' and data.get('customer_org') else ""
        
        items = data.get('items_breakdown', [])
        if items:
            rows_html = "".join([f"<tr><td>{item['name']}</td><td style='text-align: right;'>{format_price(item['price'])} SEK</td></tr>" for item in items])
        else:
            issue_desc = data.get('issue', data.get('issues', data.get('plan', data.get('item', data.get('campaign_name', 'Service')))))
            rows_html = f"<tr><td>{issue_desc}</td><td style='text-align: right;'>{formatted_total} SEK</td></tr>"

        if doc_type.startswith('Kvittens'):
            terms_text = """
            <strong>Kvittens & Uppköpsvillkor (Buyback Terms & Conditions):</strong><br>
            1. Säljaren intygar härmed att enheten är hens lagliga egendom, är fri från operatörs- eller kontobindningar och inte är anmäld stulen.<br>
            2. Personnummer har lämnats i enlighet med svensk polislag för uppköp av begagnad elektronik.<br>
            3. Äganderätten till enheten övergår fullständigt till 30 Minutes Phone Fix vid utbetalning.
            """
        else:
            terms_text = """
            <strong>Villkor & Apple Service Villkor (Repair Terms & Conditions):</strong><br>
            1. Enheten lämnas in på egen risk. Kunden ansvarar för att säkerhetskopiera data innan reparation.<br>
            2. 30 Minutes Phone Fix lämnar 3 månaders garanti på utbytta reservdelar.<br>
            3. Vid Apple-enheter rekommenderas att "Hitta min iPhone" stängs av före inlämning.
            """

        terms_html = f'<div class="terms">{terms_text}</div>'

        signature_block = f"""
        <table class="sig-table">
            <tr>
                <td>Kundens / Säljarens signatur:<br><br>________________________________________</td>
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
                        <p style="margin: 2px 0; font-size: 11px;"><strong>{branch_info['name']}</strong></p>
                        <p style="margin: 1px 0; font-size: 10px; color: #555;">
                            Adress: {branch_info['address']}<br>
                            Org.nr: {branch_info['org_nr']} | Momsreg: {branch_info['moms_reg']}<br>
                            Tel: {branch_info['phone']} | Bankgiro: {branch_info['bankgiro']}
                        </p>
                    </td>
                    <td style="text-align: right;">
                        <p class="invoice-title">{doc_type.upper()}</p>
                        <p style="margin: 2px 0; font-size: 12px; color: #d9534f;"><strong>ID / Ref:</strong> {uniq_id}</p>
                        <p style="margin: 1px 0; font-size: 11px;"><strong>Datum:</strong> {data.get('created_at', date.today())}</p>
                    </td>
                </tr>
            </table>

            <div class="meta-box">
                <table>
                    <tr>
                        <td><strong>Kund / Säljare:</strong> {data.get('customer_name', 'N/A')} {person_nr_display} {cust_org_display}</td>
                        <td><strong>Telefon:</strong> {data.get('phone', 'N/A')}</td>
                    </tr>
                    <tr>
                        <td colspan="2"><strong>Detaljer / Enhet / Artikel:</strong> {data.get('device', data.get('item', data.get('address', 'N/A')))}</td>
                    </tr>
                </table>
            </div>

            <table class="details-table">
                <thead>
                    <tr>
                        <th>Beskrivning</th>
                        <th style="text-align: right;">Belopp (SEK)</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                    <tr style="background-color: #f8f9fa;">
                        <td><strong>Totalt belopp:</strong></td>
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
                @page {{ size: A4; margin: 10mm; }}
                body {{ font-family: Helvetica, Arial, sans-serif; padding: 10px; color: #222; background: #fff; margin: 0; font-size: 11px; line-height: 1.2; }}
                .page-container {{ max-width: 100%; margin: 0 auto; background: #fff; padding: 5px; }}
                .header-table {{ width: 100%; border-collapse: collapse; margin-bottom: 10px; border-bottom: 2px solid #007AFF; padding-bottom: 8px; }}
                .header-table td {{ vertical-align: top; }}
                .logo {{ max-height: 45px; max-width: 140px; margin-bottom: 4px; object-fit: contain; }}
                .company-title {{ font-size: 15px; font-weight: bold; color: #007AFF; margin: 0; }}
                .invoice-title {{ font-size: 18px; font-weight: bold; text-align: right; color: #333; margin: 0; }}
                .meta-box {{ background: #f8f9fa; padding: 8px; border-radius: 4px; margin-bottom: 10px; border: 1px solid #e9ecef; }}
                .meta-box table {{ width: 100%; border-collapse: collapse; }}
                .meta-box td {{ padding: 3px; font-size: 11px; }}
                .details-table {{ width: 100%; border-collapse: collapse; margin-bottom: 10px; }}
                .details-table th, .details-table td {{ border: 1px solid #dee2e6; padding: 6px; text-align: left; font-size: 11px; }}
                .details-table th {{ background-color: #f1f3f5; color: #333; }}
                .terms {{ font-size: 9px; color: #666; margin-bottom: 10px; line-height: 1.25; border-left: 3px solid #007AFF; padding-left: 6px; }}
                .sig-table {{ width: 100%; margin-top: 10px; border-collapse: collapse; font-size: 10px; }}
                .sig-table td {{ width: 50%; padding: 5px; vertical-align: bottom; }}
            </style>
        </head>
        <body>
            <div class="page-container">
                {single_receipt_content}
            </div>
        </body>
        </html>
        """
        return html_content

    # --- SCHEDULE PRINT DOCUMENT GENERATOR (A4 PRINTABLE) ---
    def generate_schedule_print_html(emp_name, branch, month_year, schedule_data, title_prefix):
        branch_info = COMPANY_INFO.get(branch, COMPANY_INFO["Eskilstuna"])
        rows_html = "".join([f"<tr><td>{k}</td><td style='text-align: right;'>{v}</td></tr>" for k, v in schedule_data.items()])
        
        html_content = f"""
        <!DOCTYPE html>
        <html lang="sv">
        <head>
            <meta charset="UTF-8">
            <title>Arbetsschema - {emp_name}</title>
            <style>
                @page {{ size: A4; margin: 15mm; }}
                body {{ font-family: Helvetica, Arial, sans-serif; color: #222; background: #fff; margin: 0; font-size: 12px; line-height: 1.4; }}
                .container {{ max-width: 100%; margin: 0 auto; }}
                .header {{ border-bottom: 2px solid #007AFF; padding-bottom: 10px; margin-bottom: 20px; width: 100%; }}
                .header table {{ width: 100%; border-collapse: collapse; }}
                .title {{ font-size: 20px; font-weight: bold; color: #007AFF; margin: 0; }}
                .sub-title {{ font-size: 14px; font-weight: bold; color: #333; margin: 5px 0; }}
                .table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
                .table th, .table td {{ border: 1px solid #dee2e6; padding: 8px 12px; font-size: 12px; text-align: left; }}
                .table th {{ background-color: #f1f3f5; color: #333; }}
                .footer {{ margin-top: 30px; font-size: 11px; text-align: center; color: #666; border-top: 1px solid #ddd; padding-top: 10px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <table>
                        <tr>
                            <td>
                                <p class="title">30 Minutes Phone Fix</p>
                                <p style="margin: 2px 0;"><strong>{branch_info['name']}</strong></p>
                                <p style="margin: 0; color: #555;">Org.nr: {branch_info['org_nr']} | Tel: {branch_info['phone']}</p>
                            </td>
                            <td style="text-align: right;">
                                <p class="sub-title">{title_prefix}</p>
                                <p style="margin: 2px 0;"><strong>Anställd / الموظف:</strong> {emp_name}</p>
                                <p style="margin: 0;"><strong>Månad / الشهر:</strong> {month_year}</p>
                            </td>
                        </tr>
                    </table>
                </div>

                <table class="table">
                    <thead>
                        <tr>
                            <th>Datum & Dag (التاريخ واليوم)</th>
                            <th style="text-align: right;">Arbetstid (وقت العمل)</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows_html}
                    </tbody>
                </table>

                <div class="footer">
                    <p>30 Minutes Phone Fix - Arbetsschema &bull; Utskriftsdatum: {date.today()}</p>
                </div>
            </div>
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
                label=txt["download_web"],
                data=html_content,
                file_name=file_name,
                mime="text/html",
                key=f"download_web_btn_{key_suffix}"
            )
        
        st.components.v1.html(html_content, height=620, scrolling=False)

    if st.sidebar.button(txt["reset"]):
        if 'active_doc' in st.session_state:
            del st.session_state['active_doc']
        st.rerun()

    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10, tab11 = st.tabs([
        txt["tab_dash"], txt["tab_repair"], txt["tab_quote"], txt["tab_invoice"], 
        txt["tab_sub"], txt["tab_buyback"], txt["tab_campaign"], txt["tab_preorder"], txt["tab_stock"], txt["tab_schedule"], txt["tab_search"]
    ])

    with tab1:
        st.header(f"{txt['tab_dash']} ({global_branch})")
        conn = get_db_connection()
        rep_count = pd.read_sql_query("SELECT COUNT(*) FROM repairs WHERE branch = ?", conn, params=(global_branch,)).iloc[0,0]
        inv_count = pd.read_sql_query("SELECT COUNT(*) FROM invoices WHERE branch = ?", conn, params=(global_branch,)).iloc[0,0]
        quote_count = pd.read_sql_query("SELECT COUNT(*) FROM quotes WHERE branch = ?", conn, params=(global_branch,)).iloc[0,0]
        buy_count = pd.read_sql_query("SELECT COUNT(*) FROM buyback WHERE branch = ?", conn, params=(global_branch,)).iloc[0,0]
        pre_count = pd.read_sql_query("SELECT COUNT(*) FROM preorders WHERE branch = ?", conn, params=(global_branch,)).iloc[0,0]
        conn.close()

        col_d1, col_d2, col_d3, col_d4 = st.columns(4)
        col_d1.metric("🛠️ Total Repairs", rep_count)
        col_d2.metric("📄 B2B Invoices", inv_count)
        col_d3.metric("💡 Quotes", quote_count)
        col_d4.metric("📋 Preorders", pre_count)

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

            st.markdown("---")
            st.subheader(txt["recent_records"])
            conn = get_db_connection()
            rep_df = pd.read_sql_query("SELECT id, customer_name, phone, device, price, created_at FROM repairs WHERE branch = ? ORDER BY id DESC LIMIT 5", conn, params=(global_branch,))
            conn.close()
            if not rep_df.empty:
                st.dataframe(rep_df, use_container_width=True)

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

            st.markdown("---")
            st.subheader(txt["recent_records"])
            conn = get_db_connection()
            quo_df = pd.read_sql_query("SELECT id, customer_name, phone, device, total, created_at FROM quotes WHERE branch = ? ORDER BY id DESC LIMIT 5", conn, params=(global_branch,))
            conn.close()
            if not quo_df.empty:
                st.dataframe(quo_df, use_container_width=True)

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

            st.markdown("---")
            st.subheader(txt["recent_records"])
            conn = get_db_connection()
            inv_df = pd.read_sql_query("SELECT id, invoice_no, customer_name, amount, invoice_type, created_at FROM invoices WHERE branch = ? ORDER BY id DESC LIMIT 5", conn, params=(global_branch,))
            conn.close()
            if not inv_df.empty:
                st.dataframe(inv_df, use_container_width=True)

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

        st.markdown("---")
        st.subheader(txt["recent_records"])
        conn = get_db_connection()
        sub_df = pd.read_sql_query("SELECT id, customer_name, phone, plan, price, created_at FROM subscriptions WHERE branch = ? ORDER BY id DESC LIMIT 5", conn, params=(global_branch,))
        conn.close()
        if not sub_df.empty:
            st.dataframe(sub_df, use_container_width=True)

    with tab6:
        st.header(f"{txt['tab_buyback']} ({global_branch})")
        if 'active_doc' in st.session_state and st.session_state['active_doc'].get('key', '').startswith('buy_new_'):
            display_document_preview(st.session_state['active_doc']['html'], st.session_state['active_doc']['filename'], st.session_state['active_doc']['key'])
        else:
            with st.form("buyback_form"):
                b_name = st.text_input(txt["comp_name"])
                b_person_nr = st.text_input(txt["org_nr_cust"], value="ÅÅMMDD-XXXX")
                b_phone = st.text_input(txt["phone"])
                b_device = st.text_input(txt["buy_model"], value="iPhone 13 - Grade A (IMEI: ...)")
                b_payout = st.number_input(txt["price"], min_value=0.0, step=50.0, format="%d")
                b_emp = st.text_input(txt["employee"])
                b_sub_btn = st.form_submit_button("Spara & Skriv ut Kvittens (Buyback)")
                if b_sub_btn:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO buyback (branch, customer_name, person_nr, phone, device, payout, employee, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                                   (global_branch, b_name, b_person_nr, b_phone, b_device, b_payout, b_emp, str(date.today())))
                    conn.commit()
                    last_id = cursor.lastrowid
                    conn.close()
                    
                    buy_data = {
                        "branch": global_branch, "repair_id": f"BUY-{date.today().strftime('%Y%m%d')}-{last_id:03d}",
                        "customer_name": b_name, "person_nr": b_person_nr, "phone": b_phone,
                        "device": b_device, "price": b_payout, "employee": b_emp,
                        "created_at": str(date.today())
                    }
                    html_doc = generate_html_document("Kvittens - Enhetsköp (Buyback)", buy_data, COMPANY_INFO)
                    st.session_state['active_doc'] = {
                        'html': html_doc,
                        'filename': f"Kvittens_Buyback_{last_id}.html",
                        'key': f"buy_new_{last_id}"
                    }
                    st.success("Kvittens har sparats framgångsrikt!")
                    st.rerun()

            st.markdown("---")
            st.subheader(txt["recent_records"])
            conn = get_db_connection()
            buy_df = pd.read_sql_query("SELECT id, customer_name, person_nr, device, payout, created_at FROM buyback WHERE branch = ? ORDER BY id DESC LIMIT 5", conn, params=(global_branch,))
            conn.close()
            if not buy_df.empty:
                st.dataframe(buy_df, use_container_width=True)

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

        st.markdown("---")
        st.subheader(txt["recent_records"])
        conn = get_db_connection()
        camp_df = pd.read_sql_query("SELECT id, campaign_name, discount, start_date, end_date, created_at FROM campaigns WHERE branch = ? ORDER BY id DESC LIMIT 5", conn, params=(global_branch,))
        conn.close()
        if not camp_df.empty:
            st.dataframe(camp_df, use_container_width=True)

    with tab8:
        st.header(f"📋 {txt['tab_preorder']} ({global_branch})")
        with st.form("preorder_form"):
            p_name = st.text_input(txt["comp_name"], key="pre_name")
            p_phone = st.text_input(txt["phone"], key="pre_phone")
            p_item = st.text_input(txt["pre_item"], value="iPhone 16 Pro Max Reservdel", key="pre_item_val")
            p_dep = st.number_input("Handpenning / Deposit (SEK)", min_value=0.0, step=50.0, format="%d", key="pre_dep")
            p_emp = st.text_input(txt["employee"], key="pre_emp")
            if st.form_submit_button(txt["save"]):
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("INSERT INTO preorders (branch, customer_name, phone, item, deposit, employee, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                               (global_branch, p_name, p_phone, p_item, p_dep, p_emp, str(date.today())))
                conn.commit()
                conn.close()
                st.success(txt["saved_success"])

        st.markdown("---")
        st.subheader(txt["recent_records"])
        conn = get_db_connection()
        pre_df = pd.read_sql_query("SELECT id, customer_name, phone, item, deposit, created_at FROM preorders WHERE branch = ? ORDER BY id DESC LIMIT 5", conn, params=(global_branch,))
        conn.close()
        if not pre_df.empty:
            st.dataframe(pre_df, use_container_width=True)

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

        st.markdown("---")
        st.subheader(txt["recent_records"])
        conn = get_db_connection()
        stock_df = pd.read_sql_query("SELECT id, part_name, category, quantity, price, created_at FROM stock WHERE branch = ? ORDER BY id DESC LIMIT 5", conn, params=(global_branch,))
        conn.close()
        if not stock_df.empty:
            st.dataframe(stock_df, use_container_width=True)

    with tab10:
        st.header(f"📅 {txt['tab_schedule']}")
        
        # Check active document preview for schedule printing if active
        if 'active_doc' in st.session_state and st.session_state['active_doc'].get('key', '').startswith('sch_print_'):
            display_document_preview(st.session_state['active_doc']['html'], st.session_state['active_doc']['filename'], st.session_state['active_doc']['key'])
        else:
            schedule_mode = st.radio("اختر القسم / Välj sektion", [
                "1️⃣ الأوقات المتاحة للموظفين (Availability)", 
                "2️⃣ خريطة حالة الأيام والتنبيهات (Color Map & Alerts)",
                "3️⃣ جدول العمل الفعلي المعتمد للمدير (Actual Schedule)"
            ])
            
            swedish_days = {
                "Monday": "Måndag", "Tuesday": "Tisdag", "Wednesday": "Onsdag",
                "Thursday": "Torsdag", "Friday": "Fredag", "Saturday": "Lördag", "Sunday": "Söndag"
            }
            today_date = date.today()

            if schedule_mode.startswith("1️⃣"):
                st.subheader("إدخال الأوقات المتاحة للموظف (ما يمكنه عمله)")
                with st.form("availability_form"):
                    col_a1, col_a2, col_a3 = st.columns(3)
                    with col_a1:
                        av_emp = st.selectbox("الموظف / Anställd", ["Ommar", "Hampik", "Saad", "Luay"], key="av_emp")
                    with col_a2:
                        av_branch = st.selectbox("الفرع / Butik", ["Eskilstuna", "Västerås"], key="av_branch")
                    with col_a3:
                        av_month = st.text_input("الشهر والسنة / Månad", value=today_date.strftime("%B %Y"), key="av_month")
                    
                    av_inputs = {}
                    st.markdown("### الأوقات المتاحة لكل يوم:")
                    for i in range(30):
                        curr_d = today_date + timedelta(days=i)
                        eng_w = curr_d.strftime("%A")
                        swe_w = swedish_days.get(eng_w, eng_w)
                        d_str = curr_d.strftime("%Y-%m-%d")
                        lbl = f"{swe_w} ({d_str})"
                        
                        c1, c2, c3 = st.columns([2, 2, 2])
                        with c1: st.markdown(f"**{lbl}**")
                        with c2: st_t = st.selectbox(f"AvStart {i}", ["10:00", "Ledig / Off", "09:00", "12:00"], key=f"av_st_{i}", label_visibility="collapsed")
                        with c3: en_t = st.selectbox(f"AvEnd {i}", ["20:00", "18:00", "16:00", "Ledig / Off"], key=f"av_en_{i}", label_visibility="collapsed")
                        av_inputs[lbl] = f"{st_t} - {en_t}"

                    if st.form_submit_button("حفظ الأوقات المتاحة / Spara tillgänglighet"):
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        cursor.execute("INSERT INTO schedules (branch, employee_name, month_year, schedule_type, schedule_details, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                                       (av_branch, av_emp, av_month, "Availability", json.dumps(av_inputs), str(today_date)))
                        conn.commit()
                        conn.close()
                        st.success("تم حفظ أوقات الموظف بنجاح!")
                        st.rerun()

                st.markdown("---")
                st.subheader("الأوقات المتاحة المحفوظة للموظفين:")
                conn = get_db_connection()
                av_df = pd.read_sql_query("SELECT id, employee_name, branch, month_year, schedule_details, created_at FROM schedules WHERE schedule_type = 'Availability' ORDER BY id DESC", conn)
                conn.close()
                if not av_df.empty:
                    for idx, row in av_df.iterrows():
                        with st.expander(f"👤 الموظف: {row['employee_name']} | الفرع: {row['branch']} | الشهر: {row['month_year']} (تاريخ: {row['created_at']})"):
                            try:
                                d_dict = json.loads(row['schedule_details'])
                                st.dataframe(pd.DataFrame(list(d_dict.items()), columns=["Datum & Dag", "Möjlig tid"]), use_container_width=True)
                            except:
                                st.write(row['schedule_details'])
                            if st.button("🗑️ حذف", key=f"del_av_{row['id']}"):
                                delete_record_by_id("schedules", row['id'])
                                st.success("تم الحذف بنجاح!")
                                st.rerun()

            elif schedule_mode.startswith("2️⃣"):
                st.subheader("🗺️ خريطة حالة الأيام والتنبيهات (Color Map & Alerts)")
                st.markdown("متابعة الأيام (رمادي = لم تُعَبأ بعد | أصفر = تم تعبئتها واعتمادها بنجاح)")
                
                conn = get_db_connection()
                act_df_check = pd.read_sql_query("SELECT schedule_details FROM schedules WHERE schedule_type = 'Actual'", conn)
                conn.close()
                
                filled_dates = set()
                unfilled_dates = []
                
                # Generate all 30 upcoming dates
                all_30_dates = []
                for i in range(30):
                    curr_d = today_date + timedelta(days=i)
                    eng_w = curr_d.strftime("%A")
                    swe_w = swedish_days.get(eng_w, eng_w)
                    d_str = curr_d.strftime("%Y-%m-%d")
                    all_30_dates.append(f"{swe_w} ({d_str})")

                if not act_df_check.empty:
                    for _, r in act_df_check.iterrows():
                        try:
                            d_dict = json.loads(r['schedule_details'])
                            for dk, dv in d_dict.items():
                                if " - " in dv and "Ledig" not in dv:
                                    filled_dates.add(dk)
                        except: pass

                for lbl in all_30_dates:
                    if lbl not in filled_dates:
                        unfilled_dates.append(lbl)

                # --- MANAGER ALERT IF DAYS ARE NOT FILLED ---
                if unfilled_dates:
                    st.warning(f"⚠️ **تنبيه للمدير:** يوجد {len(unfilled_dates)} أيام لم يتم تعبئتها أو اعتمادها بعد في جدول العمل الفعلي! يرجى مراجعتها وتعبئتها لكي لا تنسى.")
                else:
                    st.success("🎉 ممتاز! جميع أيام الشهر القادم معبأة ومعتمدة بالكامل.")

                cols_map = st.columns(5)
                for i, lbl in enumerate(all_30_dates):
                    is_filled = lbl in filled_dates
                    bg_color = "#ffeb3b" if is_filled else "#e0e0e0"
                    text_color = "#000"
                    status_text = "مُعبأ (Yellow)" if is_filled else "غير معبأ (Gray)"
                    
                    with cols_map[i % 5]:
                        st.markdown(f"""
                            <div style="background-color: {bg_color}; color: {text_color}; padding: 10px; border-radius: 8px; text-align: center; margin-bottom: 10px; border: 1px solid #ccc;">
                                <strong style="font-size: 11px;">{lbl}</strong><br><span style="font-size: 10px;">{status_text}</span>
                            </div>
                        """, unsafe_allow_html=True)

            else:
                st.subheader("📅 جدول العمل الفعلي المعتمد للمدير (فلترة الموظفين المتاحين فقط)")
                
                conn = get_db_connection()
                av_records = pd.read_sql_query("SELECT employee_name, branch, schedule_details FROM schedules WHERE schedule_type = 'Availability'", conn)
                conn.close()

                with st.form("actual_schedule_form"):
                    col_ac1, col_ac2, col_ac3 = st.columns(3)
                    with col_ac1:
                        ac_emp = st.selectbox("الموظف / Anställd", ["Ommar", "Hampik", "Saad", "Luay"], key="ac_emp")
                    with col_ac2:
                        ac_branch = st.selectbox("الفرع / Butik", ["Eskilstuna", "Västerås"], key="ac_branch")
                    with col_ac3:
                        ac_month = st.text_input("الشهر والسنة / Månad", value=today_date.strftime("%B %Y"), key="ac_month")
                    
                    ac_inputs = {}
                    st.markdown("### جدول العمل الفعلي المعتمد:")
                    
                    for i in range(30):
                        curr_d = today_date + timedelta(days=i)
                        eng_w = curr_d.strftime("%A")
                        swe_w = swedish_days.get(eng_w, eng_w)
                        d_str = curr_d.strftime("%Y-%m-%d")
                        lbl = f"{swe_w} ({d_str})"
                        
                        is_available = True
                        for _, av_row in av_records.iterrows():
                            if av_row['employee_name'] == ac_emp and av_row['branch'] == ac_branch:
                                try:
                                    av_dict = json.loads(av_row['schedule_details'])
                                    t_val = av_dict.get(lbl, "")
                                    if "Ledig" in t_val:
                                        is_available = False
                                except: pass

                        if is_available:
                            c1, c2, c3 = st.columns([2, 2, 2])
                            with c1: st.markdown(f"**{lbl}** ✅ متاح")
                            with c2: st_t = st.selectbox(f"AcStart {i}", ["10:00", "09:00", "12:00", "Ledig / Off"], key=f"ac_st_{i}", label_visibility="collapsed")
                            with c3: en_t = st.selectbox(f"AcEnd {i}", ["20:00", "18:00", "16:00", "Ledig / Off"], key=f"ac_en_{i}", label_visibility="collapsed")
                            ac_inputs[lbl] = f"{st_t} - {en_t}"
                        else:
                            ac_inputs[lbl] = "Ledig / Off"
                            st.markdown(f"<span style='color: gray;'>{lbl} ❌ غير متاح (تم استبعاده تلقائياً لعدم وجود توفر)</span>", unsafe_allow_html=True)

                    if st.form_submit_button("حفظ جدول العمل الفعلي / Spara fast schema"):
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        cursor.execute("INSERT INTO schedules (branch, employee_name, month_year, schedule_type, schedule_details, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                                       (ac_branch, ac_emp, ac_month, "Actual", json.dumps(ac_inputs), str(today_date)))
                        conn.commit()
                        conn.close()
                        st.success("تم حفظ جدول العمل الفعلي المعتمد بنجاح!")
                        st.rerun()

                st.markdown("---")
                st.subheader("جداول العمل الفعلي المعتمدة المحفوظة (مع خيارات الطباعة A4):")
                conn = get_db_connection()
                ac_df = pd.read_sql_query("SELECT id, employee_name, branch, month_year, schedule_details, created_at FROM schedules WHERE schedule_type = 'Actual' ORDER BY id DESC", conn)
                conn.close()
                if not ac_df.empty:
                    for idx, row in ac_df.iterrows():
                        with st.expander(f"👤 الموظف: {row['employee_name']} | الفرع: {row['branch']} | الشهر: {row['month_year']} (تاريخ: {row['created_at']})"):
                            try:
                                d_dict = json.loads(row['schedule_details'])
                                total_hours = 0.0
                                for day_key, val in d_dict.items():
                                    if " - " in val and "Ledig" not in val:
                                        parts = val.split(" - ")
                                        try:
                                            st_h, st_m = map(int, parts[0].split(":"))
                                            en_h, en_m = map(int, parts[1].split(":"))
                                            hrs = (en_h + en_m/60.0) - (st_h + st_m/60.0)
                                            if hrs > 0: total_hours += hrs
                                        except: pass

                                st.dataframe(pd.DataFrame(list(d_dict.items()), columns=["Datum & Dag", "Fast Arbetstid"]), use_container_width=True)
                                st.markdown(f"### ⏱️ إجمالي ساعات العمل الفعلية للشهر: **{total_hours:.1f} ساعة / Timmar**")
                                
                                # --- PRINT & EXPORT BUTTONS ---
                                col_p1, col_p2, col_p3 = st.columns(3)
                                with col_p1:
                                    if st.button("🖨️ معاينة وطباعة الشهر (A4)", key=f"print_month_{row['id']}"):
                                        html_print = generate_schedule_print_html(row['employee_name'], row['branch'], row['month_year'], d_dict, "MÅNADSSCHEMA (شهرى)")
                                        st.session_state['active_doc'] = {
                                            'html': html_print,
                                            'filename': f"Schema_Month_{row['employee_name']}.html",
                                            'key': f"sch_print_{row['id']}"
                                        }
                                        st.rerun()
                                with col_p2:
                                    # Filter first 7 days for weekly print example
                                    weekly_dict = dict(list(d_dict.items())[:7])
                                    if st.button("🖨️ طباعة أول أسبوع (A4)", key=f"print_week_{row['id']}"):
                                        html_print_w = generate_schedule_print_html(row['employee_name'], row['branch'], row['month_year'], weekly_dict, "VECKOSCHEMA (أسبوعي)")
                                        st.session_state['active_doc'] = {
                                            'html': html_print_w,
                                            'filename': f"Schema_Week_{row['employee_name']}.html",
                                            'key': f"sch_print_w_{row['id']}"
                                        }
                                        st.rerun()
                                with col_p3:
                                    if st.button("🗑️ حذف هذا الجدول", key=f"del_ac_{row['id']}"):
                                        delete_record_by_id("schedules", row['id'])
                                        st.success("تم الحذف بنجاح!")
                                        st.rerun()

                            except Exception as e:
                                st.write(row['schedule_details'])

    with tab11:
        st.header(f"{txt['tab_search']} ({global_branch})")
        if 'active_doc' in st.session_state and not st.session_state['active_doc'].get('key', '').startswith(('rep_new_', 'quote_new_', 'inv_new_', 'buy_new_', 'sch_print_')):
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
                col_inv_a, col_inv_b = st.columns([2, 1])
                with col_inv_a:
                    sel_inv = st.selectbox("🖨️ Välj Faktura ID:", inv_res['id'].tolist(), key="sel_inv_id")
                with col_inv_b:
                    if sel_inv and st.button("📄 Visa / Skriv ut", key=f"btn_inv_{sel_inv}"):
                        row = inv_res[inv_res['id'] == sel_inv].iloc[0]
                        doc_data = {"branch": global_branch, "repair_id": row['invoice_no'], "customer_name": row['customer_name'], "customer_org": row['customer_org'], "phone": row['phone'], "issue": "Företagsreparation", "amount": row['amount'], "created_at": str(row['created_at'])[:10]}
                        html = generate_html_document("Faktura", doc_data, COMPANY_INFO)
                        st.session_state['active_doc'] = {'html': html, 'filename': f"{row['invoice_no']}.html", 'key': f"search_inv_{sel_inv}"}
                        st.rerun()
                    if sel_inv and st.button(txt["delete_btn"], key=f"del_inv_{sel_inv}"):
                        delete_record_by_id("invoices", sel_inv)
                        st.success(txt["deleted_success"])
                        st.rerun()

            st.subheader("🛠️ Reparationer Arkiv")
            rep_res = pd.read_sql_query("SELECT id, customer_name, phone, device, issue, price, created_at FROM repairs WHERE branch = ? AND (customer_name LIKE ? OR device LIKE ? OR phone LIKE ?)", conn, params=(global_branch, q_like, q_like, q_like))
            if not rep_res.empty:
                st.dataframe(rep_res, use_container_width=True)
                col_rep_a, col_rep_b = st.columns([2, 1])
                with col_rep_a:
                    sel_rep = st.selectbox("🖨️ Välj Inlämning ID:", rep_res['id'].tolist(), key="sel_rep_id")
                with col_rep_b:
                    if sel_rep and st.button("📄 Visa / Skriv ut", key=f"btn_rep_{sel_rep}"):
                        row = rep_res[rep_res['id'] == sel_rep].iloc[0]
                        doc_data = {"branch": global_branch, "repair_id": f"REP-{str(row['created_at'])[:10].replace('-','')}-{sel_rep:03d}", "customer_name": row['customer_name'], "phone": row['phone'], "device": row['device'], "issue": row['issue'], "price": row['price'], "created_at": str(row['created_at'])[:10]}
                        html = generate_html_document("Inlämningskvitto", doc_data, COMPANY_INFO)
                        st.session_state['active_doc'] = {'html': html, 'filename': f"Inlamningskvitto_{sel_rep}.html", 'key': f"search_rep_{sel_rep}"}
                        st.rerun()
                    if sel_rep and st.button(txt["delete_btn"], key=f"del_rep_{sel_rep}"):
                        delete_record_by_id("repairs", sel_rep)
                        st.success(txt["deleted_success"])
                        st.rerun()

            st.subheader("💡 Kostnadsförslag Arkiv")
            quote_res = pd.read_sql_query("SELECT id, customer_name, phone, device, issues, total, created_at FROM quotes WHERE branch = ? AND (customer_name LIKE ? OR device LIKE ?)", conn, params=(global_branch, q_like, q_like))
            if not quote_res.empty:
                st.dataframe(quote_res, use_container_width=True)
                col_q_a, col_q_b = st.columns([2, 1])
                with col_q_a:
                    sel_q = st.selectbox("🖨️ Välj Kostnadsförslag ID:", quote_res['id'].tolist(), key="sel_q_id")
                with col_q_b:
                    if sel_q and st.button("📄 Visa / Skriv ut", key=f"btn_q_{sel_q}"):
                        row = quote_res[quote_res['id'] == sel_q].iloc[0]
                        doc_data = {"branch": global_branch, "repair_id": f"QUO-{str(row['created_at'])[:10].replace('-','')}-{sel_q:03d}", "customer_name": row['customer_name'], "phone": row['phone'], "device": row['device'], "issue": row['issues'], "total": row['total'], "created_at": str(row['created_at'])[:10]}
                        html = generate_html_document("Kostnadsförslag", doc_data, COMPANY_INFO)
                        st.session_state['active_doc'] = {'html': html, 'filename': f"Kostnadsforslag_{sel_q}.html", 'key': f"search_q_{sel_q}"}
                        st.rerun()
                    if sel_q and st.button(txt["delete_btn"], key=f"del_q_{sel_q}"):
                        delete_record_by_id("quotes", sel_q)
                        st.success(txt["deleted_success"])
                        st.rerun()

            st.subheader("🔄 Uppköp / Kvittens Arkiv (Buyback)")
            buy_res = pd.read_sql_query("SELECT id, customer_name, person_nr, phone, device, payout, created_at FROM buyback WHERE branch = ? AND (customer_name LIKE ? OR person_nr LIKE ? OR device LIKE ?)", conn, params=(global_branch, q_like, q_like, q_like))
            if not buy_res.empty:
                st.dataframe(buy_res, use_container_width=True)
                col_buy_a, col_buy_b = st.columns([2, 1])
                with col_buy_a:
                    sel_buy = st.selectbox("🖨️ Välj Kvittens ID:", buy_res['id'].tolist(), key="sel_buy_id")
                with col_buy_b:
                    if sel_buy and st.button("📄 Visa / Skriv ut", key=f"btn_buy_{sel_buy}"):
                        row = buy_res[buy_res['id'] == sel_buy].iloc[0]
                        doc_data = {"branch": global_branch, "repair_id": f"BUY-{str(row['created_at'])[:10].replace('-','')}-{sel_buy:03d}", "customer_name": row['customer_name'], "person_nr": row['person_nr'], "phone": row['phone'], "device": row['device'], "price": row['payout'], "created_at": str(row['created_at'])[:10]}
                        html = generate_html_document("Kvittens - Enhetsköp (Buyback)", doc_data, COMPANY_INFO)
                        st.session_state['active_doc'] = {'html': html, 'filename': f"Kvittens_{sel_buy}.html", 'key': f"search_buy_{sel_buy}"}
                        st.rerun()
                    if sel_buy and st.button(txt["delete_btn"], key=f"del_buy_{sel_buy}"):
                        delete_record_by_id("buyback", sel_buy)
                        st.success(txt["deleted_success"])
                        st.rerun()

            st.subheader("📋 Förbeställningar Arkiv (Preorders)")
            pre_res = pd.read_sql_query("SELECT id, customer_name, phone, item, deposit, created_at FROM preorders WHERE branch = ? AND (customer_name LIKE ? OR item LIKE ?)", conn, params=(global_branch, q_like, q_like))
            if not pre_res.empty:
                st.dataframe(pre_res, use_container_width=True)
                col_pre_a, col_pre_b = st.columns([2, 1])
                with col_pre_a:
                    sel_pre = st.selectbox("🗑️ Välj Förbeställning ID:", pre_res['id'].tolist(), key="sel_pre_id")
                with col_pre_b:
                    if sel_pre and st.button(txt["delete_btn"], key=f"del_pre_{sel_pre}"):
                        delete_record_by_id("preorders", sel_pre)
                        st.success(txt["deleted_success"])
                        st.rerun()

            st.subheader("📦 Lager (Stock)")
            stock_res = pd.read_sql_query("SELECT id, part_name, category, quantity, price, created_at FROM stock WHERE branch = ? AND part_name LIKE ?", conn, params=(global_branch, q_like))
            if not stock_res.empty:
                st.dataframe(stock_res, use_container_width=True)
                col_st_a, col_st_b = st.columns([2, 1])
                with col_st_a:
                    sel_st = st.selectbox("🗑️ Välj Lager ID:", stock_res['id'].tolist(), key="sel_st_id")
                with col_st_b:
                    if sel_st and st.button(txt["delete_btn"], key=f"del_st_{sel_st}"):
                        delete_record_by_id("stock", sel_st)
                        st.success(txt["deleted_success"])
                        st.rerun()

            conn.close()
