"""Tests for the in-memory SmsPort fake."""

from frontdesk.infrastructure.memory import InMemorySms


async def test_sms_fake_records_each_message() -> None:
    sms = InMemorySms()

    await sms.send("+15551234567", "Booked: Fri 10:00")
    await sms.send("+15559876543", "See you Tuesday")

    assert sms.sent == [
        ("+15551234567", "Booked: Fri 10:00"),
        ("+15559876543", "See you Tuesday"),
    ]
