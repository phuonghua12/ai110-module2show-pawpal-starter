"""Tests for PawPal+ core behaviors.

Focus on the behaviors that matter most for a care planner:
- tasks aggregate correctly across pets,
- the schedule is ordered by time of day,
- build_plan respects the time budget and prefers higher priority,
- completion tracking (mark done, reset, summary) works.
"""

import pytest

from pawpal_system import Owner, Pet, Task, Scheduler, PRIORITY_RANK


@pytest.fixture
def owner_with_two_pets():
    """An owner with two pets and a mix of tasks."""
    dog = Pet("Mochi", "dog")
    dog.add_task(Task("Evening walk", "18:00", duration_minutes=30, priority="medium"))
    dog.add_task(Task("Morning walk", "08:00", duration_minutes=30, priority="high"))
    dog.add_task(Task("Meds", "09:00", duration_minutes=5, priority="high"))

    cat = Pet("Luna", "cat")
    cat.add_task(Task("Feed", "07:30", duration_minutes=10, priority="high", frequency="daily"))
    cat.add_task(Task("Groom", "11:00", duration_minutes=40, priority="low", frequency="weekly"))

    owner = Owner("Jordan", available_minutes=120)
    owner.add_pet(dog)
    owner.add_pet(cat)
    return owner


# --- aggregation across pets --------------------------------------------
def test_owner_all_tasks_flattens_across_pets(owner_with_two_pets):
    assert len(owner_with_two_pets.all_tasks()) == 5


def test_scheduler_reads_tasks_through_owner(owner_with_two_pets):
    sched = Scheduler(owner_with_two_pets)
    assert len(sched.all_tasks()) == 5


def test_removing_a_pet_removes_its_tasks(owner_with_two_pets):
    owner = owner_with_two_pets
    luna = owner.pets[1]
    owner.remove_pet(luna)
    assert len(owner.all_tasks()) == 3


# --- ordering ------------------------------------------------------------
def test_daily_schedule_is_ordered_by_time(owner_with_two_pets):
    sched = Scheduler(owner_with_two_pets)
    times = [t.time for t in sched.daily_schedule()]
    assert times == sorted(times)
    assert times[0] == "07:30"  # earliest


def test_priority_rank_orders_by_importance_not_spelling():
    ranked = sorted(["low", "high", "medium"], key=lambda p: -PRIORITY_RANK[p])
    assert ranked == ["high", "medium", "low"]


# --- build_plan: budget + priority --------------------------------------
def test_build_plan_respects_time_budget():
    pet = Pet("Rex", "dog")
    pet.add_task(Task("A", "08:00", duration_minutes=30, priority="high"))
    pet.add_task(Task("B", "09:00", duration_minutes=30, priority="high"))
    pet.add_task(Task("C", "10:00", duration_minutes=30, priority="high"))
    owner = Owner("Sam", available_minutes=60)
    owner.add_pet(pet)
    sched = Scheduler(owner)

    sched.build_plan()
    assert sched.total_minutes <= 60
    assert len(sched.scheduled_tasks) == 2  # only two 30-min tasks fit


def test_build_plan_prefers_higher_priority():
    pet = Pet("Rex", "dog")
    pet.add_task(Task("Low but early", "06:00", duration_minutes=50, priority="low"))
    pet.add_task(Task("High", "12:00", duration_minutes=50, priority="high"))
    owner = Owner("Sam", available_minutes=50)  # only room for one
    owner.add_pet(pet)
    sched = Scheduler(owner)

    sched.build_plan()
    scheduled = [t.description for t in sched.scheduled_tasks]
    skipped = [t.description for t in sched.skipped_tasks]
    assert "High" in scheduled
    assert "Low but early" in skipped


def test_build_plan_output_is_time_ordered():
    pet = Pet("Rex", "dog")
    pet.add_task(Task("Later", "15:00", duration_minutes=10, priority="high"))
    pet.add_task(Task("Earlier", "08:00", duration_minutes=10, priority="high"))
    owner = Owner("Sam", available_minutes=120)
    owner.add_pet(pet)
    sched = Scheduler(owner)

    sched.build_plan()
    times = [t.time for t in sched.scheduled_tasks]
    assert times == sorted(times)


def test_build_plan_skips_completed_tasks():
    pet = Pet("Rex", "dog")
    done = Task("Already fed", "08:00", duration_minutes=10, priority="high")
    done.mark_complete()
    pet.add_task(done)
    pet.add_task(Task("Walk", "09:00", duration_minutes=10, priority="high"))
    owner = Owner("Sam", available_minutes=120)
    owner.add_pet(pet)
    sched = Scheduler(owner)

    sched.build_plan()
    descriptions = [t.description for t in sched.scheduled_tasks]
    assert "Already fed" not in descriptions
    assert "Walk" in descriptions


def test_build_plan_defaults_to_owner_budget():
    pet = Pet("Rex", "dog")
    pet.add_task(Task("Walk", "09:00", duration_minutes=100, priority="high"))
    owner = Owner("Sam", available_minutes=30)  # too small for the 100-min task
    owner.add_pet(pet)
    sched = Scheduler(owner)

    sched.build_plan()  # no explicit budget -> uses owner.available_minutes
    assert sched.scheduled_tasks == []
    assert len(sched.skipped_tasks) == 1


# --- completion tracking -------------------------------------------------
def test_mark_complete_and_summary(owner_with_two_pets):
    sched = Scheduler(owner_with_two_pets)
    sched.all_tasks()[0].mark_complete()
    assert "1/5" in sched.summary()


def test_reset_daily_tasks_only_resets_daily(owner_with_two_pets):
    sched = Scheduler(owner_with_two_pets)
    for t in sched.all_tasks():
        t.mark_complete()
    sched.reset_daily_tasks()
    # weekly "Groom" stays complete; daily ones are reset
    still_done = [t.description for t in sched.completed_tasks()]
    assert still_done == ["Groom"]


def test_explain_reports_scheduled_and_skipped():
    pet = Pet("Rex", "dog")
    pet.add_task(Task("Keep", "08:00", duration_minutes=10, priority="high"))
    pet.add_task(Task("Drop", "09:00", duration_minutes=100, priority="low"))
    owner = Owner("Sam", available_minutes=20)
    owner.add_pet(pet)
    sched = Scheduler(owner)

    sched.build_plan()
    text = sched.explain()
    assert "Keep" in text
    assert "skipped Drop" in text
