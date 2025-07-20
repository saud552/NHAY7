#!/bin/bash

# 🚀 سكريبت بناء TDLib التلقائي لمشروع ZeMusic
# تاريخ الإنشاء: 2025-01-28

set -e

echo "🔧 بدء بناء TDLib..."

# إنشاء مجلد TDLib
mkdir -p tdlib
cd tdlib

# تحميل أحدث إصدار من TDLib
if [ ! -d "td" ]; then
    echo "📥 تحميل TDLib من GitHub..."
    git clone https://github.com/tdlib/td.git
else
    echo "🔄 تحديث TDLib..."
    cd td
    git pull
    cd ..
fi

# الدخول إلى مجلد المصدر
cd td

# إنشاء مجلد البناء
rm -rf build
mkdir build
cd build

echo "⚙️ تكوين CMake..."
cmake -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_INSTALL_PREFIX:PATH=../tdlib \
      -DTD_ENABLE_LTO=ON \
      -DTD_ENABLE_JNI=OFF \
      ..

echo "🏗️ بناء TDLib..."
# استخدام جميع المعالجات المتاحة
CORES=$(nproc)
echo "🚀 استخدام $CORES معالج للبناء..."

cmake --build . --target install -j $CORES

echo "✅ تم بناء TDLib بنجاح!"
echo "📁 مسار التثبيت: $(pwd)/../tdlib"

# العودة للمجلد الرئيسي
cd ../../../

# إنشاء رمز مختصر للمكتبات
if [ -d "tdlib/td/tdlib" ]; then
    echo "🔗 إنشاء روابط المكتبات..."
    
    # إنشاء مجلد libs في المستودع
    mkdir -p libs
    
    # نسخ المكتبات المطلوبة
    cp -r tdlib/td/tdlib/* libs/
    
    echo "📚 تم نسخ المكتبات إلى مجلد libs/"
fi

echo "🎉 بناء TDLib مكتمل بنجاح!"