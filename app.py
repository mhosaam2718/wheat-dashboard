import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import os

# 1. إعداد الصفحة وتفعيل المظهر الواسع (Enterprise Layout)
st.set_page_config(page_title="لوحة تحكم توريد القمح", layout="wide")

# 2. حماية وتأمين الواجهة ودعم اللغة العربية واتجاه RTL بالكامل عبر الـ CSS
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

# كود ذكي لتحديد مسار قاعدة البيانات سواء محلياً أو أونلاين
if os.path.exists("./database/wheat_data.db"):
    DB_PATH = "./database/wheat_data.db"
elif os.path.exists("./wheat_data.db"):
    DB_PATH = "./wheat_data.db"
else:
    DB_PATH = "wheat_data.db"


@st.cache_data(ttl=5)
def load_data_from_db():
    """دالة قراءة البيانات بكفاءة عالية مع خاصية الكاش الذكي (Cache) لمنع التحميل الزائد"""
    if not os.path.exists(DB_PATH):
        return pd.DataFrame()
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql("SELECT * FROM wheat_supplies", conn)
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()

# العنوان الرئيسي للوحة التحكم
st.title("🌾 منظومة أتمتة ومتابعة حركة توريد القمح اليومية")
st.write("تحليل فوري ومؤشرات أداء مستخرجة تلقائياً من الملفات المجمعة.")

df = load_data_from_db()

if df.empty:
    st.warning("⚠️ لا توجد بيانات متاحة حالياً. يرجى التأكد من تشغيل سكربت المراقبة `watcher.py` أولاً، ووضع ملفات الإكسل في مجلد `data_input`.")
else:
    # المسميات القياسية المتوافقة تماماً مع طبقة فحص البيانات الاحترافية
    col_date = 'التاريخ'
    col_qty = 'الكمية'
    col_grade = 'الدرجة'
    col_supplier = 'اسم_المورد'
    col_source = 'مصدر_البيانات'

    # تحويل التاريخ لنسق صحيح لترتيب الرسم البياني بشكل سليم وللفلترة
    df[col_date] = pd.to_datetime(df[col_date], errors='coerce').dt.date

    # --- 🎛️ شريط الفلاتر المتقدمة الجانبي (Advanced Sidebar Filters) ---
    st.sidebar.header("🔍 فلاتر وتصفية البيانات المتقدمة")
    
    # 1. فلتر الموردين
    all_suppliers = ["الكل"] + list(df[col_supplier].unique())
    selected_supplier = st.sidebar.selectbox("اختر اسم المورد:", all_suppliers)
    
    # 2. فلتر درجات القمح
    all_grades = ["الكل"] + list(df[col_grade].unique())
    selected_grade = st.sidebar.selectbox("اختر درجة الجودة:", all_grades)
    
    # 3. فلتر نطاق التاريخ الديناميكي
    min_date = df[col_date].min()
    max_date = df[col_date].max()
    selected_date_range = st.sidebar.date_input("اختر الفترة الزمنية:", [min_date, max_date], min_value=min_date, max_value=max_date)

    # --- تطبيق الفلاتر برمجياً على البيانات المسحوبة (Data Querying) ---
    filtered_df = df.copy()
    
    if selected_supplier != "الكل":
        filtered_df = filtered_df[filtered_df[col_supplier] == selected_supplier]
        
    if selected_grade != "الكل":
        filtered_df = filtered_df[filtered_df[col_grade] == selected_grade]
        
    if len(selected_date_range) == 2:
        start_date, end_date = selected_date_range
        filtered_df = filtered_df[(filtered_df[col_date] >= start_date) & (filtered_df[col_date] <= end_date)]

    # --- كروت مؤشرات الأداء السريعة (KPIs) بناءً على الفلترة ---
    total_qty = filtered_df[col_qty].sum()
    unique_suppliers = filtered_df[col_supplier].nunique()
    total_records = len(filtered_df)
    
    kpi1, kpi2, kpi3 = st.columns(3)
    with kpi1:
        st.metric(label="إجمالي الكميات الموردة للفلتر الحالي (طن)", value=f"{total_qty:,.2f}")
    with kpi2:
        st.metric(label="عدد الموردين المتطابقين", value=unique_suppliers)
    with kpi3:
        st.metric(label="إجمالي حركات التوريد المتطابقة", value=total_records)

    st.markdown("---")

    # --- المخططات البيانية التفاعلية عالية الأداء بدون تشوهات الحروف الجانبية ---
    chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    st.subheader("📈 حركة التوريد اليومية")
    if not filtered_df.empty:
        daily_data = filtered_df.groupby(col_date)[col_qty].sum().reset_index()
        fig_line = px.line(daily_data, x=col_date, y=col_qty, markers=True)
        fig_line.update_layout(
            # ضبط مكان العنوان وتغيير لونه للأسود
            title={
                'text': "معدل التوريد اليومي التراكمي", 
                'y': 0.95, 'x': 0.5, 
                'xanchor': 'center', 'yanchor': 'top',
                'font': {'color': 'black', 'size': 16}
            },
            # ضبط المحور الأفقي ولون خطه للأسود
            xaxis={
                'title': "التاريخ", 
                'title_font': {'size': 14, 'color': 'black'}, 
                'tickfont': {'color': 'black'},
                'tickangle': -45
            },
            # ضبط المحور الرأسي ولون خطه للأسود
            yaxis={
                'title': "الكمية (طن)", 
                'title_font': {'size': 14, 'color': 'black'},
                'tickfont': {'color': 'black'}
            },
            # زيادة الهوامش لمنع خروج الكلام خارج المستطيل
            margin=dict(l=60, r=40, t=80, b=80),
            paper_bgcolor='white',  # خلفية الرسم بيضاء ليتضح اللون الأسود
            plot_bgcolor='white'
        )
        st.plotly_chart(fig_line, use_container_width=True)
    else:
        st.info("لا توجد بيانات لعرض الرسم الخطي بناءً على الفلاتر الحالية.")

