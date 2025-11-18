# Chore App Mathematics: Penalties and Bonuses

## Overview

The Chore App implements a comprehensive point-based reward system with various mathematical calculations for bonuses and penalties. All calculations use decimal arithmetic to maintain precision.

## Core Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `POINTS_TO_MONEY_CONVERSION_RATE` | 100 | Points required for money conversion |
| `POINT_VALUE_MULTIPLIER` | 1 | Multiplier for point calculations |
| `EARLY_BONUS_START_HOUR` | 5 | Hour when early bonus becomes available |
| `MAX_PENALTY_PERCENTAGE` | 100 | Maximum penalty percentage |
| `REJECTION_PENALTY` | 100 | Penalty percentage for rejected chores |

## 1. Early Bonus Calculation

When a child claims a chore before the bonus end time and early bonus is enabled:

### Formula
If `current_time ≤ bonus_end_time` AND `current_time ≥ EARLY_BONUS_START_HOUR` AND `early_bonus = true`:

```math
bonus\_percent = settings['bonus_percent']
```

```math
addPoints = chore.points \times \left( \frac{bonus\_percent + 100}{100} \right)
```

```math
bonus\_points = addPoints - chore.points
```

### Example
- Chore points: 10
- Bonus percentage: 20%
- Early bonus start: 05:00
- Bonus end time: 14:00

If claimed at 08:00:
```math
addPoints = 10 \times \left( \frac{20 + 100}{100} \right) = 10 \times 1.2 = 12
```

```math
bonus\_points = 12 - 10 = 2
```

## 2. Chore Approval Penalty

When a parent approves a chore claim with a penalty:

### Formula
```math
penalty\_decimal = \frac{penalty}{100}
```

```math
points\_awarded = choreClaim.points - (choreClaim.points \times penalty\_decimal)
```

With constraint:
```math
points\_awarded = \max(0, points\_awarded)
```

### Example
- Chore claim points: 15
- Penalty: 25%

```math
penalty\_decimal = \frac{25}{100} = 0.25
```

```math
points\_awarded = 15 - (15 \times 0.25) = 15 - 3.75 = 11.25
```

## 3. Incomplete Chore Penalty

Applied nightly to children who haven't completed available chores:

### Formula
```math
completed\_chores\_ids = \{chore.id \mid ChoreClaim.chore = chore \land ChoreClaim.user = child \land ChoreClaim.approved > 0\}
```

```math
incomplete\_sum = \sum_{\text{available chores}} chore.points - \sum_{\text{completed chores}} chore.points
```

```math
penalty\_percentage = settings['incomplete\_chores\_penalty']
```

```math
penalty\_amount = \frac{penalty\_percentage}{100} \times incomplete\_sum
```

### Example
- Available chores: Chore A (10 pts), Chore B (15 pts), Chore C (20 pts)
- Completed by child: Chore A (10 pts), Chore C (20 pts)
- Incomplete penalty: 30%

```math
incomplete\_sum = (10 + 15 + 20) - (10 + 20) = 45 - 30 = 15
```

```math
penalty\_amount = \frac{30}{100} \times 15 = 0.3 \times 15 = 4.5
```

Child loses 4.5 points.

## 4. Daily Bonus Application

Applied nightly to all children:

### Formula
```math
original\_balance = user.points\_balance
```

```math
points\_balance = \max(original\_balance, settings['min\_points'])
```

```math
points\_balance = points\_balance + settings['daily\_bonus']
```

If `points_balance > settings['max_points']`:
```math
excess = points\_balance - settings['max\_points']
```

```math
pocket\_money\_increase = excess \times settings['point\_value']
```

```math
points\_balance = settings['max\_points']
```

```math
pocket\_money = pocket\_money + pocket\_money\_increase
```

### Example
- Current points: 45
- Min points: 10
- Max points: 50
- Daily bonus: 8
- Point value: $0.05

```math
points\_balance = \max(45, 10) = 45
```

```math
points\_balance = 45 + 8 = 53
```

Since 53 > 50:
```math
excess = 53 - 50 = 3
```

