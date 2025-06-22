import os
from typing import List
import yaml

languages = {}
languages_present = {}

def get_string(lang: str):
    return languages[lang]

# احصل على المسار الواقعي لمجلد langs بجانب هذا الملف
BASE = os.path.dirname(os.path.realpath(__file__))
LANG_DIR = os.path.join(BASE, "langs")

for filename in os.listdir(LANG_DIR):
    if filename.endswith(".yml"):
        if "en" not in languages and filename == "en.yml":
            en_path = os.path.join(LANG_DIR, filename)
            languages["en"] = yaml.safe_load(open(en_path, encoding="utf8"))
            languages_present["en"] = languages["en"]["name"]
        language_name = filename[:-4]
        if language_name == "en":
            continue
        path = os.path.join(LANG_DIR, filename)
        languages[language_name] = yaml.safe_load(open(path, encoding="utf8"))
        # دمج المفاتيح المفقودة
        for item in languages["en"]:
            if item not in languages[language_name]:
                languages[language_name][item] = languages["en"][item]
        try:
            languages_present[language_name] = languages[language_name]["name"]
        except KeyError:
            print(f"There is some issue with the language file: {filename}")
            exit()

# تحقق نهائي من وجود en
if "en" not in languages:
    print("There is some issue with the language file inside bot.")
    exit()
