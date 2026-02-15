from __future__ import annotations

import argparse
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

from dotenv import load_dotenv


def _post_form(url: str, form: dict[str, str]) -> tuple[int, str]:
    data = urllib.parse.urlencode(form).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    with urllib.request.urlopen(req, timeout=20) as resp:
        body = resp.read().decode("utf-8", errors="ignore")
        return resp.status, body


def run(user_id: int) -> None:
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    load_dotenv(root / ".env")

    from app import config, db
    from app.liqpay_utils import b64encode_json, liqpay_signature

    local_base = f"http://127.0.0.1:{int(getattr(config, 'WEBHOOK_PORT', 8080) or 8080)}"

    db.upsert_user(user_id, "payment_smoke", "Payment Smoke", "en")
    db.set_coins(user_id, 0)

    coins_sku, (coins_amount, coins_price) = next(iter(config.LIQPAY_COIN_PACKS.items()))
    coins_order = db.create_order(user_id, coins_sku, int(coins_price) * 100, "UAH")

    with urllib.request.urlopen(f"{local_base}/pay/{coins_order}", timeout=20) as resp:
        pay_html = resp.read().decode("utf-8", errors="ignore")
        assert resp.status == 200, f"/pay failed: {resp.status}"
        assert "liqpay.ua/api/3/checkout" in pay_html, "Checkout form not generated"

    coins_before = db.get_coins(user_id)
    data_b64 = b64encode_json({"order_id": coins_order, "status": "success"})
    sig = liqpay_signature(config.LIQPAY_PRIVATE_KEY, data_b64)
    status, body = _post_form(f"{local_base}/liqpay/callback", {"data": data_b64, "signature": sig})
    assert status == 200 and body.strip().lower() == "ok", f"Coins callback failed: {status} {body}"
    coins_after = db.get_coins(user_id)
    assert coins_after - coins_before == int(coins_amount), "Coins were not credited correctly"
    assert str(db.get_order(coins_order)["status"]) == "PAID", "Coins order status is not PAID"

    # Idempotency: second callback must not credit again.
    status, _ = _post_form(f"{local_base}/liqpay/callback", {"data": data_b64, "signature": sig})
    assert status == 200, "Duplicate callback failed"
    coins_after_repeat = db.get_coins(user_id)
    assert coins_after_repeat == coins_after, "Duplicate callback changed coins balance"

    # Non-success status should not mark order as paid.
    fail_order = db.create_order(user_id, coins_sku, int(coins_price) * 100, "UAH")
    fail_b64 = b64encode_json({"order_id": fail_order, "status": "failure"})
    fail_sig = liqpay_signature(config.LIQPAY_PRIVATE_KEY, fail_b64)
    status, _ = _post_form(f"{local_base}/liqpay/callback", {"data": fail_b64, "signature": fail_sig})
    assert status == 200, "Failure status callback failed"
    assert str(db.get_order(fail_order)["status"]) == "NEW", "Failure status changed order to PAID"

    vip_before = float(db.vip_until(user_id))
    vip_effective_before = max(vip_before, time.time())
    vip_order = db.create_order(user_id, config.LIQPAY_VIP_SKU, int(config.LIQPAY_VIP_PRICE_UAH) * 100, "UAH")
    vip_b64 = b64encode_json({"order_id": vip_order, "status": "sandbox"})
    vip_sig = liqpay_signature(config.LIQPAY_PRIVATE_KEY, vip_b64)
    status, body = _post_form(f"{local_base}/liqpay/callback", {"data": vip_b64, "signature": vip_sig})
    assert status == 200 and body.strip().lower() == "ok", f"VIP callback failed: {status} {body}"
    vip_after = float(db.vip_until(user_id))
    assert vip_after > vip_before, "VIP was not extended"
    assert vip_after - vip_effective_before >= int(config.LIQPAY_VIP_DAYS) * 86400 - 10, "VIP extension is too small"
    assert str(db.get_order(vip_order)["status"]) == "PAID", "VIP order status is not PAID"

    print(f"OK coins_delta={coins_after - coins_before}")
    print(f"OK coins_idempotent={coins_after_repeat == coins_after}")
    print(f"OK failure_keeps_new={str(db.get_order(fail_order)['status']) == 'NEW'}")
    print(f"OK vip_extended_seconds={int(vip_after - vip_effective_before)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run local LiqPay smoke checks against running webhook server.")
    parser.add_argument("--user-id", type=int, default=990000001, help="Synthetic user id used for smoke checks")
    args = parser.parse_args()
    run(args.user_id)


if __name__ == "__main__":
    main()
