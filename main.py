"""
main.py — PawPal+ CLI demo

Run this file to verify the backend logic works before connecting it to the UI:
    python main.py
"""

from pawpal_system import Owner, Pet, Task, Scheduler


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
    # 3. Add tasks to Mochi (dog)
    # ------------------------------------------------------------------ #
    mochi.add_task(Task(title="Morning walk",    duration_minutes=30, priority="high",   category="walk"))
    mochi.add_task(Task(title="Breakfast",       duration_minutes=10, priority="high",   category="feeding"))
    mochi.add_task(Task(title="Evening walk",    duration_minutes=25, priority="medium", category="walk"))
    mochi.add_task(Task(title="Play fetch",      duration_minutes=20, priority="medium", category="enrichment"))
    mochi.add_task(Task(title="Brush coat",      duration_minutes=15, priority="low",    category="grooming"))

    # ------------------------------------------------------------------ #
    # 4. Add tasks to Luna (cat)
    # ------------------------------------------------------------------ #
    luna.add_task(Task(title="Medication",       duration_minutes=5,  priority="high",   category="medication"))
    luna.add_task(Task(title="Feeding",          duration_minutes=10, priority="high",   category="feeding"))
    luna.add_task(Task(title="Laser toy session",duration_minutes=15, priority="low",    category="enrichment"))

    # ------------------------------------------------------------------ #
    # 5. Run the scheduler and print the plan
    # ------------------------------------------------------------------ #
    scheduler = Scheduler(owner=jordan)
    schedule = scheduler.generate_schedule()

    print()
    print(scheduler.explain_plan(schedule))

    # ------------------------------------------------------------------ #
    # 6. Quick demo: filter by priority
    # ------------------------------------------------------------------ #
    print()
    print("High-priority tasks only:")
    print("-" * 32)
    for task in scheduler.filter_by_priority("high"):
        print(f"  • {task.title} ({task.duration_minutes} min)")

    # ------------------------------------------------------------------ #
    # 7. Mark one task complete and regenerate to see the difference
    # ------------------------------------------------------------------ #
    print()
    print("Marking 'Morning walk' as complete and regenerating...")
    for task in mochi.get_tasks():
        if task.title == "Morning walk":
            task.mark_complete()

    updated_schedule = scheduler.generate_schedule()
    print()
    print(scheduler.explain_plan(updated_schedule))


if __name__ == "__main__":
    main()
