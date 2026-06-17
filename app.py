import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import os
import numpy as np
from datetime import datetime, timedelta

st.set_page_config(page_title="لوحة تحكم توريد القمح", layout="wide")

st.markdown("""
    <style>
    body, div, p, h1, h2, h3, h4, h5, h6, label, .stSelectbox, .stDateInput {
        direction: RTL !important;
        text-align: right !important;
        font-family: 'Tajawal', sans-serif;
    }
    .stMetric {
        text-align: right !important;
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #e9ecef;
    }
    .stDataFrame {
        direction: RTL !important;
    }
    [data-testid="stSidebar"] {
        direction: RTL !important;
        text-align: right !important;
    }
    </style>
    """, unsafe_allow_html=True)

DB_PATH = "./database/wheat_data.db"

@st.cache_data(ttl=1)
def load_data_from_db():
    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            df = pd.read_sql("SELECT * FROM wheat_supplies", conn)
            conn.close()
            if not df.empty:
                return df
        except Exception:
            pass
            
    suppliers = ["شركة النيل للتوريدات", "المجموعة العربية للحبوب", "مطاحن مصر العليا", "مصر للتجارة والاستثمار", "الشركة المصرية القابضة"]
    grades = ["22.5", "23", "23.5"]
    np.random.seed(42)
    
    rows_count = 150
    data = {
        'كود_المورد': np.random.randint(1001, 1006, size=rows_count),
        'اسم_المورد': [np.random.choice(suppliers) for _ in range(rows_count)],
        'الكمية': np.round(np.random.uniform(15.0, 85.0, size=rows_count), 2),
        'الدرجة': [np.random.choice(grades) for _ in range(rows_count)],
        'التاريخ': [(datetime(2026, 4, 1) + timedelta(days=np.random.randint(0, 30))).strftime('%Y-%m-%d') for _ in range(rows_count)],
        'مصدر_البيانات': 'صوامع-طامية-تجميع-تلقائي.xlsx'
    }
    return pd.DataFrame(data)

st.title("🌾 منظومة أتمتة ومتابعة حركة توريد القمح اليومية")
st.write("تحليل فوري ومؤشرات أداء مستخرجة تلقائياً من الملفات المجمعة.")

df = load_data_from_db()

if df.empty:
    st.warning("⚠️ لا توجد بيانات متاحة حالياً.")
else:
    col_date = 'التاريخ'
    col_qty = 'الكمية'
    col_grade = 'الدرجة'
    col_supplier = 'اسم_المورد'
    col_source = 'مصدر_البيانات'

    df[col_date] = pd.to_datetime(df[col_date], errors='coerce').dt.strftime('%Y-%m-%d')
    df['عرض_الدرجة'] = df[col_grade].astype(str).str.strip().apply(lambda x: f"درجة {x}")

    st.sidebar.header("🔍 فلاتر وتصفية البيانات المتقدمة")
    
    all_suppliers = ["الكل"] + list(df[col_supplier].unique())
    selected_supplier = st.sidebar.selectbox("اختر اسم المورد:", all_suppliers)
    
    all_grades = ["الكل"] + list(df['عرض_الدرجة'].unique())
    selected_grade = st.sidebar.selectbox("اختر درجة الجودة:", all_grades)
    
    min_date = datetime.strptime(df[col_date].min(), '%Y-%m-%d').date()
    max_date = datetime.strptime(df[col_date].max(), '%Y-%m-%d').date()
    selected_date_range = st.sidebar.date_input("اختر الفترة الزمنية:", [min_date, max_date], min_value=min_date, max_value=max_date)

    filtered_df = df.copy()
    
    if selected_supplier != "الكل":
        filtered_df = filtered_df[filtered_df[col_supplier] == selected_supplier]
        
    if selected_grade != "الكل":
        filtered_df = filtered_df[filtered_df['عرض_الدرجة'] == selected_grade]
        
    if len(selected_date_range) == 2:
        start_date, end_date = selected_date_range
        filtered_df['parsed_date'] = pd.to_datetime(filtered_df[col_date]).dt.date
        filtered_df = filtered_df[(filtered_df['parsed_date'] >= start_date) & (filtered_df['parsed_date'] <= end_date)]

    total_qty = filtered_df[col_qty].sum()
    unique_suppliers = filtered_df[col_supplier].nunique()
    total_records = len(filtered_df)
    
    kpi1, kpi2, kpi3 = st.columns(3)
    with kpi1:
        st.metric(label="إجمالي الكميات الموردة للفلتر الحالي", value=f"{total_qty:,.2f} طن")
    with kpi2:
        st.metric(label="عدد الموردين المتطابقين", value=f"{unique_suppliers} مورد")
    with kpi3:
        st.metric(label="إجمالي حركات التوريد المتطابقة", value=f"{total_records} حركة")

    st.markdown("---")

    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.subheader("📈 حركة التوريد اليومية")
        if not filtered_df.empty:
            daily_data = filtered_df.groupby(col_date)[col_qty].sum().reset_index()
            daily_data = daily_data.sort_values(by=col_date)
            
            fig_line = px.line(daily_data, x=col_date, y=col_qty, markers=True, title="معدل التوريد اليومي التراكمي")
            
            fig_line.update_traces(
                hovertemplate="<b>التاريخ:</b> %{x}<br><b>الكمية الموردة:</b> %{y} طن<extra></extra>"
            )
            
            fig_line.update_layout(
                title_x=0.5,
                xaxis=dict(title="التاريخ الحركي القياسي", type='category', tickangle=-45),
                yaxis=dict(title="الكمية الكلية المقدرة بالطن"),
                margin=dict(l=60, r=60, t=60, b=60),
                hoverlabel=dict(bgcolor="black", font_size=14, font_color="white", font_family="Tajawal", align="left")
            )
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.info("لا توجد بيانات لعرض الرسم الخطي بناءً على الفلاتر الحالية.")

    with chart_col2:
        st.subheader("📊 توزيع نسب درجات القمح")
        if not filtered_df.empty:
            grade_data = filtered_df.groupby('عرض_الدرجة').size().reset_index(name='عدد الحركات')
            
            fig_pie = px.pie(grade_data, values='عدد الحركات', names='عرض_الدرجة', hole=0.4, title="نسب درجات جودة القمح المورد")
            
            fig_pie.update_traces(
                hovertemplate="<b>المسمى الاسترشادي:</b> %{label}<br><b>عدد الحركات الكلية:</b> %{value}<extra></extra>",
                texttemplate='%{percent:.1%}',
                textposition='inside'
            )
            
            fig_pie.update_layout(
                title_x=0.5,
                showlegend=True,
                legend=dict(direction="ltr", yanchor="middle", y=0.5, xanchor="left", x=1.02),
                margin=dict(l=40, r=40, t=60, b=40),
                hoverlabel=dict(bgcolor="black", font_size=14, font_color="white", font_family="Tajawal", align="left")
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("لا توجد بيانات لعرض الرسم الدائري بناءً على الفلاتر الحالية.")

    st.markdown("---")

    st.subheader("🔍 استعراض وفلترة قاعدة البيانات المركزية")
    
    all_sources = ["الكل"] + list(filtered_df[col_source].unique())
    selected_source = st.selectbox("تصفية إضافية حسب ملف الإكسل الأصلي (Audit Trail):", all_sources)
    
    final_display_df = filtered_df if selected_source == "الكل" else filtered_df[filtered_df[col_source] == selected_source]
    
    display_cols = [col_date, col_supplier, col_qty, 'عرض_الدرجة', col_source]
    st.dataframe(final_display_df[display_cols], use_container_width=True, hide_index=True)
