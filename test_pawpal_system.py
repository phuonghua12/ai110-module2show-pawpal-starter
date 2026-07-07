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


# --- simple unit tests ---------------------------------------------------
def test_mark_complete_changes_status():
    """Calling mark_complete() flips a task from not-done to done."""
    task = Task("Feed", "08:00")
    assert task.completed is False  # starts incomplete
    task.mark_complete()
    assert task.completed is True


def test_adding_task_increases_pet_task_count():
    """Adding a task to a Pet increases that pet's task count by one."""
    pet = Pet("Mochi", "dog")
    assert len(pet.tasks) == 0
    pet.add_task(Task("Walk", "08:00"))
    assert len(pet.tasks) == 1


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


def test_sort_by_time_orders_all_tasks(owner_with_two_pets):
    sched = Scheduler(owner_with_two_pets)
    times = [t.time for t in sched.sort_by_time()]
    assert times == sorted(times)
    assert times[0] == "07:30"  # earliest across both pets


def test_sort_by_time_accepts_a_subset_and_is_non_destructive():
    early = Task("Early", "08:00", priority="high")
    late = Task("Late", "15:00", priority="high")
    subset = [late, early]
    sched = Scheduler(Owner("Sam"))

    ordered = sched.sort_by_time(subset)
    assert [t.description for t in ordered] == ["Early", "Late"]
    assert subset == [late, early]  # original list untouched


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


# --- filtering by pet / status / frequency ------------------------------
def test_filter_tasks_by_pet(owner_with_two_pets):
    sched = Scheduler(owner_with_two_pets)
    luna = owner_with_two_pets.pets[1]
    descriptions = [t.description for t in sched.filter_tasks(pet=luna)]
    assert descriptions == ["Feed", "Groom"]  # only Luna's, time-ordered


def test_filter_tasks_by_status(owner_with_two_pets):
    sched = Scheduler(owner_with_two_pets)
    sched.all_tasks()[0].mark_complete()  # a daily task -> spawns its next run
    assert len(sched.filter_tasks(completed=True)) == 1
    # 4 originally-pending tasks + the freshly spawned next occurrence
    assert len(sched.filter_tasks(completed=False)) == 5


def test_filter_tasks_by_pet_name(owner_with_two_pets):
    sched = Scheduler(owner_with_two_pets)
    descriptions = [t.description for t in sched.filter_tasks(pet_name="Luna")]
    assert descriptions == ["Feed", "Groom"]  # only Luna's, time-ordered


def test_filter_tasks_unknown_pet_name_returns_empty(owner_with_two_pets):
    sched = Scheduler(owner_with_two_pets)
    assert sched.filter_tasks(pet_name="Nobody") == []


def test_filter_tasks_by_pet_name_and_status(owner_with_two_pets):
    sched = Scheduler(owner_with_two_pets)
    # complete Luna's "Feed"; her "Groom" stays pending
    luna = owner_with_two_pets.pets[1]
    next(t for t in luna.tasks if t.description == "Feed").mark_complete()
    pending = [t.description for t in sched.filter_tasks(pet_name="Luna", completed=False)]
    # completing daily "Feed" spawns its next occurrence, which is pending again
    assert pending == ["Feed", "Groom"]


def test_filter_tasks_combines_pet_and_frequency(owner_with_two_pets):
    sched = Scheduler(owner_with_two_pets)
    luna = owner_with_two_pets.pets[1]
    daily = [t.description for t in sched.filter_tasks(pet=luna, frequency="daily")]
    assert daily == ["Feed"]  # Luna's weekly "Groom" is excluded


def test_filter_tasks_is_time_ordered(owner_with_two_pets):
    sched = Scheduler(owner_with_two_pets)
    times = [t.time for t in sched.filter_tasks()]
    assert times == sorted(times)


