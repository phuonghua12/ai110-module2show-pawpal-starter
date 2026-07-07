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

from dataclasses import dataclass, field

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

    def mark_complete(self):
        """Mark this task as done."""
        self.completed = True

    def mark_incomplete(self):
        """Reset this task to not-done (e.g. at the start of a new day)."""
        self.completed = False

    def __str__(self):
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
        """Attach a task to this pet."""
        self.tasks.append(task)

    def remove_task(self, task):
        """Detach a task from this pet (no error if it isn't present)."""
        if task in self.tasks:
            self.tasks.remove(task)

    def __str__(self):
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
        return f"{self.name} — {len(self.pets)} pet(s)"


class Scheduler:
    """The 'brain': retrieves, organizes, and manages tasks across all pets.

    Operates on a single Owner and reads through to every pet's tasks.
    """

    def __init__(self, owner):
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

    # --- organize -------------------------------------------------------
    def daily_schedule(self):
        """All tasks ordered by time of day (earliest first)."""
        return sorted(self.all_tasks(), key=lambda t: t.time)

    def tasks_by_frequency(self, frequency):
        """All tasks matching the given frequency (e.g. 'daily')."""
        return [t for t in self.all_tasks() if t.frequency == frequency]

    def pending_tasks(self):
        """Tasks not yet completed, ordered by time."""
        return [t for t in self.daily_schedule() if not t.completed]

    def completed_tasks(self):
        """Tasks already completed."""
        return [t for t in self.all_tasks() if t.completed]

    # --- plan (constraints + priority) ----------------------------------
    def build_plan(self, available_minutes=None):
        """Pick pending tasks that fit the time budget, highest priority first.

        Greedy: sort pending tasks by priority (then time), then take each one
        while it still fits in the remaining minutes. Chosen tasks are stored
        (time-ordered) on self.scheduled_tasks; the rest go to self.skipped_tasks.
        Returns the scheduled tasks.
        """
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
            lines.append(f"  {t.time} — {t.description} "
                         f"({t.duration_minutes}m, {t.priority} priority)")
        for t in self.skipped_tasks:
            lines.append(f"  skipped {t.description} "
                         f"({t.priority} priority) — not enough time")
        return "\n".join(lines)

    # --- manage ---------------------------------------------------------
    def reset_daily_tasks(self):
        """Mark every 'daily' task incomplete — e.g. to start a fresh day."""
        for task in self.tasks_by_frequency("daily"):
            task.mark_incomplete()

    def summary(self):
        """A short human-readable status line: done vs. total."""
        total = len(self.all_tasks())
        done = len(self.completed_tasks())
        return f"{done}/{total} task(s) completed across {len(self.owner.pets)} pet(s)"
