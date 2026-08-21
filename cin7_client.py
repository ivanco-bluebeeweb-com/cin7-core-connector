"""Cin7 Core External API v2 HTTP client -- static Account ID + Application
Key header auth, thin wrappers over the REST resources.

WHY STATIC HEADER AUTH, NOT A TOKEN EXCHANGE -- see app.py module
docstring for the full architectural reasoning. Every request carries
`api-auth-accountid` and `api-auth-applicationkey` headers (confirmed
2026-08-21, CONNECTOR_DISCOVERY.md Critical #3) -- there is no token
endpoint to call first, unlike MuleSoft/Power Automate's client-
credentials flow.

WHY inventory.dearsystems.com/ExternalApi/v2, NOT api.cin7.com.

Cin7 Core (formerly DEAR Systems) and Cin7 Omni are two different
products with two different APIs and two different credential shapes
(CONNECTOR_DISCOVERY.md Critical #1). This client hard-codes the Core
base URL and never touches api.cin7.com.

WHY A FIXED 429 MEANING, NOT A GENERIC RATE_LIMITED GUESS.

Cin7 Core's own documented API status codes page states 429 means
exactly "You reached 60 calls per minute API limit" -- a fixed,
documented number, unlike Shopify's cost-based leaky bucket. The error
message below quotes that number directly instead of a vague "slow
down", so the user knows precisely what ceiling was hit.

WHY 403 MEANS "METHOD AUTHENTICATION FAILED", A SEPARATE CODE FROM 401.

Cin7 Core's API status codes documentation does not use 401 for bad
credentials at all -- it returns 403 "Method authentication failed" for
a rejected Account ID/Application Key pair. This client maps 403 to
CREDENTIALS_REJECTED accordingly (not a generic PERMISSION_DENIED), so
error messages don't send a user down the wrong path (there is no
separate "your key works but lacks a permission" state documented for
this API, unlike MuleSoft/Salesforce's scoped-permission model).
"""
from __future__ import annotations

import asyncio

CIN7_BASE = "https://inventory.dearsystems.com/ExternalApi/v2"

ACCOUNT_MISSING = "CIN7_ACCOUNT_MISSING"
CREDENTIALS_REJECTED = "CIN7_CREDENTIALS_REJECTED"
NOT_FOUND = "CIN7_NOT_FOUND"
METHOD_NOT_ALLOWED = "CIN7_METHOD_NOT_ALLOWED"
VALIDATION_FAILED = "CIN7_VALIDATION_FAILED"
RESPONSE_UNEXPECTED = "CIN7_RESPONSE_UNEXPECTED"
UNREACHABLE = "CIN7_UNREACHABLE"
RATE_LIMITED = "CIN7_RATE_LIMITED"
BACKEND_5XX = "CIN7_BACKEND_5XX"
BACKEND_TIMEOUT = "CIN7_BACKEND_TIMEOUT"

_MESSAGES = {
    ACCOUNT_MISSING: "No Cin7 Core account is connected yet.",
    CREDENTIALS_REJECTED: "Cin7 Core rejected this Account ID / Application Key pair. Check both values on the API setup page (Settings > Integrations & API) and reconnect.",
    NOT_FOUND: "Cin7 Core has no such record, or this endpoint does not exist (check the exact endpoint name -- e.g. /Product, not /Products).",
    METHOD_NOT_ALLOWED: "Cin7 Core does not allow this HTTP method on this endpoint.",
    VALIDATION_FAILED: "Cin7 Core rejected the request -- the posted data failed validation.",
    RESPONSE_UNEXPECTED: "Cin7 Core returned a response the connector could not safely interpret.",
    UNREACHABLE: "Could not reach Cin7 Core.",
    RATE_LIMITED: "Cin7 Core's documented limit is 60 calls per minute; that was reached. Try again shortly.",
    BACKEND_5XX: "Cin7 Core returned a server error while processing the request; try again shortly.",
    BACKEND_TIMEOUT: "Cin7 Core took too long to respond; try again shortly.",
}
_RETRYABLE = {RATE_LIMITED, BACKEND_5XX, BACKEND_TIMEOUT}


