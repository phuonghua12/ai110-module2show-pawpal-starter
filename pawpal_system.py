"""PawPal+ system implementation.

Four-class design (see diagrams/uml.mmd):
- Task    : a single care activity (description, time, duration, priority,
            frequency, done?)
- Pet     : pet details plus the tasks that belong to it
- Owner   : manages multiple pets and exposes all their tasks
- Scheduler: retrieves, organizes, and manages tasks across all pets, and
            builds a daily plan constrained by available time + priority

Assumptions:
- `time` is a 24-hour "HH:MM" string (e.g. "08:00"); zero-padding makes it
  sort chronologically as plain text.
- `frequency` is one of VALID_FREQUENCIES.
- `priority` is one of PRIORITY_RANK's keys.
"""

from datetime import datetime, timedelta
from dataclasses import dataclass, field, replace

VALID_FREQUENCIES = ("daily", "weekly", "monthly")

# Numeric rank for each priority so tasks sort by importance, not spelling.
# (Sorting the raw strings would give "high" < "low" < "medium".)
PRIORITY_RANK = {"high": 3, "medium": 2, "low": 1}


@dataclass
class Task:
    """A single care activity for a pet."""

    description: str
    time: str  # "HH:MM", 24-hour
    duration_minutes: int = 15
    priority: str = "medium"  # one of PRIORITY_RANK
    frequency: str = "daily"  # one of VALID_FREQUENCIES
    completed: bool = False
    # Back-reference to the owning Pet, set by Pet.add_task(). Kept out of the
    # constructor and out of equality/repr so tasks stay plain value objects.
    pet: object = field(default=None, init=False, repr=False, compare=False)

    # Frequencies that recur and so spawn a follow-up when completed.
    RECURRING = ("daily", "weekly")

    def mark_complete(self):
        """Mark this task as done.

        For recurring ('daily'/'weekly') tasks that belong to a pet, this also
        drops a fresh, not-yet-done copy onto the same pet for the next
        occurrence, so the care routine keeps rolling on its own. Completing an
        already-done task is a no-op (it won't spawn duplicates).
        """
        if self.completed:
            return
        self.completed = True
        nxt = self.next_occurrence()
        if nxt is not None and self.pet is not None:
            self.pet.add_task(nxt)

    def mark_incomplete(self):
        """Reset this task to not-done (e.g. at the start of a new day)."""
        self.completed = False

    def next_occurrence(self):
        """Return a fresh, incomplete copy of this task for its next run.

        Returns None for one-off frequencies (e.g. 'monthly' is not treated as
        auto-recurring here). Tasks carry a time-of-day but no calendar date,
        so the copy reuses the same time — it represents 'the next day/week's
        run', not a specific future date.
        """
        if self.frequency not in self.RECURRING:
            return None
        return replace(self, completed=False)

    # --- time-window helpers (used for ordering + conflict detection) ---
    def start_dt(self):
        """Start time as a datetime.

        strptime parses "HH:MM" onto a fixed placeholder date (1900-01-01) and
        validates it — a bad string like "25:00" raises ValueError instead of
        silently miscomputing.
        """
        return datetime.strptime(self.time, "%H:%M")

    def end_dt(self):
        """End time as a datetime = start + duration.

        Using timedelta means a task that runs past midnight (e.g. 23:30 + 60m)
        rolls into the next day correctly instead of overflowing the hour.
        """
        return self.start_dt() + timedelta(minutes=self.duration_minutes)

    def end_time(self):
        """End time as an "HH:MM" display string (e.g. '08:00' + 30m -> '08:30')."""
        return self.end_dt().strftime("%H:%M")

    def overlaps(self, other):
        """True if this task's time window overlaps `other`'s.

        Two windows overlap when each starts before the other ends. Touching
        edges (one ends exactly when the next starts) do NOT count as a clash.
        """
        return self.start_dt() < other.end_dt() and other.start_dt() < self.end_dt()

    def __str__(self):
        """Render the task as a checkbox line for display."""
        box = "x" if self.completed else " "
        return (
            f"[{box}] {self.time} {self.description} "
            f"({self.duration_minutes}m, {self.priority}, {self.frequency})"
        )