# --- time-window math (datetime / timedelta) ----------------------------
def test_end_time_adds_duration():
    task = Task("Walk", "08:00", duration_minutes=30)
    assert task.end_time() == "08:30"


def test_end_time_rolls_past_the_hour():
    task = Task("Long play", "08:45", duration_minutes=30)
    assert task.end_time() == "09:15"  # crosses the hour boundary cleanly


def test_end_time_rolls_past_midnight():
    task = Task("Late walk", "23:30", duration_minutes=60)
    assert task.end_time() == "00:30"  # timedelta wraps into the next day


def test_invalid_time_string_is_rejected():
    with pytest.raises(ValueError):
        Task("Bad", "25:00").end_time()  # strptime validates the "HH:MM" input


# --- conflict detection --------------------------------------------------
def test_find_conflicts_detects_overlap():
    pet = Pet("Rex", "dog")
    pet.add_task(Task("Walk", "08:00", duration_minutes=30, priority="high"))
    pet.add_task(Task("Vet call", "08:15", duration_minutes=20, priority="high"))
    owner = Owner("Sam")
    owner.add_pet(pet)
    sched = Scheduler(owner)

    conflicts = sched.find_conflicts()
    assert len(conflicts) == 1
    earlier, later = conflicts[0]
    assert (earlier.description, later.description) == ("Walk", "Vet call")


def test_find_conflicts_ignores_touching_edges():
    pet = Pet("Rex", "dog")
    pet.add_task(Task("Walk", "08:00", duration_minutes=30, priority="high"))
    pet.add_task(Task("Feed", "08:30", duration_minutes=10, priority="high"))
    owner = Owner("Sam")
    owner.add_pet(pet)
    sched = Scheduler(owner)

    assert sched.find_conflicts() == []  # 08:30 starts exactly when walk ends


def test_find_conflicts_spans_multiple_pets():
    dog = Pet("Rex", "dog")
    dog.add_task(Task("Walk", "08:00", duration_minutes=30, priority="high"))
    cat = Pet("Luna", "cat")
    cat.add_task(Task("Feed", "08:10", duration_minutes=10, priority="high"))
    owner = Owner("Sam")
    owner.add_pet(dog)
    owner.add_pet(cat)
    sched = Scheduler(owner)

    assert len(sched.find_conflicts()) == 1  # can't walk dog and feed cat at once


def test_same_pet_conflict_is_classified():
    pet = Pet("Mochi", "dog")
    pet.add_task(Task("Walk", "08:00", duration_minutes=30, priority="high"))
    pet.add_task(Task("Vet call", "08:15", duration_minutes=20, priority="high"))
    owner = Owner("Sam")
    owner.add_pet(pet)
    sched = Scheduler(owner)

    assert len(sched.same_pet_conflicts()) == 1
    assert sched.cross_pet_conflicts() == []


def test_cross_pet_conflict_is_classified():
    dog = Pet("Mochi", "dog")
    dog.add_task(Task("Walk", "08:00", duration_minutes=30, priority="high"))
    cat = Pet("Luna", "cat")
    cat.add_task(Task("Feed", "08:10", duration_minutes=10, priority="high"))
    owner = Owner("Sam")
    owner.add_pet(dog)
    owner.add_pet(cat)
    sched = Scheduler(owner)

    assert len(sched.cross_pet_conflicts()) == 1
    assert sched.same_pet_conflicts() == []


def test_describe_conflict_names_pets():
    dog = Pet("Mochi", "dog")
    walk = Task("Walk", "08:00", duration_minutes=30, priority="high")
    dog.add_task(walk)
    cat = Pet("Luna", "cat")
    feed = Task("Feed", "08:10", duration_minutes=10, priority="high")
    cat.add_task(feed)
    owner = Owner("Sam")
    owner.add_pet(dog)
    owner.add_pet(cat)
    sched = Scheduler(owner)

    text = sched.describe_conflict(walk, feed)
    assert "Mochi's" in text and "Luna's" in text  # cross-pet names both owners

    # same-pet form names the pet once
    other = Task("Vet call", "08:05", duration_minutes=10, priority="high")
    dog.add_task(other)
    assert sched.describe_conflict(walk, other).startswith("Mochi:")


