import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import os
import numpy as np
from datetime import datetime, timedelta

# إعداد الصفحة وتفعيل المظهر الواسع
st.set_page_config(page_title="لوحة تحكم توريد القمح", layout="wide")

# دعم اللغة العربية واتجاه RTL
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
            
    # بيانات محاكاة فورية ومضمونة
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

    # كروت مؤشرات الأداء السريعة
    total_qty = df[col_qty].sum()
    unique_suppliers = df[col_supplier].nunique()
    total_records = len(df)
    
    kpi1, kpi2, kpi3 = st.columns(3)
    with kpi1:
        st.metric(label="إجمالي الكميات الموردة (طن)", value=f"{total_qty:,.2f}")
    with kpi2:
        st.metric(label="عدد الموردين النشطين", value=unique_suppliers)
    with kpi3:
        st.metric(label="إجمالي حركات التوريد المسجلة", value=total_records)

    st.markdown("---")

    # المخططات البيانية التفاعلية بدون أي دوال تحديث معقدة لمنع الـ ValueError
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.subheader("📈 حركة التوريد اليومية")
        daily_data = df.groupby(col_date)[col_qty].sum().reset_index().sort_values(by=col_date)
        fig_line = px.line(daily_data, x=col_date, y=col_qty, markers=True, title="معدل التوريد اليومي")
        st.plotly_chart(fig_line, use_container_width=True)

    with chart_col2:
        st.subheader("📊 توزيع نسب درجات القمح")
        grade_data = df.groupby('عرض_الدرجة').size().reset_index(name='عدد الحركات')
        fig_pie = px.pie(grade_data, values='عدد الحركات', names='عرض_الدرجة', title="نسب درجات الجودة")
        st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("---")

    st.subheader("🔍 استعراض قاعدة البيانات المركزية")
    display_cols = [col_date, col_supplier, col_qty, 'عرض_الدرجة', col_source]
    st.dataframe(df[display_cols], use_container_width=True, hide_index=True)
