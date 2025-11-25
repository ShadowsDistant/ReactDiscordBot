from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional

import aiohttp


class PocketBaseError(Exception):
    """Raised when a PocketBase request fails."""


class PocketBaseClient:
    def __init__(
        self,
        base_url: Optional[str],
        admin_email: Optional[str],
        admin_password: Optional[str],
    ) -> None:
        self.base_url = base_url.rstrip("/") if base_url else None
        self.admin_email = admin_email
        self.admin_password = admin_password
        self._token: Optional[str] = None
        self._auth_lock = asyncio.Lock()

    @property
    def is_configured(self) -> bool:
        return bool(self.base_url and self.admin_email and self.admin_password)

    async def get_user_by_discord_id(self, discord_id: int) -> Dict[str, Any]:
        result = await self._request(
            "GET",
            "/api/collections/users/records",
            params={
                "filter": f"discord_user_id={int(discord_id)}",
                "perPage": 1,
            },
        )
        items = result.get("items", [])
        if not items:
            raise PocketBaseError(
                "No PocketBase user is linked to your Discord account."
            )
        return items[0]

    async def get_active_shift(self, user_id: str) -> Optional[Dict[str, Any]]:
        result = await self._request(
            "GET",
            "/api/collections/shifts/records",
            params={
                "filter": f'user="{user_id}" && status="active"',
                "perPage": 1,
            },
        )
        items = result.get("items", [])
        return items[0] if items else None

    async def create_shift(self, user_id: str) -> Dict[str, Any]:
        return await self._request(
            "POST",
            "/api/collections/shifts/records",
            json={"user": user_id, "status": "active"},
        )

    async def complete_shift(
        self, shift_id: str, end_time: str, duration_minutes: int
    ) -> Dict[str, Any]:
        return await self._request(
            "PATCH",
            f"/api/collections/shifts/records/{shift_id}",
            json={
                "end_time": end_time,
                "status": "completed",
                "duration_minutes": duration_minutes,
            },
        )

    async def get_latest_shift(self, user_id: str) -> Optional[Dict[str, Any]]:
        result = await self._request(
            "GET",
            "/api/collections/shifts/records",
            params={
                "filter": f'user="{user_id}"',
                "sort": "-start_time",
                "perPage": 1,
            },
        )
        items = result.get("items", [])
        return items[0] if items else None

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        auth_required: bool = True,
    ) -> Any:
        if not self.base_url:
            raise PocketBaseError("PocketBase base URL has not been configured.")

        if auth_required:
            await self._ensure_token()

        url = f"{self.base_url}{path}"
        for attempt in range(2):
            headers = {}
            if auth_required and self._token:
                headers["Authorization"] = f"Bearer {self._token}"

            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method,
                    url,
                    params=params,
                    json=json,
                    headers=headers,
                ) as response:
                    data = await self._consume_response(response)
                    if response.status == 401 and auth_required and attempt == 0:
                        self._token = None
                        await self._ensure_token()
                        continue

                    if response.status >= 400:
                        raise PocketBaseError(self._extract_error_message(data))

                    return data

        raise PocketBaseError("Authentication with PocketBase failed.")

    async def _ensure_token(self) -> None:
        if self._token:
            return

        if not self.is_configured:
            raise PocketBaseError(
                "PocketBase admin credentials have not been configured via environment variables."
            )

        async with self._auth_lock:
            if self._token:
                return

            payload = {
                "identity": self.admin_email,
                "password": self.admin_password,
            }
            url = f"{self.base_url}/api/admins/auth-with-password"
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    data = await self._consume_response(response)
                    if response.status >= 400:
                        raise PocketBaseError(self._extract_error_message(data))

                    token = data.get("token") if isinstance(data, dict) else None
                    if not token:
                        raise PocketBaseError(
                            "PocketBase authentication did not return a token."
                        )
                    self._token = token

    @staticmethod
    async def _consume_response(response: aiohttp.ClientResponse) -> Any:
        content_type = response.headers.get("Content-Type", "")
        if "application/json" in content_type:
            return await response.json()
        return await response.text()

    @staticmethod
    def _extract_error_message(data: Any) -> str:
        if isinstance(data, dict):
            message = data.get("message") or data.get("error")
            details = data.get("data")
            if isinstance(details, dict):
                detail_messages = []
                for field, detail in details.items():
                    if isinstance(detail, dict):
                        detail_message = detail.get("message")
                        if detail_message:
                            detail_messages.append(f"{field}: {detail_message}")
                    elif detail:
                        detail_messages.append(f"{field}: {detail}")
                if detail_messages:
                    details_text = "; ".join(detail_messages)
                    return f"{message}: {details_text}" if message else details_text
            return message or "PocketBase request failed."
        return str(data) if data else "PocketBase request failed."