```math
pocket\_money\_increase = 3 \times 0.05 = 0.15
```

```math
points\_balance = 50
```

## 5. Leaderboard Scoring

Calculated nightly based on daily chore completion:

### Formula
```math
chore\_points[user] = \sum_{\text{today's PointLog entries}} points\_change \text{ where chore ≠ ''}
```

Sorted by `total_points` descending.

**1st Place:**
```math
award_1 = settings['leaderboard\_awards']
```

**2nd Place:**
```math
award_2 = \frac{settings['leaderboard\_awards']}{2}
```

**3rd Place:**
```math
award_3 = \frac{settings['leaderboard\_awards']}{5}
```

### Example
- Leaderboard awards setting: 20 points
- 1st place: 20 points
- 2nd place: 20 ÷ 2 = 10 points
- 3rd place: 20 ÷ 5 = 4 points

## 6. Points to Money Conversion

When child converts points to pocket money:

### Requirements
```math
points\_balance \geq \frac{settings['max\_points']}{2}
```

```math
points\_balance \geq POINTS\_TO\_MONEY\_CONVERSION\_RATE
```

### Formula
```math
money\_amount = POINTS\_TO\_MONEY\_CONVERSION\_RATE \times settings['point\_value']
```

```math
pocket\_money = pocket\_money + money\_amount
```

```math
points\_balance = points\_balance - POINTS\_TO\_MONEY\_CONVERSION\_RATE
```

### Example
- Points to convert: 100
- Point value: $0.10
- Max points: 60

Check requirements:
```math
100 \geq \frac{60}{2} = 100 \geq 30 ✓
```

```math
100 \geq 100 ✓
```

```math
money\_amount = 100 \times 0.10 = 10.00
```

## 7. Rejection Penalty

When a parent rejects a chore claim:

### Formula
```math
points\_change = 0
```

```math
penalty = REJECTION\_PENALTY = 100
```

```math
reason = 'Rejected'
```

No points awarded, but logged with 100% penalty for tracking.

## 8. Auto-Approval Penalty

Configured penalty applied to pending chores nightly:

### Formula
```math
auto\_penalty = 100 - settings['auto\_approve']
```

```math
points\_awarded = choreClaim.points - (choreClaim.points \times \frac{auto\_penalty}{100})
```

### Example
- Auto-approve setting: 80% (meaning 20% penalty)
- Chore points: 12

```math
auto\_penalty = 100 - 80 = 20
```

```math
points\_awarded = 12 - (12 \times \frac{20}{100}) = 12 - 2.4 = 9.6
```

## Mathematical Properties

### Precision and Rounding
- All calculations use `Decimal` fields with 2 decimal places
- No rounding applied - full precision maintained
- Atomic database operations prevent race conditions

### Constraints
- Points balance cannot go negative (except specific penalties)
- Penalty percentages: 0 ≤ penalty ≤ 100
- Bonus percentages: Can exceed 100% for multipliers > 1

### Balance Calculations
```math
final\_balance = initial\_balance + \sum bonuses - \sum penalties
```

Where:
- Bonuses: early bonuses, daily bonuses, leaderboard awards
- Penalties: approval penalties, incomplete penalties, rejection penalties

### Time-Based Constraints
- Early bonus: `EARLY_BONUS_START_HOUR ≤ current_hour ≤ bonus_end_time`
- Chore availability: Time-window based availability
- Daily reset: All calculations reset at 23:30 nightly

## Configuration Dependencies

All calculations depend on configurable settings:

| Setting Key | Affects |
|-------------|---------|
| `bonus_percent` | Early bonus multiplier |
| `daily_bonus` | Nightly point addition |
| `max_points` | Point balance cap |
| `min_points` | Point balance floor |
| `point_value` | Money conversion rate |
| `leaderboard_awards` | Competition prizes |
| `incomplete_chores_penalty` | Penalty percentage |
| `auto_approve` | Auto-approval confidence |

This mathematical framework ensures fair, predictable, and configurable reward/penalty systems for the chore management application.