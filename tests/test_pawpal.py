"""
tests/test_pawpal.py — Unit tests for PawPal+ core logic

Run with:
    python -m pytest
"""

import os
import tempfile
from datetime import date, timedelta

import pytest
from pawpal_system import Owner, Pet, Task, Scheduler


# ------------------------------------------------------------------ #
# Helpers — shared fixtures to avoid copy-pasting setup code
# ------------------------------------------------------------------ #

def make_owner(minutes: int = 120) -> Owner:
    """Return a simple Owner with a configurable time budget."""
    return Owner(name="Jordan", available_minutes_per_day=minutes)


def make_pet(name: str = "Mochi") -> Pet:
    """Return a simple Pet."""
    return Pet(name=name, species="dog", age=3)


# ================================================================== #
# Task tests
# ================================================================== #

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


# ================================================================== #
# Pet tests
# ================================================================== #

def test_add_task_increases_pet_task_count():
    """Adding tasks to a pet should increase the count returned by get_tasks()."""
    pet = make_pet()
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
    tasks_copy.clear()          # mutate the copy
    assert len(pet.get_tasks()) == 1  # original unchanged


# ================================================================== #
# Scheduler — basic schedule generation
# ================================================================== #

def test_scheduler_respects_time_budget():
    """The scheduler must not exceed the owner's available_minutes_per_day."""
    owner = make_owner(minutes=40)
    pet = make_pet()
    pet.add_task(Task(title="Long walk",  duration_minutes=30, priority="high",   category="walk"))
    pet.add_task(Task(title="Feeding",    duration_minutes=10, priority="high",   category="feeding"))
    pet.add_task(Task(title="Play fetch", duration_minutes=20, priority="medium", category="enrichment"))
    owner.add_pet(pet)

    schedule = Scheduler(owner=owner).generate_schedule()
    assert sum(t.duration_minutes for t in schedule) <= owner.available_minutes_per_day


def test_scheduler_skips_completed_tasks():
    """Tasks already marked complete should not appear in the generated schedule."""
    owner = make_owner()
    pet = make_pet()

    done = Task(title="Morning walk", duration_minutes=30, priority="high", category="walk")
    done.mark_complete()
    pending = Task(title="Feeding", duration_minutes=10, priority="high", category="feeding")

    pet.add_task(done)
    pet.add_task(pending)
    owner.add_pet(pet)

    titles = [t.title for t in Scheduler(owner=owner).generate_schedule()]
    assert "Morning walk" not in titles
    assert "Feeding" in titles


def test_scheduler_orders_by_priority():
    """High-priority tasks should appear before lower-priority ones in the schedule."""
    owner = make_owner()
    pet = make_pet()
    pet.add_task(Task(title="Low task",    duration_minutes=10, priority="low",    category="enrichment"))
    pet.add_task(Task(title="High task",   duration_minutes=10, priority="high",   category="walk"))
    pet.add_task(Task(title="Medium task", duration_minutes=10, priority="medium", category="feeding"))
    owner.add_pet(pet)

    priorities = [t.priority for t in Scheduler(owner=owner).generate_schedule()]
    assert priorities.index("high") < priorities.index("medium")
    assert priorities.index("medium") < priorities.index("low")


# ================================================================== #
# Scheduler — edge cases
# ================================================================== #

def test_scheduler_with_no_pets_returns_empty():
    """An owner with no pets registered should produce an empty schedule."""
    owner = make_owner()
    assert Scheduler(owner=owner).generate_schedule() == []


def test_scheduler_with_pet_but_no_tasks_returns_empty():
    """A pet with no tasks attached should still produce an empty schedule."""
    owner = make_owner()
    owner.add_pet(make_pet())
    assert Scheduler(owner=owner).generate_schedule() == []


def test_scheduler_zero_budget_returns_empty():
    """When the owner has no available time, nothing should be scheduled."""
    owner = make_owner(minutes=0)
    pet = make_pet()
    pet.add_task(Task(title="Walk", duration_minutes=30, priority="high", category="walk"))
    owner.add_pet(pet)
    assert Scheduler(owner=owner).generate_schedule() == []


