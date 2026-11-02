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
    "Eskilstuna": {"name": "30 Minutes Phone Fix Eskilstuna", "address": "Drottninggatan X, Eskilstuna", "phone": "016-XXX XX XX"},
    "Västerås": {"name": "30 Minutes Phone Fix Västerås", "address": "Stora Gatan Y, Västerås", "phone": "021-XXX XX XX"}
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

# --- MOCK DOCUMENT GENERATOR FUNCTION ---
def generate_pdf_from_record(doc_type, data, company_info):
    buffer = io.BytesIO()
    content = f"""
==================================================
{company_info[data['branch']]['name']}
Address: {company_info[data['branch']]['address']}
Phone: {company_info[data['branch']]['phone']}
==================================================
Document Type: {doc_type.upper()} (KOSTNADSFÖRSLAG)
Date: {data.get('created_at', date.today())}
Branch: {data['branch']}
--------------------------------------------------
Customer Name: {data.get('customer_name', 'N/A')}
Phone Number: {data.get('phone', 'N/A')}
Device Model: {data.get('device', 'N/A')}
--------------------------------------------------
REPAIR DETAILS & REQUIRED SERVICE:
{data.get('issue', data.get('issues', 'N/A'))}
--------------------------------------------------
Total Amount (inkl. moms): {data.get('price', data.get('amount', data.get('total', 0.0)))} SEK
Handled by: {data.get('employee', 'N/A')}
==================================================
Thank you for choosing 30 Minutes Phone Fix!
Giltighetstid / Validity: 30 dagar.
"""
    buffer.write(content.encode('utf-8'))
    buffer.seek(0)
    return buffer

def display_pdf_preview(buffer, file_name, key_suffix):
    doc_text = buffer.getvalue().decode('utf-8')
    b64_data = base64.b64encode(buffer.getvalue()).decode()
    
    st.markdown("### 📄 معاينة المستند (Document Preview)")
    
    # زر إضافي صريح للعودة الفورية إلى التطبيق من شاشة المعاينة
    if st.button("🔙 العودة إلى التطبيق والقائمة / Back to App", type="primary", key=f"back_app_btn_{key_suffix}"):
        if 'active_doc' in st.session_state:
            del st.session_state['active_doc']
        st.rerun()

    st.markdown(f"""
    <div style="background-color: #ffffff; padding: 20px; border-radius: 10px; border: 1px solid #ccc; font-family: monospace; white-space: pre-wrap; color: #000000; box-shadow: 0 2px 5px rgba(0,0,0,0.1); margin-top: 15px; margin-bottom: 15px; max-height: 350px; overflow-y: auto;">
{doc_text}
    </div>
    """, unsafe_allow_html=True)
    
    download_html = f"""
    <div style="margin-bottom: 20px;">
        <a href="data:text/plain;base64,{b64_data}" download="{file_name}" target="_blank" style="display: block; background-color: #007AFF; color: white; text-align: center; padding: 14px 20px; border-radius: 10px; font-size: 16px; font-weight: bold; text-decoration: none; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">
            📥 فتح المستند للطباعة والمشاركة (Open & Share)
        </a>
    </div>
    """
    st.markdown(download_html, unsafe_allow_html=True)
    
    st.text_area("محتوى نصي قابل للنسخ / Copy Text", doc_text, height=120, key=f"copy_area_{key_suffix}")

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
    with st.form("repair_form"):
        c_name = st.text_input("اسم العميل / Customer Name")
        c_phone = st.text_input("رقم الهاتف / Phone Number")
        c_device = st.text_input("نوع الجهاز / Device Model")
        c_issue = st.text_area("وصف العطل / Issue Description")
        c_price = st.number_input("التكلفة / Price (SEK)", min_value=0.0, step=50.0)
        c_emp = st.text_input("اسم الموظف / Employee Name")
        submitted = st.form_submit_button("حفظ الإصلاح / Save Repair")
        if submitted:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO repairs (branch, customer_name, phone, device, issue, price, status, employee, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                           (global_branch, c_name, c_phone, c_device, c_issue, c_price, "Pending", c_emp, str(date.today())))
            conn.commit()
            conn.close()
            st.success("تم حفظ بيانات الإصلاح بنجاح!")

