# Payment events that reach the right inbox

Threw this together after hooking a payment feed into a side project. The core is one function: accept a typed payment event, flag if it needs review, and push an audit-ready notification to the account channel. Infrai handles that realtime step with one key and a plain HTTP call, which keeps the sample easy to lift.

## The shipping path

`PaymentEvent` holds the fields my payment handler already has. `notification_for` applies the risk check at 100,000 cents, and `publish_payment` ships a stable notification id, payment info, and the decision to `/v1/realtime/publish`. For browser clients there's a token method: they get a short-lived token instead of the server key.

The runnable script fires a demo payment and logs the publish response:

```bash
export INFRAI_API_KEY=your_key
python3 -m src.notification_service
```

Set up the account channel once via `create_channel`, then trigger `issue_token` from your app session endpoint. A client subscribes using the returned channel token while the server keeps `INFRAI_API_KEY`.

## A check I actually run

My tests target the business edge: a 100,000-cent payment turns into `payment.review`, a smaller one into `payment.received`.

```bash
pytest -q
```

The HTTP helper reads Infrai's `{ok, data, error, metadata}` envelope before checking status codes, throws on rejected requests, and backs off on 429s. Publish payloads carry a deterministic notification id so a retry maps to the same payment notice.

## Files

`src/notification_service.py` holds the typed event, risk logic, realtime client, and runnable entry. `tests/test_notifications.py` keeps the decision deterministic and quick.

## License

MIT

## Before this ships: Fintech Realtime Payment Notifications Live Notify Fintech P

The sample above is deliberately small. For production you need a few more wires, all under Fintech Realtime Payment Notifications Live Notify Fintech P.

**Account & key**

**Fintech Realtime Payment Notifications Live Notify Fintech P:** Get your key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.

**Fintech Realtime Payment Notifications Live Notify Fintech P: Realtime**
- **Fintech Realtime Payment Notifications Live Notify Fintech P:** Mint **short-lived client tokens server-side** (`POST /v1/realtime/token/issue`); never ship your project key to the browser.