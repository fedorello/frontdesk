"""PostgreSQL adapters for the persistence ports (SQLAlchemy Core + asyncpg)."""

import json
from collections.abc import Sequence
from datetime import datetime, time, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from frontdesk.application.ports import (
    Account,
    ApprovalRecord,
    Clock,
    IdGenerator,
    LlmConfig,
    RecentMessage,
    SecretCipher,
    TelegramBotConfig,
)
from frontdesk.domain.availability import ensure_bookable, free_slots
from frontdesk.domain.enums import AppointmentStatus, Channel, MessageRole, ReminderStatus
from frontdesk.domain.errors import (
    AppointmentNotFound,
    DoubleBooking,
    ServiceNotFound,
)
from frontdesk.domain.ids import (
    AccountId,
    AppointmentId,
    BusinessId,
    CustomerId,
    ReminderId,
    ResourceId,
    ServiceId,
)
from frontdesk.domain.models import (
    Appointment,
    Business,
    Customer,
    IntakeAnswer,
    IntakeField,
    KnowledgeItem,
    Message,
    Reminder,
    Resource,
    Service,
    TimeSlot,
    WorkingHours,
    initial_appointment_status,
)
from frontdesk.domain.money import Money

Row = Any  # a SQLAlchemy RowMapping


def _json(value: object) -> list[Any]:
    if isinstance(value, str):
        return list(json.loads(value))
    return list(value) if isinstance(value, list) else []


def _json_obj(value: object) -> dict[str, Any]:
    if isinstance(value, str):
        return dict(json.loads(value))
    return dict(value) if isinstance(value, dict) else {}


def _to_business(row: Row) -> Business:
    knowledge = tuple(KnowledgeItem(k["question"], k["answer"]) for k in _json(row["knowledge"]))
    return Business(
        BusinessId(row["id"]),
        row["name"],
        row["timezone"],
        lead_time_minutes=row["lead_time_minutes"],
        buffer_minutes=row["buffer_minutes"],
        knowledge=knowledge,
        description=row["description"],
        address=row["address"],
        online=row["online"],
        locale=row["locale"],
        owner_name=row["owner_name"],
    )


def _to_hours(value: object) -> tuple[WorkingHours, ...]:
    return tuple(
        WorkingHours(h["weekday"], time.fromisoformat(h["opens"]), time.fromisoformat(h["closes"]))
        for h in _json(value)
    )


def _hours_json(working_hours: Sequence[WorkingHours]) -> str:
    return json.dumps(
        [
            {"weekday": h.weekday, "opens": h.opens.isoformat(), "closes": h.closes.isoformat()}
            for h in working_hours
        ]
    )


def _to_intake_fields(value: object) -> tuple[IntakeField, ...]:
    return tuple(
        IntakeField(f["name"], f.get("description", ""), f.get("ask", "")) for f in _json(value)
    )


def _intake_fields_json(fields: Sequence[IntakeField]) -> str:
    return json.dumps(
        [{"name": f.name, "description": f.description, "ask": f.ask} for f in fields]
    )


def _to_intake_answers(value: object) -> tuple[IntakeAnswer, ...]:
    return tuple(IntakeAnswer(a["name"], a["value"]) for a in _json(value))


def _intake_json(answers: Sequence[IntakeAnswer]) -> str:
    return json.dumps([{"name": a.name, "value": a.value} for a in answers])


def _to_resource(row: Row) -> Resource:
    return Resource(
        ResourceId(row["id"]),
        BusinessId(row["business_id"]),
        row["name"],
        _to_hours(row["working_hours"]),
    )


def _to_service(row: Row) -> Service:
    price = (
        Money(row["price_cents"], row["currency"])
        if row["price_cents"] is not None and row["currency"]
        else None
    )
    resource_ids = tuple(ResourceId(r) for r in _json(row["resource_ids"]))
    return Service(
        ServiceId(row["id"]),
        BusinessId(row["business_id"]),
        row["name"],
        row["duration_minutes"],
        price,
        resource_ids,
        description=row["description"],
        working_hours=_to_hours(row["working_hours"]),
        max_advance_days=row["max_advance_days"],
        intake_fields=_to_intake_fields(row["intake_fields"]),
        requires_confirmation=row["requires_confirmation"],
    )


def _to_customer(row: Row) -> Customer:
    return Customer(
        CustomerId(row["id"]),
        BusinessId(row["business_id"]),
        Channel(row["channel"]),
        row["address"],
        row["name"],
        row["language"],
        handled_by_owner=row["handled_by_owner"],
    )


