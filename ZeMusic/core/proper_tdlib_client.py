"""
🔥 Proper TDLib Client Implementation
Based on official C# TDLib example
"""

import asyncio
import json
import ctypes
import threading
import time
import logging
from typing import Dict, Any, Optional, Callable
from enum import Enum

logger = logging.getLogger(__name__)

class AuthorizationState(Enum):
    """حالات التفويض مثل كود C#"""
    WAIT_TDLIB_PARAMETERS = "authorizationStateWaitTdlibParameters"
    WAIT_PHONE_NUMBER = "authorizationStateWaitPhoneNumber"
    WAIT_EMAIL_ADDRESS = "authorizationStateWaitEmailAddress"
    WAIT_EMAIL_CODE = "authorizationStateWaitEmailCode"
    WAIT_OTHER_DEVICE_CONFIRMATION = "authorizationStateWaitOtherDeviceConfirmation"
    WAIT_CODE = "authorizationStateWaitCode"
    WAIT_REGISTRATION = "authorizationStateWaitRegistration"
    WAIT_PASSWORD = "authorizationStateWaitPassword"
    READY = "authorizationStateReady"
    LOGGING_OUT = "authorizationStateLoggingOut"
    CLOSING = "authorizationStateClosing"
    CLOSED = "authorizationStateClosed"

class ProperTDLibClient:
    """TDLib Client صحيح مبني على منطق C#"""
    
    def __init__(self, api_id: int, api_hash: str, phone: str, 
                 database_directory: str = "tdlib"):
        self.api_id = api_id
        self.api_hash = api_hash
        self.phone = phone
        self.database_directory = database_directory
        
        # Client state (مثل كود C#)
        self.client_id = None
        self.client = None
        self.authorization_state = None
        self.have_authorization = False
        self.need_quit = False
        self.can_quit = False
        
        # Events (مثل AutoResetEvent في C#)
        self.got_authorization = asyncio.Event()
        self.auth_callbacks = {}
        
        # Load TDLib
        self._load_tdlib()
        
    def _load_tdlib(self):
        """تحميل TDLib مثل C#"""
        try:
            # Load TDLib shared library
            self.td_lib = ctypes.CDLL('/usr/local/lib/libtdjson.so')
            
            # Define function signatures (مثل C#)
            self.td_lib.td_create_client_id.restype = ctypes.c_int
            self.td_lib.td_send.argtypes = [ctypes.c_int, ctypes.c_char_p]
            self.td_lib.td_receive.argtypes = [ctypes.c_double]
            self.td_lib.td_receive.restype = ctypes.c_char_p
            self.td_lib.td_execute.argtypes = [ctypes.c_char_p]
            self.td_lib.td_execute.restype = ctypes.c_char_p
            
            # Create client ID (مثل C#)
            self.client_id = self.td_lib.td_create_client_id()
            logger.info(f"🚀 TDLib Client created with ID: {self.client_id}")
            
            # Start update handler thread (مثل C#)
            self._start_update_handler()
            
            # Start authorization flow (trigger first update)
            self._trigger_authorization()
            
        except Exception as e:
            logger.error(f"❌ Failed to load TDLib: {e}")
            raise
    
    def _start_update_handler(self):
        """بدء معالج التحديثات مثل C#"""
        def update_handler():
            while not self.need_quit:
                try:
                    # Receive updates (مثل C#)
                    update = self.td_lib.td_receive(2.0)  # timeout 2 seconds
                    if update:
                        update_str = update.decode('utf-8')
                        update_obj = json.loads(update_str)
                        self._handle_update(update_obj)
                except Exception as e:
                    logger.error(f"Update handler error: {e}")
                    time.sleep(1)
        
        # Start in background thread (مثل C#)
        thread = threading.Thread(target=update_handler, daemon=True)
        thread.start()
    
    def _trigger_authorization(self):
        """بدء تدفق التفويض مثل C#"""
        try:
            # Send a simple request to trigger authorization flow
            # This will cause TDLib to send updateAuthorizationState
            request = {
                '@type': 'getAuthorizationState'
            }
            self._send_request(request)
            logger.info("🔄 Authorization flow triggered")
        except Exception as e:
            logger.error(f"❌ Failed to trigger authorization: {e}")
    
    def _handle_update(self, update: Dict[str, Any]):
        """معالج التحديثات مثل UpdateHandler في C#"""
        update_type = update.get('@type', '')
        logger.debug(f"📥 Received update: {update_type}")
        
        if update_type == 'updateAuthorizationState':
            auth_state = update.get('authorization_state', {})
            auth_type = auth_state.get('@type', '')
            logger.info(f"🔐 Authorization state update: {auth_type}")
            self._on_authorization_state_updated(auth_type, auth_state)
        elif update_type == 'authorizationState':
            # Handle direct authorization state response
            auth_type = update.get('@type', '')
            logger.info(f"🔐 Direct authorization state: {auth_type}")
            self._on_authorization_state_updated(auth_type, update)
        # يمكن إضافة معالجات أخرى هنا
    
    def _on_authorization_state_updated(self, state_type: str, state_data: Dict[str, Any]):
        """معالج حالة التفويض مثل OnAuthorizationStateUpdated في C#"""
        logger.info(f"🔄 Authorization state: {state_type}")
        self.authorization_state = state_type
        
        if state_type == AuthorizationState.WAIT_TDLIB_PARAMETERS.value:
            self._set_tdlib_parameters()
            
        elif state_type == AuthorizationState.WAIT_PHONE_NUMBER.value:
            self._request_phone_number()
            
        elif state_type == AuthorizationState.WAIT_CODE.value:
            self._request_verification_code()
            
        elif state_type == AuthorizationState.WAIT_PASSWORD.value:
            self._request_password()
            
        elif state_type == AuthorizationState.READY.value:
            self.have_authorization = True
            self.got_authorization.set()
            logger.info("✅ Authorization completed successfully!")
            
        elif state_type == AuthorizationState.CLOSED.value:
            logger.info("🔒 Client closed")
            if not self.need_quit:
                # Recreate client (مثل C#)
                self._load_tdlib()
            else:
                self.can_quit = True
    
    def _set_tdlib_parameters(self):
        """تعيين معاملات TDLib مثل C#"""
        request = {
            '@type': 'setTdlibParameters',
            'database_directory': self.database_directory,
            'use_message_database': True,
            'use_secret_chats': True,
            'api_id': self.api_id,
            'api_hash': self.api_hash,
            'system_language_code': 'en',
            'device_model': 'ZeMusic Bot',
            'application_version': '1.0'
        }
        self._send_request(request)
    
    def _request_phone_number(self):
        """طلب رقم الهاتف مثل C#"""
        if self.phone:
            request = {
                '@type': 'setAuthenticationPhoneNumber',
                'phone_number': self.phone,
                'settings': None
            }
            self._send_request(request)
            logger.info(f"📱 Phone number sent: {self.phone}")
        else:
            logger.error("❌ No phone number provided")
    
    def _request_verification_code(self):
        """طلب كود التحقق - سيتم معالجته من الخارج"""
        logger.info("📟 Waiting for verification code...")
        # سيتم استدعاء send_verification_code من الخارج
    
    def _request_password(self):
        """طلب كلمة المرور - سيتم معالجتها من الخارج"""
        logger.info("🔐 Waiting for 2FA password...")
        # سيتم استدعاء send_password من الخارج
    
    def send_verification_code(self, code: str):
        """إرسال كود التحقق مثل C#"""
        request = {
            '@type': 'checkAuthenticationCode',
            'code': code
        }
        self._send_request(request)
        logger.info(f"📟 Verification code sent: {code}")
    
    def send_password(self, password: str):
        """إرسال كلمة مرور 2FA مثل C#"""
        request = {
            '@type': 'checkAuthenticationPassword',
            'password': password
        }
        self._send_request(request)
        logger.info("🔐 2FA password sent")
    
    def _send_request(self, request: Dict[str, Any]):
        """إرسال طلب لـ TDLib مثل _client.Send في C#"""
        if self.client_id:
            request_json = json.dumps(request).encode('utf-8')
            logger.debug(f"📤 Sending request: {request.get('@type', 'unknown')}")
            self.td_lib.td_send(self.client_id, request_json)
        else:
            logger.error("❌ Cannot send request: no client_id")
    
    async def wait_for_authorization(self, timeout: float = 300):
        """انتظار التفويض مثل _gotAuthorization.WaitOne() في C#"""
        try:
            await asyncio.wait_for(self.got_authorization.wait(), timeout=timeout)
            return self.have_authorization
        except asyncio.TimeoutError:
            logger.error("⏰ Authorization timeout")
            return False
    
    def close(self):
        """إغلاق العميل مثل C#"""
        self.need_quit = True
        if self.client_id:
            request = {
                '@type': 'close'
            }
            self._send_request(request)
    
    def is_authorized(self) -> bool:
        """فحص حالة التفويض"""
        return self.have_authorization
    
    def get_current_state(self) -> str:
        """الحصول على الحالة الحالية"""
        return self.authorization_state or "Unknown"


