import os
import streamlit as st
from pawpal_system import Owner, Pet, Task, Scheduler

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")
st.caption("Your daily pet care planner — add pets, build a task list, and generate a smart schedule.")

st.divider()

# ------------------------------------------------------------------ #
# Constants
# ------------------------------------------------------------------ #
DATA_FILE = "data.json"

CATEGORY_EMOJI = {
    "walk":        "🦮",
    "feeding":     "🍽️",
    "medication":  "💊",
    "grooming":    "✂️",
    "enrichment":  "🎾",
    "other":       "📋",
}

PRIORITY_EMOJI = {
    "high":   "🔴",
    "medium": "🟡",
    "low":    "🟢",
}


def priority_label(p: str) -> str:
    """Return an emoji-prefixed priority string for display."""
    return f"{PRIORITY_EMOJI.get(p, '')} {p}"


def category_label(c: str) -> str:
    """Return an emoji-prefixed category string for display."""
    return f"{CATEGORY_EMOJI.get(c, '')} {c}"


# ------------------------------------------------------------------ #
# Session state bootstrap
# ------------------------------------------------------------------ #
# Streamlit reruns this file top-to-bottom on every interaction.
# We keep the Owner object in st.session_state so it (and all the
# pets / tasks attached to it) survives each rerun.
# On the very first run we try to restore from data.json so the user
# never loses their data when they close and reopen the tab.
if "owner" not in st.session_state:
    if os.path.exists(DATA_FILE):
        try:
            st.session_state.owner = Owner.load_from_json(DATA_FILE)
        except Exception:
            st.session_state.owner = None
    else:
        st.session_state.owner = None

# ------------------------------------------------------------------ #
# Section 1 — Owner Setup
# ------------------------------------------------------------------ #
st.subheader("1. Owner Setup")

existing_owner = st.session_state.owner
with st.form("owner_form"):
    owner_name = st.text_input(
        "Your name",
        value=existing_owner.name if existing_owner else "Jordan",
    )
    available_mins = st.number_input(
        "Available minutes per day",
        min_value=10,
        max_value=480,
        value=existing_owner.available_minutes_per_day if existing_owner else 90,
    )
    save_owner = st.form_submit_button("Save Owner")

if save_owner:
    previous_pets = existing_owner.get_pets() if existing_owner else []
    st.session_state.owner = Owner(
        name=owner_name,
        available_minutes_per_day=int(available_mins),
    )
    for pet in previous_pets:
        st.session_state.owner.add_pet(pet)
    st.session_state.owner.save_to_json(DATA_FILE)
    st.success(f"Owner profile saved for **{owner_name}** ({available_mins} min/day).")

if st.session_state.owner is None:
    st.info("Fill in your owner profile above to get started.")
    st.stop()

owner: Owner = st.session_state.owner

# ------------------------------------------------------------------ #
# Section 2 — Pets
# ------------------------------------------------------------------ #
st.divider()
st.subheader("2. Your Pets")

with st.form("add_pet_form"):
    col1, col2, col3 = st.columns(3)
    with col1:
        pet_name = st.text_input("Pet name", value="Mochi")
    with col2:
        species = st.selectbox("Species", ["dog", "cat", "other"])
    with col3:
        age = st.number_input("Age (years)", min_value=0, max_value=30, value=3)
    health_notes = st.text_input("Health notes (optional)", placeholder="e.g. needs daily medication")
    add_pet_btn = st.form_submit_button("Add Pet")

if add_pet_btn:
    owner.add_pet(
        Pet(name=pet_name, species=species, age=int(age), health_notes=health_notes)
    )
    owner.save_to_json(DATA_FILE)
    st.success(f"**{pet_name}** added!")

pets = owner.get_pets()
if pets:
    pet_summary = [
        {"Name": p.name, "Species": p.species, "Age": p.age, "Health notes": p.health_notes or "—"}
        for p in pets
    ]
    st.dataframe(pet_summary, use_container_width=True, hide_index=True)
else:
    st.info("No pets yet. Add one above.")

# ------------------------------------------------------------------ #
# Section 3 — Tasks
# ------------------------------------------------------------------ #
st.divider()
st.subheader("3. Care Tasks")

if not pets:
    st.warning("Add at least one pet before adding tasks.")