def _to_appointment(row: Row) -> Appointment:
    return Appointment(
        AppointmentId(row["id"]),
        BusinessId(row["business_id"]),
        ServiceId(row["service_id"]),
        ResourceId(row["resource_id"]),
        CustomerId(row["customer_id"]),
        TimeSlot(row["starts_at"], row["ends_at"]),
        AppointmentStatus(row["status"]),
        _to_intake_answers(row["intake"]),
    )


def _to_reminder(row: Row) -> Reminder:
    return Reminder(
        ReminderId(row["id"]),
        BusinessId(row["business_id"]),
        AppointmentId(row["appointment_id"]),
        row["due_at"],
        row["kind"],
        ReminderStatus(row["status"]),
    )


class SqlBusinessRepository:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sf = sessionmaker

    async def for_channel(self, channel: Channel, to_address: str) -> Business | None:
        async with self._sf() as session:
            row = (
                (
                    await session.execute(
                        text(
                            "SELECT b.* FROM business b "
                            "JOIN channel_binding c ON c.business_id = b.id "
                            "WHERE c.channel = :ch AND c.address = :addr"
                        ),
                        {"ch": channel.value, "addr": to_address},
                    )
                )
                .mappings()
                .first()
            )
            return _to_business(row) if row else None

    async def get(self, business_id: BusinessId) -> Business:
        async with self._sf() as session:
            row = (
                (
                    await session.execute(
                        text("SELECT * FROM business WHERE id = :id"), {"id": str(business_id)}
                    )
                )
                .mappings()
                .first()
            )
            if row is None:
                raise KeyError(str(business_id))
            return _to_business(row)

    async def find(self, business_id: BusinessId) -> Business | None:
        async with self._sf() as session:
            row = (
                (
                    await session.execute(
                        text("SELECT * FROM business WHERE id = :id"), {"id": str(business_id)}
                    )
                )
                .mappings()
                .first()
            )
        return _to_business(row) if row else None

    async def upsert(self, business: Business) -> None:
        knowledge = json.dumps(
            [{"question": k.question, "answer": k.answer} for k in business.knowledge]
        )
        async with self._sf() as session:
            await session.execute(
                text(
                    "INSERT INTO business (id, name, timezone, lead_time_minutes, buffer_minutes, "
                    "knowledge, description, address, online, locale, owner_name) "
                    "VALUES (:id, :name, :tz, :lead, :buf, CAST(:kb AS jsonb), :desc, :addr, "
                    ":online, :locale, :owner) "
                    "ON CONFLICT (id) DO UPDATE SET name = :name, timezone = :tz, "
                    "lead_time_minutes = :lead, buffer_minutes = :buf, "
                    "knowledge = CAST(:kb AS jsonb), description = :desc, address = :addr, "
                    "online = :online, locale = :locale, owner_name = :owner"
                ),
                {
                    "id": str(business.id),
                    "name": business.name,
                    "tz": business.timezone,
                    "lead": business.lead_time_minutes,
                    "buf": business.buffer_minutes,
                    "kb": knowledge,
                    "desc": business.description,
                    "addr": business.address,
                    "online": business.online,
                    "locale": business.locale,
                    "owner": business.owner_name,
                },
            )
            await session.commit()


