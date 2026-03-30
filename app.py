import streamlit as st
from pawpal_system import Owner, Pet, Task, Scheduler

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")
st.caption("Your daily pet care planner — add pets, build a task list, and generate a smart schedule.")

st.divider()

# ------------------------------------------------------------------ #
# Session state bootstrap
# ------------------------------------------------------------------ #
# Streamlit reruns this file top-to-bottom on every interaction.
# We keep the Owner object in st.session_state so it (and all the
# pets / tasks attached to it) survives each rerun.
if "owner" not in st.session_state:
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
    # Carry any pets already registered so they aren't lost on an update
    previous_pets = existing_owner.get_pets() if existing_owner else []
    st.session_state.owner = Owner(
        name=owner_name,
        available_minutes_per_day=int(available_mins),
    )
    for pet in previous_pets:
        st.session_state.owner.add_pet(pet)
    st.success(f"Owner profile saved for **{owner_name}** ({available_mins} min/day).")

# Nothing below this point makes sense without an owner — stop early.
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
        with col2:
            selected_pet_name = st.selectbox("Assign to pet", pet_names)
            priority = st.selectbox("Priority", ["low", "medium", "high"], index=2)
            category = st.selectbox(
                "Category",
                ["walk", "feeding", "medication", "grooming", "enrichment", "other"],
            )
        add_task_btn = st.form_submit_button("Add Task")

    if add_task_btn:
        target_pet = next(p for p in pets if p.name == selected_pet_name)
        target_pet.add_task(
            Task(
                title=task_title,
                duration_minutes=int(duration),
                priority=priority,
                category=category,
            )
        )
        st.success(f"**{task_title}** added to {selected_pet_name}!")

    # Display all tasks across every pet
    all_rows = []
    for pet in pets:
        for task in pet.get_tasks():
            all_rows.append(
                {
                    "Pet": pet.name,
                    "Task": task.title,
                    "Duration (min)": task.duration_minutes,
                    "Priority": task.priority,
                    "Category": task.category,
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
        st.warning("No tasks could be scheduled. Check that tasks aren't all marked complete or exceed your time budget.")
    else:
        st.success(f"Scheduled **{len(schedule)}** task(s) out of {total_tasks} total.")
        st.code(scheduler.explain_plan(schedule), language=None)

if total_tasks == 0:
    st.info("Add tasks in Section 3 to enable scheduling.")