@dataclass
class Pet:
    """Stores pet details and the list of tasks that belong to it."""

    name: str
    species: str
    tasks: list = field(default_factory=list)  # list[Task]

    def add_task(self, task):
        """Attach a task to this pet (and record this pet on the task)."""
        task.pet = self
        self.tasks.append(task)

    def remove_task(self, task):
        """Detach a task from this pet (no error if it isn't present)."""
        if task in self.tasks:
            self.tasks.remove(task)

    def __str__(self):
        """Render the pet with its species and task count."""
        return f"{self.name} ({self.species}) — {len(self.tasks)} task(s)"


@dataclass
class Owner:
    """Manages multiple pets and provides access to all their tasks."""

    name: str
    pets: list = field(default_factory=list)  # list[Pet]
    available_minutes: int = 120  # daily time budget the owner can spend on care

    def add_pet(self, pet):
        """Add a pet to this owner."""
        self.pets.append(pet)

    def remove_pet(self, pet):
        """Remove a pet from this owner (no error if it isn't present)."""
        if pet in self.pets:
            self.pets.remove(pet)

    def all_tasks(self):
        """Return every task across all of this owner's pets (flattened)."""
        return [task for pet in self.pets for task in pet.tasks]

    def __str__(self):
        """Render the owner with a count of their pets."""
        return f"{self.name} — {len(self.pets)} pet(s)"