class SqlServiceRepository:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sf = sessionmaker

    async def get(self, service_id: ServiceId) -> Service:
        async with self._sf() as session:
            row = (
                (
                    await session.execute(
                        text("SELECT * FROM service WHERE id = :id"), {"id": str(service_id)}
                    )
                )
                .mappings()
                .first()
            )
            if row is None:
                raise ServiceNotFound(str(service_id))
            return _to_service(row)

    async def by_name(self, business_id: BusinessId, name: str) -> Service | None:
        async with self._sf() as session:
            row = (
                (
                    await session.execute(
                        text(
                            "SELECT * FROM service "
                            "WHERE business_id = :bid AND lower(name) = lower(:n)"
                        ),
                        {"bid": str(business_id), "n": name},
                    )
                )
                .mappings()
                .first()
            )
            return _to_service(row) if row else None

    async def for_business(self, business_id: BusinessId) -> list[Service]:
        async with self._sf() as session:
            rows = (
                (
                    await session.execute(
                        text("SELECT * FROM service WHERE business_id = :bid"),
                        {"bid": str(business_id)},
                    )
                )
                .mappings()
                .all()
            )
            return [_to_service(row) for row in rows]

    async def upsert(self, service: Service) -> None:
        rids = json.dumps([str(r) for r in service.resource_ids])
        async with self._sf() as session:
            await session.execute(
                text(
                    "INSERT INTO service (id, business_id, name, duration_minutes, price_cents, "
                    "currency, resource_ids, description, working_hours, max_advance_days, "
                    "intake_fields, requires_confirmation) "
                    "VALUES (:id, :bid, :name, :dur, :cents, :cur, CAST(:rids AS jsonb), :desc, "
                    "CAST(:wh AS jsonb), :adv, CAST(:intake AS jsonb), :confirm) "
                    "ON CONFLICT (id) DO UPDATE SET name = :name, duration_minutes = :dur, "
                    "price_cents = :cents, currency = :cur, resource_ids = CAST(:rids AS jsonb), "
                    "description = :desc, working_hours = CAST(:wh AS jsonb), "
                    "max_advance_days = :adv, intake_fields = CAST(:intake AS jsonb), "
                    "requires_confirmation = :confirm "
                    # Tenant guard: only the owning business may update an existing service,
                    # so a forged service_id from another tenant can't be overwritten.
                    "WHERE service.business_id = :bid"
                ),
                {
                    "id": str(service.id),
                    "bid": str(service.business_id),
                    "name": service.name,
                    "dur": service.duration_minutes,
                    "cents": service.price.amount_cents if service.price else None,
                    "cur": service.price.currency if service.price else None,
                    "rids": rids,
                    "desc": service.description,
                    "wh": _hours_json(service.working_hours),
                    "adv": service.max_advance_days,
                    "intake": _intake_fields_json(service.intake_fields),
                    "confirm": service.requires_confirmation,
                },
            )
            await session.commit()

    async def remove(self, service_id: ServiceId, business_id: BusinessId) -> None:
        # Scoped by business so one owner can't delete another tenant's service by id.
        async with self._sf() as session:
            await session.execute(
                text("DELETE FROM service WHERE id = :id AND business_id = :bid"),
                {"id": str(service_id), "bid": str(business_id)},
            )
            await session.commit()


class SqlResourceRepository:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sf = sessionmaker

    async def for_business(self, business_id: BusinessId) -> list[Resource]:
        async with self._sf() as session:
            rows = (
                (
                    await session.execute(
                        text("SELECT * FROM resource WHERE business_id = :bid"),
                        {"bid": str(business_id)},
                    )
                )
                .mappings()
                .all()
            )
            return [_to_resource(row) for row in rows]

    async def upsert(self, resource: Resource) -> None:
        hours = _hours_json(resource.working_hours)
        async with self._sf() as session:
            await session.execute(
                text(
                    "INSERT INTO resource (id, business_id, name, working_hours) "
                    "VALUES (:id, :bid, :name, CAST(:wh AS jsonb)) "
                    "ON CONFLICT (id) DO UPDATE SET name = :name, "
                    "working_hours = CAST(:wh AS jsonb) "
                    # Tenant guard: only the owning business may update an existing resource.
                    "WHERE resource.business_id = :bid"
                ),
                {
                    "id": str(resource.id),
                    "bid": str(resource.business_id),
                    "name": resource.name,
                    "wh": hours,
                },
            )
            await session.commit()


class SqlCustomerRepository:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession], ids: IdGenerator) -> None:
        self._sf = sessionmaker
        self._ids = ids

    async def upsert(
        self, business_id: BusinessId, channel: Channel, address: str, name: str | None = None
    ) -> Customer:
        async with self._sf() as session:
            # Keep the display name fresh; never overwrite a known name with a null.
            await session.execute(
                text(
                    "INSERT INTO customer (id, business_id, channel, address, name) "
                    "VALUES (:id, :bid, :ch, :addr, :name) "
                    "ON CONFLICT (business_id, channel, address) "
                    "DO UPDATE SET name = COALESCE(EXCLUDED.name, customer.name)"
                ),
                {
                    "id": self._ids.new(),
                    "bid": str(business_id),
                    "ch": channel.value,
                    "addr": address,
                    "name": name,
                },
            )
            await session.commit()
            row = (
                (
                    await session.execute(
                        text(
                            "SELECT * FROM customer WHERE business_id = :bid AND channel = :ch "
                            "AND address = :addr"
                        ),
                        {"bid": str(business_id), "ch": channel.value, "addr": address},
                    )
                )
                .mappings()
                .first()
            )
            assert row is not None
            return _to_customer(row)

    async def get(self, customer_id: CustomerId) -> Customer:
        async with self._sf() as session:
            row = (
                (
                    await session.execute(
                        text("SELECT * FROM customer WHERE id = :id"), {"id": str(customer_id)}
                    )
                )
                .mappings()
                .first()
            )
            if row is None:
                raise KeyError(str(customer_id))
            return _to_customer(row)

    async def set_handled(self, customer_id: CustomerId, handled: bool) -> None:
        async with self._sf() as session:
            await session.execute(
                text("UPDATE customer SET handled_by_owner = :h WHERE id = :id"),
                {"h": handled, "id": str(customer_id)},
            )
            await session.commit()


