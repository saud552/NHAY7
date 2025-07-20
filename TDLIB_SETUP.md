# 🔧 دليل إعداد وبناء TDLib لمشروع ZeMusic

## 📋 نظرة عامة

**TDLib** (Telegram Database Library) هي مكتبة متعددة المنصات لبناء تطبيقات Telegram عالية الأداء. هذا الدليل يوضح كيفية بناء وتكامل TDLib مع مشروع ZeMusic.

---

## 🛠️ المتطلبات الأساسية

### **🖥️ متطلبات النظام:**
- **المعالج:** 64-bit (x86_64 أو ARM64)
- **الذاكرة:** 4GB+ RAM (أثناء البناء)
- **التخزين:** 2GB+ مساحة فارغة
- **نظام التشغيل:** Linux, macOS, Windows

### **📦 الحزم المطلوبة (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install -y build-essential cmake git zlib1g-dev libssl-dev gperf php-cli python3 python3-pip
```

### **🍎 macOS:**
```bash
brew install cmake gperf php openssl
```

### **🪟 Windows:**
- Visual Studio 2019+ مع C++ tools
- CMake 3.20+
- Git for Windows

---

## 🚀 طرق البناء

### **🔧 الطريقة الأولى: سكريبت تلقائي (موصى به)**

```bash
# تشغيل سكريبت البناء التلقائي
./build_tdlib.sh
```

### **📝 الطريقة الثانية: بناء يدوي**

```bash
# 1. إنشاء مجلد TDLib
mkdir -p tdlib && cd tdlib

# 2. تحميل المصدر
git clone https://github.com/tdlib/td.git
cd td

# 3. إنشاء مجلد البناء
mkdir build && cd build

# 4. تكوين CMake
cmake -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_INSTALL_PREFIX:PATH=../tdlib \
      -DTD_ENABLE_LTO=ON \
      -DTD_ENABLE_JNI=OFF \
      ..

# 5. بناء وتثبيت
cmake --build . --target install -j $(nproc)
```

---

## 📁 هيكل الملفات بعد البناء

```
زeMUSIC/
├── tdlib/
│   └── td/
│       ├── build/          # ملفات البناء
│       └── tdlib/          # المكتبات المبنية
│           ├── bin/        # الملفات التنفيذية
│           ├── include/    # ملفات الهيدر
│           └── lib/        # المكتبات
├── libs/                   # نسخة من المكتبات (للتوزيع)
├── build_tdlib.sh         # سكريبت البناء
├── requirements_tdlib.txt  # متطلبات البناء
└── TDLIB_SETUP.md         # هذا الملف
```

---

## 🔗 التكامل مع ZeMusic

### **🐍 Python Integration:**

```python
import json
import ctypes
import ctypes.util

# تحميل مكتبة TDLib
tdlib_path = "./libs/lib/libtdjson.so"  # Linux
# tdlib_path = "./libs/lib/libtdjson.dylib"  # macOS  
# tdlib_path = "./libs/bin/tdjson.dll"  # Windows

tdjson = ctypes.CDLL(tdlib_path)

# إعداد الدوال
tdjson.td_json_client_create.restype = ctypes.c_void_p
tdjson.td_json_client_send.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
tdjson.td_json_client_receive.argtypes = [ctypes.c_void_p, ctypes.c_double]
tdjson.td_json_client_receive.restype = ctypes.c_char_p

# إنشاء عميل TDLib
client = tdjson.td_json_client_create()

# إرسال طلب
request = {
    "@type": "getOption",
    "name": "version"
}
tdjson.td_json_client_send(client, json.dumps(request).encode('utf-8'))

# استقبال النتيجة
result = tdjson.td_json_client_receive(client, 1.0)
print(json.loads(result.decode('utf-8')))
```

---

## ⚙️ إعدادات البناء المتقدمة

### **🎯 تحسين الأداء:**
```bash
cmake -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_INSTALL_PREFIX:PATH=../tdlib \
      -DTD_ENABLE_LTO=ON \
      -DTD_ENABLE_DOTNET=OFF \
      -DTD_ENABLE_JNI=OFF \
      -DCMAKE_CXX_FLAGS="-O3 -march=native" \
      ..
```

### **🐛 بناء للتطوير:**
```bash
cmake -DCMAKE_BUILD_TYPE=Debug \
      -DCMAKE_INSTALL_PREFIX:PATH=../tdlib \
      -DTD_ENABLE_ASSERTIONS=ON \
      ..
```

---

## 🐞 حل المشاكل الشائعة

### **❌ خطأ: "cmake: command not found"**
```bash
# Ubuntu/Debian
sudo apt install cmake

# macOS
brew install cmake

# إعادة تشغيل Terminal بعد التثبيت
```

### **❌ خطأ: "OpenSSL not found"**
```bash
# Ubuntu/Debian
sudo apt install libssl-dev

# macOS
brew install openssl
export PKG_CONFIG_PATH="/usr/local/opt/openssl/lib/pkgconfig"
```

### **❌ خطأ: "Out of memory during compilation"**
```bash
# تقليل عدد المعالجات المستخدمة
cmake --build . --target install -j 2

# أو استخدام swap
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

---

## 📊 معلومات الأداء

### **⏱️ أوقات البناء المتوقعة:**
- **معالج قوي (8+ cores):** 10-15 دقيقة
- **معالج متوسط (4-6 cores):** 20-30 دقيقة  
- **معالج ضعيف (2-4 cores):** 45-60 دقيقة

### **💾 استهلاك الموارد:**
- **مساحة المصدر:** ~500MB
- **مساحة البناء:** ~1.5GB
- **مساحة المكتبات:** ~200MB
- **RAM أثناء البناء:** 2-4GB

---

## 🔄 التحديثات

### **🆕 تحديث TDLib:**
```bash
cd tdlib/td
git pull
cd build
cmake --build . --target install -j $(nproc)
```

### **🧹 تنظيف البناء:**
```bash
cd tdlib/td
rm -rf build
mkdir build && cd build
# إعادة التكوين والبناء...
```

---

## 📞 الدعم والمساعدة

- **📚 الوثائق الرسمية:** https://core.telegram.org/tdlib
- **🐛 الإبلاغ عن الأخطاء:** https://github.com/tdlib/td/issues
- **💬 مجتمع Telegram:** @tdlib_chat

---

## ✅ التحقق من نجاح البناء

```bash
# التحقق من وجود المكتبات
ls -la libs/lib/
ls -la libs/include/

# اختبار سريع
python3 -c "
import ctypes
lib = ctypes.CDLL('./libs/lib/libtdjson.so')
print('✅ TDLib تم بناؤها بنجاح!')
"
```

---

**🎉 مبروك! تم إعداد TDLib بنجاح في مشروعك**