"""
PawPal+ — Logic layer
Classes: Owner, Pet, Task, Scheduler
Designed from UML (see reflection.md for diagram).
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Task:
    """A single pet care task (walk, feeding, medication, etc.)."""

    title: str
    duration_minutes: int
    priority: str          # "low" | "medium" | "high"
    category: str          # "walk" | "feeding" | "medication" | "grooming" | "enrichment" | "other"
    completed: bool = False

    def mark_complete(self) -> None:
        """Mark this task as done."""
        self.completed = True


@dataclass
class Pet:
    """Represents a pet owned by an Owner."""

    name: str
    species: str           # "dog" | "cat" | "other"
    age: int
    health_notes: str = ""
    _tasks: list = field(default_factory=list, repr=False)

    def add_task(self, task: Task) -> None:
        """Attach a care task to this pet."""
        self._tasks.append(task)

    def get_tasks(self) -> list[Task]:
        """Return all tasks for this pet."""
        return list(self._tasks)


@dataclass
class Owner:
    """Represents the pet owner with their constraints and preferences."""

    name: str
    available_minutes_per_day: int    # total free time in a day
    preferences: list[str] = field(default_factory=list)   # e.g. ["morning walks", "no late meds"]
    _pets: list = field(default_factory=list, repr=False)

    def add_pet(self, pet: Pet) -> None:
        """Register a pet under this owner."""
        self._pets.append(pet)

    def get_pets(self) -> list[Pet]:
        """Return all pets belonging to this owner."""
        return list(self._pets)


class Scheduler:
    """
    Generates a daily care plan for a pet given the owner's time constraints.
    Selects and orders tasks by priority, respecting available_minutes_per_day.
    """

    PRIORITY_RANK = {"high": 3, "medium": 2, "low": 1}

    def __init__(self, owner: Owner, pet: Pet) -> None:
        self.owner = owner
        self.pet = pet

    def generate_schedule(self) -> list[Task]:
        """
        Return an ordered list of tasks that fit within the owner's available time.
        Tasks are sorted high → low priority; ties keep original insertion order.
        """
        pass  # TODO: implement in Phase 2

    def explain_plan(self, schedule: list[Task]) -> str:
        """
        Return a human-readable explanation of why each task was included
        and what was left out.
        """
        pass  # TODO: implement in Phase 2

    def filter_by_priority(self, min_priority: str) -> list[Task]:
        """
        Return only tasks whose priority is >= min_priority.
        Useful for focusing on must-do tasks when time is tight.
        """
        pass  # TODO: implement in Phase 2
