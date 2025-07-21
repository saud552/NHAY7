#!/usr/bin/env python3
"""
أداة تشخيص نظام إضافة الحسابات المساعدة
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def check_assistant_status():
    """فحص حالة نظام الحسابات المساعدة"""
    print("🔍 فحص حالة نظام إضافة الحسابات المساعدة...")
    print("=" * 50)
    
    try:
        # فحص استيراد النظام
        from ZeMusic.core.realistic_assistant_manager import realistic_assistant_manager
        print("✅ تم تحميل نظام الحسابات المساعدة بنجاح")
        
        # فحص الحسابات التجريبية
        mock_accounts = realistic_assistant_manager.mock_accounts_db
        print(f"📱 عدد الحسابات التجريبية: {len(mock_accounts)}")
        
        for phone, info in mock_accounts.items():
            has_2fa = "✅" if info.get('has_2fa') else "❌"
            print(f"   • {phone} - {info['first_name']} - 2FA: {has_2fa} - كود: {info['valid_code']}")
        
        # فحص الحالات النشطة
        active_states = realistic_assistant_manager.user_states
        pending_sessions = realistic_assistant_manager.pending_sessions
        verification_codes = realistic_assistant_manager.verification_codes
        
        print(f"\n📊 الحالات النشطة:")
        print(f"   • حالات المستخدمين: {len(active_states)}")
        print(f"   • الجلسات المعلقة: {len(pending_sessions)}")
        print(f"   • كودات التحقق النشطة: {len(verification_codes)}")
        
        if verification_codes:
            print("\n🔐 كودات التحقق النشطة:")
            import time
            for phone, code_info in verification_codes.items():
                remaining = max(0, int(code_info['expires_at'] - time.time()))
                status = "نشط" if remaining > 0 else "منتهي"
                print(f"   • {phone}: {code_info['code']} - {status} ({remaining}s)")
        
        # فحص قاعدة البيانات
        try:
            import sqlite3
            if os.path.exists("assistant_accounts.db"):
                with sqlite3.connect("assistant_accounts.db") as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM assistant_accounts WHERE is_active = 1")
                    count = cursor.fetchone()[0]
                    print(f"\n🗄️ قاعدة البيانات: {count} حساب مساعد محفوظ")
            else:
                print(f"\n🗄️ قاعدة البيانات: لم يتم إنشاؤها بعد")
        except Exception as db_error:
            print(f"\n❌ خطأ في قاعدة البيانات: {db_error}")
        
        print(f"\n🎯 النظام جاهز للاستخدام!")
        print(f"📝 للاختبار: /owner ← إدارة الحسابات ← إضافة حساب مساعد")
        
    except Exception as e:
        print(f"❌ خطأ في فحص النظام: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_assistant_status()