def test_find_conflicts_ignores_completed_tasks():
    pet = Pet("Rex", "dog")
    # monthly so completing it does NOT spawn a same-time successor
    done = Task("Vet visit", "08:00", duration_minutes=30, priority="high", frequency="monthly")
    pet.add_task(done)
    pet.add_task(Task("Vet call", "08:15", duration_minutes=20, priority="high"))
    owner = Owner("Sam")
    owner.add_pet(pet)
    sched = Scheduler(owner)

    assert len(sched.find_conflicts()) == 1  # the two pending tasks clash
    done.mark_complete()  # once done, it's no longer competing for time
    assert sched.find_conflicts() == []


def test_conflict_warning_all_clear():
    pet = Pet("Rex", "dog")
    pet.add_task(Task("Walk", "08:00", duration_minutes=30, priority="high"))
    pet.add_task(Task("Feed", "09:00", duration_minutes=10, priority="high"))
    owner = Owner("Sam")
    owner.add_pet(pet)
    sched = Scheduler(owner)

    assert "No scheduling conflicts" in sched.conflict_warning()


def test_conflict_warning_reports_overlap():
    pet = Pet("Rex", "dog")
    pet.add_task(Task("Walk", "08:00", duration_minutes=30, priority="high"))
    pet.add_task(Task("Vet call", "08:15", duration_minutes=20, priority="high"))
    owner = Owner("Sam")
    owner.add_pet(pet)
    sched = Scheduler(owner)

    msg = sched.conflict_warning()
    assert "⚠" in msg and "overlaps" in msg


def test_conflict_warning_does_not_crash_on_bad_time():
    pet = Pet("Rex", "dog")
    pet.add_task(Task("Good", "08:00", duration_minutes=30, priority="high"))
    pet.add_task(Task("Bad", "25:99", duration_minutes=10, priority="high"))  # invalid
    owner = Owner("Sam")
    owner.add_pet(pet)
    sched = Scheduler(owner)

    # find_conflicts() would raise ValueError here; conflict_warning() must not.
    msg = sched.conflict_warning()
    assert "Bad" in msg and "25:99" in msg


def test_explain_reports_conflicts():
    pet = Pet("Rex", "dog")
    pet.add_task(Task("Walk", "08:00", duration_minutes=30, priority="high"))
    pet.add_task(Task("Vet call", "08:15", duration_minutes=20, priority="high"))
    owner = Owner("Sam", available_minutes=120)
    owner.add_pet(pet)
    sched = Scheduler(owner)

    sched.build_plan()
    assert "overlaps" in sched.explain()


# --- completion tracking -------------------------------------------------
def test_mark_complete_and_summary(owner_with_two_pets):
    sched = Scheduler(owner_with_two_pets)
    sched.all_tasks()[0].mark_complete()  # daily task -> spawns next occurrence
    # 1 done; total grew from 5 to 6 because the next occurrence was created
    assert "1/6" in sched.summary()


# --- recurring tasks auto-regenerate on completion ----------------------
def test_completing_daily_task_spawns_next_occurrence():
    pet = Pet("Rex", "dog")
    walk = Task("Walk", "08:00", duration_minutes=30, priority="high", frequency="daily")
    pet.add_task(walk)

    walk.mark_complete()
    assert len(pet.tasks) == 2  # original + the next occurrence
    nxt = pet.tasks[1]
    assert nxt is not walk               # a genuinely new instance
    assert nxt.completed is False        # the next run starts not-done
    assert nxt.description == "Walk"     # same activity, time, duration, etc.
    assert nxt.time == "08:00"
    assert nxt.frequency == "daily"


