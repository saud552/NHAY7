#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🧪 اختبار TDLib - مشروع ZeMusic
تاريخ الإنشاء: 2025-01-28
"""

import sys
import json
import ctypes
import ctypes.util
from pathlib import Path

def test_tdlib():
    """اختبار أساسي لمكتبة TDLib"""
    
    print("🧪 بدء اختبار TDLib...")
    
    # تحديد مسار المكتبة
    lib_path = Path("libs/lib/libtdjson.so")
    
    if not lib_path.exists():
        print("❌ خطأ: لم يتم العثور على مكتبة TDLib")
        print(f"المسار المتوقع: {lib_path.absolute()}")
        return False
    
    try:
        # تحميل المكتبة
        print(f"📚 تحميل المكتبة من: {lib_path}")
        tdjson = ctypes.CDLL(str(lib_path))
        print("✅ تم تحميل المكتبة بنجاح")
        
        # إعداد الدوال
        tdjson.td_json_client_create.restype = ctypes.c_void_p
        tdjson.td_json_client_send.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        tdjson.td_json_client_receive.argtypes = [ctypes.c_void_p, ctypes.c_double]
        tdjson.td_json_client_receive.restype = ctypes.c_char_p
        tdjson.td_json_client_destroy.argtypes = [ctypes.c_void_p]
        
        # إنشاء عميل TDLib
        print("🔗 إنشاء عميل TDLib...")
        client = tdjson.td_json_client_create()
        
        if not client:
            print("❌ خطأ: فشل في إنشاء عميل TDLib")
            return False
        
        print("✅ تم إنشاء العميل بنجاح")
        
        # إرسال طلب للحصول على معلومات الإصدار
        print("📡 إرسال طلب الحصول على إصدار TDLib...")
        request = {
            "@type": "getOption",
            "name": "version"
        }
        
        tdjson.td_json_client_send(client, json.dumps(request).encode('utf-8'))
        
        # استقبال النتيجة
        print("📨 انتظار الاستجابة...")
        result = tdjson.td_json_client_receive(client, 2.0)
        
        if result:
            response = json.loads(result.decode('utf-8'))
            print("✅ تم استقبال الاستجابة:")
            print(f"   📋 النوع: {response.get('@type', 'غير معروف')}")
            if response.get('@type') == 'optionValue':
                version = response.get('value', {}).get('value', 'غير معروف')
                print(f"   🔖 إصدار TDLib: {version}")
            else:
                print(f"   📄 المحتوى: {json.dumps(response, indent=2, ensure_ascii=False)}")
        else:
            print("⚠️ لم يتم استقبال استجابة (قد يكون طبيعياً للاختبار الأول)")
        
        # تنظيف الموارد
        print("🧹 تنظيف الموارد...")
        tdjson.td_json_client_destroy(client)
        
        print("🎉 اختبار TDLib مكتمل بنجاح!")
        return True
        
    except Exception as e:
        print(f"❌ خطأ أثناء الاختبار: {e}")
        return False

def get_tdlib_info():
    """عرض معلومات TDLib المبنية"""
    
    print("\n📋 معلومات TDLib:")
    
    # معلومات المكتبات
    lib_dir = Path("libs/lib")
    if lib_dir.exists():
        print(f"📁 مجلد المكتبات: {lib_dir.absolute()}")
        libraries = list(lib_dir.glob("*.so*")) + list(lib_dir.glob("*.a"))
        print(f"📚 عدد المكتبات: {len(libraries)}")
        
        print("\n🔍 المكتبات الموجودة:")
        for lib in sorted(libraries):
            size = lib.stat().st_size / (1024 * 1024)  # MB
            print(f"   • {lib.name} ({size:.1f} MB)")
    
    # معلومات الهيدرز
    include_dir = Path("libs/include")
    if include_dir.exists():
        print(f"\n📁 مجلد الهيدرز: {include_dir.absolute()}")
        headers = list(include_dir.rglob("*.h"))
        print(f"📄 عدد ملفات الهيدر: {len(headers)}")

if __name__ == "__main__":
    print("🚀 مرحباً بك في اختبار TDLib لمشروع ZeMusic!")
    print("=" * 50)
    
    # عرض معلومات TDLib
    get_tdlib_info()
    print("\n" + "=" * 50)
    
    # تشغيل الاختبار
    success = test_tdlib()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ جميع الاختبارات نجحت! TDLib جاهزة للاستخدام.")
        sys.exit(0)
    else:
        print("❌ بعض الاختبارات فشلت. يرجى مراجعة الأخطاء أعلاه.")
        sys.exit(1)