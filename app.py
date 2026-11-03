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
            "comp_name": "Företagsnamn (Company Name)",
            "org_nr_cust": "Kundens Org.nr / VAT-nr",
            "phone": "Telefonnummer",
            "address": "Fakturaadress",
            "device": "Enhet / Modell",
            "issue": "Felbeskrivning / Åtgärd",
            "price": "Pris (SEK inkl. moms)",
            "employee": "Handläggare / Anställd",
            "save_repair": "Spara inlämningskvitto",
            "success_repair": "Inlämnandet har sparats framgångsrikt!",
            "preview": "Dokumentförhandsgranskning",
            "back_app": "Tillbaka till appen",
            "download_web": "Ladda ner som webbsida",
            "inv_no": "Fakturarummer",
            "total_amt": "Totalt belopp (SEK)",
            "inv_type": "Fakturatyp (B2B)",
            "create_inv": "Skapa och förhandsgranska företagsfaktura",
            "success_inv": "Företagsfakturan har skapats framgångsrikt!",
            "search_q": "Sök på företagsnamn, org.nr eller fakturanummer",
            "select_item_print": "Välj ID för att skriva ut eller dela dokumentet:",
            "service_header": "⚙️ Välj fel och specifika reparationer (Select Repairs)"
        }
    else:
        txt = {
            "welcome": "مرحباً بك",
            "branch": "اختر الفرع",
            "tab_dash": "📊 لوحة التحكم",
            "tab_repair": "🛠️ الإصلاحات",
            "tab_quote": "💡 عرض سعر / Kostnadsförslag",
            "tab_invoice": "📄 فواتير الشركات (B2B)",
            "tab_sub": "📦 الاشتراكات",
            "tab_buyback": "🔄 شراء الأجهزة",
            "tab_campaign": "🎯 الحملات",
            "tab_preorder": "📋 الطلبات المسبقة",
            "tab_stock": "📦 المخزون",
            "tab_search": "🔍 البحث والأرشيف",
            "reset": "🔄 إعادة ضبط العرض",
            "comp_name": "اسم الشركة / المؤسسة (Company Name)",
            "org_nr_cust": "رقم تسجيل الشركة Org.nr / VAT",
            "phone": "رقم الهاتف",
            "address": "عنوان الشركة",
            "device": "نوع الجهاز / الموديل",
            "issue": "وصف العطل / الإجراء",
            "price": "السعر (كرون شامل الضريبة)",
            "employee": "اسم الموظف / المسؤول",
            "save_repair": "حفظ إيصال الإصلاح",
            "success_repair": "تم حفظ الإصلاح بنجاح!",
            "preview": "معاينة المستند",
            "back_app": "العودة إلى التطبيق",
            "download_web": "تحميل كملف ويب",
            "inv_no": "رقم الفاتورة",
            "total_amt": "المبلغ الإجمالي (كرون)",
            "inv_type": "نوع فاتورة الشركات (B2B)",
            "create_inv": "إصدار ومعاينة فاتورة الشركة",
            "success_inv": "تم إصدار فاتورة الشركة بنجاح!",
            "search_q": "بحث باسم الشركة، رقم التسجيل أو رقم الفاتورة",
            "select_item_print": "اختر المعرف (ID) لطباعة أو مشاركة المستند:",
            "service_header": "⚙️ تحديد الأعطال والقطع المطلوبة (Select Repairs)"
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
            "bankgiro": "123-4567",
            "logo_url": "https://i.imgur.com/3Z50x08.png" # يمكنك استبدال هذا الرابط برابط شعار شركتك الفعلي
        },
        "Västerås": {
            "name": "30 Minutes Phone Fix Västerås AB", 
            "address": "Gunborg Nymans Väg 2, 632 22 Eskilstuna", 
            "phone": "0700122444",
            "org_nr": "559537-1724",
            "moms_reg": "SE559537172401",
            "bankgiro": "765-4321",
            "logo_url": "https://i.imgur.com/3Z50x08.png" # يمكنك استبدال هذا الرابط برابط شعار شركتك الفعلي
        }
    }

    # --- DATABASE SETUP & AUTO MIGRATION ---
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
        
        try:
            cursor.execute("ALTER TABLE invoices ADD COLUMN invoice_type TEXT")
            cursor.execute("ALTER TABLE invoices ADD COLUMN customer_org TEXT")
        except sqlite3.OperationalError:
            pass

        conn.commit()
        conn.close()

    init_db()

    # --- FORMAT PRICE HELPER ---
    def format_price(val):
        try:
            f_val = float(val)
            return str(int(f_val))
        except:
            return str(val)

    # --- SWEDISH PROFESSIONAL B2B INVOICE & DOCUMENT GENERATOR WITH LOGO ---
    def generate_html_document(doc_type, data, company_info):
        branch_info = company_info.get(data['branch'], company_info["Eskilstuna"])
        raw_amount = data.get('price', data.get('amount', data.get('total', 0)))
        formatted_total = format_price(raw_amount)

        cust_org_display = f"<br><strong>Org.nr / VAT:</strong> {data.get('customer_org', 'N/A')}" if doc_type == 'Faktura' and data.get('customer_org') else ""

        html_content = f"""
        <!DOCTYPE html>
        <html lang="sv">
        <head>
            <meta charset="UTF-8">
            <title>{doc_type.upper()}</title>
            <style>
                body {{ font-family: Helvetica, Arial, sans-serif; padding: 30px; color: #222; background: #fff; margin: 0; }}
                .header-table {{ width: 100%; border-collapse: collapse; margin-bottom: 25px; border-bottom: 2px solid #007AFF; padding-bottom: 15px; }}
                .header-table td {{ vertical-align: top; }}
                .logo {{ max-height: 60px; max-width: 180px; margin-bottom: 10px; }}
                .company-title {{ font-size: 18px; font-weight: bold; color: #007AFF; margin: 0; }}
                .invoice-title {{ font-size: 24px; font-weight: bold; text-align: right; color: #333; margin: 0; }}
                .meta-box {{ background: #f8f9fa; padding: 15px; border-radius: 6px; margin-bottom: 25px; border: 1px solid #e9ecef; }}
                .meta-box table {{ width: 100%; border-collapse: collapse; }}
                .meta-box td {{ padding: 5px; font-size: 14px; }}
                .details-table {{ width: 100%; border-collapse: collapse; margin-bottom: 25px; }}
                .details-table th, .details-table td {{ border: 1px solid #dee2e6; padding: 12px; text-align: left; font-size: 14px; }}
                .details-table th {{ background-color: #f1f3f5; color: #333; }}
                .f-skatt {{ font-size: 12px; color: #555; margin-top: 10px; }}
                .footer {{ text-align: center; margin-top: 40px; font-size: 11px; color: #6c757d; border-top: 1px solid #dee2e6; padding-top: 15px; }}
            </style>
        </head>
        <body>
            <table class="header-table">
                <tr>
                    <td>
                        <img src="{branch_info['logo_url']}" alt="Logo" class="logo">
                        <p class="company-title">30 Minutes Phone Fix</p>
                        <p style="margin: 4px 0; font-size: 14px;"><strong>{branch_info['name']}</strong></p>
                        <p style="margin: 2px 0; font-size: 13px; color: #555;">
                            Adress: {branch_info['address']}<br>
                            Org.nr: {branch_info['org_nr']}<br>
                            Momsreg.nr: {branch_info['moms_reg']}<br>
                            Tel: {branch_info['phone']}
                        </p>
                        <div class="f-skatt">Godkänd för F-skatt | Bankgiro: {branch_info['bankgiro']}</div>
                    </td>
                    <td style="text-align: right;">
                        <p class="invoice-title">{doc_type.upper()}</p>
                        <p style="margin: 5px 0; font-size: 14px;"><strong>Datum:</strong> {data.get('created_at', date.today())}</p>
                        <p style="margin: 5px 0; font-size: 14px;"><strong>Förfallodatum:</strong> {(date.today() + timedelta(days=30))}</p>
                    </td>
                </tr>
            </table>

            <div class="meta-box">
                <table>
                    <tr>
                        <td><strong>Företag / Kund:</strong> {data.get('customer_name', 'N/A')} {cust_org_display}</td>
                        <td><strong>Telefon:</strong> {data.get('phone', 'N/A')}</td>
                    </tr>
                    <tr>
                        <td colspan="2"><strong>Adress / Enhet:</strong> {data.get('device', data.get('address', 'N/A'))}</td>
                    </tr>
                </table>
            </div>

            <table class="details-table">
                <tr>
                    <th>Beskrivning / Tjänst (Description & Service)</th>
                    <th style="text-align: right;">Totalt (SEK inkl. moms)</th>
                </tr>
                <tr>
                    <td>{data.get('issue', data.get('issues', 'Service'))}</td>
                    <td style="text-align: right;"><strong>{formatted_total} SEK</strong></td>
                </tr>
            </table>

            <p style="font-size: 13px;"><strong>Handläggare:</strong> {data.get('employee', 'N/A')}</p>

            <div class="footer">
                <p>30 Minutes Phone Fix | Giltighetstid: 30 dagar | Välkommen åter!</p>
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
                label=f"🌐 {txt['download_web']}",
                data=html_content,
                file_name=file_name,
                mime="text/html",
                key=f"download_web_btn_{key_suffix}"
            )

        st.components.v1.html(html_content, height=480, scrolling=True)

    # --- SIDEBAR RESET ---
    if st.sidebar.button(txt["reset"]):
        if 'active_doc' in st.session_state:
            del st.session_state['active_doc']
        st.rerun()

    # --- TABS DEFINITION ---
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10 = st.tabs([
        txt["tab_dash"], txt["tab_repair"], txt["tab_quote"], txt["tab_invoice"], 
        txt["tab_sub"], txt["tab_buyback"], txt["tab_campaign"], txt["tab_preorder"], txt["tab_stock"], txt["tab_search"]
    ])

    with tab1:
        st.header(f"{txt['tab_dash']} ({global_branch})")
        st.metric("Status", "Online", "OK")

    with tab2:
        st.header(f"{txt['tab_repair']} ({global_branch})")
        if 'active_doc' in st.session_state and st.session_state['active_doc'].get('key', '').startswith('rep_new_'):
            display_document_preview(st.session_state['active_doc']['html'], st.session_state['active_doc']['filename'], st.session_state['active_doc']['key'])
        else:
            with st.form("repair_form"):
                c_name = st.text_input(txt["comp_name"])
                c_phone = st.text_input(txt["phone"])
                c_device = st.text_input(txt["device"])
                c_issue = st.text_area(txt["issue"])
                c_price = st.number_input(txt["price"], min_value=0.0, step=50.0, format="%d")
                c_emp = st.text_input(txt["employee"])
                submitted = st.form_submit_button(txt["save_repair"])
                if submitted:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO repairs (branch, customer_name, phone, device, issue, price, status, employee, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                   (global_branch, c_name, c_phone, c_device, c_issue, c_price, "Pending", c_emp, str(date.today())))
                    conn.commit()
                    last_id = cursor.lastrowid
                    conn.close()
                    
                    rec_data = {
                        "branch": global_branch, "repair_id": str(last_id),
                        "customer_name": c_name, "phone": c_phone, "device": c_device,
                        "issue": c_issue, "price": c_price, "employee": c_emp,
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

    # --- TAB 3: KOSTNADSFÖRSLAG ---
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
                col_s1, col_s2, col_s3 = st.columns(3)
                with col_s1:
                    s_display = st.checkbox("📱 Skärmbyte (Display)", key="q_s_display")
                    s_battery = st.checkbox("🔋 Batteribyte (Battery)", key="q_s_battery")
                with col_s2:
                    s_camera = st.checkbox("📷 Kamerabyte / Kameralins (Camera)", key="q_s_camera")
                    s_charger = st.checkbox("🔌 Laddkontakt (Charging Port)", key="q_s_charger")
                with col_s3:
                    s_back = st.checkbox("🔍 Baksida glas (Back Glass)", key="q_s_back")
                    s_water = st.checkbox("💧 Vattenskada (Water Damage)", key="q_s_water")
                
                q_extra = st.text_area("Övriga kommentarer / Felbeskrivning (Additional notes)", key="q_extra")
                q_total = st.number_input(txt["price"], min_value=0.0, step=50.0, format="%d", key="q_total")
                q_emp = st.text_input(txt["employee"], key="q_emp")
                
                q_sub = st.form_submit_button("Spara & Förhandsgranska Kostnadsförslag")
                if q_sub:
                    selected_repairs = []
                    if s_display: selected_repairs.append("Skärmbyte (Display Replacement)")
                    if s_battery: selected_repairs.append("Batteribyte (Battery Replacement)")
                    if s_camera: selected_repairs.append("Kamerabyte / Kameralins (Camera Service)")
                    if s_charger: selected_repairs.append("Laddkontakt reparation (Charging Port)")
                    if s_back: selected_repairs.append("Baksida byte (Back Glass)")
                    if s_water: selected_repairs.append("Vattenskada rengöring (Water Damage)")
                    if q_extra: selected_repairs.append(q_extra)
                    
                    full_issue_text = " | ".join(selected_repairs) if selected_repairs else "Allmän undersökning och service"
                    
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO quotes (branch, customer_name, phone, device, issues, total, profit, employee, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                   (global_branch, q_name, q_phone, q_device, full_issue_text, q_total, q_total * 0.3, q_emp, str(date.today())))
                    conn.commit()
                    last_id = cursor.lastrowid
                    conn.close()
                    
                    q_data = {
                        "branch": global_branch, "customer_name": q_name, "phone": q_phone,
                        "device": q_device, "issue": full_issue_text, "total": q_total,
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

    # --- TAB 4: B2B INVOICES ---
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
                        "branch": global_branch, "invoice_no": i_no, "customer_name": i_name,
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

    with tab5: st.header("Subscriptions")
    with tab6: st.header("Buyback")
    with tab7: st.header("Campaigns")
    with tab8: st.header("Pre-orders")
    with tab9: st.header("Stock")

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
            
            inv_res = pd.read_sql_query("SELECT id, invoice_no, customer_name, customer_org, phone, amount, invoice_type, created_at FROM invoices WHERE branch = ? AND (customer_name LIKE ? OR customer_org LIKE ? OR invoice_no LIKE ?)", conn, params=(global_branch, q_like, q_like, q_like))
            if not inv_res.empty:
                st.subheader("📄 Företagsfakturor Arkiv")
                st.dataframe(inv_res, use_container_width=True)
                sel_id = st.selectbox(txt["select_item_print"], inv_res['id'].tolist(), key="sel_inv_id")
                if sel_id:
                    i_row = inv_res[inv_res['id'] == sel_id].iloc[0]
                    if st.button("📄 Skriv ut / Visa Företagsfaktura", key=f"btn_gen_inv_{sel_id}"):
                        inv_data = {
                            "branch": global_branch, "invoice_no": i_row['invoice_no'],
                            "customer_name": i_row['customer_name'], "customer_org": i_row['customer_org'],
                            "phone": i_row['phone'], "issue": "Företagsreparation och reservdelar", "amount": i_row['amount'],
                            "invoice_type": i_row['invoice_type'], "created_at": str(i_row['created_at'])[:10]
                        }
                        html_doc = generate_html_document("Faktura", inv_data, COMPANY_INFO)
                        st.session_state['active_doc'] = {
                            'html': html_doc,
                            'filename': f"{i_row['invoice_no']}.html",
                            'key': f"search_inv_{sel_id}"
                        }
                        st.rerun()
            conn.close()
