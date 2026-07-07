"""Terminal testing ground for PawPal+.

Run with:  python main.py

Builds a small owner/pets/tasks example — deliberately adding tasks OUT OF
ORDER — then prints the results through the Scheduler's sorting and filtering
methods so you can eyeball that the logic works without the Streamlit UI.
"""

from pawpal_system import Owner, Pet, Task, Scheduler


def main():
    # --- create pets (tasks added deliberately OUT OF TIME ORDER) -------
    mochi = Pet("Mochi", "dog")
    mochi.add_task(Task("Evening walk", "18:00", duration_minutes=30, priority="medium"))
    mochi.add_task(Task("Morning walk", "08:00", duration_minutes=30, priority="high"))
    mochi.add_task(Task("Grooming", "11:00", duration_minutes=40, priority="low",
                        frequency="weekly"))

    luna = Pet("Luna", "cat")
    luna.add_task(Task("Play", "16:00", duration_minutes=15, priority="medium"))
    luna.add_task(Task("Feed", "07:30", duration_minutes=10, priority="high"))
    # Same 08:00 slot as Mochi's Morning walk — a deliberate clash to show the
    # scheduler catch two tasks scheduled at the same time (across pets here).
    luna.add_task(Task("Vet check", "08:00", duration_minutes=20, priority="high"))

    # --- create owner and attach pets -----------------------------------
    owner = Owner("Jordan", available_minutes=90)
    owner.add_pet(mochi)
    owner.add_pet(luna)

    scheduler = Scheduler(owner)

    print(f"Owner: {owner}")
    for pet in owner.pets:
        print(f"  - {pet}")
    print()

    # --- tasks as entered (unsorted), to show they went in out of order -
    print("Tasks as entered (insertion order, unsorted):")
    for task in scheduler.all_tasks():
        print(f"  {task}")
    print()

    # --- sort_by_time(): the same tasks put back in chronological order --
    print("Sorted by time (scheduler.sort_by_time()):")
    for task in scheduler.sort_by_time():
        print(f"  {task}")
    print()

    # --- filter_tasks(pet_name=...): just one pet's tasks, time-ordered --
    print("Filtered to Mochi's tasks (filter_tasks(pet_name='Mochi')):")
    for task in scheduler.filter_tasks(pet_name="Mochi"):
        print(f"  {task}")
    print()

    # --- filter_tasks(completed=...): by completion status --------------
    scheduler.filter_tasks(pet_name="Luna")[0].mark_complete()  # complete Luna's earliest
    print("Pending tasks (filter_tasks(completed=False)):")
    for task in scheduler.filter_tasks(completed=False):
        print(f"  {task}")
    print()
    print("Completed tasks (filter_tasks(completed=True)):")
    for task in scheduler.filter_tasks(completed=True):
        print(f"  {task}")
    print()

    # --- conflict detection: two tasks at the same time -----------------
    print("Conflict check (scheduler.conflict_warning()):")
    print(scheduler.conflict_warning())
    print()

    # --- a plan that respects the owner's time budget + priority --------
    scheduler.build_plan()
    print(f"Recommended plan (fits {owner.available_minutes} min budget):")
    print(scheduler.explain())
    print()
    print(scheduler.summary())


if __name__ == "__main__":
    main()
