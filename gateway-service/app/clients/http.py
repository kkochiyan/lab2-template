from typing import TypeVar

import httpx
from pydantic import TypeAdapter, ValidationError

from app.errors import UpstreamError

ResponseData = TypeVar("ResponseData")


def username_headers(username: str) -> dict[str, bytes]:
    # Preserve the header bytes Starlette decoded with Latin-1.
    return {"X-User-Name": username.encode("latin-1")}


class ServiceClient:
    def __init__(self, client: httpx.AsyncClient, service: str) -> None:
        self._client = client
        self._service = service

    async def _request(
        self,
        method: str,
        path: str,
        *,
        headers: dict[str, bytes] | None = None,
        params: dict[str, int] | None = None,
        json: dict[str, object] | None = None,
    ) -> httpx.Response:
        try:
            response = await self._client.request(
                method, path, headers=headers, params=params, json=json,
            )
            return response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise UpstreamError(self._service, timed_out=True) from exc
        except httpx.HTTPStatusError as exc:
            raise UpstreamError(self._service, upstream_status=exc.response.status_code) from exc
        except httpx.RequestError as exc:
            raise UpstreamError(self._service) from exc

    def _decode(
        self, response: httpx.Response, schema: TypeAdapter[ResponseData]
    ) -> ResponseData:
        try:
            return schema.validate_json(response.content)
        except ValidationError as exc:
            raise UpstreamError(self._service) from exc