class TDLibAuthManager:
    """مدير التفويض المبني على منطق C#"""
    
    def __init__(self):
        self.active_clients = {}
        self.pending_auth = {}
    
    async def create_client(self, api_id: int, api_hash: str, phone: str, 
                          user_id: int) -> ProperTDLibClient:
        """إنشاء عميل جديد"""
        try:
            client = ProperTDLibClient(api_id, api_hash, phone)
            self.active_clients[user_id] = client
            self.pending_auth[user_id] = {
                'client': client,
                'phone': phone,
                'state': 'initializing'
            }
            return client
        except Exception as e:
            logger.error(f"❌ Failed to create client: {e}")
            raise
    
    async def complete_authorization(self, user_id: int, code: str = None, 
                                   password: str = None) -> bool:
        """إكمال التفويض"""
        if user_id not in self.pending_auth:
            return False
        
        client_info = self.pending_auth[user_id]
        client = client_info['client']
        
        current_state = client.get_current_state()
        
        if current_state == AuthorizationState.WAIT_CODE.value and code:
            client.send_verification_code(code)
            
        elif current_state == AuthorizationState.WAIT_PASSWORD.value and password:
            client.send_password(password)
        
        # انتظار التفويض
        success = await client.wait_for_authorization(timeout=60)
        
        if success:
            # نقل من pending إلى active
            del self.pending_auth[user_id]
            logger.info(f"✅ Authorization completed for user {user_id}")
        
        return success
    
    def get_client(self, user_id: int) -> Optional[ProperTDLibClient]:
        """الحصول على عميل"""
        return self.active_clients.get(user_id)
    
    def get_pending_auth(self, user_id: int) -> Optional[Dict[str, Any]]:
        """الحصول على تفويض معلق"""
        return self.pending_auth.get(user_id)


# مثيل مدير التفويض
tdlib_auth_manager = TDLibAuthManager()