def test_completing_weekly_task_spawns_next_occurrence():
    pet = Pet("Rex", "dog")
    groom = Task("Groom", "11:00", duration_minutes=40, priority="low", frequency="weekly")
    pet.add_task(groom)

    groom.mark_complete()
    assert len(pet.tasks) == 2
    assert pet.tasks[1].completed is False


def test_completing_monthly_task_does_not_spawn():
    pet = Pet("Rex", "dog")
    vet = Task("Vet visit", "09:00", duration_minutes=60, priority="high", frequency="monthly")
    pet.add_task(vet)

    vet.mark_complete()
    assert len(pet.tasks) == 1  # monthly is one-off here — no auto-regeneration


def test_completing_twice_does_not_double_spawn():
    pet = Pet("Rex", "dog")
    walk = Task("Walk", "08:00", duration_minutes=30, priority="high", frequency="daily")
    pet.add_task(walk)

    walk.mark_complete()
    walk.mark_complete()  # already done -> no-op, must not spawn a second copy
    assert len(pet.tasks) == 2


def test_next_occurrence_is_returned_and_pet_less_tasks_do_not_spawn():
    # A task not attached to a pet can still describe its next run, but has
    # nowhere to auto-attach it, so completing it adds nothing.
    loose = Task("Walk", "08:00", frequency="daily")
    assert loose.next_occurrence() is not None
    loose.mark_complete()  # no pet -> nothing to attach to; just marks done
    assert loose.completed is True


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


# =========================================================================
# Required coverage: sorting, recurrence, conflict detection (+ edge cases)
# =========================================================================

# --- 1. Sorting correctness ---------------------------------------------
def test_sorting_returns_chronological_order():
    """Tasks entered out of order come back earliest-time-first."""
    pet = Pet("Rex", "dog")
    # Added deliberately shuffled.
    pet.add_task(Task("Evening", "18:00", priority="high"))
    pet.add_task(Task("Dawn", "06:15", priority="high"))
    pet.add_task(Task("Noon", "12:00", priority="high"))
    owner = Owner("Sam")
    owner.add_pet(pet)
    sched = Scheduler(owner)

    times = [t.time for t in sched.sort_by_time()]
    assert times == ["06:15", "12:00", "18:00"]
    assert times == sorted(times)  # invariant: fully chronological


def test_equal_times_preserve_insertion_order():
    """Ties on identical times keep insertion order (sort is stable)."""
    pet = Pet("Rex", "dog")
    first = Task("First at 8", "08:00", priority="high")
    second = Task("Second at 8", "08:00", priority="low")
    pet.add_task(first)
    pet.add_task(second)
    owner = Owner("Sam")
    owner.add_pet(pet)
    sched = Scheduler(owner)

    ordered = [t.description for t in sched.sort_by_time()]
    assert ordered == ["First at 8", "Second at 8"]


def test_schedule_is_empty_with_no_tasks():
    """Sorting/planning an owner with no tasks is graceful, not a crash."""
    sched = Scheduler(Owner("Empty"))
    assert sched.sort_by_time() == []
    assert sched.daily_schedule() == []
    sched.build_plan()
    assert sched.scheduled_tasks == []
    assert sched.find_conflicts() == []


# --- 2. Recurrence logic -------------------------------------------------
def test_completing_daily_task_creates_next_day_task():
    """Marking a DAILY task complete spawns a fresh task for the next day.

    Tasks carry a time-of-day but no calendar date, so 'the next day's run'
    is represented by a new, incomplete copy at the same time.
    """
    pet = Pet("Rex", "dog")
    walk = Task("Walk", "08:00", duration_minutes=30, priority="high",
                frequency="daily")
    pet.add_task(walk)
    assert len(pet.tasks) == 1

    walk.mark_complete()

    assert len(pet.tasks) == 2                 # original + next day's run
    nxt = pet.tasks[1]
    assert nxt is not walk                     # a genuinely new task
    assert nxt.completed is False              # next day starts not-done
    assert walk.completed is True              # today's run is done
    assert (nxt.description, nxt.time, nxt.frequency) == ("Walk", "08:00", "daily")


