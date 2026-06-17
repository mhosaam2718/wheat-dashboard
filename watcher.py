import os
import time
import glob
import sqlite3
import pandas as pd
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# المسارات النسبية لسهولة النقل وضمان المرونة
INPUT_DIR = "./data_input"
DB_DIR = "./database"
DB_PATH = os.path.join(DB_DIR, "wheat_data.db")

# --- الهيكل القياسي المطلوب للأعمدة ---
REQUIRED_COLUMNS = ['كود_المورد', 'اسم_المورد', 'الكمية', 'الدرجة', 'التاريخ']

# إنشاء المجلدات تلقائياً إن لم تكن موجودة
os.makedirs(INPUT_DIR, exist_ok=True)
os.makedirs(DB_DIR, exist_ok=True)

def validate_and_clean_file(file_path):
    """دالة فحص سلامة الملف وتنظيف بياناته قبل الدمج"""
    try:
        df = pd.read_excel(file_path)
        
        # 1. تنظيف أولي: حذف الصفوف الفارغة تماماً
        df.dropna(how='all', inplace=True)
        if df.empty:
            print(f"⚠️ تنبيه: الملف {os.path.basename(file_path)} فارغ تماماً وتم تجاهله.")
            return None

        # 2. تنظيف أسماء الأعمدة من المسافات العشوائية لضمان دقة الفحص
        df.columns = [str(col).strip() for col in df.columns]

        # 3. طبقة التحقق الصارمة (Schema Validation)
        missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
        if missing_cols:
            print(f"❌ خطأ فادح: الملف '{os.path.basename(file_path)}' يفتقد للأعمدة الأساسية التالية: {missing_cols}. تم استبعاده لحماية النظام.")
            return None

        # 4. توحيد البيانات النصية ومعالجة الأخطاء الإملائية الناتجة عن المسافات
        text_cols = df.select_dtypes(include=['object']).columns
        for col in text_cols:
            df[col] = df[col].astype(str).str.strip()
            # استبدال الفراغات المتعددة بفراغ واحد
            df[col] = df[col].str.replace(r'\s+', ' ', regex=True)

        # 5. معالجة القيم المفقودة في الحقول الحرجة لتجنب أخطاء قواعد البيانات
        df['كود_المورد'] = df['كود_المورد'].fillna('غير معرف')
        df['اسم_المورد'] = df['اسم_المورد'].fillna('مورد مجهول')
        df['الدرجة'] = df['الدرجة'].fillna('غير محددة')
        df['الكمية'] = pd.to_numeric(df['الكمية'], errors='coerce').fillna(0.0)

        # 6. إضافة عمود التدقيق (Audit Trail) لمعرفة مصدر كل سجل
        df['مصدر_البيانات'] = os.path.basename(file_path)

        return df[REQUIRED_COLUMNS + ['مصدر_البيانات']]

    except Exception as e:
        print(f"❌ فشل فحص وتجهيز الملف {os.path.basename(file_path)}. السبب: {e}")
        return None

def run_etl_pipeline():
    """خط الإنتاج الذكي (ETL Pipeline) لدمج وتصفية البيانات وتحميلها لقاعدة البيانات"""
    all_files = glob.glob(os.path.join(INPUT_DIR, "*.xlsx"))
    if not all_files:
        print("ℹ️ المجلد فارغ. لا توجد ملفات إكسل لمعالجتها حالياً.")
        return

    valid_dfs = []
    for file in all_files:
        processed_df = validate_and_clean_file(file)
        if processed_df is not None:
            valid_dfs.append(processed_df)

    if valid_dfs:
        # تجميع كل الملفات السليمة في DataFrame واحد
        final_df = pd.concat(valid_dfs, ignore_index=True)
        
        # --- تعديل تثبيت التاريخ القياسي قبل النقل لقاعدة البيانات لضمان المظهر الصحيح ---
        if 'التاريخ' in final_df.columns:
            final_df['التاريخ'] = pd.to_datetime(final_df['التاريخ'], errors='coerce').dt.strftime('%Y-%m-%d')
        
        # إزالة التكرارات التلقائية
        initial_count = len(final_df)
        final_df.drop_duplicates(subset=REQUIRED_COLUMNS, keep='first', inplace=True)
        duplicates_removed = initial_count - len(final_df)
        
        if duplicates_removed > 0:
            print(f"🧹 تم تنظيف وإزالة {duplicates_removed} صف مكرر تلقائياً.")

        # الحفظ الآمن والمنظم في قاعدة بيانات SQLite
        try:
            conn = sqlite3.connect(DB_PATH)
            # استبدال البيانات القديمة بالبيانات المحدثة والمصفاة بالكامل
            final_df.to_sql("wheat_supplies", conn, if_exists="replace", index=False)
            conn.close()
            print(f"✅ تم تحديث قاعدة البيانات المركزية بنجاح! إجمالي السجلات السليمة: {len(final_df)}")
        except Exception as e:
            print(f"❌ خطأ أثناء الكتابة في قاعدة البيانات المجمعة: {e}")
    else:
        print("⚠️ لم يتم تحديث قاعدة البيانات لأنه لم يتم العثور على أي ملف إكسل مطابق للشروط القياسية.")

class SafeWatcherHandler(FileSystemEventHandler):
    """مراقب ذكي ومستقر لحركة المجلد"""
    def on_any_event(self, event):
        if event.is_directory:
            return
        # الاستجابة الفورية عند إضافة أو تعديل ملف إكسل
        if event.event_type in ['created', 'modified'] and event.src_path.endswith('.xlsx'):
            print(f"🔔 استشعار حركة ملف: {os.path.basename(event.src_path)} - جاري الفحص والدمج...")
            # مهلة أمان (2 ثانية) لضمان اكتمال كتابة وحفظ الملف من قبل المستخدم بشكل كامل قبل قرائته
            time.sleep(2) 
            run_etl_pipeline()

if __name__ == "__main__":
    print("🌟 تم تشغيل نظام الفحص والمراقبة الاحترافي (Enterprise Watcher)...")
    # تشغيل المعالجة لأول مرة فور بدء السيرفر للتأكد من جاهزية البيانات
    run_etl_pipeline()
    
    event_handler = SafeWatcherHandler()
    observer = Observer()
    observer.schedule(event_handler, path=INPUT_DIR, recursive=False)
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 تم إيقاف نظام المراقبة بنجاح.")
        observer.stop()
    observer.join()