class SqlConversationRepository:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sf = sessionmaker

    async def history(self, customer: Customer, *, limit: int = 30) -> list[Message]:
        async with self._sf() as session:
            rows = (
                (
                    await session.execute(
                        text(
                            "SELECT role, body, at, tool_call_id FROM message "
                            "WHERE customer_id = :cid "
                            "ORDER BY id DESC LIMIT :lim"
                        ),
                        {"cid": str(customer.id), "lim": limit},
                    )
                )
                .mappings()
                .all()
            )
            messages = [
                Message(MessageRole(r["role"]), r["body"], r["at"], r["tool_call_id"]) for r in rows
            ]
            messages.reverse()
            return messages

    async def append(self, customer: Customer, message: Message) -> None:
        async with self._sf() as session:
            await session.execute(
                text(
                    "INSERT INTO message (business_id, customer_id, role, body, at, tool_call_id) "
                    "VALUES (:bid, :cid, :role, :body, :at, :tcid)"
                ),
                {
                    "bid": str(customer.business_id),
                    "cid": str(customer.id),
                    "role": message.role.value,
                    "body": message.text,
                    "at": message.at,
                    "tcid": message.tool_call_id,
                },
            )
            await session.commit()

    async def recent_for_business(
        self, business_id: BusinessId, *, limit: int = 30
    ) -> list[RecentMessage]:
        async with self._sf() as session:
            rows = (
                (
                    await session.execute(
                        text(
                            "SELECT m.role, m.body, m.at, c.address, c.id AS customer_id, "
                            "c.handled_by_owner, c.name FROM message m "
                            "JOIN customer c ON c.id = m.customer_id "
                            "WHERE m.business_id = :bid ORDER BY m.id DESC LIMIT :lim"
                        ),
                        {"bid": str(business_id), "lim": limit},
                    )
                )
                .mappings()
                .all()
            )
            return [
                RecentMessage(
                    r["address"],
                    r["role"],
                    r["body"],
                    r["at"],
                    customer_id=str(r["customer_id"]),
                    handled=r["handled_by_owner"],
                    customer_name=r["name"],
                )
                for r in rows
            ]


class SqlAppointmentRepository:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sf = sessionmaker

    async def get(self, appointment_id: AppointmentId) -> Appointment:
        async with self._sf() as session:
            row = (
                (
                    await session.execute(
                        text("SELECT * FROM appointment WHERE id = :id"),
                        {"id": str(appointment_id)},
                    )
                )
                .mappings()
                .first()
            )
            if row is None:
                raise AppointmentNotFound(str(appointment_id))
            return _to_appointment(row)

    async def for_business(self, business_id: BusinessId) -> list[Appointment]:
        async with self._sf() as session:
            rows = (
                (
                    await session.execute(
                        text(
                            "SELECT * FROM appointment WHERE business_id = :bid ORDER BY starts_at"
                        ),
                        {"bid": str(business_id)},
                    )
                )
                .mappings()
                .all()
            )
            return [_to_appointment(row) for row in rows]