def test_completing_monthly_task_creates_no_next_task():
    """Non-recurring (monthly) tasks do not auto-spawn a follow-up."""
    pet = Pet("Rex", "dog")
    vet = Task("Vet", "09:00", priority="high", frequency="monthly")
    pet.add_task(vet)

    vet.mark_complete()
    assert len(pet.tasks) == 1


# --- 3. Conflict detection ----------------------------------------------
def test_conflict_detection_flags_duplicate_times():
    """Two tasks at the SAME time are flagged as a conflict."""
    pet = Pet("Rex", "dog")
    a = Task("Walk", "08:00", duration_minutes=30, priority="high")
    b = Task("Feed", "08:00", duration_minutes=10, priority="high")
    pet.add_task(a)
    pet.add_task(b)
    owner = Owner("Sam")
    owner.add_pet(pet)
    sched = Scheduler(owner)

    conflicts = sched.find_conflicts()
    assert len(conflicts) == 1
    pair = {conflicts[0][0].description, conflicts[0][1].description}
    assert pair == {"Walk", "Feed"}
    # and it shows up in the human-readable warning
    assert "overlaps" in sched.conflict_warning()


def test_three_way_overlap_reports_all_real_pairs():
    """A long task overlapping two shorter ones yields exactly the real pairs.

    Guards the early-`break` optimization in find_conflicts(): 'Mid' and 'Late'
    do NOT overlap each other, so only (Long, Mid) and (Long, Late) are real.
    """
    pet = Pet("Rex", "dog")
    pet.add_task(Task("Long", "08:00", duration_minutes=60, priority="high"))  # 08:00–09:00
    pet.add_task(Task("Mid", "08:10", duration_minutes=5, priority="high"))    # 08:10–08:15
    pet.add_task(Task("Late", "08:50", duration_minutes=5, priority="high"))   # 08:50–08:55
    owner = Owner("Sam")
    owner.add_pet(pet)
    sched = Scheduler(owner)

    pairs = {(a.description, b.description) for a, b in sched.find_conflicts()}
    assert pairs == {("Long", "Mid"), ("Long", "Late")}


def test_spawned_next_occurrence_does_not_conflict_with_parent():
    """Completing a daily task must not create a conflict with its own successor.

    The successor sits at the same time as the just-completed task, but
    find_conflicts() ignores completed tasks, so no false clash appears.
    """
    pet = Pet("Rex", "dog")
    walk = Task("Walk", "08:00", duration_minutes=30, priority="high", frequency="daily")
    pet.add_task(walk)
    owner = Owner("Sam")
    owner.add_pet(pet)
    sched = Scheduler(owner)

    walk.mark_complete()  # spawns an 08:00 successor
    assert len(pet.tasks) == 2
    assert sched.find_conflicts() == []  # completed parent is not a competitor


def test_explain_raises_on_bad_time_string():
    """DOCUMENTS a known inconsistency: explain() crashes on a bad time.

    conflict_warning() defends against unparseable times, but explain() calls
    find_conflicts() -> end_dt(), which raises ValueError. If explain() is ever
    hardened the same way, flip this to assert a graceful message instead.
    """
    pet = Pet("Rex", "dog")
    pet.add_task(Task("Good", "08:00", duration_minutes=30, priority="high"))
    pet.add_task(Task("Bad", "25:99", duration_minutes=10, priority="high"))
    owner = Owner("Sam", available_minutes=120)
    owner.add_pet(pet)
    sched = Scheduler(owner)

    sched.build_plan()  # fine: sorts by time string, never parses
    with pytest.raises(ValueError):
        sched.explain()  # find_conflicts() forces the parse and blows up
