import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.notification_service import PaymentEvent, notification_for


def test_large_payment_requires_review():
    payment = PaymentEvent("p1", "a1", 100_000, "USD", "Shop")
    assert notification_for(payment) == ("payment.review", "Payment needs review")


def test_small_payment_is_received():
    payment = PaymentEvent("p2", "a1", 9_999, "USD", "Cafe")
    assert notification_for(payment) == ("payment.received", "Payment received")
