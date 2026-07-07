from datetime import time

import streamlit as st

from pawpal_system import Owner, Pet, Task, Scheduler

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")

st.markdown(
    """
Welcome to **PawPal+** — add an owner, their pets, and care tasks, then generate a
daily plan that fits the owner's available time and prioritizes the important tasks.
"""
)

with st.expander("Scenario", expanded=True):
    st.markdown(
        """
**PawPal+** is a pet care planning assistant. It helps a pet owner plan care tasks
for their pet(s) based on constraints like time, priority, and preferences.

You will design and implement the scheduling logic and connect it to this Streamlit UI.
"""
    )

with st.expander("What you need to build", expanded=True):
    st.markdown(
        """
At minimum, your system should:
- Represent pet care tasks (what needs to happen, how long it takes, priority)
- Represent the pet and the owner (basic info and preferences)
- Build a plan/schedule for a day that chooses and orders tasks based on constraints
- Explain the plan (why each task was chosen and when it happens)
"""
    )

st.divider()

# --- persist the Owner in the session "vault" -------------------------------
# Create the Owner once (first run only); on later reruns reuse the same
# instance so its pets and tasks accumulate instead of resetting.
if "owner" not in st.session_state:
    st.session_state.owner = Owner("Jordan")
owner = st.session_state.owner

# --- owner details ----------------------------------------------------------
st.subheader("Owner")
owner.name = st.text_input("Owner name", value=owner.name)
owner.available_minutes = st.number_input(
    "Time available for care today (minutes)",
    min_value=1, max_value=1440, value=owner.available_minutes,
)

# --- add a pet --------------------------------------------------------------
st.subheader("Pets")
pcol1, pcol2 = st.columns(2)
with pcol1:
    new_pet_name = st.text_input("Pet name", value="Mochi")
with pcol2:
    new_pet_species = st.selectbox("Species", ["dog", "cat", "other"])

if st.button("Add pet"):
    if new_pet_name.strip():
        owner.add_pet(Pet(new_pet_name.strip(), new_pet_species))
    else:
        st.warning("Please enter a pet name.")

if owner.pets:
    for pet in owner.pets:
        st.write(f"- {pet}")
else:
    st.info("No pets yet. Add one above.")

# --- add a task to a pet ----------------------------------------------------
st.subheader("Tasks")
if owner.pets:
    target_pet_name = st.selectbox("Add task to", [p.name for p in owner.pets])

    tcol1, tcol2, tcol3 = st.columns(3)
    with tcol1:
        task_desc = st.text_input("Task", value="Morning walk")
    with tcol2:
        task_time = st.time_input("Time", value=time(8, 0))
    with tcol3:
        task_duration = st.number_input("Duration (min)", min_value=1, max_value=240, value=20)

    tcol4, tcol5 = st.columns(2)
    with tcol4:
        task_priority = st.selectbox("Priority", ["low", "medium", "high"], index=1)
    with tcol5:
        task_frequency = st.selectbox("Frequency", ["daily", "weekly", "monthly"])

    if st.button("Add task"):
        target_pet = next(p for p in owner.pets if p.name == target_pet_name)
        target_pet.add_task(
            Task(
                task_desc,
                task_time.strftime("%H:%M"),
                duration_minutes=int(task_duration),
                priority=task_priority,
                frequency=task_frequency,
            )
        )
else:
    st.caption("Add a pet first, then you can give it tasks.")

# --- show all tasks across pets, ordered by time ----------------------------
rows = [
    {
        "time": t.time,
        "pet": pet.name,
        "task": t.description,
        "min": t.duration_minutes,
        "priority": t.priority,
        "frequency": t.frequency,
        "done": t.completed,
    }
    for pet in owner.pets
    for t in pet.tasks
]
rows.sort(key=lambda r: r["time"])
if rows:
    st.write("All tasks (by time):")
    st.table(rows)

st.divider()

# --- generate the plan ------------------------------------------------------
st.subheader("Build Schedule")
if st.button("Generate schedule"):
    if not owner.all_tasks():
        st.warning("No tasks to schedule yet. Add a pet and some tasks first.")
    else:
        scheduler = Scheduler(owner)
        scheduler.build_plan()  # uses owner.available_minutes
        st.text(scheduler.explain())
        st.caption(scheduler.summary())

        conflicts = scheduler.find_conflicts()
        if conflicts:
            for earlier, later in conflicts:
                st.warning(f"⚠ {scheduler.describe_conflict(earlier, later)}")
