import os

import httpx


class ApiError(Exception):

    def __init__(self, message: str, status: int):
        super().__init__(message)
        self.status = status


class ApiUnavailable(ApiError):

    def __init__(self, message: str):
        super().__init__(message, 503)


class ChatAPI:
    """Async client for the chat backend REST API."""

    def __init__(self, base_url: str | None = None):
        self._client = httpx.AsyncClient(
            base_url=base_url or os.environ.get(
                "CHAT_API_URL", "http://127.0.0.1:5002"),
            timeout=10.0,
        )
        self.token: str | None = None
        self.username: str | None = None

    async def _request(self, method: str, path: str, json: dict | None = None) -> dict:
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        try:
            response = await self._client.request(method, path, json=json, headers=headers)
        except httpx.HTTPError as exc:
            raise ApiUnavailable("could not reach the chat server") from exc

        if response.status_code >= 400:
            try:
                message = response.json().get("error", response.reason_phrase)
            except ValueError:
                message = response.reason_phrase
            if response.status_code == 503:
                raise ApiUnavailable(message)
            raise ApiError(message, response.status_code)

        return response.json()

    async def close(self) -> None:
        await self._client.aclose()

    async def login(self, username: str, password: str) -> dict:
        data = await self._request(
            "POST", "/api/auth/login", {"username": username,
                                        "password": password}
        )
        self.token = data["token"]
        self.username = data["username"]
        return data

    async def me(self) -> dict:
        return await self._request("GET", "/api/auth/me")

    async def logout(self) -> None:
        try:
            await self._request("POST", "/api/auth/logout")
        finally:
            self.token = None
            self.username = None

    async def list_users(self) -> list[str]:
        return (await self._request("GET", "/api/users"))["users"]

    async def send_dm(self, to: str, content: str) -> dict:
        return await self._request("POST", "/api/messages", {"to": to, "content": content})

    async def get_conversation(self, username: str) -> list[dict]:
        return (await self._request("GET", f"/api/messages/{username}"))["messages"]

    async def create_group(self, name: str) -> dict:
        return await self._request("POST", "/api/groups", {"name": name})

    async def list_groups(self) -> list[dict]:
        return (await self._request("GET", "/api/groups"))["groups"]

    async def add_member(self, group_id: int, username: str) -> dict:
        return await self._request(
            "POST", f"/api/groups/{group_id}/members", {"username": username}
        )

    async def send_group_message(self, group_id: int, content: str) -> dict:
        return await self._request(
            "POST", f"/api/groups/{group_id}/messages", {"content": content}
        )

    async def get_group_messages(self, group_id: int) -> list[dict]:
        return (await self._request("GET", f"/api/groups/{group_id}/messages"))["messages"]