# --- TAB 3: QUOTES (KOSTNADSFÖRSLAG WITH DETAILED REPAIR CHECKLIST) ---
with tab3:
    st.header(f"💡 إنشاء عرض سعر مفصل / Kostnadsförslag ({global_branch})")
    with st.form("quote_form"):
        q_name = st.text_input("اسم العميل / Customer Name", key="q_name")
        q_phone = st.text_input("رقم الهاتف / Phone Number", key="q_phone")
        q_device = st.text_input("موديل الجهاز / Device Model (e.g., iPhone 14)", key="q_device")
        
        st.markdown("### ⚙️ تحديد تفاصيل القطع والأعطال (Select Services & Repairs)")
        q_iss_display = st.checkbox("📱 تغيير الشاشة (Skärmbyte / Display Replacement)", key="q_iss_display")
        q_iss_battery = st.checkbox("🔋 تغيير البطارية (Batteribyte / Battery Replacement)", key="q_iss_battery")
        q_iss_charger = st.checkbox("🔌 منفذ الشحن (Laddkontakt / Charging Port)", key="q_iss_charger")
        q_iss_back = st.checkbox("🔍 الزجاج الخلفي (Baksida / Back Glass)", key="q_iss_back")
        q_iss_camera = st.checkbox("📷 الكاميرا أو الزجاج الأمامي/الخلفي للكاميرا (Kamera)", key="q_iss_camera")
        q_iss_water = st.checkbox("💧 تنظيف وتصليح أضرار السوائل (Vattenskada)", key="q_iss_water")
        
        q_extra_issue = st.text_area("ملاحظات إضافية أو أعطال أخرى / Additional Fault Details", key="q_extra_issue")
        
        q_total = st.number_input("السعر الإجمالي لعرض السعر / Total Price (SEK)", min_value=0.0, step=50.0, key="q_total")
        q_emp = st.text_input("اسم الموظف / Employee Name", key="q_emp")
        q_sub = st.form_submit_button("حفظ وعرض Kostnadsförslag")
        
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
            conn.close()
            st.success("تم إنشاء وحفظ عرض السعر (Kostnadsförslag) بالتشخيص والتفاصيل بنجاح!")

# --- TAB 4: INVOICES ---
with tab4:
    st.header(f"📄 الفواتير / Invoices ({global_branch})")
    with st.form("invoice_form"):
        i_no = st.text_input("رقم الفاتورة / Invoice No", value=f"INV-{date.today().strftime('%Y%m%d')}-01")
        i_name = st.text_input("اسم العميل", key="i_name")
        i_phone = st.text_input("رقم الهاتف", key="i_phone")
        i_addr = st.text_input("العنوان", key="i_addr")
        i_amt = st.number_input("المبلغ الإجمالي", min_value=0.0, step=50.0, key="i_amt")
        i_emp = st.text_input("الموظف", key="i_emp")
        i_sub = st.form_submit_button("إصدار الفاتورة")
        if i_sub:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO invoices (branch, invoice_no, customer_name, phone, address, amount, moms, employee, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                           (global_branch, i_no, i_name, i_phone, i_addr, i_amt, i_amt * 0.2, i_emp, str(date.today())))
            conn.commit()
            conn.close()
            st.success("تم إصدار الفاتورة بنجاح!")

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
    
    if 'active_doc' in st.session_state:
        doc_info = st.session_state['active_doc']
        
        if st.button("🔙 العودة إلى نتائج البحث / Back to Search", type="primary", key="top_back_nav_search"):
            del st.session_state['active_doc']
            st.rerun()
            
        display_pdf_preview(doc_info['buffer'], file_name=doc_info['filename'], key_suffix=doc_info['key'])
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
                    pdf_buf = generate_pdf_from_record("repair_receipt_dual", rec_data, COMPANY_INFO)
                    st.session_state['active_doc'] = {
                        'buffer': pdf_buf,
                        'filename': f"Inlamningskvitto_{selected_rep_id}.pdf",
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
                        "item_desc": "Reparation och reservdelar",
                        "amount": i_row['amount'] if inc_price else 0.0,
                        "moms": i_row['moms'] if inc_price else 0.0,
                        "currency": "SEK", "moms_rate": "25%",
                        "employee": i_row['employee'] if inc_emp else "N/A",
                        "created_at": str(i_row['created_at'])[:10] if inc_date else "",
                        "due_date": (date.today() + timedelta(days=30)).strftime('%Y-%m-%d')
                    }
                    pdf_buf = generate_pdf_from_record("invoice", inv_data, COMPANY_INFO)
                    st.session_state['active_doc'] = {
                        'buffer': pdf_buf,
                        'filename': f"{i_row['invoice_no']}.pdf",
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
                        "currency": "SEK",
                        "employee": q_row['employee'] if inc_emp else "N/A",
                        "created_at": str(q_row['created_at'])[:10] if inc_date else ""
                    }
                    pdf_buf = generate_pdf_from_record("quote", q_data, COMPANY_INFO)
                    st.session_state['active_doc'] = {
                        'buffer': pdf_buf,
                        "filename": f"Kostnadsforslag_{selected_quote_id}.pdf",
                        'key': f"search_quote_{selected_quote_id}"
                    }
                    st.rerun()

        conn.close()
