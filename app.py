# --- TAB 10: SEARCH WITH PERSISTENT PREVIEW STATE ---
with tab10:
    st.markdown("<div class='search-box'>", unsafe_allow_html=True)
    st.header(f"🔍 البحث والأرشيف وتخصيص الحقول للعرض والطباعة / Search & Field Checklist ({global_branch})")
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
            pdf_key = f"search_rep_buf_{selected_rep_id}"
            
            if st.button("📄 معاينة وطباعة إيصال الإصلاح", key=f"btn_gen_rep_{selected_rep_id}"):
                rec_data = {
                    "branch": global_branch, "repair_id": str(r_row['id']),
                    "customer_name": r_row['customer_name'] if inc_name else "N/A",
                    "phone": r_row['phone'] if inc_phone else "N/A",
                    "device": r_row['device'] if inc_device else "N/A",
                    "imei": "N/A",
                    "issue": r_row['issue'] if inc_issue else "N/A",
                    "price": r_row['price'] if inc_price else 0.0,
                    "employee": r_row['employee'] if inc_emp else "N/A",
                    "created_at": str(r_row['created_at'])[:10] if inc_date else ""
                }
                st.session_state[pdf_key] = generate_pdf_from_record("repair_receipt_dual", rec_data, COMPANY_INFO)

            if pdf_key in st.session_state:
                display_pdf_preview(st.session_state[pdf_key], file_name=f"Inlamningskvitto_{selected_rep_id}.pdf", key_suffix=f"search_rep_{selected_rep_id}")
                if r_row['phone'] and inc_phone:
                    wa_t = f"Hej {r_row['customer_name']}! Här är ditt inlämningskvitto för {r_row['device']} hos 30 Minutes Phone Fix ({global_branch}). Välkommen!"
                    st.markdown(f'<a href="{get_whatsapp_link(r_row["phone"], wa_t)}" target="_blank" class="whatsapp-btn">💬 إرسال الإيصال عبر WhatsApp للعميل</a>', unsafe_allow_html=True)
    else:
        st.info("لا توجد نتائج مطابقة في جدول الإصلاحات.")

    # 2. INVOICES SEARCH
    st.subheader("📄 الفواتير المسجلة (Invoices)")
    inv_res = pd.read_sql_query("SELECT id, invoice_no, customer_name, phone, address, amount, moms, employee, created_at FROM invoices WHERE branch = ? AND (customer_name LIKE ? OR phone LIKE ? OR invoice_no LIKE ?)", conn, params=(global_branch, q_like, q_like, q_like))
    if not inv_res.empty:
        inv_map = {'customer_name': inc_name, 'phone': inc_phone, 'amount': inc_price, 'employee': inc_emp, 'created_at': inc_date}
        st.dataframe(filter_df_columns(inv_res, inv_map), use_container_width=True)
        
        selected_inv_id = st.selectbox("🖨️ اختر رقم فاتورة (ID) لطباعة أو إرسال الفاتورة:", inv_res['id'].tolist(), key="sel_inv_id")
        if selected_inv_id:
            i_row = inv_res[inv_res['id'] == selected_inv_id].iloc[0]
            pdf_key = f"search_inv_buf_{selected_inv_id}"
            
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
                st.session_state[pdf_key] = generate_pdf_from_record("invoice", inv_data, COMPANY_INFO)

            if pdf_key in st.session_state:
                display_pdf_preview(st.session_state[pdf_key], file_name=f"{i_row['invoice_no']}.pdf", key_suffix=f"search_inv_{selected_inv_id}")
                if i_row['phone'] and inc_phone:
                    wa_t = f"Hej {i_row['customer_name']}! Här är er faktura {i_row['invoice_no']} på {i_row['amount']} SEK från 30 Minutes Phone Fix ({global_branch}). Tack!"
                    st.markdown(f'<a href="{get_whatsapp_link(i_row["phone"], wa_t)}" target="_blank" class="whatsapp-btn">💬 إرسال الفاتورة عبر WhatsApp للعميل</a>', unsafe_allow_html=True)
    else:
        st.info("لا توجد نتائج مطابقة في جدول الفواتير.")

    # 3. QUOTES SEARCH
    st.subheader("💡 عروض الأسعار (Quotes)")
    quote_res = pd.read_sql_query("SELECT id, customer_name, phone, device, issues, total, profit, employee, created_at FROM quotes WHERE branch = ? AND (customer_name LIKE ? OR phone LIKE ? OR device LIKE ?)", conn, params=(global_branch, q_like, q_like, q_like))
    if not quote_res.empty:
        q_map = {'customer_name': inc_name, 'phone': inc_phone, 'device': inc_device, 'issues': inc_issue, 'total': inc_price, 'employee': inc_emp, 'created_at': inc_date}
        st.dataframe(filter_df_columns(quote_res, q_map), use_container_width=True)
        
        selected_quote_id = st.selectbox("🖨️ اختر رقم عرض سعر (ID) لطباعة أو إرسال العرض:", quote_res['id'].tolist(), key="sel_quote_id")
        if selected_quote_id:
            q_row = quote_res[quote_res['id'] == selected_quote_id].iloc[0]
            pdf_key = f"search_quote_buf_{selected_quote_id}"
            
            if st.button("📄 معاينة وطباعة عرض السعر", key=f"btn_gen_quote_{selected_quote_id}"):
                q_data = {
                    "branch": global_branch,
                    "customer_name": q_row['customer_name'] if inc_name else "N/A",
                    "phone": q_row['phone'] if inc_phone else "N/A",
                    "device": q_row['device'] if inc_device else "N/A",
                    "issues": q_row['issues'] if inc_issue else "N/A",
                    "total": q_row['total'] if inc_price else 0.0,
                    "currency": "SEK",
                    "employee": q_row['employee'] if inc_emp else "N/A",
                    "created_at": str(q_row['created_at'])[:10] if inc_date else ""
                }
                st.session_state[pdf_key] = generate_pdf_from_record("quote", q_data, COMPANY_INFO)

            if pdf_key in st.session_state:
                display_pdf_preview(st.session_state[pdf_key], file_name=f"Kostnadsforslag_{selected_quote_id}.pdf", key_suffix=f"search_quote_{selected_quote_id}")
                if q_row['phone'] and inc_phone:
                    wa_t = f"Hej {q_row['customer_name']}! Här är ert kostnadsförslag för {q_row['device']} på {q_row['total']} SEK från 30 Minutes Phone Fix ({global_branch}). Välkommen!"
                    st.markdown(f'<a href="{get_whatsapp_link(q_row["phone"], wa_t)}" target="_blank" class="whatsapp-btn">💬 إرسال عرض السعر عبر WhatsApp للعميل</a>', unsafe_allow_html=True)
    else:
        st.info("لا توجد نتائج مطابقة في جدول عروض الأسعار.")

    # 4. SUBSCRIPTIONS
    st.subheader("💳 الاشتراكات (Subscriptions)")
    sub_res = pd.read_sql_query("SELECT id, customer_name, phone, device, plan_type, price, employee, start_date FROM subscriptions WHERE branch = ? AND (customer_name LIKE ? OR phone LIKE ? OR device LIKE ?)", conn, params=(global_branch, q_like, q_like, q_like))
    if not sub_res.empty:
        sub_map = {'customer_name': inc_name, 'phone': inc_phone, 'device': inc_device, 'plan_type': inc_status, 'price': inc_price, 'employee': inc_emp, 'start_date': inc_date}
        st.dataframe(filter_df_columns(sub_res, sub_map), use_container_width=True)

    # 5. BUYBACKS & ACTION
    st.subheader("📱 شراء الأجهزة (Buybacks)")
    bb_res = pd.read_sql_query("SELECT id, customer_name, phone, person_nummer, device, purchase_price, employee, created_at FROM buybacks WHERE branch = ? AND (customer_name LIKE ? OR phone LIKE ? OR device LIKE ?)", conn, params=(global_branch, q_like, q_like, q_like))
    if not bb_res.empty:
        bb_map = {'customer_name': inc_name, 'phone': inc_phone, 'device': inc_device, 'purchase_price': inc_price, 'employee': inc_emp, 'created_at': inc_date}
        st.dataframe(filter_df_columns(bb_res, bb_map), use_container_width=True)
        
        selected_bb_id = st.selectbox("🖨️ اختر رقم شراء (ID) لإيصال الشراء:", bb_res['id'].tolist(), key="sel_bb_id")
        if selected_bb_id:
            b_row = bb_res[bb_res['id'] == selected_bb_id].iloc[0]
            pdf_key = f"search_bb_buf_{selected_bb_id}"
            
            if st.button("📄 معاينة وطباعة إيصال الشراء", key=f"btn_gen_bb_{selected_bb_id}"):
                bb_data = {
                    "branch": global_branch, "buyback_id": str(b_row['id']),
                    "customer_name": b_row['customer_name'] if inc_name else "N/A",
                    "phone": b_row['phone'] if inc_phone else "N/A",
                    "person_nummer": b_row['person_nummer'],
                    "device": b_row['device'] if inc_device else "N/A",
                    "imei": "N/A",
                    "purchase_price": b_row['purchase_price'] if inc_price else 0.0,
                    "currency": "SEK",
                    "employee": b_row['employee'] if inc_emp else "N/A",
                    "created_at": str(b_row['created_at'])[:10] if inc_date else ""
                }
                st.session_state[pdf_key] = generate_pdf_from_record("buyback_receipt", bb_data, COMPANY_INFO)

            if pdf_key in st.session_state:
                display_pdf_preview(st.session_state[pdf_key], file_name=f"Inkopskvitto_{selected_bb_id}.pdf", key_suffix=f"search_bb_{selected_bb_id}")
    
    conn.close()
    st.markdown("</div>", unsafe_allow_html=True)
