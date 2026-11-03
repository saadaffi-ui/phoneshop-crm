import streamlit as st
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

# --- GLOBAL BRANCH & CONFIG ---
global_branch = st.sidebar.selectbox("اختر الفرع / Select Branch", ["Eskilstuna", "Västerås"])

COMPANY_INFO = {
    "Eskilstuna": {
        "name": "30 Minutes Phone Fix Eskilstuna", 
        "address": "Drottninggatan X, Eskilstuna", 
        "phone": "016-XXX XX XX"
    },
    "Västerås": {
        "name": "30 Minutes Phone Fix Västerås", 
        "address": "Stora Gatan Y, Västerås", 
        "phone": "021-XXX XX XX"
    }
}

t = {
    "tab_dash": "📊 لوحة التحكم / Dashboard",
    "tab_repair": "🛠️ الإصلاحات / Repairs",
    "tab_quote": "💡 عرض سعر / Kostnadsförslag",
    "tab_invoice": "📄 الفواتير / Invoices",
    "tab_sub": "📦 الاشتراكات / Subscriptions",
    "tab_buyback": "🔄 شراء الأجهزة / Buyback",
    "tab_campaign": "🎯 الحملات / Campaigns",
    "tab_preorder": "📋 الطلبات المسبقة / Pre-orders",
    "tab_stock": "📦 المخزون / Stock",
    "tab_search": "🔍 البحث والأرشيف / Search & Archive"
}

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
                        phone TEXT, address TEXT, amount REAL, moms REAL, 
                        employee TEXT, created_at TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS quotes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        branch TEXT, customer_name TEXT, phone TEXT, 
                        device TEXT, issues TEXT, total REAL, profit REAL, 
                        employee TEXT, created_at TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- HTML DOCUMENT GENERATOR (FIXES IOS PREVIEW & FORMAT ISSUES) ---
def generate_html_document(doc_type, data, company_info):
    branch_info = company_info.get(data['branch'], company_info["Eskilstuna"])
    html_content = f"""
    <!DOCTYPE html>
    <html lang="sv">
    <head>
        <meta charset="UTF-8">
        <title>{doc_type.upper()}</title>
        <style>
            body {{ font-family: Helvetica, Arial, sans-serif; padding: 25px; color: #111; background: #fff; }}
            .header {{ text-align: center; border-bottom: 2px solid #007AFF; padding-bottom: 15px; margin-bottom: 20px; }}
            .header h2 {{ margin: 0; color: #007AFF; }}
            .info-box {{ background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px; border: 1px solid #e9ecef; }}
            .details-table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
            .details-table th, .details-table td {{ border: 1px solid #dee2e6; padding: 10px 12px; text-align: left; }}
            .details-table th {{ background-color: #f1f3f5; }}
            .footer {{ text-align: center; margin-top: 30px; font-size: 12px; color: #6c757d; border-top: 1px solid #dee2e6; padding-top: 10px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h2>30 Minutes Phone Fix</h2>
            <p><strong>{branch_info['name']}</strong><br>{branch_info['address']} | Tel: {branch_info['phone']}</p>
        </div>
        
        <div class="info-box">
            <h3>Dokumenttyp: {doc_type.upper()}</h3>
            <p><strong>Datum:</strong> {data.get('created_at', date.today())}</p>
            <p><strong>Kund:</strong> {data.get('customer_name', 'N/A')}</p>
            <p><strong>Telefon:</strong> {data.get('phone', 'N/A')}</p>
            <p><strong>Enhet / Modell:</strong> {data.get('device', data.get('address', 'N/A'))}</p>
        </div>

        <table class="details-table">
            <tr>
                <th>Reparation / Åtgärd (Details & Required Service)</th>
                <th>Pris (SEK inkl. moms)</th>
            </tr>
            <tr>
                <td>{data.get('issue', data.get('issues', data.get('item_desc', 'Allmän service')))}</td>
                <td><strong>{data.get('price', data.get('amount', data.get('total', 0.0)))} SEK</strong></td>
            </tr>
        </table>

        <p><strong>Handläggare / Anställd:</strong> {data.get('employee', 'N/A')}</p>

        <div class="footer">
            <p>Tack för att du väljer 30 Minutes Phone Fix! | Giltighetstid: 30 dagar.</p>
        </div>
    </body>
    </html>
    """
    return html_content

