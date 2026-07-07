"""PawPal+ system skeleton.

Class skeletons generated from diagrams/uml.mmd (4-class design):
Owner, Pet, and Task are data classes (implemented as @dataclass);
Scheduler holds the logic and the resulting schedule. Scheduler method
bodies are empty stubs — no logic yet.
"""

from dataclasses import dataclass


@dataclass
class Owner:
    """Represents the pet owner and their care constraints/preferences."""

    name: str
    available_minutes: int


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
        self.total_minutes = 0     # total time the schedule uses

    def build_plan(self, tasks, available_minutes):
        """Choose and order tasks that fit within available_minutes."""
        pass

    def explain(self):
        """Return a human-readable explanation of why the plan looks like it does."""
        pass

    def _sort_tasks(self, tasks):
        """Order tasks (e.g. by priority, then duration). Helper for build_plan."""
        pass

    def _fits(self, task, remaining):
        """Return True if task's duration fits in the remaining minutes."""
        pass
