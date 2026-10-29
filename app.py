import streamlit as st
import sqlite3
import os
from datetime import datetime, date
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import io
import pandas as pd
import base64

# --- Database Setup ---
def get_db():
    conn = sqlite3.connect("local_crm.db", check_same_thread=False)
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS repairs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        branch TEXT, customer_name TEXT, phone TEXT, email TEXT,
        device TEXT, imei TEXT, issue TEXT, price REAL,
        status TEXT, employee TEXT, created_at TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        branch TEXT, customer_name TEXT, phone TEXT, address TEXT, 
        invoice_no TEXT, amount REAL, moms REAL, currency TEXT, employee TEXT, created_at TEXT
    )""")
    conn.commit()
    conn.close()

init_db()

st.set_page_config(page_title="30 Minutes Phone Fix CRM", layout="wide", page_icon="📱")

COMPANY_INFO = {
    "Eskilstuna": {"name": "30 MINUTES PHONE FIX", "address": "Gunborg Nymans Väg 2, Eskilstuna", "phone": "0700122444", "org_nr": "5593708034", "swish": "123 407 16 76"},
    "Västerås": {"name": "30 MINUTES PHONE FIX", "address": "Västerås", "phone": "0700122444", "org_nr": "559537-1724", "swish": "123 339 15 47"}
}

# --- Header & Branch Selection ---
col1, col2 = st.columns(2)
with col1:
    global_branch = st.selectbox("🏢 Select Branch / الفرع", ["Eskilstuna", "Västerås"])
with col2:
    lang = st.selectbox("🌐 Language / اللغة", ["Svenska", "English", "العربية"])

comp = COMPANY_INFO[global_branch]
st.markdown(f"**Butik:** {comp['name']} | **Tel:** {comp['phone']} | **Swish:** {comp['swish']}")
st.markdown("---")

# --- Simple Login ---
if 'auth' not in st.session_state:
    st.session_state['auth'] = False

if not st.session_state['auth']:
    pin = st.text_input("🔑 PIN Code (tunapark):", type="password")
    if pin == "tunapark":
        st.session_state['auth'] = True
        st.rerun()
    elif pin:
        st.error("❌ PIN-kod felaktig!")
    st.stop()

if st.sidebar.button("🔒 Logga ut"):
    st.session_state['auth'] = False
    st.rerun()

# --- Tabs ---
tab1, tab2 = st.tabs(["🛠️ Nytt Ärende / إصلاح جديد", "📄 Faktura / فاتورة"])

with tab1:
    st.subheader("تسجيل إصلاح جديد / Nytt Ärende")
    emp = st.text_input("اسم الموظف / Handläggare")
    name = st.text_input("اسم العميل / Kundens namn")
    phone = st.text_input("رقم الهاتف / Telefon")
    device = st.text_input("الجهاز / Enhet")
    price = st.number_input("السعر / Pris", min_value=0.0, step=50.0)
    issue = st.text_area("العطل / Beskrivning")

    if st.button("حفظ وحفظ البيانات", type="primary"):
        if name and phone and emp:
            conn = get_db()
            c = conn.cursor()
            c.execute("INSERT INTO repairs (branch, customer_name, phone, device, issue, price, status, employee, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                      (global_branch, name, phone, device, issue, price, "Pågår", emp, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
            conn.close()
            st.success("✅ تم حفظ طلب الإصلاح بنجاح!")
        else:
            st.warning("⚠️ يرجى تعبئة الحقول الأساسية واسم الموظف.")

with tab2:
    st.subheader("إنشاء فاتورة / Skapa Faktura")
    inv_emp = st.text_input("اسم الموظف للفاتورة")
    inv_name = st.text_input("اسم العميل للفاتورة")
    inv_price = st.number_input("المبلغ الإجمالي / Total", min_value=0.0, step=50.0)
    
    if st.button("إنشاء فاتورة وسداد Swish"):
        st.success(f"✅ الفاتورة جاهزة بمبلغ {inv_price} SEK. رقم Swish للفرع: {comp['swish']}")