class SqlReminderStore:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sf = sessionmaker

    async def schedule(self, reminders: Sequence[Reminder]) -> None:
        async with self._sf() as session:
            for reminder in reminders:
                await session.execute(
                    text(
                        "INSERT INTO reminder "
                        "(id, business_id, appointment_id, due_at, kind, status)"
                        " VALUES (:id, :bid, :aid, :due, :kind, :status)"
                    ),
                    {
                        "id": str(reminder.id),
                        "bid": str(reminder.business_id),
                        "aid": str(reminder.appointment_id),
                        "due": reminder.due_at,
                        "kind": reminder.kind,
                        "status": reminder.status.value,
                    },
                )
            await session.commit()

    async def cancel_for(self, appointment_id: AppointmentId) -> None:
        async with self._sf() as session:
            await session.execute(
                text(
                    "UPDATE reminder SET status = 'cancelled' "
                    "WHERE appointment_id = :aid AND status = 'pending'"
                ),
                {"aid": str(appointment_id)},
            )
            await session.commit()

    async def claim_due(self, now: datetime, *, limit: int = 100) -> list[Reminder]:
        async with self._sf() as session:
            rows = (
                (
                    await session.execute(
                        text(
                            "SELECT * FROM reminder WHERE status = 'pending' AND due_at <= :now "
                            "ORDER BY due_at FOR UPDATE SKIP LOCKED LIMIT :lim"
                        ),
                        {"now": now, "lim": limit},
                    )
                )
                .mappings()
                .all()
            )
            reminders = [_to_reminder(row) for row in rows]
            await session.commit()
            return reminders

    async def mark_sent(self, reminder_id: ReminderId) -> None:
        async with self._sf() as session:
            await session.execute(
                text("UPDATE reminder SET status = 'sent' WHERE id = :id"),
                {"id": str(reminder_id)},
            )
            await session.commit()


class SqlCalendar:
    def __init__(
        self, sessionmaker: async_sessionmaker[AsyncSession], ids: IdGenerator, clock: Clock
    ) -> None:
        self._sf = sessionmaker
        self._ids = ids
        self._clock = clock

    async def _load_business(self, session: AsyncSession, business_id: str) -> Business:
        row = (
            (
                await session.execute(
                    text("SELECT * FROM business WHERE id = :id"), {"id": business_id}
                )
            )
            .mappings()
            .first()
        )
        assert row is not None
        return _to_business(row)

    async def _load_service(self, session: AsyncSession, service_id: str) -> Service:
        row = (
            (
                await session.execute(
                    text("SELECT * FROM service WHERE id = :id"), {"id": service_id}
                )
            )
            .mappings()
            .first()
        )
        assert row is not None
        return _to_service(row)

    async def _busy(
        self, session: AsyncSession, resource_id: str, *, ignore: str | None = None
    ) -> list[TimeSlot]:
        sql = (
            "SELECT starts_at, ends_at FROM appointment "
            "WHERE resource_id = :rid AND status <> 'cancelled'"
        )
        params: dict[str, str] = {"rid": resource_id}
        if ignore is not None:
            sql += " AND id <> :ignore"
            params["ignore"] = ignore
        rows = (await session.execute(text(sql), params)).mappings().all()
        return [TimeSlot(row["starts_at"], row["ends_at"]) for row in rows]

    async def find_availability(
        self, service: Service, around: datetime, *, limit: int = 5
    ) -> list[TimeSlot]:
        async with self._sf() as session:
            business = await self._load_business(session, str(service.business_id))
            busy = await self._busy(session, str(service.resource_ids[0]))
        return free_slots(
            business=business,
            working_hours=service.working_hours,
            busy=busy,
            duration_minutes=service.duration_minutes,
            now=self._clock.now(),
            around=around,
            max_advance_days=service.max_advance_days,
            limit=limit,
        )

    async def book(
        self,
        service: Service,
        resource_id: ResourceId,
        customer: Customer,
        slot: TimeSlot,
        intake: tuple[IntakeAnswer, ...] = (),
    ) -> Appointment:
        async with self._sf() as session:
            business = await self._load_business(session, str(service.business_id))
            # Buffer + working-hours + lead are application rules; the DB exclusion
            # constraint is the race-safe guarantee against exact overlaps.
            busy = await self._busy(session, str(resource_id))
            buffer = timedelta(minutes=business.buffer_minutes)
            for taken in busy:
                if slot.overlaps(TimeSlot(taken.starts_at - buffer, taken.ends_at + buffer)):
                    raise DoubleBooking("the resource is already booked for that time")
            ensure_bookable(
                business=business,
                working_hours=service.working_hours,
                busy=[],
                slot=slot,
                now=self._clock.now(),
                max_advance_days=service.max_advance_days,
            )
            appointment = Appointment(
                AppointmentId(self._ids.new()),
                business.id,
                service.id,
                resource_id,
                customer.id,
                slot,
                status=initial_appointment_status(service),
                intake=intake,
            )
            try:
                await self._insert(session, appointment)
                await session.commit()
            except IntegrityError as error:
                await session.rollback()
                raise DoubleBooking("the resource is already booked for that time") from error
            return appointment

    async def _insert(self, session: AsyncSession, appointment: Appointment) -> None:
        await session.execute(
            text(
                "INSERT INTO appointment "
                "(id, business_id, service_id, resource_id, customer_id, "
                "starts_at, ends_at, status, intake)"
                " VALUES (:id, :bid, :sid, :rid, :cid, :start, :end, :status, "
                "CAST(:intake AS jsonb))"
            ),
            {
                "id": str(appointment.id),
                "bid": str(appointment.business_id),
                "sid": str(appointment.service_id),
                "rid": str(appointment.resource_id),
                "cid": str(appointment.customer_id),
                "start": appointment.slot.starts_at,
                "end": appointment.slot.ends_at,
                "intake": _intake_json(appointment.intake),
                "status": appointment.status.value,
            },
        )

    async def move(self, appointment_id: AppointmentId, slot: TimeSlot) -> Appointment:
        async with self._sf() as session:
            current = await self._get(session, appointment_id)
            business = await self._load_business(session, str(current.business_id))
            service = await self._load_service(session, str(current.service_id))
            busy = await self._busy(session, str(current.resource_id), ignore=str(appointment_id))
            buffer = timedelta(minutes=business.buffer_minutes)
            for taken in busy:
                if slot.overlaps(TimeSlot(taken.starts_at - buffer, taken.ends_at + buffer)):
                    raise DoubleBooking("the resource is already booked for that time")
            ensure_bookable(
                business=business,
                working_hours=service.working_hours,
                busy=[],
                slot=slot,
                now=self._clock.now(),
                max_advance_days=service.max_advance_days,
            )
            await session.execute(
                text("UPDATE appointment SET starts_at = :start, ends_at = :end WHERE id = :id"),
                {"start": slot.starts_at, "end": slot.ends_at, "id": str(appointment_id)},
            )
            await session.commit()
            return await self._get(session, appointment_id)

    async def cancel(self, appointment_id: AppointmentId) -> Appointment:
        async with self._sf() as session:
            await session.execute(
                text("UPDATE appointment SET status = 'cancelled' WHERE id = :id"),
                {"id": str(appointment_id)},
            )
            await session.commit()
            return await self._get(session, appointment_id)

    async def confirm(self, appointment_id: AppointmentId) -> Appointment:
        async with self._sf() as session:
            # Load first so the domain rule (no confirming a cancelled one) is enforced.
            confirmed = (await self._get(session, appointment_id)).confirmed()
            await session.execute(
                text("UPDATE appointment SET status = :status WHERE id = :id"),
                {"status": confirmed.status.value, "id": str(appointment_id)},
            )
            await session.commit()
            return confirmed

    async def _get(self, session: AsyncSession, appointment_id: AppointmentId) -> Appointment:
        row = (
            (
                await session.execute(
                    text("SELECT * FROM appointment WHERE id = :id"), {"id": str(appointment_id)}
                )
            )
            .mappings()
            .first()
        )
        if row is None:
            raise AppointmentNotFound(str(appointment_id))
        return _to_appointment(row)


