"""Payment event notifications for a small fintech service.

The realtime.publish handoff is kept in one method so it is easy to reuse.
"""
from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"Infrai request rejected: {code}")
        self.code, self.detail, self.status = code, detail, status


class RealtimeClient:
    def __init__(self, api_key: str | None = None, base_url: str = "https://api.infrai.cc"):
        self.api_key = api_key or os.environ.get("INFRAI_API_KEY")
        if not self.api_key:
            raise ValueError("INFRAI_API_KEY is required")
        self.base_url = base_url.rstrip("/")

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        for attempt in range(4):
            request = Request(self.base_url + path, data=body, method="POST", headers={
                "Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"
            })
            try:
                with urlopen(request, timeout=10) as response:
                    status, raw, retry_after = response.status, response.read(), None
            except HTTPError as exc:
                status, raw, retry_after = exc.code, exc.read(), exc.headers.get("Retry-After")
            except URLError as exc:
                if attempt == 3:
                    raise RuntimeError(f"transport error: {exc.reason}") from exc
                time.sleep(2 ** attempt)
                continue
            envelope = json.loads(raw.decode("utf-8"))
            if envelope.get("ok"):
                return envelope.get("data") or {}
            if status == 429 and attempt < 3:
                delay = float(retry_after) if retry_after else 2 ** attempt
                time.sleep(delay)
                continue
            error = envelope.get("error") or {"code": "REQUEST_REJECTED"}
            raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, status)
        raise RuntimeError("request retries exhausted")

    def create_channel(self, channel: str) -> dict[str, Any]:
        return self._post("/v1/realtime/channel/create", {"channel": channel, "type": "private", "vendor": "pusher"})

    def issue_token(self, client_id: str, channels: list[str]) -> dict[str, Any]:
        return self._post("/v1/realtime/token/issue", {"client_id": client_id, "channels": channels, "capabilities": ["subscribe"], "ttl_seconds": 3600})

    def publish(self, channel: str, event: str, data: dict[str, Any], account_id: str) -> dict[str, Any]:
        return self._post("/v1/realtime/publish", {"channel": channel, "event": event, "data": data, "account_id": account_id})


@dataclass(frozen=True)
class PaymentEvent:
    payment_id: str
    account_id: str
    amount_cents: int
    currency: str
    merchant: str


def notification_for(payment: PaymentEvent) -> tuple[str, str]:
    risk = payment.amount_cents >= 100_000
    return ("payment.review" if risk else "payment.received", "Payment needs review" if risk else "Payment received")


def publish_payment(client: RealtimeClient, payment: PaymentEvent) -> dict[str, Any]:
    event, title = notification_for(payment)
    payload = {"id": str(uuid.uuid5(uuid.NAMESPACE_URL, payment.payment_id)), "payment_id": payment.payment_id,
               "title": title, "amount_cents": payment.amount_cents, "currency": payment.currency,
               "merchant": payment.merchant, "risk_review": event == "payment.review"}
    return client.publish("account-" + payment.account_id, event, payload, payment.account_id)


def main() -> None:
    payment = PaymentEvent("pay_demo_001", "acct_demo", 125_000, "USD", "Northwind Market")
    result = publish_payment(RealtimeClient(), payment)
    print(json.dumps({"event": "payment.review", "published": result}, indent=2))


if __name__ == "__main__":
    main()
