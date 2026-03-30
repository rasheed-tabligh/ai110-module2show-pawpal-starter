"""
main.py — PawPal+ CLI demo

Run this file to verify the backend logic works before connecting it to the UI:
    python main.py
"""

from pawpal_system import Owner, Pet, Task, Scheduler


def section(title: str) -> None:
    """Print a clearly labelled section header."""
    print(f"\n{'=' * 52}")
    print(f"  {title}")
    print(f"{'=' * 52}")


def main():
    # ------------------------------------------------------------------ #
    # 1. Set up the owner
    # ------------------------------------------------------------------ #
    jordan = Owner(
        name="Jordan",
        available_minutes_per_day=90,
        preferences=["morning walks", "no late medications"],
    )

    # ------------------------------------------------------------------ #
    # 2. Create two pets and register them with the owner
    # ------------------------------------------------------------------ #
    mochi = Pet(name="Mochi", species="dog", age=3)
    luna = Pet(name="Luna", species="cat", age=5, health_notes="Needs daily medication")

    jordan.add_pet(mochi)
    jordan.add_pet(luna)

    # ------------------------------------------------------------------ #
    # 3. Add tasks — intentionally out of time order to test sort_by_time
    #    Some tasks have a scheduled_time; some are flexible (no time set).
    #    Medication is marked "daily" recurring.
    # ------------------------------------------------------------------ #
    mochi.add_task(Task(title="Evening walk",    duration_minutes=25, priority="medium", category="walk",        scheduled_time="17:00"))
    mochi.add_task(Task(title="Morning walk",    duration_minutes=30, priority="high",   category="walk",        scheduled_time="07:30"))
    mochi.add_task(Task(title="Breakfast",       duration_minutes=10, priority="high",   category="feeding",     scheduled_time="08:00"))
    mochi.add_task(Task(title="Play fetch",      duration_minutes=20, priority="medium", category="enrichment"))
    mochi.add_task(Task(title="Brush coat",      duration_minutes=15, priority="low",    category="grooming"))

    luna.add_task(Task(title="Medication",       duration_minutes=5,  priority="high",   category="medication",  scheduled_time="08:30", recurrence="daily"))
    luna.add_task(Task(title="Feeding",          duration_minutes=10, priority="high",   category="feeding",     scheduled_time="08:15"))
    luna.add_task(Task(title="Laser toy session",duration_minutes=15, priority="low",    category="enrichment"))

    scheduler = Scheduler(owner=jordan)

    # ------------------------------------------------------------------ #
    # 4. Generate and display the priority-based daily schedule
    # ------------------------------------------------------------------ #
    section("Priority-Based Daily Schedule")
    schedule = scheduler.generate_schedule()
    print(scheduler.explain_plan(schedule))

    # ------------------------------------------------------------------ #
    # 5. Sort the scheduled tasks by their wall-clock time
    #    (tasks without a scheduled_time go to the end)
    # ------------------------------------------------------------------ #
    section("Schedule Sorted by Time of Day")
    timed_schedule = scheduler.sort_by_time(schedule)
    for task in timed_schedule:
        time_label = f"@ {task.scheduled_time}" if task.scheduled_time else "(flexible)"
        print(f"  {time_label:<12}  {task.title}  ({task.duration_minutes} min | {task.priority})")

    # ------------------------------------------------------------------ #
    # 6. Filter tasks by pet name
    # ------------------------------------------------------------------ #
    section("Filter: Mochi's Tasks Only")
    for task in scheduler.filter_tasks(pet_name="Mochi"):
        status = "done" if task.completed else "pending"
        print(f"  [{status}]  {task.title}")

    # ------------------------------------------------------------------ #
    # 7. Recurring task — complete Luna's daily medication and verify
    #    that the next occurrence is automatically created
    # ------------------------------------------------------------------ #
    section("Recurring Task: Complete Luna's Daily Medication")
    med_task = next(t for t in luna.get_tasks() if t.title == "Medication")
    next_med = scheduler.complete_task(med_task, luna)

    print(f"  Completed: '{med_task.title}' — status: {med_task.completed}")
    if next_med:
        print(f"  Next occurrence created: '{next_med.title}' due {next_med.due_date} (recurs {next_med.recurrence})")

    # Filter completed tasks to confirm
    print()
    print("  Pending tasks for Luna:")
    for task in scheduler.filter_tasks(pet_name="Luna", completed=False):
        print(f"    • {task.title} (due: {task.due_date or 'today'})")

    # ------------------------------------------------------------------ #
    # 8. Conflict detection — add two tasks that overlap in time
    #    Expected: Scheduler flags the overlap without crashing
    # ------------------------------------------------------------------ #
    section("Conflict Detection")
    # Add a task that deliberately clashes with Mochi's Breakfast (08:00, 10 min → ends 08:10)
    conflicting = Task(
        title="Vet call",
        duration_minutes=20,
        priority="high",
        category="other",
        scheduled_time="08:05",   # starts at 08:05 while Breakfast runs 08:00–08:10
    )
    mochi.add_task(conflicting)

    full_schedule = scheduler.generate_schedule()
    conflicts = scheduler.detect_conflicts(full_schedule)

    if conflicts:
        print("  Warnings detected:")
        for warning in conflicts:
            print(f"    ⚠  {warning}")
    else:
        print("  No conflicts found.")

    # ------------------------------------------------------------------ #
    # 9. Regenerate final schedule (medication is now complete, conflict visible)
    # ------------------------------------------------------------------ #
    section("Final Schedule After Updates")
    final_schedule = scheduler.sort_by_time(scheduler.generate_schedule())
    for task in final_schedule:
        time_label = f"@ {task.scheduled_time}" if task.scheduled_time else "(flexible)"
        print(f"  {time_label:<12}  {task.title}  ({task.duration_minutes} min | {task.priority})")


if __name__ == "__main__":
    main()
