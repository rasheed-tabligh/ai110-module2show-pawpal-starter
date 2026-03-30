"""
tests/test_pawpal.py — Unit tests for PawPal+ core logic

Run with:
    python -m pytest
"""

import pytest
from pawpal_system import Owner, Pet, Task, Scheduler


# ------------------------------------------------------------------ #
# Task tests
# ------------------------------------------------------------------ #

def test_task_mark_complete_changes_status():
    """Calling mark_complete() should flip completed from False to True."""
    task = Task(title="Morning walk", duration_minutes=30, priority="high", category="walk")
    assert task.completed is False
    task.mark_complete()
    assert task.completed is True


def test_task_starts_incomplete_by_default():
    """A newly created task should always start as not completed."""
    task = Task(title="Feeding", duration_minutes=10, priority="medium", category="feeding")
    assert task.completed is False


# ------------------------------------------------------------------ #
# Pet tests
# ------------------------------------------------------------------ #

def test_add_task_increases_pet_task_count():
    """Adding tasks to a pet should increase the count returned by get_tasks()."""
    pet = Pet(name="Mochi", species="dog", age=3)
    assert len(pet.get_tasks()) == 0

    pet.add_task(Task(title="Walk", duration_minutes=20, priority="high", category="walk"))
    assert len(pet.get_tasks()) == 1

    pet.add_task(Task(title="Feed", duration_minutes=10, priority="medium", category="feeding"))
    assert len(pet.get_tasks()) == 2


def test_get_tasks_returns_copy():
    """Mutating the list returned by get_tasks() should not affect the pet's internal list."""
    pet = Pet(name="Luna", species="cat", age=5)
    pet.add_task(Task(title="Medication", duration_minutes=5, priority="high", category="medication"))

    tasks_copy = pet.get_tasks()
    tasks_copy.clear()  # mutate the copy
    assert len(pet.get_tasks()) == 1  # original unchanged


# ------------------------------------------------------------------ #
# Scheduler tests
# ------------------------------------------------------------------ #

def test_scheduler_respects_time_budget():
    """The scheduler must not exceed the owner's available_minutes_per_day."""
    owner = Owner(name="Jordan", available_minutes_per_day=40)
    pet = Pet(name="Mochi", species="dog", age=3)
    pet.add_task(Task(title="Long walk",  duration_minutes=30, priority="high",   category="walk"))
    pet.add_task(Task(title="Feeding",    duration_minutes=10, priority="high",   category="feeding"))
    pet.add_task(Task(title="Play fetch", duration_minutes=20, priority="medium", category="enrichment"))
    owner.add_pet(pet)

    scheduler = Scheduler(owner=owner)
    schedule = scheduler.generate_schedule()

    total = sum(t.duration_minutes for t in schedule)
    assert total <= owner.available_minutes_per_day


def test_scheduler_skips_completed_tasks():
    """Tasks already marked complete should not appear in the generated schedule."""
    owner = Owner(name="Jordan", available_minutes_per_day=120)
    pet = Pet(name="Mochi", species="dog", age=3)

    done_task = Task(title="Morning walk", duration_minutes=30, priority="high", category="walk")
    done_task.mark_complete()
    pending_task = Task(title="Feeding", duration_minutes=10, priority="high", category="feeding")

    pet.add_task(done_task)
    pet.add_task(pending_task)
    owner.add_pet(pet)

    scheduler = Scheduler(owner=owner)
    schedule = scheduler.generate_schedule()

    titles = [t.title for t in schedule]
    assert "Morning walk" not in titles
    assert "Feeding" in titles


def test_scheduler_orders_by_priority():
    """High-priority tasks should appear before lower-priority ones in the schedule."""
    owner = Owner(name="Jordan", available_minutes_per_day=120)
    pet = Pet(name="Mochi", species="dog", age=3)
    pet.add_task(Task(title="Low task",    duration_minutes=10, priority="low",    category="enrichment"))
    pet.add_task(Task(title="High task",   duration_minutes=10, priority="high",   category="walk"))
    pet.add_task(Task(title="Medium task", duration_minutes=10, priority="medium", category="feeding"))
    owner.add_pet(pet)

    scheduler = Scheduler(owner=owner)
    schedule = scheduler.generate_schedule()
    priorities = [t.priority for t in schedule]

    # high should come before medium, medium before low
    assert priorities.index("high") < priorities.index("medium")
    assert priorities.index("medium") < priorities.index("low")
