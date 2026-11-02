import streamlit.components.v1 as components
import base64

def display_pdf_preview(buffer, file_name, key_suffix):
    doc_text = buffer.getvalue().decode('utf-8')
    
    # تصميم واجهة داخلية تحتوي على زر للطباعة وزر للعودة داخل نفس الصفحة
    html_code = f"""
    <!DOCTYPE html>
    <html lang="sv">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                background-color: #f8f9fa;
                margin: 0;
                padding: 15px;
                color: #333;
            }}
            .card {{
                background-color: #ffffff;
                padding: 20px;
                border-radius: 12px;
                border: 1px solid #ddd;
                font-family: monospace;
                white-space: pre-wrap;
                font-size: 14px;
                line-height: 1.5;
                max-height: 450px;
                overflow-y: auto;
                box-shadow: 0 2px 6px rgba(0,0,0,0.05);
                margin-bottom: 15px;
            }}
            .btn-container {{
                display: flex;
                gap: 10px;
            }}
            .btn {{
                flex: 1;
                padding: 14px 20px;
                border-radius: 10px;
                font-size: 16px;
                font-weight: bold;
                border: none;
                cursor: pointer;
                text-align: center;
                box-shadow: 0 2px 4px rgba(0,0,0,0.15);
            }}
            .btn-print {{
                background-color: #007AFF;
                color: white;
            }}
            .btn-back {{
                background-color: #34C759;
                color: white;
            }}
        </style>
    </head>
    <body>
        <div class="card">{doc_text}</div>
        <div class="btn-container">
            <button class="btn btn-print" onclick="window.print();">🖨️ طباعة (Print)</button>
        </div>
    </body>
    </html>
    """
    
    st.markdown("### 📄 معاينة المستند (Document Preview)")
    
    # زر العودة العلوي في Streamlit لضمان الخروج الآمن
    if st.button("🔙 العودة إلى نتائج البحث / Back to Search", type="primary", key=f"top_back_{key_suffix}"):
        if 'active_doc' in st.session_state:
            del st.session_state['active_doc']
        st.rerun()
        
    components.html(html_code, height=580, scrolling=True)
    
    st.text_area("محتوى نصي قابل للنسخ / Copy Text", doc_text, height=120, key=f"copy_area_{key_suffix}")
