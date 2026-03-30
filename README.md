# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

## Smarter Scheduling

Beyond the basic priority-based scheduler, PawPal+ includes several algorithmic improvements in `pawpal_system.py`:

**Sort by time of day** — `Scheduler.sort_by_time(tasks)` orders any task list by `scheduled_time` (stored as `"HH:MM"`). It uses Python's `sorted()` with a lambda key that converts the string to minutes-since-midnight, so `"07:30"` correctly comes before `"17:00"`. Tasks with no scheduled time are pushed to the end (key returns `9999`).

**Flexible filtering** — `Scheduler.filter_tasks(pet_name, completed)` lets you slice the full task list by pet, by completion status, or both at once. Useful for quickly checking what's still pending for a specific animal.

**Recurring tasks** — `Task` now has a `recurrence` field (`"daily"` or `"weekly"`). Calling `Scheduler.complete_task(task, pet)` marks the task done and uses Python's `timedelta` to calculate the next due date, then automatically creates a fresh copy of the task and attaches it to the same pet.

**Conflict detection** — `Scheduler.detect_conflicts(schedule)` checks every pair of timed tasks for overlapping intervals using the condition `start_a < end_b and start_b < end_a`. It returns a list of plain-English warning strings instead of raising an exception, so the app stays usable even when the schedule has problems.

## Testing PawPal+

Run the full test suite with:

```bash
python -m pytest
```

Or for a detailed view of each test name:

```bash
python -m pytest tests/ -v
```

The suite lives in `tests/test_pawpal.py` and currently contains **21 tests** covering:

| Area | What's tested |
|---|---|
| Task | `mark_complete()` changes status; new tasks start incomplete |
| Pet | Adding tasks increases count; `get_tasks()` returns a copy, not a reference |
| Schedule generation | Respects time budget; skips completed tasks; orders by priority; handles empty pets/owners |
| Sort by time | Correct chronological order; untimed tasks go last |
| Filtering | By pet name; by completion status |
| Recurring tasks | Daily → next occurrence in 1 day; weekly → 7 days; non-recurring → returns `None` |
| Conflict detection | Overlapping tasks flagged; exact same start time flagged; back-to-back tasks not flagged; tasks with no time ignored |

**Confidence level: ★★★★☆ (4/5)**

The core scheduling logic — priority ordering, time budgeting, recurrence, and conflict detection — is thoroughly tested. The one gap is the Streamlit UI layer (`app.py`), which isn't covered by automated tests. Session state behavior and form interactions would need end-to-end testing tools (like Playwright or Streamlit's own testing utilities) to verify fully.
