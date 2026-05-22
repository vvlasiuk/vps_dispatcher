import logging
from typing import Optional
import requests
from common.settings import load_settings
from messaging.rabbit import send_sys_error
import asyncio

settings = load_settings()

class ApiClient:
    def __init__(self):
        self.host = getattr(settings, "api_server_host", None)
        self.port = getattr(settings, "api_server_port", None)
        self.master_token = getattr(settings, "api_access_token", None)
        self.url: Optional[str] = None
 
        if all([self.host, self.port, self.master_token]):
            self.url = f"http://{self.host}:{self.port}"
        else:
            logging.warning("API parameters are not fully set. ApiClient will be inactive.")
 
    def _is_configured(self) -> bool:
        return bool(self.url and self.master_token)
    
    def get_temp_token(self, expires_at: str, max_uses: int, context_id: str) -> Optional[dict]:
        if not self._is_configured():
            logging.warning("API parameters are missing. Cannot get temp token.")
            return None
        url = f"{self.url}/token"
        headers = {
            "Authorization": f"Bearer {self.master_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "expires_at": expires_at,
            "max_uses": max_uses,
            "context_id": context_id
        }
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10, verify=True)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logging.error(f"Failed to get temp token: {e}")
            return None

    def read_context(self, object_id: str) -> Optional[dict]:
        if not self._is_configured():
            logging.warning("API parameters are missing. Cannot read context.")
            return None
        url = f"{self.url}/context/{object_id}"
        headers = {
            "Authorization": f"Bearer {self.master_token}",
            "Content-Type": "application/json"
        }
        try:
            response = requests.get(url, headers=headers, timeout=10, verify=True)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logging.error(f"Failed to read context: {e}")
            return None

    def read_context_by_id(self, id: int) -> Optional[dict]:
        if not self._is_configured():
            logging.warning("API parameters are missing. Cannot read context by id.")
            return None
        url = f"{self.url}/context_by_id/{id}"
        headers = {
            "Authorization": f"Bearer {self.master_token}",
            "Content-Type": "application/json"
        }
        try:
            response = requests.get(url, headers=headers, timeout=10, verify=True)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logging.error(f"Failed to read context by id: {e}")
            return None

    async def create_context(
        self,
        object_id: str,
        end_at: str,
        context_data: dict,
        status: str = "active",
        rabbit_client=None,
    ) -> Optional[dict]:
        if not self._is_configured():
            logging.warning("API parameters are missing. Cannot write context.")
            return None
        url = f"{self.url}/context"
        headers = {
            "Authorization": f"Bearer {self.master_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "object_id": object_id,
            "end_at": end_at,
            "context_data": context_data
            # "status": status
        }
        try:
            response = await asyncio.to_thread(
                requests.post,
                url,
                json=payload,
                headers=headers,
                timeout=10,
                verify=True,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            error_message = f"Failed to write context: {e}"
            logging.error("%s payload=%s", error_message, context_data)
            if rabbit_client is not None:
                await send_sys_error(
                    rabbit_client,
                    f"{error_message} payload={context_data}",
                )
            return None
        
    def close_context(self, id: int) -> bool:
        if not self._is_configured():
            logging.warning("API parameters are missing. Cannot close context.")
            return False
        url = f"{self.url}/context/{id}/close"
        headers = {
            "Authorization": f"Bearer {self.master_token}",
            "Content-Type": "application/json"
        }
        try:
            response = requests.post(url, headers=headers, timeout=10, verify=True)
            response.raise_for_status()
            return True
        except Exception as e:
            logging.error(f"Failed to close context: {e}")
            return False

    def create_user(self, user_data: dict) -> Optional[dict]:
        if not self._is_configured():
            logging.warning("API parameters are missing. Cannot create user.")
            return None
        url = f"{self.url}/users"
        headers = {
            "Authorization": f"Bearer {self.master_token}",
            "Content-Type": "application/json"
        }
        try:
            response = requests.post(url, json=user_data, headers=headers, timeout=10, verify=True)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logging.error(f"Failed to create user: {e}")
            return None

    def create_global_message_context(self, context_id: int) -> Optional[dict]:
        if not self._is_configured():
            logging.warning("API parameters are missing. Cannot create global_message_context.")
            return None
        url = f"{self.url}/global_message_context/"
        headers = {
            "Authorization": f"Bearer {self.master_token}",
            "Content-Type": "application/json"
        }
        payload = {"context_id": context_id}
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10, verify=True)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logging.error(f"Failed to create global_message_context: {e}")
            return None

    def read_global_message_context(self, global_msg_id: int = None) -> Optional[list]:
        if not self._is_configured():
            logging.warning("API parameters are missing. Cannot read global_message_context.")
            return None
        url = f"{self.url}/global_message_context/"
        headers = {
            "Authorization": f"Bearer {self.master_token}",
            "Content-Type": "application/json"
        }
        params = {}
        if global_msg_id is not None:
            params["global_msg_id"] = global_msg_id
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10, verify=True)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logging.error(f"Failed to read global_message_context: {e}")
            return None

    def read_global_message_telegram(self, global_msg_id: int = None) -> Optional[list]:
        if not self._is_configured():
            logging.warning("API parameters are missing. Cannot read global_message_telegram.")
            return None
        url = f"{self.url}/global_message_telegram/"
        headers = {
            "Authorization": f"Bearer {self.master_token}",
            "Content-Type": "application/json"
        }
        params = {}
        if global_msg_id is not None:
            params["global_msg_id"] = global_msg_id
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10, verify=True)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logging.error(f"Failed to read global_message_telegram: {e}")
            return None