# ================================================================== #
# Scheduler — sort_by_time
# ================================================================== #

def test_sort_by_time_returns_chronological_order():
    """Tasks added out of order should be sorted earliest → latest by scheduled_time."""
    owner = make_owner()
    pet = make_pet()
    # Added in reverse time order on purpose
    pet.add_task(Task(title="Evening walk",  duration_minutes=25, priority="medium", category="walk",    scheduled_time="17:00"))
    pet.add_task(Task(title="Morning walk",  duration_minutes=30, priority="high",   category="walk",    scheduled_time="07:30"))
    pet.add_task(Task(title="Lunch feeding", duration_minutes=10, priority="high",   category="feeding", scheduled_time="12:00"))
    owner.add_pet(pet)

    scheduler = Scheduler(owner=owner)
    sorted_tasks = scheduler.sort_by_time(pet.get_tasks())
    times = [t.scheduled_time for t in sorted_tasks]
    assert times == ["07:30", "12:00", "17:00"]


def test_sort_by_time_puts_untimed_tasks_last():
    """Tasks with no scheduled_time should appear at the end of the sorted list."""
    owner = make_owner()
    pet = make_pet()
    pet.add_task(Task(title="Grooming", duration_minutes=15, priority="low",  category="grooming"))        # no time
    pet.add_task(Task(title="Walk",     duration_minutes=30, priority="high", category="walk",    scheduled_time="08:00"))
    owner.add_pet(pet)

    scheduler = Scheduler(owner=owner)
    sorted_tasks = scheduler.sort_by_time(pet.get_tasks())
    assert sorted_tasks[0].title == "Walk"
    assert sorted_tasks[-1].title == "Grooming"


# ================================================================== #
# Scheduler — filter_tasks
# ================================================================== #

def test_filter_tasks_by_pet_name():
    """filter_tasks(pet_name=...) should return only that pet's tasks."""
    owner = make_owner()
    mochi = make_pet("Mochi")
    luna  = Pet(name="Luna", species="cat", age=5)
    mochi.add_task(Task(title="Walk",       duration_minutes=30, priority="high", category="walk"))
    luna.add_task( Task(title="Medication", duration_minutes=5,  priority="high", category="medication"))
    owner.add_pet(mochi)
    owner.add_pet(luna)

    scheduler = Scheduler(owner=owner)
    mochi_tasks = scheduler.filter_tasks(pet_name="Mochi")
    assert len(mochi_tasks) == 1
    assert mochi_tasks[0].title == "Walk"


def test_filter_tasks_by_completion_status():
    """filter_tasks(completed=False) should return only pending tasks."""
    owner = make_owner()
    pet = make_pet()
    done = Task(title="Walk", duration_minutes=30, priority="high", category="walk")
    done.mark_complete()
    pending = Task(title="Feeding", duration_minutes=10, priority="high", category="feeding")
    pet.add_task(done)
    pet.add_task(pending)
    owner.add_pet(pet)

    scheduler = Scheduler(owner=owner)
    pending_tasks = scheduler.filter_tasks(completed=False)
    assert len(pending_tasks) == 1
    assert pending_tasks[0].title == "Feeding"


# ================================================================== #
# Scheduler — complete_task / recurrence
# ================================================================== #

def test_complete_daily_task_creates_next_occurrence():
    """Completing a daily task should add a new pending task to the same pet."""
    owner = make_owner()
    pet = Pet(name="Luna", species="cat", age=5)
    task = Task(
        title="Medication", duration_minutes=5, priority="high",
        category="medication", recurrence="daily",
    )
    pet.add_task(task)
    owner.add_pet(pet)

    scheduler = Scheduler(owner=owner)
    next_task = scheduler.complete_task(task, pet)

    assert task.completed is True
    assert next_task is not None
    assert next_task.title == "Medication"
    assert next_task.completed is False
    assert next_task.due_date == str(date.today() + timedelta(days=1))
    assert len(pet.get_tasks()) == 2  # original (done) + new (pending)


