# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

## 🖥️ Sample Output

Running `python main.py` builds a two-pet example (with a deliberate 08:00
clash) and exercises the scheduler end to end:

```
Owner: Jordan — 2 pet(s)
  - Mochi (dog) — 3 task(s)
  - Luna (cat) — 3 task(s)

Sorted by time (scheduler.sort_by_time()):
  [ ] 07:30 Feed (10m, high, daily)
  [ ] 08:00 Morning walk (30m, high, daily)
  [ ] 08:00 Vet check (20m, high, daily)
  [ ] 11:00 Grooming (40m, low, weekly)
  [ ] 16:00 Play (15m, medium, daily)
  [ ] 18:00 Evening walk (30m, medium, daily)

Conflict check (scheduler.conflict_warning()):
⚠ Mochi's 08:00 Morning walk overlaps Luna's 08:00 Vet check

Recommended plan (fits 90 min budget):
Planned 75 min of care:
  07:30–07:40 — Feed (10m, high priority)
  08:00–08:30 — Morning walk (30m, high priority)
  08:00–08:20 — Vet check (20m, high priority)
  16:00–16:15 — Play (15m, medium priority)
  skipped Evening walk (medium priority) — not enough time
  skipped Grooming (low priority) — not enough time
Heads up — overlapping tasks:
  ⚠ Mochi's 08:00 Morning walk overlaps Luna's 08:00 Vet check

1/7 task(s) completed across 2 pet(s)
```

(Trimmed slightly — main.py also prints the unsorted list and the per-pet /
per-status filtered views.)

## Testing PawPal+

Run the full test suite with:

```bash
python -m pytest
```

The suite (`test_pawpal_system.py`) covers the behaviors that matter most for a
care planner:

- Sorting correctness — tasks entered out of order are returned in
  chronological order, ties on equal times keep insertion order, and an empty
  schedule is handled gracefully.
- Recurrence logic — completing a daily/weekly task spawns a fresh,
  not-yet-done copy for its next occurrence (same time = "the next day's run"),
  while monthly tasks stay one-off and completing twice never double-spawns.
- Conflict detection — overlapping time windows are flagged (including two
  tasks at the same time), classified as same-pet vs cross-pet, and reported
  through a conflict_warning() that never crashes on bad time data. A
  three-way-overlap test guards the early-exit optimization, and a spawned next
  occurrence is checked not to clash with the task that created it.
- Aggregation, filtering & planning — tasks flatten across pets, filter by
  pet/status/frequency, and build_plan() respects the owner's time budget
  while preferring higher-priority tasks; explain() reports what was
  scheduled, skipped, and any conflicts.
- Time-window math — "HH:MM" parsing plus duration handles hour and
  midnight rollover, and rejects invalid times like "25:00".

Successful run:

```
$ python -m pytest -q
....................................................                     [100%]
52 passed in 0.02s
```

Confidence Level: 3.5 stars

## ✨ Features

- **Sorting by time of day** — `sort_by_time()` orders tasks chronologically by
  their zero-padded `"HH:MM"` string (so text order = clock order), using a
  stable sort that preserves insertion order on ties. Non-destructive: it
  returns a new list and leaves the input untouched. `daily_schedule()` is the
  whole-day view built on top of it.
- **Aggregation across pets** — `Owner.all_tasks()` flattens every pet's task
  list into one collection, so the scheduler plans the owner's whole day rather
  than one pet at a time.
- **Multi-criteria filtering** — `filter_tasks(pet, pet_name, completed,
  frequency)` filters by pet (object *or* name), completion status, and/or
  frequency in any combination, always returned time-ordered. `pending_tasks()`
  and `completed_tasks()` are convenience views.
- **Priority + time-budget planning (greedy)** — `build_plan()` sorts pending
  tasks by priority rank (high → medium → low, ties broken by earlier time) and
  greedily selects those that fit the owner's `available_minutes`, tracking both
  chosen and skipped tasks. Priority is ranked numerically (`PRIORITY_RANK`) so
  it sorts by importance, not alphabetically.