else:
    pet_names = [p.name for p in pets]

    with st.form("add_task_form"):
        col1, col2 = st.columns(2)
        with col1:
            task_title = st.text_input("Task title", value="Morning walk")
            duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
            task_time = st.text_input("Scheduled time (optional)", placeholder="e.g. 08:30")
        with col2:
            selected_pet_name = st.selectbox("Assign to pet", pet_names)
            priority = st.selectbox("Priority", ["low", "medium", "high"], index=2)
            category = st.selectbox(
                "Category",
                ["walk", "feeding", "medication", "grooming", "enrichment", "other"],
            )
            recurrence_input = st.selectbox("Recurrence", ["none", "daily", "weekly"])
        add_task_btn = st.form_submit_button("Add Task")

    if add_task_btn:
        raw_time = task_time.strip()
        if raw_time and not (len(raw_time) == 5 and raw_time[2] == ":"):
            st.warning(f"'{raw_time}' is not a valid time — use HH:MM (e.g. 08:30). Time was not saved.")
            raw_time = ""
        target_pet = next(p for p in pets if p.name == selected_pet_name)
        target_pet.add_task(
            Task(
                title=task_title,
                duration_minutes=int(duration),
                priority=priority,
                category=category,
                scheduled_time=raw_time,
                recurrence="" if recurrence_input == "none" else recurrence_input,
            )
        )
        owner.save_to_json(DATA_FILE)
        st.success(f"**{task_title}** added to {selected_pet_name}!")

    # Display all tasks with emoji labels
    all_rows = []
    for pet in pets:
        for task in pet.get_tasks():
            all_rows.append(
                {
                    "Pet": pet.name,
                    "Task": task.title,
                    "Time": task.scheduled_time or "—",
                    "Duration (min)": task.duration_minutes,
                    "Priority": priority_label(task.priority),
                    "Category": category_label(task.category),
                    "Recurrence": task.recurrence or "—",
                    "Done": "✓" if task.completed else "",
                }
            )
    if all_rows:
        st.dataframe(all_rows, use_container_width=True, hide_index=True)
    else:
        st.info("No tasks yet. Add one above.")

# ------------------------------------------------------------------ #
# Section 4 — Generate Schedule
# ------------------------------------------------------------------ #
st.divider()
st.subheader("4. Generate Daily Schedule")

total_tasks = sum(len(p.get_tasks()) for p in owner.get_pets())
st.caption(
    f"Owner: **{owner.name}** · Time budget: **{owner.available_minutes_per_day} min** · Tasks on file: **{total_tasks}**"
)

if st.button("Generate Schedule", type="primary", disabled=total_tasks == 0):
    scheduler = Scheduler(owner=owner)
    schedule = scheduler.generate_schedule()

    if not schedule:
        st.warning(
            "No tasks could be scheduled. "
            "Check that tasks aren't all marked complete or that each task fits within your time budget."
        )
    else:
        # ---- Conflict warnings ----------------------------------------
        conflicts = scheduler.detect_conflicts(schedule)
        if conflicts:
            st.markdown("**⚠️ Schedule Conflicts Detected**")
            for warning in conflicts:
                st.warning(warning)

        # ---- Success summary ------------------------------------------
        time_used = sum(t.duration_minutes for t in schedule)
        st.success(
            f"Scheduled **{len(schedule)}** task(s) — "
            f"**{time_used}** of **{owner.available_minutes_per_day}** min used."
        )

        # ---- Schedule table sorted by time with emoji labels ----------
        timed_schedule = scheduler.sort_by_time(schedule)
        task_pet_map = {
            id(t): p.name
            for p in owner.get_pets()
            for t in p.get_tasks()
        }
        schedule_rows = [
            {
                "Time": t.scheduled_time or "flexible",
                "Task": t.title,
                "Duration (min)": t.duration_minutes,
                "Priority": priority_label(t.priority),
                "Pet": task_pet_map.get(id(t), "?"),
                "Category": category_label(t.category),
            }
            for t in timed_schedule
        ]
        st.dataframe(schedule_rows, use_container_width=True, hide_index=True)

        # ---- Skipped tasks --------------------------------------------
        all_incomplete = [t for t in scheduler.get_all_tasks() if not t.completed]
        scheduled_ids = {id(t) for t in schedule}
        skipped = [t for t in all_incomplete if id(t) not in scheduled_ids]
        if skipped:
            with st.expander(f"Skipped tasks ({len(skipped)}) — not enough time remaining"):
                for t in skipped:
                    st.caption(
                        f"{PRIORITY_EMOJI.get(t.priority, '')} {t.title} "
                        f"({t.duration_minutes} min | {t.priority})"
                    )

        # ---- Find Next Slot tool -------------------------------------
        st.divider()
        with st.expander("🔍 Find the next available slot"):
            st.caption(
                "Enter a duration to find the earliest gap in your timed schedule "
                "where a new task of that length would fit."
            )
            col1, col2 = st.columns(2)
            with col1:
                slot_duration = st.number_input(
                    "Task duration (min)", min_value=1, max_value=240, value=15, key="slot_dur"
                )
            with col2:
                after_time = st.text_input(
                    "Search after (HH:MM)", value="00:00", key="slot_after"
                )
            if st.button("Find Slot", key="find_slot_btn"):
                slot = scheduler.find_next_slot(int(slot_duration), after_time)
                if slot:
                    st.success(
                        f"Next available: **{slot}** — a {slot_duration}-min task would fit here."
                    )
                else:
                    st.warning("No available slot found in the remaining day.")

if total_tasks == 0:
    st.info("Add tasks in Section 3 to enable scheduling.")
