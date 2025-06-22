import os
import yaml

# قاموسي تخزين اللغات ونُسخها
languages = {}
languages_present = {}

# تحديد مسار مجلد اللغات اعتمادًا على موقع هذا الملف
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LANG_DIR = os.path.join(BASE_DIR, "langs")

# التحقق من وجود المجلد
if not os.path.isdir(LANG_DIR):
    print(f"❌ المجلد {LANG_DIR} غير موجود.")
    exit(1)

# تحميل كافة ملفات .yml من مجلد اللغات
for filename in os.listdir(LANG_DIR):
    if not filename.endswith(".yml"):
        continue

    lang_code = filename[:-4]
    path = os.path.join(LANG_DIR, filename)

    try:
        data = yaml.safe_load(open(path, encoding="utf-8"))
    except Exception as e:
        print(f"❌ خطأ عند تحميل ملف اللغة {filename}: {e}")
        exit(1)

    languages[lang_code] = data
    languages_present[lang_code] = data.get("name", lang_code)

# التأكد من وجود اللغة الإنجليزية
if "en" not in languages:
    print("❌ ملف اللغة en.yml مفقود في strings/langs/")
    exit(1)

# ملء المفاتيح الناقصة في اللغات الأخرى بمحتوى الإنجليزية
default = languages["en"]
for code, data in languages.items():
    if code == "en":
        continue
    for key in default:
        if key not in data:
            data[key] = default[key]

def get_string(lang: str):
    """تُرجع مصفوفة النصوص للغة المطلوبة، أو الإنجليزية إذا غير موجودة."""
    return languages.get(lang, languages["en"])