- **Conflict detection (interval overlap)** — `find_conflicts()` compares task
  time windows (`start_dt`/`end_dt` via `datetime`/`timedelta`) and flags any
  overlap, including two tasks at the same time. Touching edges (one ends as the
  next begins) don't count. It scans in sorted order with an early exit once no
  later task can overlap. `same_pet_conflicts()` / `cross_pet_conflicts()`
  classify each clash (one pet can't do two things; the owner can't be two
  places at once).
- **Crash-proof conflict warnings** — `conflict_warning()` returns a
  human-readable message (all-clear note or a bullet list of overlaps) and
  isolates unparseable times into their own warning line instead of raising, so
  one bad entry never takes down the check. Surfaced live in the Streamlit UI.
- **Daily/weekly recurrence** — completing a `daily` or `weekly` task
  (`mark_complete()` → `next_occurrence()`) automatically spawns a fresh,
  not-yet-done copy on the same pet for its next run. `monthly` is treated as
  one-off, and completing an already-done task is a no-op (no double-spawn).
- **Time-window math with rollover** — `end_time()` adds duration with
  `timedelta`, correctly crossing the hour and midnight boundaries (e.g. 23:30 +
  60m → 00:30), and validates input so a bad time like `"25:00"` is rejected.
- **Plan explanation & summary** — `explain()` reports what was scheduled, what
  was skipped and why, plus any conflicts; `summary()` gives a done/total status
  line across all pets.

## 📐 Smarter Scheduling

All scheduling logic lives in the `Scheduler` class (the "brain"), with a few
time-math helpers on `Task`, in [`pawpal_system.py`](pawpal_system.py). Here is
each feature and the method that implements it.

| Feature | Method(s) | What it does |
|---------|-----------|--------------|
| Sorting by time | Scheduler.sort_by_time(), Scheduler.daily_schedule() | Orders tasks chronologically by their time. sort_by_time() sorts all tasks (or an optional subset) non-destructively; daily_schedule() is the whole-day view built on it. |
| Filtering | Scheduler.filter_tasks(pet, pet_name, completed, frequency) | One method that filters by pet (object *or* name), completion status, and/or frequency in any combination — e.g. filter_tasks(pet_name="Luna", completed=False). Convenience views `pending_tasks() and completed_tasks() filter by status. |
| Conflict detection | Scheduler.find_conflicts(), same_pet_conflicts(), cross_pet_conflicts(), describe_conflict(), conflict_warning() | Detects tasks whose time windows overlap (not just exact start times) using Task.start_dt()/end_dt(). Classifies each clash as same-pet vs cross-pet, and conflict_warning() returns a safe, human-readable message that never crashes on bad time data. |
| Recurring tasks | `Task.mark_complete(), Task.next_occurrence() | Completing a daily/weekly task automatically spawns a fresh, not-yet-done copy for its next occurrence on the same pet. monthly is treated as one-off. Frequency is also filterable via filter_tasks(frequency=...). |
| Time-window math (supporting) | Task.start_dt(), end_dt(), end_time(), overlaps() | Parse "HH:MM" and add duration with datetime/timedelta — handles hour and midnight rollover, and validates input (a bad time like "25:00" raises ValueError). |
| Planning (constraints) | Scheduler.build_plan(), explain() | Greedily selects pending tasks that fit the owner's time budget, highest priority first (ties broken by earlier time). explain() reports what was scheduled, what was skipped, and any conflicts. |

### Notes on behavior

- Conflict detection detects but does not resolve. Overlapping tasks are flagged (in explain() and the UI) but both are still scheduled — the owner decides. 
- Only pending tasks are checked for conflicts. A completed task isn't competing for time, which also prevents a recurring task from "clashing" with the next occurrence it just spawned.
- No calendar dates. Tasks carry a time-of-day but no date, so a spawned next occurrence reuses the same HH:MM and represents "the next day/week's run."

## 📸 Demo Walkthrough

Describe your app in numbered steps so a reader can follow along without watching a video:

1. <!-- Describe this step -->

2. <!-- Describe this step -->
3. <!-- Describe this step -->
4. <!-- Describe this step -->
5. <!-- Add more steps as needed -->

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->
