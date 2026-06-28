# Service Groups — shared schedules, one calendar per specialist

> Concept + design. Why service groups exist, the problem they solve, and how they're built.

## 1. The problem

A small business often offers **several services that are really the same one person**. An
astrologer might sell a "Personal consultation", a "Compatibility reading", and a "Career
session" — but there is only **one** astrologer. They can be in exactly one appointment at a
time, and they keep **one** weekly schedule.

Today the data model gets this subtly wrong:

- A **schedule (`working_hours`) lives on each Service.** So those three services each carry
  their own copy of the same schedule. The owner has to keep three copies in sync by hand —
  tedious and error-prone.
- **Double-booking is prevented per _resource_**, not per service: the Postgres
  `no_double_book` exclusion constraint keys on `appointment.resource_id`. So whether two
  services can collide depends entirely on whether they point at the **same resource**.
- Right now every service is hard-wired to a single shared resource (`"main"`), so collisions
  happen to be prevented — but only by accident, and there is **no way to model a second
  specialist** with an independent calendar.

The danger the owner is worried about is real: if two services that are the same person ever
ended up on **different** resources, the customer could book **both at the same time** and
double-book the specialist. And conversely, two services that are **different** people are
forced to share one calendar, so they can't be booked in parallel even though they should.

## 2. The solution: groups

Introduce a first-class **group**: a set of services that **share one schedule and one
calendar**. A group is exactly a "specialist" (or a room, a chair — any single bookable
capacity).

- Services in the **same group** share **one** weekly schedule and **one** booking calendar —
  the specialist can never be double-booked, and the schedule is edited in **one** place.
- Services in **different groups** are **independent**: different specialists have separate
  schedules and can be booked **in parallel**.

A group maps directly onto the existing **`Resource`** scheduling primitive — the thing the
`no_double_book` exclusion constraint already keys on. We don't invent a new table or a new
constraint; we **move the schedule onto the group** and let an owner manage **more than one**.

### The model change

| | Before | After |
|---|---|---|
| Schedule (`working_hours`) | on each **Service** | on the **Group** (`Resource`) |
| A service's bookable times | `service.working_hours` | its **group's** `working_hours` |
| Double-booking unit | `resource_id` (the exclusion constraint) | unchanged — the **group** is the resource |
| Groups per business | always one hidden `"main"` | **many**, owner-managed |
| A service belongs to | a resource (always `"main"`) | exactly **one group**, owner-chosen |

So:

- **`Service.working_hours` is removed.** A service no longer owns a schedule.
- **`Group` (Resource) owns `working_hours`.** That schedule is what availability is computed
  against.
- **Availability for a service** = the **group's** schedule, minus the **group's** existing
  appointments, in slots of the service's duration, within the service's `max_advance_days`.
- **Booking** is unchanged at the guarantee level: the DB exclusion constraint on the group's
  `resource_id` is still the race-safe "no two overlapping appointments on one calendar".

### Why this is correct

The invariant we need is: *one specialist, one timeline.* That is precisely
"one resource, no overlapping appointments", which the exclusion constraint already enforces.
By making the **group own the schedule** and **every service point at exactly one group**, two
services of the same specialist are guaranteed to:

1. draw availability from the **same** schedule, and
2. compete for the **same** calendar — so booking one at 14:00 makes the other unbookable at
   14:00.

Two services in **different** groups touch different resources, so they're independent by
construction.

## 3. Data & API

- **`resource` table** keeps `working_hours` (already present) — this is now the source of
  truth for schedules. A business has one row per group.
- **`service` table** drops `working_hours` (migration `0016`). A service keeps `resource_ids`
  — the **single group** it belongs to. (The booking path already uses `resource_ids[0]`.)
- **Backfill:** before dropping `service.working_hours`, each group's schedule is set from its
  member services' hours (union of windows — never makes a service *less* available than
  before), so existing businesses keep working without reconfiguration.
- **API:**
  - Groups CRUD under `/api/businesses/{id}/resources` (list/upsert already exist; add
    **delete**, guarded so a group with appointments can't be silently dropped).
  - A service's `PUT` carries the chosen group in `resource_ids`.
  - `find_availability(service)` loads the service's group and computes against
    `group.working_hours`.

## 4. UI

- **Settings → Groups:** a section to create/rename groups and edit **each group's weekly
  schedule** (the `WeeklyHoursEditor` moves here from the service card). Shows which services
  belong to each group.
- **Service editor:** drops the schedule editor; gains a **Group** selector ("which specialist
  / calendar is this service on?"). New services default to the business's first group.
- Localized in all four languages.

## 5. Invariants (enforced + tested)

1. Two services in the same group **cannot** be booked into overlapping times (one calendar).
2. Two services in different groups **can** be booked in parallel.
3. A service's availability reflects **its group's** schedule, not its own (it has none).
4. Editing a group's schedule changes availability for **all** its services at once.
5. A group with existing appointments cannot be deleted out from under them.

## 6. Out of scope (for now)

- A service spanning **multiple** groups (e.g. needs a therapist *and* a room simultaneously).
  The model keeps `resource_ids` plural to allow this later, but the UI assigns exactly one.
- Per-group lead time / buffer (these stay business-level for now).
