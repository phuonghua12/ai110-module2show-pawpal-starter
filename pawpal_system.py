"""PawPal+ system skeleton.

Class skeletons generated from diagrams/uml.mmd (4-class design):
Owner, Pet, and Task are data classes (implemented as @dataclass);
Scheduler holds the logic and the resulting schedule. Scheduler method
bodies are empty stubs — no logic yet.
"""

from dataclasses import dataclass, field

# Numeric rank for each priority so tasks can be sorted correctly.
# (Sorting the raw strings would order them alphabetically:
#  "high" < "low" < "medium", which is wrong.)
PRIORITY_RANK = {"high": 3, "medium": 2, "low": 1}


@dataclass
class Owner:
    """Represents the pet owner and their care constraints/preferences."""

    name: str
    available_minutes: int
    pets: list = field(default_factory=list)  # list[Pet] this owner cares for


@dataclass
class Pet:
    """Represents the animal being cared for."""

    name: str
    species: str


@dataclass
class Task:
    """Represents one unit of care: what it is, how long it takes, how important."""

    title: str
    duration_minutes: int
    priority: str  # "low" | "medium" | "high"


class Scheduler:
    """Builds and holds a daily care schedule from tasks + constraints."""

    def __init__(self):
        self.scheduled_tasks = []  # list[Task] chosen for the day, in order
        self.skipped_tasks = []    # list[Task] left out (didn't fit) — used by explain()
        self.total_minutes = 0     # total time the schedule uses

    def build_plan(self, owner, tasks):
        """Choose and order tasks that fit within owner.available_minutes."""
        pass

    def explain(self):
        """Return a human-readable explanation of why the plan looks like it does."""
        pass

    def _sort_tasks(self, tasks):
        """Order tasks by priority (via PRIORITY_RANK), then duration. Helper for build_plan."""
        pass

    def _fits(self, task, remaining):
        """Return True if task's duration fits in the remaining minutes."""
        pass