class SqlTelegramBotRepository:
    """Stores a business's Telegram bot; the bot token is encrypted at rest."""

    def __init__(
        self, sessionmaker: async_sessionmaker[AsyncSession], cipher: SecretCipher
    ) -> None:
        self._sf = sessionmaker
        self._cipher = cipher

    def _to_config(self, row: Row) -> TelegramBotConfig:
        return TelegramBotConfig(
            BusinessId(row["business_id"]),
            self._cipher.decrypt(row["bot_token"]),
            row["secret_token"],
            row["username"],
            row["webhook_set"],
            row["last_update_id"],
        )

    async def get(self, business_id: BusinessId) -> TelegramBotConfig | None:
        async with self._sf() as session:
            row = (
                (
                    await session.execute(
                        text("SELECT * FROM telegram_bot WHERE business_id = :bid"),
                        {"bid": str(business_id)},
                    )
                )
                .mappings()
                .first()
            )
        return self._to_config(row) if row else None

    async def list_polling(self) -> list[TelegramBotConfig]:
        async with self._sf() as session:
            rows = (
                (await session.execute(text("SELECT * FROM telegram_bot WHERE NOT webhook_set")))
                .mappings()
                .all()
            )
        return [self._to_config(row) for row in rows]

    async def upsert(self, config: TelegramBotConfig) -> None:
        # ON CONFLICT keeps last_update_id so a reconnect doesn't replay old updates.
        async with self._sf() as session:
            await session.execute(
                text(
                    "INSERT INTO telegram_bot "
                    "(business_id, bot_token, secret_token, username, webhook_set, last_update_id) "
                    "VALUES (:bid, :tok, :sec, :usr, :web, :luid) "
                    "ON CONFLICT (business_id) DO UPDATE SET "
                    "bot_token = :tok, secret_token = :sec, username = :usr, webhook_set = :web"
                ),
                {
                    "bid": str(config.business_id),
                    "tok": self._cipher.encrypt(config.bot_token),
                    "sec": config.secret_token,
                    "usr": config.username,
                    "web": config.webhook_set,
                    "luid": config.last_update_id,
                },
            )
            await session.commit()

    async def set_offset(self, business_id: BusinessId, last_update_id: int) -> None:
        async with self._sf() as session:
            await session.execute(
                text("UPDATE telegram_bot SET last_update_id = :luid WHERE business_id = :bid"),
                {"luid": last_update_id, "bid": str(business_id)},
            )
            await session.commit()


