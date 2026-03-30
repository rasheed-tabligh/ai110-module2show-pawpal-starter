"""
PawPal+ — Logic layer
Classes: Owner, Pet, Task, Scheduler
Designed from UML (see reflection.md for diagram).
"""

from dataclasses import dataclass, field


@dataclass
class Task:
    """A single pet care activity with a title, duration, priority, and category."""

    title: str
    duration_minutes: int
    priority: str   # "low" | "medium" | "high"
    category: str   # "walk" | "feeding" | "medication" | "grooming" | "enrichment" | "other"
    completed: bool = False

    def mark_complete(self) -> None:
        """Mark this task as done."""
        self.completed = True


@dataclass
class Pet:
    """Stores a pet's profile and its list of care tasks."""

    name: str
    species: str    # "dog" | "cat" | "other"
    age: int
    health_notes: str = ""
    _tasks: list = field(default_factory=list, repr=False, init=False)

    def add_task(self, task: Task) -> None:
        """Attach a care task to this pet."""
        self._tasks.append(task)

    def get_tasks(self) -> list[Task]:
        """Return all tasks assigned to this pet."""
        return list(self._tasks)


@dataclass
class Owner:
    """Stores owner info, their daily time budget, and the pets they own."""

    name: str
    available_minutes_per_day: int   # total care time the owner has each day
    preferences: list[str] = field(default_factory=list)  # e.g. ["morning walks", "no late meds"]
    _pets: list = field(default_factory=list, repr=False, init=False)

    def add_pet(self, pet: Pet) -> None:
        """Register a pet under this owner."""
        self._pets.append(pet)

    def get_pets(self) -> list[Pet]:
        """Return all pets belonging to this owner."""
        return list(self._pets)


class Scheduler:
    """
    The scheduling brain of PawPal+.

    Collects tasks from ALL of the owner's pets, sorts them by priority,
    and greedily builds a daily plan that fits within the owner's time budget.
    """

    # Maps priority label to a numeric rank for sorting.
    PRIORITY_RANK = {"high": 3, "medium": 2, "low": 1}

    def __init__(self, owner: Owner) -> None:
        self.owner = owner

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def get_all_tasks(self) -> list[Task]:
        """Collect every task from every pet the owner has."""
        tasks = []
        for pet in self.owner.get_pets():
            tasks.extend(pet.get_tasks())
        return tasks

    def _task_to_pet_map(self) -> dict:
        """Build a lookup from task id → pet name (used for display)."""
        mapping = {}
        for pet in self.owner.get_pets():
            for task in pet.get_tasks():
                mapping[id(task)] = pet.name
        return mapping

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_schedule(self) -> list[Task]:
        """
        Return a prioritized list of tasks that fit within the owner's daily time budget.

        Only incomplete tasks are considered. Tasks are sorted high → low priority;
        ties preserve the original insertion order. Tasks are added greedily until
        the time budget is used up.
        """
        candidates = [t for t in self.get_all_tasks() if not t.completed]
        sorted_tasks = sorted(
            candidates,
            key=lambda t: self.PRIORITY_RANK.get(t.priority, 0),
            reverse=True,
        )

        schedule: list[Task] = []
        time_used = 0
        for task in sorted_tasks:
            if time_used + task.duration_minutes <= self.owner.available_minutes_per_day:
                schedule.append(task)
                time_used += task.duration_minutes

        return schedule

    def explain_plan(self, schedule: list[Task]) -> str:
        """
        Return a readable summary of the schedule: what was included (with start times)
        and what was skipped because the time budget ran out.
        """
        owner_name = self.owner.name
        available = self.owner.available_minutes_per_day
        task_pet = self._task_to_pet_map()

        if not schedule:
            return f"No tasks could be scheduled for {owner_name} today."

        scheduled_ids = {id(t) for t in schedule}

        lines = [
            f"Daily Care Plan — {owner_name}",
            f"Time budget: {available} min",
            "=" * 46,
        ]

        time_used = 0
        for task in schedule:
            pet_label = task_pet.get(id(task), "?")
            lines.append(
                f"  [{time_used:>3} min]  {task.title}"
                f"  ({task.duration_minutes} min | {task.priority} | {pet_label})"
            )
            time_used += task.duration_minutes

        lines.append(f"\n  Total: {time_used} / {available} min used")

        # Show what didn't make it in
        all_incomplete = [t for t in self.get_all_tasks() if not t.completed]
        skipped = [t for t in all_incomplete if id(t) not in scheduled_ids]
        if skipped:
            lines.append("\nSkipped (not enough time remaining):")
            for task in skipped:
                pet_label = task_pet.get(id(task), "?")
                lines.append(
                    f"  - {task.title}"
                    f"  ({task.duration_minutes} min | {task.priority} | {pet_label})"
                )

        return "\n".join(lines)

    def filter_by_priority(self, min_priority: str) -> list[Task]:
        """
        Return all tasks whose priority is at or above min_priority.
        Useful for quickly seeing only high-importance items.
        """
        min_rank = self.PRIORITY_RANK.get(min_priority, 0)
        return [
            t for t in self.get_all_tasks()
            if self.PRIORITY_RANK.get(t.priority, 0) >= min_rank
        ]
