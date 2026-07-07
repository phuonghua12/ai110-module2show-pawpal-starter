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

Still open by choice: tasks are not yet linked to a specific `Pet` (single-pet assumption for now), and there are no per-task clock start times.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