class SqlLlmConfigRepository:
    """Stores a business's LLM provider; the API key is encrypted at rest."""

    def __init__(
        self, sessionmaker: async_sessionmaker[AsyncSession], cipher: SecretCipher
    ) -> None:
        self._sf = sessionmaker
        self._cipher = cipher

    async def get(self, business_id: BusinessId) -> LlmConfig | None:
        async with self._sf() as session:
            row = (
                (
                    await session.execute(
                        text("SELECT * FROM llm_config WHERE business_id = :bid"),
                        {"bid": str(business_id)},
                    )
                )
                .mappings()
                .first()
            )
        if row is None:
            return None
        ciphertext = row["api_key_ciphertext"]
        return LlmConfig(
            BusinessId(row["business_id"]),
            row["mode"],
            row["provider"],
            row["model"],
            row["base_url"],
            self._cipher.decrypt(ciphertext) if ciphertext else None,
            row["api_key_hint"],
        )

    async def upsert(self, config: LlmConfig) -> None:
        ciphertext = self._cipher.encrypt(config.api_key) if config.api_key else None
        async with self._sf() as session:
            await session.execute(
                text(
                    "INSERT INTO llm_config (business_id, mode, provider, model, base_url, "
                    "api_key_ciphertext, api_key_hint) "
                    "VALUES (:bid, :mode, :prov, :model, :url, :cipher, :hint) "
                    "ON CONFLICT (business_id) DO UPDATE SET "
                    "mode = :mode, provider = :prov, model = :model, base_url = :url, "
                    "api_key_ciphertext = :cipher, api_key_hint = :hint"
                ),
                {
                    "bid": str(config.business_id),
                    "mode": config.mode,
                    "prov": config.provider,
                    "model": config.model,
                    "url": config.base_url,
                    "cipher": ciphertext,
                    "hint": config.api_key_hint,
                },
            )
            await session.commit()


class SqlChannelBindingRepository:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sf = sessionmaker

    async def upsert(self, channel: Channel, address: str, business_id: BusinessId) -> None:
        async with self._sf() as session:
            await session.execute(
                text(
                    "INSERT INTO channel_binding (channel, address, business_id) "
                    "VALUES (:ch, :addr, :bid) "
                    "ON CONFLICT (channel, address) DO UPDATE SET business_id = :bid"
                ),
                {"ch": channel.value, "addr": address, "bid": str(business_id)},
            )
            await session.commit()

    async def remove(self, channel: Channel, address: str) -> None:
        async with self._sf() as session:
            await session.execute(
                text("DELETE FROM channel_binding WHERE channel = :ch AND address = :addr"),
                {"ch": channel.value, "addr": address},
            )
            await session.commit()


def _to_account(row: Row) -> Account:
    return Account(
        AccountId(row["id"]),
        row["email"],
        row["password_hash"],
        BusinessId(row["business_id"]) if row["business_id"] else None,
    )


class SqlAccountRepository:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sf = sessionmaker

    async def by_email(self, email: str) -> Account | None:
        async with self._sf() as session:
            row = (
                (
                    await session.execute(
                        text("SELECT * FROM account WHERE email = :e"), {"e": email}
                    )
                )
                .mappings()
                .first()
            )
        return _to_account(row) if row else None

    async def get(self, account_id: AccountId) -> Account | None:
        async with self._sf() as session:
            row = (
                (
                    await session.execute(
                        text("SELECT * FROM account WHERE id = :id"), {"id": str(account_id)}
                    )
                )
                .mappings()
                .first()
            )
        return _to_account(row) if row else None

    async def upsert(self, account: Account) -> None:
        async with self._sf() as session:
            await session.execute(
                text(
                    "INSERT INTO account (id, email, password_hash, business_id) "
                    "VALUES (:id, :email, :ph, :bid) "
                    "ON CONFLICT (id) DO UPDATE SET "
                    "email = :email, password_hash = :ph, business_id = :bid"
                ),
                {
                    "id": str(account.id),
                    "email": account.email,
                    "ph": account.password_hash,
                    "bid": str(account.business_id) if account.business_id else None,
                },
            )
            await session.commit()