with chart_col2:
    st.subheader("📊 توزيع نسب درجات القمح")
    if not filtered_df.empty:
        grade_data = filtered_df.groupby(col_grade).size().reset_index(name='عدد الحركات')
        fig_pie = px.pie(grade_data, values='عدد الحركات', names=col_grade, hole=0.4)
        fig_pie.update_layout(
            # ضبط مكان العنوان وتغيير لونه للأسود
            title={
                'text': "نسب درجات جودة القمح المورد", 
                'y': 0.95, 'x': 0.5, 
                'xanchor': 'center', 'yanchor': 'top',
                'font': {'color': 'black', 'size': 16}
            },
            # ضبط نص قائمة البيانات (Legend) للأسود
            legend={'font': {'color': 'black'}},
            showlegend=True,
            # زيادة الهوامش العلوية والسفلية لمنع خروج العنوان
            margin=dict(l=40, r=40, t=80, b=40),
            paper_bgcolor='white'
        )
        # جعل النصوص المكتوبة على أجزاء الدائرة باللون الأسود وداخل الإطار
        fig_pie.update_traces(textposition='inside', textinfo='percent+label', insidetextfont=dict(color='black'))
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("لا توجد بيانات لعرض الرسم الدائري بناءً على الفلاتر الحالية.")

    st.markdown("---")

# --- استعراض البيانات المجمعة والمصفاة بالكامل مع إمكانية التصفية حسب اسم الملف ---
st.subheader("🔍 استعراض وفلترة قاعدة البيانات المركزية")

all_sources = ["الكل"] + list(filtered_df[col_source].unique())
selected_source = st.selectbox("تصفية إضافية حسب ملف الإكسل الأصلي :", all_sources)

final_display_df = filtered_df if selected_source == "الكل" else filtered_df[filtered_df[col_source] == selected_source]

# عمل نسخة للعمل عليها بأمان
display_df = final_display_df.copy()

# الحل القاطع للتاريخ: تنظيف شامل للاسم والقيم
# 1. تنظيف أسماء الأعمدة من أي مسافات مخفية قد تمنع الكود من رؤية عمود "التاريخ"
display_df.columns = display_df.columns.str.strip()

if "التاريخ" in display_df.columns:
    # 2. محاولة تحويل العمود إلى نوع تاريخ حقيقي مع إجبار الصيغة وتجاهل الأخطاء الزائدة
    display_df["التاريخ"] = pd.to_datetime(display_df["التاريخ"], errors='coerce')
    
    # 3. تحويله إلى نص بالصيغة الصحيحة مباشرة، واستبدال القيم المفقودة بنص فارغ حتى لا يظهر NaT
    display_df["التاريخ"] = display_df["التاريخ"].dt.strftime('%Y-%m-%d').fillna("")

# عرض الجدول بعرض الشاشة بالكامل
st.dataframe(display_df, use_container_width=True, hide_index=True)
