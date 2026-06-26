"""Opaque, per-entity id types so ids never get mixed up."""

from typing import NewType

BusinessId = NewType("BusinessId", str)
ServiceId = NewType("ServiceId", str)
ResourceId = NewType("ResourceId", str)
CustomerId = NewType("CustomerId", str)
AppointmentId = NewType("AppointmentId", str)
ReminderId = NewType("ReminderId", str)
AccountId = NewType("AccountId", str)