def fail(code: str, detail: str = "") -> dict:
    message = _MESSAGES.get(code, code)
    if detail:
        message = f"{message} ({detail})"
    return {"ok": False, "error_code": code, "error": message, "retryable": code in _RETRYABLE}


class ClientFail(Exception):
    def __init__(self, payload: dict):
        super().__init__(payload.get("error", "Cin7 Core request failed"))
        self.payload = payload


def _headers(account_id: str, application_key: str) -> dict:
    return {
        "api-auth-accountid": account_id,
        "api-auth-applicationkey": application_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _check_status(resp, action: str):
    if resp.status_code in (200, 201, 202, 204):
        if resp.status_code == 204:
            return {}
        return resp.body if isinstance(resp.body, (dict, list)) else {}
    if resp.status_code == 403:
        raise ClientFail(fail(CREDENTIALS_REJECTED, action))
    if resp.status_code == 404:
        raise ClientFail(fail(NOT_FOUND, action))
    if resp.status_code == 405:
        raise ClientFail(fail(METHOD_NOT_ALLOWED, action))
    if resp.status_code == 400:
        detail = ""
        if isinstance(resp.body, dict):
            detail = str(resp.body.get("Message") or resp.body.get("ErrorMessage") or "")
        raise ClientFail(fail(VALIDATION_FAILED, detail or action))
    if resp.status_code == 429:
        raise ClientFail(fail(RATE_LIMITED, action))
    if resp.status_code >= 500:
        raise ClientFail(fail(BACKEND_5XX, action))
    raise ClientFail(fail(RESPONSE_UNEXPECTED, f"{action}: HTTP {resp.status_code}"))


async def check_connection(ctx, account_id: str, application_key: str) -> dict:
    """Cheap GET /me (account/company info) to prove the key pair actually
    works, same pattern as MuleSoft's cheap GET /applications probe."""
    resp = await ctx.http.get(
        f"{CIN7_BASE}/me",
        headers=_headers(account_id, application_key),
    )
    try:
        _check_status(resp, "verify connection")
    except ClientFail as e:
        return e.payload
    return {"ok": True}


# ──────────────────────────────────────────────────────────────────────────
# Generic verb helpers with a bounded retry-on-429 (Cin7 Core's limit is a
# fixed, documented 60/min -- a short single backoff sleep here absorbs a
# transient burst without silently discarding the caller's request).
# ──────────────────────────────────────────────────────────────────────────


async def _request(ctx, method: str, account_id: str, application_key: str, path: str, *,
                    params: dict | None = None, json: dict | None = None, action: str = "",
                    _retried: bool = False):
    url = f"{CIN7_BASE}{path}"
    headers = _headers(account_id, application_key)
    fn = getattr(ctx.http, method)
    kwargs: dict = {"headers": headers}
    if params is not None:
        kwargs["params"] = {k: v for k, v in params.items() if v is not None}
    if json is not None:
        kwargs["json"] = json
    resp = await fn(url, **kwargs)
    if resp.status_code == 429 and not _retried:
        await asyncio.sleep(2.0)
        return await _request(ctx, method, account_id, application_key, path,
                               params=params, json=json, action=action, _retried=True)
    return _check_status(resp, action or path)


async def cin7_get(ctx, account_id: str, application_key: str, path: str, *, params: dict | None = None, action: str = ""):
    return await _request(ctx, "get", account_id, application_key, path, params=params, action=action)


async def cin7_post(ctx, account_id: str, application_key: str, path: str, *, json: dict | None = None, action: str = ""):
    return await _request(ctx, "post", account_id, application_key, path, json=json, action=action)


async def cin7_put(ctx, account_id: str, application_key: str, path: str, *, json: dict | None = None, action: str = ""):
    return await _request(ctx, "put", account_id, application_key, path, json=json, action=action)


async def cin7_delete(ctx, account_id: str, application_key: str, path: str, *, params: dict | None = None, action: str = ""):
    return await _request(ctx, "delete", account_id, application_key, path, params=params, action=action)