def display_document_preview(html_content, file_name, key_suffix):
    b64_html = base64.b64encode(html_content.encode('utf-8')).decode('utf-8')
    
    st.markdown("### 📄 معاينة المستند (Document Preview)")
    
    if st.button("🔙 العودة إلى التطبيق والقائمة / Back to App", type="primary", key=f"back_app_btn_{key_suffix}"):
        if 'active_doc' in st.session_state:
            del st.session_state['active_doc']
        st.rerun()

    # معاينة حية متوافقة داخل الإطار
    st.components.v1.html(html_content, height=420, scrolling=True)
    
    # زر آمن وفعال للفتح والطباعة والمشاركة على الآيفون
    download_html = f"""
    <div style="margin: 15px 0;">
        <a href="data:text/html;base64,{b64_html}" download="{file_name}" target="_blank" style="display: block; background-color: #007AFF; color: white; text-align: center; padding: 14px 20px; border-radius: 10px; font-size: 16px; font-weight: bold; text-decoration: none; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">
            🖨️ فتح للطباعة والمشاركة (Open & Print / Share)
        </a>
    </div>
    """
    st.markdown(download_html, unsafe_allow_html=True)

# --- SIDEBAR RESET & CONTROLS ---
if st.sidebar.button("🔄 إعادة ضبط العرض / Reset Session"):
    if 'active_doc' in st.session_state:
        del st.session_state['active_doc']
    st.rerun()

# --- DEFINE ALL TABS FIRST ---
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10 = st.tabs([
    t["tab_dash"], t["tab_repair"], t["tab_quote"], t["tab_invoice"], 
    t["tab_sub"], t["tab_buyback"], t["tab_campaign"], t["tab_preorder"], t["tab_stock"], t["tab_search"]
])

# --- TAB 1: DASHBOARD ---
with tab1:
    st.header(f"📊 لوحة التحكم الرئيسية / Dashboard ({global_branch})")
    st.metric("الحالة التشغيلية", "متصل ويعمل بكفاءة عالية", "جاهز")

# --- TAB 2: REPAIRS ---
with tab2:
    st.header(f"🛠️ تسجيل إصلاح جديد / New Repair ({global_branch})")
    
    if 'active_doc' in st.session_state and st.session_state['active_doc'].get('key', '').startswith('rep_new_'):
        display_document_preview(st.session_state['active_doc']['html'], st.session_state['active_doc']['filename'], st.session_state['active_doc']['key'])
    else:
        with st.form("repair_form"):
            c_name = st.text_input("اسم العميل / Customer Name")
            c_phone = st.text_input("رقم الهاتف / Phone Number")
            c_device = st.text_input("نوع الجهاز / Device Model")
            c_issue = st.text_area("وصف العطل / Issue Description")
            c_price = st.number_input("التكلفة / Price (SEK)", min_value=0.0, step=50.0)
            c_emp = st.text_input("اسم الموظف / Employee Name")
            submitted = st.form_submit_button("حفظ ومعاينة إيصال الإصلاح")
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
                st.success("تم حفظ الإصلاح بنجاح!")
                st.rerun()