def test_complete_weekly_task_creates_next_occurrence_in_seven_days():
    """Completing a weekly task should schedule the next one seven days out."""
    owner = make_owner()
    pet = make_pet()
    task = Task(
        title="Bath time", duration_minutes=20, priority="low",
        category="grooming", recurrence="weekly",
    )
    pet.add_task(task)
    owner.add_pet(pet)

    scheduler = Scheduler(owner=owner)
    next_task = scheduler.complete_task(task, pet)

    assert next_task is not None
    assert next_task.due_date == str(date.today() + timedelta(weeks=1))


def test_complete_non_recurring_task_returns_none():
    """Completing a task with no recurrence should return None (no new task created)."""
    owner = make_owner()
    pet = make_pet()
    task = Task(title="Walk", duration_minutes=30, priority="high", category="walk")
    pet.add_task(task)
    owner.add_pet(pet)

    scheduler = Scheduler(owner=owner)
    result = scheduler.complete_task(task, pet)

    assert result is None
    assert len(pet.get_tasks()) == 1  # no new task added


# ================================================================== #
# Scheduler — detect_conflicts
# ================================================================== #

def test_detect_conflicts_flags_overlapping_tasks():
    """Two tasks whose time windows overlap should produce a conflict warning."""
    owner = make_owner()
    pet = make_pet()
    # Walk runs 08:00 – 08:30; Grooming starts at 08:15 → overlap
    t1 = Task(title="Walk",     duration_minutes=30, priority="high",   category="walk",     scheduled_time="08:00")
    t2 = Task(title="Grooming", duration_minutes=20, priority="medium", category="grooming", scheduled_time="08:15")
    pet.add_task(t1)
    pet.add_task(t2)
    owner.add_pet(pet)

    warnings = Scheduler(owner=owner).detect_conflicts([t1, t2])
    assert len(warnings) == 1
    assert "Walk" in warnings[0]
    assert "Grooming" in warnings[0]


def test_detect_conflicts_exact_same_start_time():
    """Two tasks starting at the exact same time should always conflict."""
    owner = make_owner()
    pet = make_pet()
    t1 = Task(title="Walk",    duration_minutes=30, priority="high", category="walk",    scheduled_time="09:00")
    t2 = Task(title="Feeding", duration_minutes=10, priority="high", category="feeding", scheduled_time="09:00")
    pet.add_task(t1)
    pet.add_task(t2)
    owner.add_pet(pet)

    warnings = Scheduler(owner=owner).detect_conflicts([t1, t2])
    assert len(warnings) == 1


def test_detect_no_conflicts_for_sequential_tasks():
    """Tasks scheduled back-to-back (one ends exactly when the next starts) should not conflict."""
    owner = make_owner()
    pet = make_pet()
    # Walk ends at 08:30; Feeding starts at 08:30 — touching but not overlapping
    t1 = Task(title="Walk",    duration_minutes=30, priority="high", category="walk",    scheduled_time="08:00")
    t2 = Task(title="Feeding", duration_minutes=10, priority="high", category="feeding", scheduled_time="08:30")
    pet.add_task(t1)
    pet.add_task(t2)
    owner.add_pet(pet)

    warnings = Scheduler(owner=owner).detect_conflicts([t1, t2])
    assert warnings == []


def test_detect_conflicts_ignores_tasks_without_scheduled_time():
    """Tasks with no scheduled_time set should never be flagged as conflicts."""
    owner = make_owner()
    pet = make_pet()
    t1 = Task(title="Play",     duration_minutes=20, priority="medium", category="enrichment")
    t2 = Task(title="Grooming", duration_minutes=15, priority="low",    category="grooming")
    pet.add_task(t1)
    pet.add_task(t2)
    owner.add_pet(pet)

    warnings = Scheduler(owner=owner).detect_conflicts([t1, t2])
    assert warnings == []


# ================================================================== #
# JSON persistence (to_dict / from_dict / save_to_json / load_from_json)
# ================================================================== #

