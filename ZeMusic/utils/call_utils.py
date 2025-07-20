"""
🔧 أدوات مساعدة لإدارة المكالمات الصوتية
تحتوي على وظائف متقدمة لتحليل وإدارة المكالمات
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

@dataclass
class CallStatistics:
    """إحصائيات المكالمة"""
    total_participants: int
    speaking_count: int
    muted_count: int
    active_count: int
    average_duration: float
    peak_participants: int
    call_start_time: datetime

class AdvancedCallAnalyzer:
    """محلل متقدم لبيانات المكالمات"""
    
    def __init__(self):
        self.call_history = {}
        self.participant_patterns = {}
    
    def analyze_speaking_pattern(self, participants: List) -> Dict[str, float]:
        """تحليل أنماط التحدث للمشاركين"""
        patterns = {}
        
        for participant in participants:
            user_id = participant.user_id
            
            # تتبع تاريخ التحدث
            if user_id not in self.participant_patterns:
                self.participant_patterns[user_id] = {
                    'total_time': 0,
                    'speaking_sessions': 0,
                    'last_activity': datetime.now()
                }
            
            if participant.is_speaking:
                self.participant_patterns[user_id]['speaking_sessions'] += 1
                self.participant_patterns[user_id]['last_activity'] = datetime.now()
            
            # حساب معدل النشاط
            pattern_data = self.participant_patterns[user_id]
            activity_score = min(pattern_data['speaking_sessions'] / 10, 1.0)
            patterns[user_id] = activity_score
        
        return patterns
    
    def get_call_quality_score(self, participants: List) -> Tuple[float, str]:
        """حساب درجة جودة المكالمة"""
        if not participants:
            return 0.0, "لا توجد مكالمة"
        
        total = len(participants)
        speaking = sum(1 for p in participants if p.is_speaking)
        muted = sum(1 for p in participants if p.is_muted)
        
        # حساب النقاط
        participation_score = (total - muted) / total if total > 0 else 0
        activity_score = speaking / total if total > 0 else 0
        
        # النقاط الإجمالية
        overall_score = (participation_score * 0.7 + activity_score * 0.3) * 100
        
        # تقييم نصي
        if overall_score >= 80:
            quality_text = "ممتازة 🌟"
        elif overall_score >= 60:
            quality_text = "جيدة 👍"
        elif overall_score >= 40:
            quality_text = "متوسطة 👌"
        else:
            quality_text = "ضعيفة 👎"
        
        return overall_score, quality_text

def format_duration(seconds: int) -> str:
    """تنسيق المدة الزمنية"""
    if seconds < 60:
        return f"{seconds}ث"
    elif seconds < 3600:
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        return f"{minutes}د {remaining_seconds}ث"
    else:
        hours = seconds // 3600
        remaining_minutes = (seconds % 3600) // 60
        return f"{hours}س {remaining_minutes}د"

def generate_call_report(participants: List, call_start_time: datetime) -> str:
    """إنشاء تقرير مفصل للمكالمة"""
    if not participants:
        return "📭 لا توجد بيانات لإنشاء التقرير"
    
    analyzer = AdvancedCallAnalyzer()
    call_duration = (datetime.now() - call_start_time).total_seconds()
    
    # الإحصائيات الأساسية
    total = len(participants)
    speaking = sum(1 for p in participants if p.is_speaking)
    muted = sum(1 for p in participants if p.is_muted)
    active = total - muted
    
    # تحليل الجودة
    quality_score, quality_text = analyzer.get_call_quality_score(participants)
    
    # أنماط التحدث
    speaking_patterns = analyzer.analyze_speaking_pattern(participants)
    
    report = f"""
📋 **تقرير مفصل للمكالمة**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏱️ **معلومات زمنية:**
• مدة المكالمة: {format_duration(int(call_duration))}
• وقت البداية: {call_start_time.strftime('%H:%M:%S')}
• التوقيت الحالي: {datetime.now().strftime('%H:%M:%S')}

👥 **إحصائيات المشاركة:**
• إجمالي المشاركين: {total}
• النشطون (مايك مفتوح): {active} ({(active/total*100):.1f}%)
• الصامتون (مايك مغلق): {muted} ({(muted/total*100):.1f}%)
• يتحدثون حالياً: {speaking} ({(speaking/total*100):.1f}%)

📊 **تقييم الجودة:**
• النقاط: {quality_score:.1f}/100
• التقييم: {quality_text}

🎯 **أكثر المشاركين نشاطاً:**
"""
    
    # ترتيب المشاركين حسب النشاط
    active_participants = [(p, speaking_patterns.get(p.user_id, 0)) for p in participants]
    active_participants.sort(key=lambda x: x[1], reverse=True)
    
    for i, (participant, activity_score) in enumerate(active_participants[:5], 1):
        activity_level = "🔥" if activity_score > 0.7 else "⚡" if activity_score > 0.4 else "💤"
        report += f"{i}. {participant.user_mention} {activity_level}\n"
    
    report += f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    return report

def create_participants_summary(participants: List) -> str:
    """إنشاء ملخص سريع للمشاركين"""
    if not participants:
        return "لا يوجد مشاركون"
    
    total = len(participants)
    speaking = sum(1 for p in participants if p.is_speaking)
    muted = sum(1 for p in participants if p.is_muted)
    
    return f"👥 {total} • 🎤 {speaking} • 🔇 {muted}"

async def monitor_call_changes(assistant, chat_id: int, callback_func=None):
    """مراقبة التغييرات في المكالمة"""
    previous_participants = set()
    
    while True:
        try:
            participants = await assistant.get_participants(chat_id)
            current_participants = {p.user_id for p in participants}
            
            # التحقق من التغييرات
            joined = current_participants - previous_participants
            left = previous_participants - current_participants
            
            if joined or left:
                if callback_func:
                    await callback_func(joined, left, participants)
            
            previous_participants = current_participants
            await asyncio.sleep(10)  # فحص كل 10 ثوانٍ
            
        except Exception:
            break

class CallNotificationManager:
    """مدير إشعارات المكالمة"""
    
    def __init__(self):
        self.active_monitors = {}
    
    async def start_monitoring(self, chat_id: int, assistant, notification_chat_id: int = None):
        """بدء مراقبة المكالمة"""
        if chat_id in self.active_monitors:
            return
        
        async def on_change(joined, left, participants):
            """معالج تغييرات المكالمة"""
            if not notification_chat_id:
                return
            
            message = ""
            if joined:
                message += f"📞 انضم للمكالمة: {len(joined)} شخص\n"
            if left:
                message += f"📴 غادر المكالمة: {len(left)} شخص\n"
            
            if message:
                summary = create_participants_summary(participants)
                message += f"\n{summary}"
                
                # إرسال الإشعار (يمكن تخصيصه)
                # await app.send_message(notification_chat_id, message)
        
        # بدء المراقبة
        task = asyncio.create_task(
            monitor_call_changes(assistant, chat_id, on_change)
        )
        self.active_monitors[chat_id] = task
    
    def stop_monitoring(self, chat_id: int):
        """إيقاف مراقبة المكالمة"""
        if chat_id in self.active_monitors:
            self.active_monitors[chat_id].cancel()
            del self.active_monitors[chat_id]

# مثيل عام لمدير الإشعارات
notification_manager = CallNotificationManager()