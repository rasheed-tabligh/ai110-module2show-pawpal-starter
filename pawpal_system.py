"""
PawPal+ — Logic layer
Classes: Owner, Pet, Task, Scheduler
Designed from UML (see reflection.md for diagram).
"""

import json
from dataclasses import dataclass, field
from datetime import date, timedelta


@dataclass
class Task:
    """A single pet care activity with a title, duration, priority, and category."""

    title: str
    duration_minutes: int
    priority: str       # "low" | "medium" | "high"
    category: str       # "walk" | "feeding" | "medication" | "grooming" | "enrichment" | "other"
    scheduled_time: str = ""   # optional wall-clock start time in "HH:MM" format
    recurrence: str = ""       # "" | "daily" | "weekly"
    due_date: str = ""         # optional "YYYY-MM-DD" used by recurring tasks
    completed: bool = False

    def mark_complete(self) -> None:
        """Mark this task as done."""
        self.completed = True

    def to_dict(self) -> dict:
        """Serialize this task to a plain dictionary (for JSON storage)."""
        return {
            "title": self.title,
            "duration_minutes": self.duration_minutes,
            "priority": self.priority,
            "category": self.category,
            "scheduled_time": self.scheduled_time,
            "recurrence": self.recurrence,
            "due_date": self.due_date,
            "completed": self.completed,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        """Reconstruct a Task from a dictionary produced by to_dict()."""
        return cls(
            title=data["title"],
            duration_minutes=data["duration_minutes"],
            priority=data["priority"],
            category=data["category"],
            scheduled_time=data.get("scheduled_time", ""),
            recurrence=data.get("recurrence", ""),
            due_date=data.get("due_date", ""),
            completed=data.get("completed", False),
        )


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

    def to_dict(self) -> dict:
        """Serialize this pet (and its tasks) to a plain dictionary."""
        return {
            "name": self.name,
            "species": self.species,
            "age": self.age,
            "health_notes": self.health_notes,
            "tasks": [t.to_dict() for t in self._tasks],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Pet":
        """Reconstruct a Pet (and its tasks) from a dictionary produced by to_dict()."""
        pet = cls(
            name=data["name"],
            species=data["species"],
            age=data["age"],
            health_notes=data.get("health_notes", ""),
        )
        for task_data in data.get("tasks", []):
            pet.add_task(Task.from_dict(task_data))
        return pet


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

    def to_dict(self) -> dict:
        """Serialize this owner (and all pets and tasks) to a plain dictionary."""
        return {
            "name": self.name,
            "available_minutes_per_day": self.available_minutes_per_day,
            "preferences": self.preferences,
            "pets": [p.to_dict() for p in self._pets],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Owner":
        """Reconstruct an Owner (with all pets and tasks) from a dictionary."""
        owner = cls(
            name=data["name"],
            available_minutes_per_day=data["available_minutes_per_day"],
            preferences=data.get("preferences", []),
        )
        for pet_data in data.get("pets", []):
            owner.add_pet(Pet.from_dict(pet_data))
        return owner

    def save_to_json(self, filepath: str = "data.json") -> None:
        """Write the full owner profile (pets + tasks) to a JSON file."""
        with open(filepath, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load_from_json(cls, filepath: str = "data.json") -> "Owner":
        """Load and reconstruct an Owner from a previously saved JSON file."""
        with open(filepath) as f:
            data = json.load(f)
        return cls.from_dict(data)


class Scheduler:
    """
    The scheduling brain of PawPal+.

    Collects tasks from ALL of the owner's pets, sorts them by priority,
    and greedily builds a daily plan that fits within the owner's time budget.
    Supports time-based sorting, status/pet filtering, recurring tasks,
    and lightweight conflict detection.
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

    @staticmethod
    def _time_to_minutes(time_str: str) -> int:
        """
        Convert an 'HH:MM' string to minutes since midnight.
        Returns 9999 for tasks with no scheduled_time so they sort to the end.
        """
        if not time_str:
            return 9999
        h, m = time_str.split(":")
        return int(h) * 60 + int(m)

    @staticmethod
    def _minutes_to_time(minutes: int) -> str:
        """Convert minutes since midnight back to an 'HH:MM' string."""
        return f"{minutes // 60:02d}:{minutes % 60:02d}"

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

    def sort_by_time(self, tasks: list[Task]) -> list[Task]:
        """
        Sort a list of tasks by their scheduled_time (HH:MM) in ascending order.

        Uses a lambda with _time_to_minutes as the sort key so that "08:00" < "10:30".
        Tasks with no scheduled_time are pushed to the end (key returns 9999).
        """
        return sorted(tasks, key=lambda t: self._time_to_minutes(t.scheduled_time))

    def filter_tasks(
        self,
        pet_name: str | None = None,
        completed: bool | None = None,
    ) -> list[Task]:
        """
        Filter tasks across all pets by pet name and/or completion status.

        Pass pet_name to see only one pet's tasks.
        Pass completed=True/False to filter by done/pending.
        Passing neither returns everything (same as get_all_tasks).
        """
        results = []
        for pet in self.owner.get_pets():
            if pet_name is not None and pet.name != pet_name:
                continue
            for task in pet.get_tasks():
                if completed is not None and task.completed != completed:
                    continue
                results.append(task)
        return results

    def complete_task(self, task: Task, pet: Pet) -> Task | None:
        """
        Mark a task complete and, if it recurs, auto-create the next occurrence.

        For a 'daily' task the next due_date is today + 1 day (timedelta(days=1)).
        For a 'weekly' task it is today + 7 days (timedelta(weeks=1)).
        The new Task is added directly to the same pet and returned so the caller
        can display it. Returns None for non-recurring tasks.
        """
        task.mark_complete()
        if not task.recurrence:
            return None

        today = date.today()
        if task.recurrence == "daily":
            next_date = today + timedelta(days=1)
        elif task.recurrence == "weekly":
            next_date = today + timedelta(weeks=1)
        else:
            return None

        next_task = Task(
            title=task.title,
            duration_minutes=task.duration_minutes,
            priority=task.priority,
            category=task.category,
            scheduled_time=task.scheduled_time,
            recurrence=task.recurrence,
            due_date=str(next_date),
        )
        pet.add_task(next_task)
        return next_task

    def detect_conflicts(self, schedule: list[Task]) -> list[str]:
        """
        Check for overlapping tasks in the schedule and return warning strings.

        Only tasks with a scheduled_time are checked. Two tasks conflict when
        one starts before the other finishes: start_a < end_b AND start_b < end_a.
        Returns an empty list if no conflicts are found — it never raises an exception,
        so the app keeps running even when the schedule has problems.
        """
        # Build (task, start_minutes, end_minutes) for every timed task
        timed = [
            (
                t,
                self._time_to_minutes(t.scheduled_time),
                self._time_to_minutes(t.scheduled_time) + t.duration_minutes,
            )
            for t in schedule
            if t.scheduled_time
        ]

        warnings = []
        for i in range(len(timed)):
            for j in range(i + 1, len(timed)):
                task_a, start_a, end_a = timed[i]
                task_b, start_b, end_b = timed[j]
                if start_a < end_b and start_b < end_a:
                    warnings.append(
                        f"Conflict: '{task_a.title}' ({task_a.scheduled_time}, "
                        f"{task_a.duration_minutes} min) overlaps with "
                        f"'{task_b.title}' ({task_b.scheduled_time}, {task_b.duration_minutes} min)"
                    )
        return warnings

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
            time_tag = f" @ {task.scheduled_time}" if task.scheduled_time else ""
            lines.append(
                f"  [{time_used:>3} min]  {task.title}{time_tag}"
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

    def find_next_slot(self, duration_minutes: int, after_time: str = "00:00") -> str | None:
        """
        Find the earliest gap in the current timed schedule where a task of
        the given duration would fit without overlapping anything.

        Algorithm: sort all timed tasks by start time, then scan forward with
        a 'cursor' that advances past each occupied window. The first position
        where (cursor + duration) fits before the next task's start is returned.
        Returns None if no gap exists before midnight.

        Only tasks that have a scheduled_time are treated as fixed; flexible
        (untimed) tasks are invisible to this method — they don't block slots.
        """
        schedule = self.generate_schedule()

        # Build sorted list of (start, end) for every timed task in the schedule
        occupied = sorted(
            [
                (
                    self._time_to_minutes(t.scheduled_time),
                    self._time_to_minutes(t.scheduled_time) + t.duration_minutes,
                )
                for t in schedule
                if t.scheduled_time
            ],
            key=lambda x: x[0],
        )

        cursor = self._time_to_minutes(after_time)
        end_of_day = 24 * 60  # 1440 minutes

        for task_start, task_end in occupied:
            if task_start < cursor:
                # This block is before the cursor, but it might still push us forward
                if task_end > cursor:
                    cursor = task_end
                continue
            # There is a gap between cursor and the next block — check if it fits
            if task_start - cursor >= duration_minutes:
                return self._minutes_to_time(cursor)
            # Gap too small — jump past this block
            cursor = task_end

        # Check the remaining time after the last occupied block
        if end_of_day - cursor >= duration_minutes:
            return self._minutes_to_time(cursor)

        return None

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
