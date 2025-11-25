from __future__ import annotations

from typing import Any, Dict, Optional

import aiohttp


class PocketBaseError(Exception):
    """Raised when a PocketBase request fails."""


class PocketBaseAuthenticationError(PocketBaseError):
    """Raised when PocketBase rejects an auth token."""


class PocketBaseClient:
    def __init__(self, base_url: Optional[str]) -> None:
        self.base_url = base_url.rstrip("/") if base_url else None

    @property
    def is_configured(self) -> bool:
        return bool(self.base_url)

    async def get_user_by_discord_id(
        self, auth_token: str, discord_id: int
    ) -> Dict[str, Any]:
        result = await self._request(
            "GET",
            "/api/collections/users/records",
            params={
                "filter": f"discord_user_id={int(discord_id)}",
                "perPage": 1,
            },
            auth_token=auth_token,
            require_auth=True,
        )
        items = result.get("items", [])
        if not items:
            raise PocketBaseError(
                "No PocketBase user is linked to your Discord account."
            )
        return items[0]

    async def get_active_shift(
        self, auth_token: str, user_id: str
    ) -> Optional[Dict[str, Any]]:
        result = await self._request(
            "GET",
            "/api/collections/shifts/records",
            params={
                "filter": f'user="{user_id}" && status="active"',
                "perPage": 1,
            },
            auth_token=auth_token,
            require_auth=True,
        )
        items = result.get("items", [])
        return items[0] if items else None

    async def create_shift(self, auth_token: str, user_id: str) -> Dict[str, Any]:
        return await self._request(
            "POST",
            "/api/collections/shifts/records",
            json={"user": user_id, "status": "active"},
            auth_token=auth_token,
            require_auth=True,
        )

    async def complete_shift(
        self,
        auth_token: str,
        shift_id: str,
        end_time: str,
        duration_minutes: int,
    ) -> Dict[str, Any]:
        return await self._request(
            "PATCH",
            f"/api/collections/shifts/records/{shift_id}",
            json={
                "end_time": end_time,
                "status": "completed",
                "duration_minutes": duration_minutes,
            },
            auth_token=auth_token,
            require_auth=True,
        )

    async def get_latest_shift(
        self, auth_token: str, user_id: str
    ) -> Optional[Dict[str, Any]]:
        result = await self._request(
            "GET",
            "/api/collections/shifts/records",
            params={
                "filter": f'user="{user_id}"',
                "sort": "-start_time",
                "perPage": 1,
            },
            auth_token=auth_token,
            require_auth=True,
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
        auth_token: Optional[str] = None,
        require_auth: bool = False,
    ) -> Any:
        if not self.base_url:
            raise PocketBaseError("PocketBase base URL has not been configured.")

        headers = {}
        if require_auth:
            if not auth_token:
                raise PocketBaseAuthenticationError(
                    "You need to link your PocketBase auth key with /login before using this command."
                )
            headers["Authorization"] = f"Bearer {auth_token}"

        url = f"{self.base_url}{path}"
        async with aiohttp.ClientSession() as session:
            async with session.request(
                method,
                url,
                params=params,
                json=json,
                headers=headers,
            ) as response:
                data = await self._consume_response(response)
                if response.status == 401:
                    raise PocketBaseAuthenticationError(
                        "PocketBase rejected your auth key. Please run /login again."
                    )
                if response.status >= 400:
                    raise PocketBaseError(self._extract_error_message(data))
                return data

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
