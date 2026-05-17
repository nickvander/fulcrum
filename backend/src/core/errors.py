"""Localized HTTP errors.

`LocalizedHTTPException` carries a stable `code` (e.g. ``apiErrors.product.notFound``)
and optional ``params`` for interpolation, alongside the human-readable
``detail`` that FastAPI already returns. The exception handler wired in
``main.py`` flattens those into the response body, so the wire shape is::

    {"detail": "Product 7 not found", "code": "apiErrors.product.notFound", "params": {"id": 7}}

Endpoints that still raise plain ``HTTPException`` continue to work — the
frontend helper falls back to ``detail`` when ``code`` is absent.
"""
from typing import Any, Mapping

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse


class LocalizedHTTPException(HTTPException):
    def __init__(
        self,
        status_code: int,
        code: str,
        params: Mapping[str, Any] | None = None,
        detail: str | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        super().__init__(status_code=status_code, detail=detail or code, headers=dict(headers) if headers else None)
        self.code = code
        self.params = dict(params) if params else {}


async def localized_http_exception_handler(
    request: Request, exc: LocalizedHTTPException
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "code": exc.code, "params": exc.params},
        headers=exc.headers,
    )
