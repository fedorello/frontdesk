"""Opaque, per-entity id types so ids never get mixed up."""

from typing import NewType

BusinessId = NewType("BusinessId", str)
ServiceId = NewType("ServiceId", str)
ResourceId = NewType("ResourceId", str)
CustomerId = NewType("CustomerId", str)
AppointmentId = NewType("AppointmentId", str)
ReminderId = NewType("ReminderId", str)
AccountId = NewType("AccountId", str)
LinkCode = NewType("LinkCode", str)  # a one-time code that links an owner's Telegram chat
FeatureKey = NewType("FeatureKey", str)  # a premium feature's stable key, e.g. "voice_receptionist"
DemoLeadId = NewType("DemoLeadId", str)  # a captured landing-demo lead