class SqlUsageStore:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sf = sessionmaker

    async def increment_and_count(self, business_id: BusinessId, day: str) -> int:
        async with self._sf() as session:
            count = (
                await session.execute(
                    text(
                        "INSERT INTO usage_counter (business_id, day, count) "
                        "VALUES (:bid, :day, 1) "
                        "ON CONFLICT (business_id, day) "
                        "DO UPDATE SET count = usage_counter.count + 1 "
                        "RETURNING count"
                    ),
                    {"bid": str(business_id), "day": day},
                )
            ).scalar_one()
            await session.commit()
            return int(count)

    async def count(self, business_id: BusinessId, day: str) -> int:
        async with self._sf() as session:
            result = (
                await session.execute(
                    text("SELECT count FROM usage_counter WHERE business_id = :bid AND day = :day"),
                    {"bid": str(business_id), "day": day},
                )
            ).scalar_one_or_none()
            return int(result) if result is not None else 0


class SqlBusinessEraser:
    """Deletes a business and every row that belongs to it, in FK-safe order."""

    # Child rows first (so foreign keys never block the delete), business last.
    _TABLES = (
        "approval",
        "reminder",
        "message",
        "appointment",
        "customer",
        "service",
        "resource",
        "channel_binding",
        "telegram_bot",
        "llm_config",
        "usage_counter",
        "account",
    )

    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sf = sessionmaker

    async def erase(self, business_id: BusinessId) -> None:
        async with self._sf() as session:
            for table in self._TABLES:
                await session.execute(
                    text(f"DELETE FROM {table} WHERE business_id = :bid"),
                    {"bid": str(business_id)},
                )
            await session.execute(
                text("DELETE FROM business WHERE id = :bid"), {"bid": str(business_id)}
            )
            await session.commit()


class SqlApprovalStore:
    """Postgres-backed approval queue (the ``ApprovalStore`` port) — restart-safe and shared
    across processes, so a poller-raised approval shows in the API's inbox."""

    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sf = sessionmaker

    async def add(self, record: ApprovalRecord) -> None:
        async with self._sf() as session:
            await session.execute(
                text(
                    "INSERT INTO approval (request_id, business_id, tool, summary, risk, args, "
                    "status) VALUES (:rid, :bid, :tool, :summary, :risk, CAST(:args AS jsonb), "
                    ":status)"
                ),
                {
                    "rid": record.request_id,
                    "bid": record.business_id,
                    "tool": record.tool,
                    "summary": record.summary,
                    "risk": record.risk,
                    "args": json.dumps(record.args),
                    "status": record.status,
                },
            )
            await session.commit()

    async def pending(self, business_id: str) -> list[ApprovalRecord]:
        async with self._sf() as session:
            rows = (
                await session.execute(
                    text(
                        "SELECT request_id, tool, summary, risk, args FROM approval "
                        "WHERE business_id = :bid AND status = 'pending' ORDER BY created_at"
                    ),
                    {"bid": business_id},
                )
            ).all()
        return [
            ApprovalRecord(
                request_id=row.request_id,
                business_id=business_id,
                tool=row.tool,
                summary=row.summary,
                risk=row.risk,
                args=_json_obj(row.args),
            )
            for row in rows
        ]

    async def decide(
        self, request_id: str, business_id: str, *, approved: bool
    ) -> ApprovalRecord | None:
        status = "approved" if approved else "rejected"
        async with self._sf() as session:
            # The business_id predicate scopes the decision to the owning tenant.
            row = (
                await session.execute(
                    text(
                        "UPDATE approval SET status = :status "
                        "WHERE request_id = :rid AND business_id = :bid AND status = 'pending' "
                        "RETURNING tool, summary, risk, args"
                    ),
                    {"status": status, "rid": request_id, "bid": business_id},
                )
            ).first()
            await session.commit()
        if row is None:
            return None
        return ApprovalRecord(
            request_id=request_id,
            business_id=business_id,
            tool=row.tool,
            summary=row.summary,
            risk=row.risk,
            args=_json_obj(row.args),
            status=status,
        )