class Scheduler:
    """The 'brain': retrieves, organizes, and manages tasks across all pets.

    Operates on a single Owner and reads through to every pet's tasks.
    """

    def __init__(self, owner):
        """Create a scheduler bound to one owner, with an empty plan."""
        self.owner = owner
        self.scheduled_tasks = []  # tasks chosen by build_plan, time-ordered
        self.skipped_tasks = []    # tasks build_plan left out (no time)
        self.total_minutes = 0     # minutes the current plan uses

    # --- retrieve -------------------------------------------------------
    def all_tasks(self):
        """All tasks across every pet the owner has."""
        return self.owner.all_tasks()

    def tasks_for_pet(self, pet):
        """Just the tasks belonging to one pet."""
        return list(pet.tasks)

    def filter_tasks(self, pet=None, pet_name=None, completed=None, frequency=None):
        """All tasks matching every filter given, ordered by time of day.

        Any argument left as None is ignored, so callers can filter by pet
        (object or name), by completion status, by frequency, or any mix:
            filter_tasks(completed=True)             # everything already done
            filter_tasks(pet_name="Luna")            # all of Luna's tasks
            filter_tasks(pet=luna, completed=False)  # Luna's pending tasks
            filter_tasks(frequency="daily")          # today's recurring tasks
        """
        if pet is not None:
            tasks = self.tasks_for_pet(pet)
        elif pet_name is not None:
            tasks = [t for p in self.owner.pets if p.name == pet_name
                     for t in p.tasks]
        else:
            tasks = self.all_tasks()
        if completed is not None:
            tasks = [t for t in tasks if t.completed == completed]
        if frequency is not None:
            tasks = [t for t in tasks if t.frequency == frequency]
        return self.sort_by_time(tasks)

    # --- organize -------------------------------------------------------
    def sort_by_time(self, tasks=None):
        """Return tasks ordered by their `time` attribute (earliest first).

        Defaults to every task across all pets; pass a list to sort just that
        subset. Sorting is non-destructive — the input list is left untouched.
        """
        if tasks is None:
            tasks = self.all_tasks()
        return sorted(tasks, key=lambda t: t.time)

    def daily_schedule(self):
        """All tasks ordered by time of day (earliest first)."""
        return self.sort_by_time()

    def pending_tasks(self):
        """Tasks not yet completed, ordered by time."""
        return [t for t in self.daily_schedule() if not t.completed]

    def completed_tasks(self):
        """Tasks already completed."""
        return [t for t in self.all_tasks() if t.completed]

    # --- detect conflicts -----------------------------------------------
    def find_conflicts(self):
        """Find pairs of PENDING tasks whose time windows overlap.

        Returns a list of (earlier, later) tuples. Works across all pets, so
        it catches an owner trying to walk the dog and feed the cat at once.
        Completed tasks are ignored — a task that's already done isn't
        competing for time, and skipping them also avoids a recurring task
        clashing with the fresh next-occurrence it spawned on completion.
        """
        tasks = self.pending_tasks()  # not-completed, sorted by start time
        conflicts = []
        for i, earlier in enumerate(tasks):
            for later in tasks[i + 1:]:
                if later.start_dt() >= earlier.end_dt():
                    # Sorted by start, so nothing after `later` can overlap
                    # `earlier` either — stop scanning this pair's tail.
                    break
                conflicts.append((earlier, later))
        return conflicts

    def same_pet_conflicts(self):
        """Overlapping pairs that belong to the SAME pet (the pet can't do both)."""
        return [(a, b) for a, b in self.find_conflicts() if a.pet is b.pet]

    def cross_pet_conflicts(self):
        """Overlapping pairs across DIFFERENT pets (the owner can't do both at once)."""
        return [(a, b) for a, b in self.find_conflicts() if a.pet is not b.pet]

    def describe_conflict(self, earlier, later):
        """One-line description of a conflict, naming the pet(s) involved."""
        ep = earlier.pet.name if earlier.pet else "?"
        lp = later.pet.name if later.pet else "?"
        if earlier.pet is later.pet:
            return (f"{ep}: {earlier.time} {earlier.description} "
                    f"overlaps {later.time} {later.description}")
        return (f"{ep}'s {earlier.time} {earlier.description} "
                f"overlaps {lp}'s {later.time} {later.description}")

    def conflict_warning(self):
        """A lightweight, crash-proof conflict check that returns a message.

        Instead of raising (or making the caller loop over pairs), this returns
        one human-readable string: an all-clear note, or a bullet list of the
        clashes found. A task whose time can't be parsed is reported as its own
        warning line rather than crashing the whole check — so one bad entry
        never takes the program down.
        """
        # Split tasks into ones we can safely time-check and ones we can't.
        # Only pending tasks matter — completed ones aren't competing for time.
        parseable, unparseable = [], []
        for task in self.pending_tasks():  # sorted by time string; never raises
            try:
                task.end_dt()  # forces the "HH:MM" parse + duration math
                parseable.append(task)
            except ValueError:
                unparseable.append(task)

        lines = []
        # Overlaps among the tasks we could parse (same early-exit as find_conflicts).
        for i, earlier in enumerate(parseable):
            for later in parseable[i + 1:]:
                if later.start_dt() >= earlier.end_dt():
                    break
                lines.append(f"⚠ {self.describe_conflict(earlier, later)}")
        # Bad data surfaces as a warning, not an exception.
        for task in unparseable:
            lines.append(f"⚠ couldn't check '{task.description}' — "
                         f"bad time value {task.time!r}")

        if not lines:
            return "✅ No scheduling conflicts found."
        return "\n".join(lines)

    # --- plan (constraints + priority) ----------------------------------
    def build_plan(self, available_minutes=None):
        """Greedily pick pending tasks that fit the time budget, highest priority first."""
        if available_minutes is None:
            available_minutes = self.owner.available_minutes

        # Highest priority first; ties broken by earlier time of day.
        ordered = sorted(
            self.pending_tasks(),
            key=lambda t: (-PRIORITY_RANK.get(t.priority, 0), t.time),
        )

        chosen, skipped, remaining = [], [], available_minutes
        for task in ordered:
            if self._fits(task, remaining):
                chosen.append(task)
                remaining -= task.duration_minutes
            else:
                skipped.append(task)

        self.scheduled_tasks = sorted(chosen, key=lambda t: t.time)
        self.skipped_tasks = skipped
        self.total_minutes = available_minutes - remaining
        return self.scheduled_tasks

    def _fits(self, task, remaining):
        """Return True if task's duration fits in the remaining minutes."""
        return task.duration_minutes <= remaining

    def explain(self):
        """Explain the current plan: what was scheduled and what was skipped."""
        if not self.scheduled_tasks and not self.skipped_tasks:
            return "No plan built yet. Call build_plan() first."

        lines = [f"Planned {self.total_minutes} min of care:"]
        for t in self.scheduled_tasks:
            lines.append(f"  {t.time}–{t.end_time()} — {t.description} "
                         f"({t.duration_minutes}m, {t.priority} priority)")
        for t in self.skipped_tasks:
            lines.append(f"  skipped {t.description} "
                         f"({t.priority} priority) — not enough time")

        conflicts = self.find_conflicts()
        if conflicts:
            lines.append("Heads up — overlapping tasks:")
            for earlier, later in conflicts:
                lines.append(f"  ⚠ {self.describe_conflict(earlier, later)}")
        return "\n".join(lines)

    # --- manage ---------------------------------------------------------
    def summary(self):
        """A short human-readable status line: done vs. total."""
        total = len(self.all_tasks())
        done = len(self.completed_tasks())
        return f"{done}/{total} task(s) completed across {len(self.owner.pets)} pet(s)"
