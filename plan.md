# Chore App Simplification Plan

## Goal
Strip out complex scoring/rewards/rankings. Keep: points per chore, early bonus, parent assigns to child. Add: rewards catalog children can "buy" with points. Remove: money conversion, leaderboard, daily bonuses/penalties.

---

## Phase 1: Model Cleanup

**Objective:** Simplify data models. No new features yet.

### Tasks
- Strip `User` model: remove `pocket_money`, `place_1`, `place_2`, `place_3`
- Simplify `Chore` model:
  - Remove `assignment_type` field and choices (keep only: assigned to specific child via M2M, or available to all)
  - Remove `available_time` field (always available when enabled)
  - Keep: `name`, `comment`, `points`, `daily`, `early_bonus`, `bonus_end_time`, `assigned_children`
- Simplify `ChoreClaim`: remove `multiplier_type`
- Simplify `PointLog`: remove `penalty`, `multiplier_type` fields
- Remove `Settings` model entirely (no more configurable rates/caps)
- Create migrations, run them

### Files touched
- `models.py`
- New migration file(s)

---

## Phase 2: Kill the Cron Complexity

**Objective:** Remove all nightly scoring logic. No daily action button needed anymore.

### Tasks
- Delete from `cron.py`:
  - `apply_leaderboard_scoring()` and related code
  - `apply_daily_bonus()`
  - `incomplete_chore_penalty()`
  - `auto_approve()` / `_approve_chore_claim_direct()`
- Simplify `reset_daily_chores()` to just reset daily chores available=True, clear old claims
- Update `NightlyAction.do()` to only call `reset_daily_chores()`
- Remove from `utils.py`: all references to bonus/penalty/leaderboard in `nightly_action()`
- Remove "Daily Action" button view (`daily_action`) and URL

### Files touched
- `cron.py`
- `utils.py`
- `views.py` (remove daily_action)
- `urls.py` (remove daily_action route)

---

## Phase 3: Simplify Views & Chore Flow

**Objective:** Clean up view logic to match simpler models. Remove money conversion, simplify approval.

### Tasks
- Remove `convert_points_to_money()` view and URL
- Remove `pocket_money_adjustment()` view and URL
- Simplify `claim_chore()`: remove complex assignment_type checks, time-based availability logic
- Simplify `approve_chore_claim()`: always approve at full points (remove penalty parameter). Or keep simple 100%/50% option.
- Remove `penalise_chore()` view and URL
- Update `child_profile()`: remove leaderboard query, future/missed chore filtering, money display
- Update `parent_profile()`: remove leaderboard column, money column, trophies

### Files touched
- `views.py`
- `urls.py`
- `forms.py` (simplify ChoreForm/EditChoreForm fields)

---

## Phase 4: Add Rewards System

**Objective:** New feature — parent creates rewards with point costs, children spend points to claim them.

### Tasks
- Add `Reward` model:
  - `name`, `description`, `points_cost`, `available` (boolean), `redeemed_by` (optional FK to User for one-time rewards)
- Create CRUD views for parent:
  - List all rewards
  - Create/Edit/Delete reward
- Create child view: browse available rewards, "claim" a reward (deduct points from balance)
- Add URLs and forms

### Files touched
- `models.py` (+ migration)
- `views.py`
- `urls.py`
- `forms.py`
- New templates: `rewards_list.html`, `create_reward.html`, `edit_reward.html`

---

## Phase 5: Template Cleanup & Polish

**Objective:** Update all HTML to match simplified system. Remove confusing UI elements.

### Tasks
- `child_profile.html`:
  - Remove leaderboard section, trophies display, money display
  - Remove "convert points" button
  - Remove future/missed chore sections
  - Simplify help text
  - Add link to rewards page
- `parent_profile.html`:
  - Remove money/trophies columns from children table
  - Remove leaderboard column
  - Remove Daily Action button
  - Add link to manage rewards
- Clean up any remaining references to removed features

### Files touched
- `child_profile.html`
- `parent_profile.html`
- Any other templates with stale references

---

## Notes per Phase

Each phase should:
- Be independently testable (run server, check it works)
- Not require holding context from previous phases beyond "the codebase is simpler now"
- Include running migrations if models change
