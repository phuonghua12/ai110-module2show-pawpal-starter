# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

- Briefly describe your initial UML design.

My initial design uses four classes and separates the data (the things being tracked) from the logic (the thing that does the planning). Owner, Pet, and Task are simple data classes that just hold information, while the Scheduler holds the actual scheduling logic and the resulting schedule.

- What classes did you include, and what responsibilities did you assign to each?

- Owner: represents the pet owner and their care preferences/constraints (e.g. how much time is available in a day).
- Pet: represents the animal being cared for (name, species).
- Task: represents one unit of care and its cost and importance (title, duration in minutes, priority).
- Scheduler: does the real work: takes the tasks plus constraints (available time, priority) and builds the schedule via `build_plan(tasks, available_minutes)`, then holds the chosen tasks and can `explain()` its reasoning.

The key decision was splitting "data" classes (Owner, Pet, Task) from a "behavior" class (Scheduler). That is why `build_plan()` lives on the Scheduler rather than on Owner — the owner holds information, the scheduler acts on it. I chose to keep the schedule inside the Scheduler (instead of a separate Plan class) to stay at four classes; the tradeoff is that the Scheduler now has two responsibilities — computing the plan and storing/presenting it.

**b. Design changes**

- Did your design change during implementation?

Yes. Reviewing the skeleton against my design surfaced a few gaps, and I made these changes:

- Added a `pets` list to `Owner`. My UML said an owner "owns" pets, but the code had no field for it, so the relationship only existed on the diagram. I added `pets: list[Pet]` so the code actually models the relationship.

- Added a `skipped_tasks` list to `Scheduler`. My original `Scheduler` only stored the tasks it chose, but `explain()` needs to say *why* a task was left out ("skipped grooming — no time left"). Without keeping the rejected tasks I couldn't explain the tradeoffs, so I added `skipped_tasks` alongside `scheduled_tasks`.

- Added a `PRIORITY_RANK` map. `priority` is a string ("low"/"medium"/"high"), and sorting those strings directly orders them alphabetically (high < low < medium), which is wrong. I added `PRIORITY_RANK = {"high": 3, "medium": 2, "low": 1}` so `_sort_tasks` can sort by importance instead of by spelling.

- Changed `build_plan(tasks, available_minutes)` to `build_plan(owner, tasks)`. The time budget is really the owner's constraint, so passing the `Owner` keeps the constraint attached to the object that owns it instead of relying on a loose number matching up.

Later I made a larger restructuring so the model handles multiple pets properly:

- Moved tasks *inside* `Pet`. Instead of loose tasks passed around, each `Pet` now owns its `tasks` list, `Owner` holds a list of `Pet`s, and the `Scheduler` reaches tasks through `owner.all_tasks()`. This lets one owner manage several pets without tasks becoming ambiguous. `build_plan` now reads the budget from the owner directly (`build_plan(available_minutes=None)` defaulting to `owner.available_minutes`).

- Added `frequency` and `completed` to `Task`, plus `mark_complete()` / `mark_incomplete()` and Scheduler methods (`daily_schedule`, `tasks_by_frequency`, `pending_tasks`, `reset_daily_tasks`). This turns it from a one-shot planner into something that tracks recurring care day to day.

- Briefly dropped, then re-added, `duration_minutes` and `priority`. When I restructured around frequency/completion I lost the time-budget planning, which the project requires ("duration + priority at minimum"). I added them back and kept both feature sets: the organizing methods (by frequency/completion) and the constrained `build_plan` (by priority within a time budget).

Now that tasks live on pets, the earlier "single-pet assumption" no longer applies. Still open by choice: tasks have a time-of-day but no explicit calendar date, so recurring frequencies aren't expanded across real dates yet.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?

The scheduler considers two constraints: the owner's available time for the day (`available_minutes`) and each task's `priority` (high/medium/low). `build_plan` sorts pending tasks by priority first (ties broken by time of day), then greedily takes each task while it still fits in the remaining time. It also respects completion status — completed tasks aren't re-planned.

- How did you decide which constraints mattered most?

Priority matters most. A busy owner cares more about the important task getting done than about filling every free minute, so the scheduler always tries the highest-priority tasks first and only skips a task when there genuinely isn't time.

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.

It uses a greedy, priority-first strategy rather than trying to maximize the number of tasks completed. Because it commits to high-priority tasks first, it can leave time unused: e.g. with 60 minutes, it schedules a 30-min high task and a 5-min high task (35 min used), then skips a 40-min medium task even though 25 minutes remain — those 25 minutes go unused because the next task doesn't fit.

- Why is that tradeoff reasonable for this scenario?

For pet care, doing the important things (a walk, medication) matters more than squeezing in the most tasks. A greedy priority-first plan is also simple to understand and explain to the owner, which fits the goal of the app explaining *why* it chose the plan. A "maximize tasks" approach (a knapsack solve) would be more optimal but harder to justify and overkill for a daily care list.

- A second tradeoff: conflict detection *warns* but does not *resolve*.

The scheduler detects when two tasks clash in time, but it does not act on that — it flags the conflict and still schedules both tasks. `find_conflicts()` compares full time windows (start + duration, computed with `timedelta`), so it catches partial overlaps like an 08:00–08:30 walk against an 08:15 vet call, not just tasks that start at the exact same minute. It classifies each clash as same-pet (the pet can't do both) or cross-pet (the owner can't be in two places), and `build_plan()`/`explain()` surface those warnings — but the plan still contains both conflicting tasks. So the *detection* is richer than an exact-time-match check, while the *response* stays deliberately hands-off.

- Why is that tradeoff reasonable for this scenario?

Checking overlapping durations rather than exact start times is the honest model of the constraint: real clashes are usually partial (a walk running into a feeding), and exact-match checking would silently miss them. But auto-resolving a conflict means *deciding for the owner* — bumping a task's time, dropping the lower-priority one, or shortening it — and any of those could move a medication dose or skip a walk without consent. For a care assistant, surfacing "these two overlap, your call" is safer and more transparent than a resolution the owner didn't ask for. It also keeps the planner's one job (fit tasks to the time budget by priority) separate from time-of-day conflicts, which are a different concern. Auto-resolution would be a reasonable next iteration, but only as an explicit, explained suggestion.

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)? I used AI tools during this project for all design brainstorming, debugging, refactoring.
- What kinds of prompts or questions were most helpful? I find out that the "How" type of questions were the most useful and also most of the debug code prompts.

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is. The moment that I did not accept was when AI suggested that I should overwrite some functions because it already appear somewhere else.
- How did you evaluate or verify what the AI suggested? I chose to delete it to keep the code cleaner instead.

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test? I wrote 52 tests covering sorting, adding up tasks accross pets, building the plan, filtering, reccuring tasks, conflict, and time math.
- Why were these tests important? I think these tests were important because if one quietly broke, the app would give wrong plans with no error to warn
**b. Confidence**

- How confident are you that your scheduler works correctly? 3.5
- What edge cases would you test next if you had more time? I would test very large or many tasks. I'd add more tasks than can fit in a day to make sure the planner still picks the right ones and stays fast.
---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with? Testing

**b. What you would improve**

- If you had another iteration, what would you improve or redesign? I would improve more on the methods like keep it simpler and cleaner.

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project? I learned about how important we draft our prompt effect the outcome of AI.