def test_task_to_dict_and_from_dict_round_trip():
    """Serializing a Task to dict and back should produce an identical object."""
    original = Task(
        title="Medication", duration_minutes=5, priority="high",
        category="medication", scheduled_time="08:00", recurrence="daily",
    )
    restored = Task.from_dict(original.to_dict())
    assert restored.title == original.title
    assert restored.duration_minutes == original.duration_minutes
    assert restored.scheduled_time == original.scheduled_time
    assert restored.recurrence == original.recurrence
    assert restored.completed == original.completed


def test_owner_save_and_load_json_preserves_all_data():
    """Saving an Owner to JSON and reloading it should preserve all pets and tasks."""
    owner = Owner(name="Jordan", available_minutes_per_day=90)
    pet = Pet(name="Mochi", species="dog", age=3, health_notes="loves walks")
    pet.add_task(
        Task(title="Walk", duration_minutes=30, priority="high",
             category="walk", scheduled_time="07:30", recurrence="daily")
    )
    owner.add_pet(pet)

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        filepath = f.name
    try:
        owner.save_to_json(filepath)
        loaded = Owner.load_from_json(filepath)

        assert loaded.name == "Jordan"
        assert loaded.available_minutes_per_day == 90
        assert len(loaded.get_pets()) == 1
        loaded_pet = loaded.get_pets()[0]
        assert loaded_pet.name == "Mochi"
        assert loaded_pet.health_notes == "loves walks"
        assert len(loaded_pet.get_tasks()) == 1
        loaded_task = loaded_pet.get_tasks()[0]
        assert loaded_task.title == "Walk"
        assert loaded_task.scheduled_time == "07:30"
        assert loaded_task.recurrence == "daily"
    finally:
        os.unlink(filepath)


def test_owner_load_from_json_restores_completed_status():
    """A completed task should still be marked complete after a save/load cycle."""
    owner = Owner(name="Jordan", available_minutes_per_day=90)
    pet = make_pet()
    task = Task(title="Walk", duration_minutes=30, priority="high", category="walk")
    task.mark_complete()
    pet.add_task(task)
    owner.add_pet(pet)

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        filepath = f.name
    try:
        owner.save_to_json(filepath)
        loaded = Owner.load_from_json(filepath)
        assert loaded.get_pets()[0].get_tasks()[0].completed is True
    finally:
        os.unlink(filepath)


# ================================================================== #
# Scheduler — find_next_slot
# ================================================================== #

def test_find_next_slot_returns_early_gap_before_first_task():
    """If the first timed task starts late, the slot before it should be found."""
    owner = make_owner()
    pet = make_pet()
    pet.add_task(Task(title="Walk", duration_minutes=30, priority="high", category="walk", scheduled_time="10:00"))
    owner.add_pet(pet)

    slot = Scheduler(owner=owner).find_next_slot(20, after_time="00:00")
    assert slot == "00:00"   # huge gap before 10:00


def test_find_next_slot_skips_occupied_windows():
    """The slot finder should skip over occupied time windows and find the next gap."""
    owner = make_owner(minutes=120)
    pet = make_pet()
    # Occupied: 08:00–08:30 and 08:30–08:40
    pet.add_task(Task(title="Walk",    duration_minutes=30, priority="high", category="walk",    scheduled_time="08:00"))
    pet.add_task(Task(title="Feeding", duration_minutes=10, priority="high", category="feeding", scheduled_time="08:30"))
    owner.add_pet(pet)

    # Looking for a 20-min slot after 08:00 — first gap is at 08:40
    slot = Scheduler(owner=owner).find_next_slot(20, after_time="08:00")
    assert slot == "08:40"


def test_find_next_slot_returns_none_when_day_is_full():
    """If the occupied windows run all the way to midnight, return None."""
    owner = make_owner(minutes=1440)
    pet = make_pet()
    # One task that runs from 00:00 to 23:59 (1439 min)
    pet.add_task(Task(title="Marathon", duration_minutes=1439, priority="high", category="other", scheduled_time="00:00"))
    owner.add_pet(pet)

    slot = Scheduler(owner=owner).find_next_slot(5, after_time="00:00")
    assert slot is None
