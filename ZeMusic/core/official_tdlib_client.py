#!/usr/bin/env python3
# Copyright Aliaksei Levin (levlam@telegram.org), Arseny Smirnov (arseny30@gmail.com),
# Pellegrino Prevete (pellegrinoprevete@gmail.com)  2014-2025
#
# Distributed under the Boost Software License, Version 1.0. (See accompanying
# file LICENSE_1_0.txt or copy at http://www.boost.org/LICENSE_1_0.txt)

import json
import os
import sys
import asyncio
import threading
import logging
from ctypes import CDLL, CFUNCTYPE, c_char_p, c_double, c_int
from ctypes.util import find_library
from typing import Any, Dict, Optional, Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class AuthResult:
    """نتيجة التفويض"""
    success: bool
    error: Optional[str] = None
    needs_code: bool = False
    needs_password: bool = False
    phone: Optional[str] = None

class TelegramAuthClient:
    """عميل تليجرام رسمي باستخدام TDLib"""

    def __init__(self, api_id: int, api_hash: str, phone: str = None):
        """تهيئة عميل تليجرام
        
        Args:
            api_id: Telegram API ID
            api_hash: Telegram API hash
            phone: رقم الهاتف (اختياري)
        """
        self.api_id = api_id
        self.api_hash = api_hash
        self.phone = phone
        self.auth_state = None
        self.is_authorized = False
        self.auth_callbacks = {}
        
        # Events for async handling
        self.authorization_event = asyncio.Event()
        self.code_requested = asyncio.Event()
        self.password_requested = asyncio.Event()
        
        # Initialize TDLib
        self._load_library()
        self._setup_functions()
        self._setup_logging()
        self.client_id = self._td_create_client_id()
        
        logger.info(f"🚀 Official TDLib Client created with ID: {self.client_id}")
        
        # Start update handler
        self._start_update_handler()

    def _load_library(self) -> None:
        """تحميل مكتبة TDLib"""
        tdjson_path = find_library("tdjson")
        if tdjson_path is None:
            if os.name == "nt":
                tdjson_path = os.path.join(os.path.dirname(__file__), "tdjson.dll")
            else:
                # Try common paths
                common_paths = [
                    "/usr/local/lib/libtdjson.so",
                    "/usr/lib/libtdjson.so",
                    "/usr/lib/x86_64-linux-gnu/libtdjson.so"
                ]
                for path in common_paths:
                    if os.path.exists(path):
                        tdjson_path = path
                        break
                else:
                    raise Exception("Can't find 'tdjson' library. Make sure it's installed correctly.")

        try:
            self.tdjson = CDLL(tdjson_path)
            logger.info(f"📚 TDLib loaded from: {tdjson_path}")
        except Exception as e:
            raise Exception(f"Error loading TDLib: {e}")

    def _setup_functions(self) -> None:
        """تعيين توقيعات الوظائف"""
        # Create client ID
        self._td_create_client_id = self.tdjson.td_create_client_id
        self._td_create_client_id.restype = c_int
        self._td_create_client_id.argtypes = []

        # Receive updates
        self._td_receive = self.tdjson.td_receive
        self._td_receive.restype = c_char_p
        self._td_receive.argtypes = [c_double]

        # Send requests
        self._td_send = self.tdjson.td_send
        self._td_send.restype = None
        self._td_send.argtypes = [c_int, c_char_p]

        # Execute synchronous requests
        self._td_execute = self.tdjson.td_execute
        self._td_execute.restype = c_char_p
        self._td_execute.argtypes = [c_char_p]

        # Set log callback
        self.log_message_callback_type = CFUNCTYPE(None, c_int, c_char_p)
        self._td_set_log_message_callback = self.tdjson.td_set_log_message_callback
        self._td_set_log_message_callback.restype = None
        self._td_set_log_message_callback.argtypes = [
            c_int,
            self.log_message_callback_type,
        ]

    def _setup_logging(self, verbosity_level: int = 1) -> None:
        """تكوين تسجيل TDLib"""

        @self.log_message_callback_type
        def on_log_message_callback(verbosity_level, message):
            message_str = message.decode('utf-8') if message else 'Unknown'
            if verbosity_level == 0:
                logger.error(f"TDLib fatal error: {message_str}")
            elif verbosity_level == 1:
                logger.error(f"TDLib error: {message_str}")
            elif verbosity_level == 2:
                logger.warning(f"TDLib warning: {message_str}")
            else:
                logger.debug(f"TDLib debug: {message_str}")

        self._td_set_log_message_callback(2, on_log_message_callback)
        self.execute(
            {"@type": "setLogVerbosityLevel", "new_verbosity_level": verbosity_level}
        )

    def execute(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """تنفيذ طلب متزامن"""
        query_json = json.dumps(query).encode("utf-8")
        result = self._td_execute(query_json)
        if result:
            return json.loads(result.decode("utf-8"))
        return None

    def send(self, query: Dict[str, Any]) -> None:
        """إرسال طلب غير متزامن"""
        query_json = json.dumps(query).encode("utf-8")
        logger.debug(f"📤 Sending: {query.get('@type', 'unknown')}")
        self._td_send(self.client_id, query_json)

    def receive(self, timeout: float = 1.0) -> Optional[Dict[str, Any]]:
        """استقبال تحديث من TDLib"""
        result = self._td_receive(timeout)
        if result:
            return json.loads(result.decode("utf-8"))
        return None

    def _start_update_handler(self):
        """بدء معالج التحديثات في خيط منفصل"""
        def update_handler():
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            while True:
                try:
                    event = self.receive(2.0)
                    if event:
                        # Run in the thread's event loop
                        loop.run_until_complete(self._handle_update(event))
                except Exception as e:
                    logger.error(f"Update handler error: {e}")
        
        thread = threading.Thread(target=update_handler, daemon=True)
        thread.start()
        logger.info("🔄 Update handler started")

    async def _handle_update(self, event: Dict[str, Any]):
        """معالج التحديثات"""
        event_type = event.get("@type", "")
        
        if event_type == "updateAuthorizationState":
            auth_state = event["authorization_state"]
            auth_type = auth_state["@type"]
            
            logger.info(f"🔐 Authorization state: {auth_type}")
            self.auth_state = auth_type
            
            await self._handle_authorization_state(auth_type, auth_state)

    async def _handle_authorization_state(self, auth_type: str, auth_state: Dict[str, Any]):
        """معالج حالات التفويض"""
        
        if auth_type == "authorizationStateWaitTdlibParameters":
            logger.info("📋 Setting TDLib parameters...")
            self.send({
                "@type": "setTdlibParameters",
                "database_directory": f"tdlib_data_{self.client_id}",
                "use_message_database": True,
                "use_secret_chats": True,
                "api_id": self.api_id,
                "api_hash": self.api_hash,
                "system_language_code": "en",
                "device_model": "ZeMusic Bot",
                "application_version": "1.0",
            })
            
        elif auth_type == "authorizationStateWaitPhoneNumber":
            logger.info("📱 Phone number required")
            if self.phone:
                logger.info(f"📱 Sending phone: {self.phone}")
                self.send({
                    "@type": "setAuthenticationPhoneNumber",
                    "phone_number": self.phone,
                })
            else:
                logger.error("❌ No phone number provided")
                
        elif auth_type == "authorizationStateWaitCode":
            logger.info("📟 Verification code required")
            self.code_requested.set()
            
        elif auth_type == "authorizationStateWaitPassword":
            logger.info("🔐 2FA password required")  
            self.password_requested.set()
            
        elif auth_type == "authorizationStateReady":
            logger.info("✅ Authorization complete!")
            self.is_authorized = True
            self.authorization_event.set()
            
        elif auth_type == "authorizationStateClosed":
            logger.info("🔒 Authorization closed")
            self.is_authorized = False

    async def start_authentication(self) -> AuthResult:
        """بدء عملية التفويض"""
        try:
            # Trigger authentication flow
            self.send({"@type": "getOption", "name": "version"})
            
            logger.info("🚀 Starting authentication flow...")
            
            # Wait for code request (max 30 seconds)
            try:
                await asyncio.wait_for(self.code_requested.wait(), timeout=30.0)
                return AuthResult(success=True, needs_code=True, phone=self.phone)
            except asyncio.TimeoutError:
                return AuthResult(success=False, error="Timeout waiting for code request")
                
        except Exception as e:
            logger.error(f"❌ Authentication error: {e}")
            return AuthResult(success=False, error=str(e))

    async def send_verification_code(self, code: str) -> AuthResult:
        """إرسال كود التحقق"""
        try:
            logger.info(f"📟 Sending verification code: {code}")
            self.send({"@type": "checkAuthenticationCode", "code": code})
            
            # Wait for either success or password request
            done, pending = await asyncio.wait([
                asyncio.create_task(self.authorization_event.wait()),
                asyncio.create_task(self.password_requested.wait())
            ], timeout=10.0, return_when=asyncio.FIRST_COMPLETED)
            
            # Cancel pending tasks
            for task in pending:
                task.cancel()
            
            if self.is_authorized:
                return AuthResult(success=True)
            elif self.password_requested.is_set():
                return AuthResult(success=True, needs_password=True)
            else:
                return AuthResult(success=False, error="Invalid verification code")
                
        except asyncio.TimeoutError:
            return AuthResult(success=False, error="Timeout during code verification")
        except Exception as e:
            logger.error(f"❌ Code verification error: {e}")
            return AuthResult(success=False, error=str(e))

    async def send_password(self, password: str) -> AuthResult:
        """إرسال كلمة مرور 2FA"""
        try:
            logger.info("🔐 Sending 2FA password")
            self.send({"@type": "checkAuthenticationPassword", "password": password})
            
            # Wait for authorization
            await asyncio.wait_for(self.authorization_event.wait(), timeout=10.0)
            
            if self.is_authorized:
                return AuthResult(success=True)
            else:
                return AuthResult(success=False, error="Invalid password")
                
        except asyncio.TimeoutError:
            return AuthResult(success=False, error="Timeout during password verification")
        except Exception as e:
            logger.error(f"❌ Password verification error: {e}")
            return AuthResult(success=False, error=str(e))

    def close(self):
        """إغلاق العميل"""
        if self.client_id:
            self.send({"@type": "close"})


class OfficialTDLibManager:
    """مدير TDLib الرسمي"""
    
    def __init__(self):
        self.active_clients = {}
        self.pending_auth = {}
    
    async def create_client(self, api_id: int, api_hash: str, phone: str, user_id: int) -> TelegramAuthClient:
        """إنشاء عميل جديد"""
        try:
            client = TelegramAuthClient(api_id, api_hash, phone)
            
            # Start authentication
            auth_result = await client.start_authentication()
            
            if auth_result.success:
                self.pending_auth[user_id] = {
                    'client': client,
                    'phone': phone,
                    'state': 'waiting_code' if auth_result.needs_code else 'ready'
                }
                
            return client
            
        except Exception as e:
            logger.error(f"❌ Failed to create official TDLib client: {e}")
            raise
    
    async def complete_authorization(self, user_id: int, code: str = None, password: str = None) -> bool:
        """إكمال التفويض"""
        if user_id not in self.pending_auth:
            return False
        
        client_info = self.pending_auth[user_id]
        client = client_info['client']
        
        try:
            if code:
                result = await client.send_verification_code(code)
                if result.success:
                    if result.needs_password:
                        client_info['state'] = 'waiting_password'
                        return False  # Need password
                    else:
                        # Authorization complete
                        self.active_clients[user_id] = client
                        del self.pending_auth[user_id]
                        return True
                else:
                    logger.error(f"Code verification failed: {result.error}")
                    return False
                    
            elif password:
                result = await client.send_password(password)
                if result.success:
                    # Authorization complete
                    self.active_clients[user_id] = client
                    del self.pending_auth[user_id]
                    return True
                else:
                    logger.error(f"Password verification failed: {result.error}")
                    return False
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Authorization completion error: {e}")
            return False
    
    def get_client(self, user_id: int) -> Optional[TelegramAuthClient]:
        """الحصول على عميل"""
        return self.active_clients.get(user_id)
    
    def get_pending_auth(self, user_id: int) -> Optional[Dict[str, Any]]:
        """الحصول على تفويض معلق"""
        return self.pending_auth.get(user_id)


# مثيل مدير TDLib الرسمي
official_tdlib_manager = OfficialTDLibManager()