# --- TAB 3: QUOTES (KOSTNADSFÖRSLAG WITH DETAILED REPAIR OPTIONS) ---
with tab3:
    st.header(f"💡 عرض سعر مفصل / Kostnadsförslag ({global_branch})")
    
    if 'active_doc' in st.session_state and st.session_state['active_doc'].get('key', '').startswith('quote_new_'):
        display_document_preview(st.session_state['active_doc']['html'], st.session_state['active_doc']['filename'], st.session_state['active_doc']['key'])
    else:
        with st.form("quote_form"):
            q_name = st.text_input("اسم العميل / Customer Name", key="q_name")
            q_phone = st.text_input("رقم الهاتف / Phone Number", key="q_phone")
            q_device = st.text_input("موديل الجهاز / Device Model (e.g., iPhone 14)", key="q_device")
            
            st.markdown("### ⚙️ تحديد تفاصيل القطع والأعطال (Select Services & Repairs)")
            q_iss_display = st.checkbox("📱 تغيير الشاشة (Skärmbyte / Display Replacement)", key="q_iss_display")
            q_iss_battery = st.checkbox("🔋 تغيير البطارية (Batteribyte / Battery Replacement)", key="q_iss_battery")
            q_iss_charger = st.checkbox("🔌 منفذ الشحن (Laddkontakt / Charging Port)", key="q_iss_charger")
            q_iss_back = st.checkbox("🔍 الزجاج الخلفي (Baksida / Back Glass)", key="q_iss_back")
            q_iss_camera = st.checkbox("📷 الكاميرا أو زجاج الكاميرا (Kamera / Camera Glass)", key="q_iss_camera")
            q_iss_water = st.checkbox("💧 تصليح وتنظيف أضرار السوائل (Vattenskada Rengöring)", key="q_iss_water")
            
            q_extra_issue = st.text_area("ملاحظات إضافية أو أعطال أخرى / Additional Fault Details", key="q_extra_issue")
            q_total = st.number_input("السعر الإجمالي لعرض السعر / Total Price (SEK)", min_value=0.0, step=50.0, key="q_total")
            q_emp = st.text_input("اسم الموظف / Employee Name", key="q_emp")
            q_sub = st.form_submit_button("حفظ ومعاينة Kostnadsförslag")
            
            if q_sub:
                selected_services = []
                if q_iss_display: selected_services.append("Skärmbyte (Display Replacement)")
                if q_iss_battery: selected_services.append("Batteribyte (Battery Replacement)")
                if q_iss_charger: selected_services.append("Laddkontakt reparation (Charging Port)")
                if q_iss_back: selected_services.append("Baksida byte (Back Glass)")
                if q_iss_camera: selected_services.append("Kamerareparation (Camera Service)")
                if q_iss_water: selected_services.append("Vattenskada rengöring (Water Damage)")
                if q_extra_issue: selected_services.append(q_extra_issue)
                
                full_issues_desc = " | ".join(selected_services) if selected_services else "Allmän undersökning och service"
                
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("INSERT INTO quotes (branch, customer_name, phone, device, issues, total, profit, employee, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                               (global_branch, q_name, q_phone, q_device, full_issues_desc, q_total, q_total * 0.3, q_emp, str(date.today())))
                conn.commit()
                last_id = cursor.lastrowid
                conn.close()
                
                q_data = {
                    "branch": global_branch, "customer_name": q_name, "phone": q_phone,
                    "device": q_device, "issue": full_issues_desc, "total": q_total,
                    "employee": q_emp, "created_at": str(date.today())
                }
                html_doc = generate_html_document("Kostnadsförslag", q_data, COMPANY_INFO)
                st.session_state['active_doc'] = {
                    'html': html_doc,
                    'filename': f"Kostnadsforslag_{last_id}.html",
                    'key': f"quote_new_{last_id}"
                }
                st.success("تم حفظ عرض السعر (Kostnadsförslag) بالتشخيص والتفاصيل بنجاح!")
                st.rerun()

# --- TAB 4: INVOICES ---
with tab4:
    st.header(f"📄 الفواتير / Invoices ({global_branch})")
    
    if 'active_doc' in st.session_state and st.session_state['active_doc'].get('key', '').startswith('inv_new_'):
        display_document_preview(st.session_state['active_doc']['html'], st.session_state['active_doc']['filename'], st.session_state['active_doc']['key'])
    else:
        with st.form("invoice_form"):
            i_no = st.text_input("رقم الفاتورة / Invoice No", value=f"INV-{date.today().strftime('%Y%m%d')}-01")
            i_name = st.text_input("اسم العميل", key="i_name")
            i_phone = st.text_input("رقم الهاتف", key="i_phone")
            i_addr = st.text_input("العنوان", key="i_addr")
            i_amt = st.number_input("المبلغ الإجمالي", min_value=0.0, step=50.0, key="i_amt")
            i_emp = st.text_input("الموظف", key="i_emp")
            i_sub = st.form_submit_button("إصدار ومعاينة الفاتورة")
            if i_sub:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("INSERT INTO invoices (branch, invoice_no, customer_name, phone, address, amount, moms, employee, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                               (global_branch, i_no, i_name, i_phone, i_addr, i_amt, i_amt * 0.2, i_emp, str(date.today())))
                conn.commit()
                last_id = cursor.lastrowid
                conn.close()
                
                inv_data = {
                    "branch": global_branch, "invoice_no": i_no, "customer_name": i_name,
                    "phone": i_phone, "address": i_addr, "issue": "Reparation och reservdelar",
                    "price": i_amt, "employee": i_emp, "created_at": str(date.today())
                }
                html_doc = generate_html_document("Faktura", inv_data, COMPANY_INFO)
                st.session_state['active_doc'] = {
                    'html': html_doc,
                    'filename': f"{i_no}.html",
                    'key': f"inv_new_{last_id}"
                }
                st.success("تم إصدار الفاتورة بنجاح!")
                st.rerun()

# --- TABS 5 to 9: PLACEHOLDERS ---
with tab5:
    st.header("📦 إدارة الاشتراكات (Subscriptions)")
with tab6:
    st.header("🔄 شراء الأجهزة واستبدالها (Buyback)")
with tab7:
    st.header("🎯 الحملات والتسويق (Campaigns)")
with tab8:
    st.header("📋 الطلبات المسبقة (Pre-orders)")
with tab9:
    st.header("📦 إدارة المخزون (Stock)")

# --- TAB 10: SEARCH WITH STATEFUL DOCUMENT VIEWER ---
with tab10:
    st.header(f"🔍 البحث والأرشيف وتخصيص الحقول للعرض والطباعة / Search & Field Checklist ({global_branch})")
    
    if 'active_doc' in st.session_state and not st.session_state['active_doc'].get('key', '').startswith(('rep_new_', 'quote_new_', 'inv_new_')):
        doc_info = st.session_state['active_doc']
        
        if st.button("🔙 العودة إلى نتائج البحث / Back to Search", type="primary", key="top_back_nav_search"):
            del st.session_state['active_doc']
            st.rerun()
            
        display_document_preview(doc_info['html'], doc_info['filename'], doc_info['key'])
    else:
        search_query = st.text_input("بحث بالاسم، رقم الهاتف، نوع الجهاز أو رقم الفاتورة / Search Query", key="global_search_input")
        
        st.markdown("---")
        st.markdown("### ⚙️ اختر الحقول المراد إظهارها في المعاينة والطباعة (Select Fields Checklist)")
        
        col_chk1, col_chk2, col_chk3, col_chk4 = st.columns(4)
        with col_chk1:
            inc_name = st.checkbox("Kundens namn / Customer Name", value=True, key="chk_f_name")
            inc_phone = st.checkbox("Telefon / Phone Number", value=True, key="chk_f_phone")
        with col_chk2:
            inc_device = st.checkbox("Enhet / Device & Model", value=True, key="chk_f_device")
            inc_issue = st.checkbox("Fel / Description / Details", value=True, key="chk_f_issue")
        with col_chk3:
            inc_price = st.checkbox("Pris / Price / Amount", value=True, key="chk_f_price")
            inc_status = st.checkbox("Status / Plan / Ref", value=True, key="chk_f_status")
        with col_chk4:
            inc_emp = st.checkbox("Handläggare / Employee", value=True, key="chk_f_emp")
            inc_date = st.checkbox("Datum / Created Date", value=True, key="chk_f_date")

        conn = get_db_connection()
        q_like = f"%{search_query}%" if search_query else "%"
        
        def filter_df_columns(df, column_map):
            cols_to_keep = ['id']
            for key_col, is_checked in column_map.items():
                if is_checked and key_col in df.columns:
                    cols_to_keep.append(key_col)
            return df[cols_to_keep]

        # 1. REPAIRS SEARCH
        st.subheader("📝 الإصلاحات المسجلة (Repairs)")
        rep_res = pd.read_sql_query("SELECT id, customer_name, phone, device, issue, price, status, employee, created_at FROM repairs WHERE branch = ? AND (customer_name LIKE ? OR phone LIKE ? OR device LIKE ?)", conn, params=(global_branch, q_like, q_like, q_like))
        if not rep_res.empty:
            rep_map = {'customer_name': inc_name, 'phone': inc_phone, 'device': inc_device, 'issue': inc_issue, 'price': inc_price, 'status': inc_status, 'employee': inc_emp, 'created_at': inc_date}
            st.dataframe(filter_df_columns(rep_res, rep_map), use_container_width=True)
            
            selected_rep_id = st.selectbox("🖨️ اختر رقم إصلاح (ID) لطباعة أو إرسال الإيصال:", rep_res['id'].tolist(), key="sel_rep_id")
            if selected_rep_id:
                r_row = rep_res[rep_res['id'] == selected_rep_id].iloc[0]
                if st.button("📄 معاينة وطباعة إيصال الإصلاح", key=f"btn_gen_rep_{selected_rep_id}"):
                    rec_data = {
                        "branch": global_branch, "repair_id": str(r_row['id']),
                        "customer_name": r_row['customer_name'] if inc_name else "N/A",
                        "phone": r_row['phone'] if inc_phone else "N/A",
                        "device": r_row['device'] if inc_device else "N/A",
                        "issue": r_row['issue'] if inc_issue else "N/A",
                        "price": r_row['price'] if inc_price else 0.0,
                        "employee": r_row['employee'] if inc_emp else "N/A",
                        "created_at": str(r_row['created_at'])[:10] if inc_date else ""
                    }
                    html_doc = generate_html_document("Inlämningskvitto", rec_data, COMPANY_INFO)
                    st.session_state['active_doc'] = {
                        'html': html_doc,
                        'filename': f"Inlamningskvitto_{selected_rep_id}.html",
                        'key': f"search_rep_{selected_rep_id}"
                    }
                    st.rerun()

        # 2. INVOICES SEARCH
        st.subheader("📄 الفواتير المسجلة (Invoices)")
        inv_res = pd.read_sql_query("SELECT id, invoice_no, customer_name, phone, address, amount, moms, employee, created_at FROM invoices WHERE branch = ? AND (customer_name LIKE ? OR phone LIKE ? OR invoice_no LIKE ?)", conn, params=(global_branch, q_like, q_like, q_like))
        if not inv_res.empty:
            inv_map = {'customer_name': inc_name, 'phone': inc_phone, 'amount': inc_price, 'employee': inc_emp, 'created_at': inc_date}
            st.dataframe(filter_df_columns(inv_res, inv_map), use_container_width=True)
            
            selected_inv_id = st.selectbox("🖨️ اختر رقم فاتورة (ID) لطباعة أو إرسال الفاتورة:", inv_res['id'].tolist(), key="sel_inv_id")
            if selected_inv_id:
                i_row = inv_res[inv_res['id'] == selected_inv_id].iloc[0]
                if st.button("📄 معاينة وطباعة الفاتورة", key=f"btn_gen_inv_{selected_inv_id}"):
                    inv_data = {
                        "branch": global_branch, "invoice_no": i_row['invoice_no'],
                        "customer_name": i_row['customer_name'] if inc_name else "N/A",
                        "address": i_row['address'],
                        "phone": i_row['phone'] if inc_phone else "N/A",
                        "issue": "Reparation och reservdelar",
                        "price": i_row['amount'] if inc_price else 0.0,
                        "employee": i_row['employee'] if inc_emp else "N/A",
                        "created_at": str(i_row['created_at'])[:10] if inc_date else ""
                    }
                    html_doc = generate_html_document("Faktura", inv_data, COMPANY_INFO)
                    st.session_state['active_doc'] = {
                        'html': html_doc,
                        'filename': f"{i_row['invoice_no']}.html",
                        'key': f"search_inv_{selected_inv_id}"
                    }
                    st.rerun()

        # 3. QUOTES SEARCH
        st.subheader("💡 عروض الأسعار (Kostnadsförslag)")
        quote_res = pd.read_sql_query("SELECT id, customer_name, phone, device, issues, total, profit, employee, created_at FROM quotes WHERE branch = ? AND (customer_name LIKE ? OR phone LIKE ? OR device LIKE ?)", conn, params=(global_branch, q_like, q_like, q_like))
        if not quote_res.empty:
            q_map = {'customer_name': inc_name, 'phone': inc_phone, 'device': inc_device, 'issues': inc_issue, 'total': inc_price, 'employee': inc_emp, 'created_at': inc_date}
            st.dataframe(filter_df_columns(quote_res, q_map), use_container_width=True)
            
            selected_quote_id = st.selectbox("🖨️ اختر رقم عرض سعر (ID) لطباعة أو إرسال عرض السعر:", quote_res['id'].tolist(), key="sel_quote_id")
            if selected_quote_id:
                q_row = quote_res[quote_res['id'] == selected_quote_id].iloc[0]
                if st.button("📄 معاينة وطباعة Kostnadsförslag", key=f"btn_gen_quote_{selected_quote_id}"):
                    q_data = {
                        "branch": global_branch,
                        "customer_name": q_row['customer_name'] if inc_name else "N/A",
                        "phone": q_row['phone'] if inc_phone else "N/A",
                        "device": q_row['device'] if inc_device else "N/A",
                        "issue": q_row['issues'] if inc_issue else "N/A",
                        "total": q_row['total'] if inc_price else 0.0,
                        "employee": q_row['employee'] if inc_emp else "N/A",
                        "created_at": str(q_row['created_at'])[:10] if inc_date else ""
                    }
                    html_doc = generate_html_document("Kostnadsförslag", q_data, COMPANY_INFO)
                    st.session_state['active_doc'] = {
                        'html': html_doc,
                        "filename": f"Kostnadsforslag_{selected_quote_id}.html",
                        'key': f"search_quote_{selected_quote_id}"
                    }
                    st.rerun()

        conn.close()
