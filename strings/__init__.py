import os
import yaml

languages = {}
languages_present = {}

def get_string(lang: str):
    return languages[lang]

# تحديد المسار المطلق لمجلد اللغات
BASE_DIR = os.path.dirname(os.path.realpath(__file__))
LANGS_DIR = "/storage/emulated/0/BotMusic/strings/langs"

# التأكد من وجود مجلد اللغات
if not os.path.isdir(LANGS_DIR):
    print(f"مجلد اللغات غير موجود: {LANGS_DIR}")
    exit()

# تحميل ملفات اللغات
for filename in os.listdir(LANGS_DIR):
    if filename.endswith(".yml"):
        lang_code = filename[:-4]
        file_path = os.path.join(LANGS_DIR, filename)

        try:
            with open(file_path, encoding="utf8") as file:
                data = yaml.safe_load(file)
        except Exception as e:
            print(f"فشل تحميل ملف اللغة {filename}: {e}")
            exit()

        if lang_code == "en":
            languages["en"] = data
            languages_present["en"] = data.get("name", "English")
        else:
            languages[lang_code] = data
            for key, val in languages["en"].items():
                languages[lang_code].setdefault(key, val)
            languages_present[lang_code] = data.get("name", lang_code)

# التأكد من وجود اللغة الإنجليزية
if "en" not in languages:
    print("اللغة الإنجليزية غير موجودة في ملفات اللغات.")
    exit()
