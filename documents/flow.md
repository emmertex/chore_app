# Chore App Application Flow

## Overview

The Chore App implements several key workflows for managing household chores and rewards. This document outlines the major application flows with detailed sequence diagrams and flowcharts.

## Major Workflows

### 1. Chore Claiming Process

```mermaid
flowchart TD
    A[Child logs in] --> B[View child_profile]
    B --> C[Check chore availability<br/>and time constraints]
    C --> D{Eligible to claim?}
    D -->|No| E[Show ineligible message]
    D -->|Yes| F[Claim chore]
    F --> G[Create ChoreClaim record]
    G --> H{Check assignment type}
    H -->|any_child| I[Set chore unavailable]
    H -->|all_children| J[Keep chore available]
    H -->|any_selected| K[Set chore unavailable]
    H -->|all_selected| L{Check if all selected<br/>children claimed}
    L -->|Yes| M[Set chore unavailable]
    L -->|No| N[Keep chore available]
    I --> O[Show success message]
    J --> O
    K --> O
    M --> O
    N --> O
    E --> P[End]
    O --> P
```

**Detailed Sequence:**

```mermaid
sequenceDiagram
    participant Child
    participant Browser
    participant Django as Django View
    participant DB as Database

    Child->>Browser: Click "Claim Chore" button
    Browser->>Django: POST /claim_chore/<chore_id>/
    Django->>DB: SELECT Chore WHERE id=<chore_id> FOR UPDATE
    DB-->>Django: Chore data

    Django->>Django: Check assignment eligibility
    Django->>DB: Check existing claims for user
    DB-->>Django: Claim status

    Django->>Django: Calculate bonus points if applicable
    Note over Django: If current_time <= bonus_end_time<br/>and early_bonus enabled,<br/>add bonus_percent to points

    Django->>DB: INSERT INTO ChoreClaim
    DB-->>Django: Success

    Django->>Django: Update chore availability based on assignment_type
    Django->>DB: UPDATE Chore SET available=...
    DB-->>Django: Success

    Django-->>Browser: Redirect with success message
    Browser-->>Child: Show updated profile
```

### 2. Chore Approval Process

```mermaid
flowchart TD
    A[Parent logs in] --> B[View parent_profile]
    B --> C[Review pending ChoreClaims]
    C --> D{Approve or Reject?}
    D -->|Approve| E[Enter penalty percentage<br/>0-100%]
    D -->|Reject| F[Reject chore claim]
    E --> G[Calculate points_awarded<br/>= points - (points × penalty/100)]
    G --> H[Update ChoreClaim.approved]
    H --> I[Add points to user balance]
    I --> J[Create PointLog entry]
    J --> K{Is daily chore?}
    K -->|No| L[Set chore unavailable]
    K -->|Yes| M[Keep chore available]
    F --> N[Make chore available again]
    N --> O[Create rejection PointLog<br/>with REJECTION_PENALTY]
    L --> P[Show success message]
    M --> P
    O --> P
```

**Approval Calculation Details:**

```mermaid
graph TD
    A[ChoreClaim.points] --> B[penalty_percentage]
    B --> C[penalty_decimal = penalty / 100]
    C --> D[deduction = points × penalty_decimal]
    D --> E[points_awarded = points - deduction]
    E --> F{points_awarded < 0?}
    F -->|Yes| G[points_awarded = 0]
    F -->|No| H[Use calculated value]
    G --> I[Update balances]
    H --> I
```

### 3. Points to Money Conversion

```mermaid
flowchart TD
    A[Child has points] --> B[Check minimum balance<br/>points >= max_points/2]
    B -->|No| C[Show insufficient points message]
    B -->|Yes| D[Check conversion rate<br/>points >= 100]
    D -->|No| E[Show insufficient points message]
    D -->|Yes| F[Calculate money amount<br/>money = 100 × point_value]
    F --> G[Update user balances<br/>pocket_money += money<br/>points_balance -= 100]
    G --> H[Create PointLog entry<br/>points_change = -100<br/>reason = 'Conversion to Pocket Money']
    H --> I[Show success message]
    C --> J[End]
    E --> J
    I --> J
```

### 4. Nightly Cron Job Process

```mermaid
flowchart TD
    A[Cron triggers at 23:30] --> B[Check if already run today]
    B -->|Already run| C[Skip execution]
    B -->|Not run| D[Execute nightly_action]
    D --> E[Auto-approve pending chores<br/>with configured penalty]
    E --> F[Apply incomplete chore penalties<br/>to all children]
    F --> G[Apply daily bonuses<br/>to all children]
    G --> H[Calculate leaderboard scoring<br/>and awards]
    H --> I[Reset daily chores<br/>to available state]
    I --> J[Mark job as run<br/>Log execution]
    C --> K[End]
    J --> K
```

**Nightly Action Sequence:**

```mermaid
sequenceDiagram
    participant Cron
    participant Django
    participant DB

    Cron->>Django: nightly_action()
    Django->>DB: Get all children users
    DB-->>Django: Children list

    loop For each child
        Django->>Django: incomplete_chore_penalty(child)
        Django->>DB: Calculate penalty amount
        Django->>DB: Update points_balance
        Django->>DB: Create PointLog

        Django->>Django: apply_daily_bonus(child)
        Django->>DB: Calculate bonus amount
        Django->>DB: Update points_balance
        Django->>DB: Create PointLog
    end

    Django->>Django: apply_leaderboard_scoring()
    Django->>DB: Calculate daily chore points
    Django->>DB: Award 1st, 2nd, 3rd place
    Django->>DB: Create PointLog entries

    Django->>Django: reset_daily_chores()
    Django->>DB: Delete approved ChoreClaims
    Django->>DB: Set daily Chores to available

    Django->>DB: Mark RunLog as executed
```

### 5. Leaderboard Calculation

```mermaid
flowchart TD
    A[Get today's chore points] --> B[Sum points per user<br/>from PointLog]
    B --> C[Sort by total_points DESC]
    C --> D{1st place exists?}
    D -->|Yes| E[Award 1st place<br/>points += leaderboard_awards]
    D -->|No| F[Skip 1st place]
    E --> G{2nd place exists?}
    F --> G
    G -->|Yes| H[Award 2nd place<br/>points += leaderboard_awards/2]
    G -->|No| I[Skip 2nd place]
    H --> J{3rd place exists?}
    I --> J
    J -->|Yes| K[Award 3rd place<br/>points += leaderboard_awards/5]
    J -->|No| L[Skip 3rd place]
    K --> M[Create PointLog entries<br/>for all participants]
    L --> M
    M --> N[End]
```

### 6. Daily Bonus Application

```mermaid
flowchart TD
    A[For each child] --> B[Get current points_balance]
    B --> C{points_balance < min_points?}
    C -->|Yes| D[Set points_balance = min_points]
    C -->|No| E[Keep current balance]
    D --> F[Add daily_bonus to balance]
    E --> F
    F --> G{new_balance > max_points?}
    G -->|No| H[Keep points balance]
    G -->|Yes| I[Convert excess to pocket_money<br/>excess = balance - max_points<br/>pocket_money += excess × point_value<br/>points_balance = max_points]
    H --> J[Create PointLog<br/>points_change = actual increase]
    I --> J
    J --> K[Next child]
    K --> L{All children processed?}
    L -->|No| A
    L -->|Yes| M[End]
```

### 7. Incomplete Chore Penalty

```mermaid
flowchart TD
    A[For each child] --> B[Get available chores]
    B --> C[Find completed chores by child<br/>from ChoreClaim.approved > 0]
    C --> D[Calculate incomplete_sum<br/>= sum of available chore points<br/>- completed chore points]
    D --> E{incomplete_sum > 0<br/>AND penalty > 0?}
    E -->|No| F[No penalty]
    E -->|Yes| G[Calculate penalty_amount<br/>= (penalty% / 100) × incomplete_sum]
    G --> H[Subtract from points_balance]
    H --> I[Create PointLog entry<br/>points_change = -penalty_amount<br/>penalty = penalty%<br/>reason = detailed explanation]
    F --> J[Next child]
    I --> J
    J --> K{All children processed?}
    K -->|No| A
    K -->|Yes| L[End]
```

## Error Handling Flows

### Chore Claim Validation

```mermaid
flowchart TD
    A[Claim request] --> B{User is Child?}
    B -->|No| C[Redirect to child_profile]
    B -->|Yes| D{Chore exists?}
    D -->|No| E[Error: Chore not found]
    D -->|Yes| F{Chore available?}
    F -->|No| G[Warning: Chore unavailable]
    F -->|Yes| H{Time eligible?}
    H -->|No| I[Warning: Time constraint]
    H -->|Yes| J{Assignment eligible?}
    J -->|No| K[Warning: Not assigned]
    J -->|Yes| L{Already claimed?}
    L -->|Yes| M[Warning: Already claimed]
    L -->|No| N[Proceed with claim]
    C --> O[End]
    E --> O
    G --> O
    I --> O
    K --> O
    M --> O
    N --> O
```

## Data Validation Rules

- **Penalty Percentage**: Must be 0-100%
- **Points Balance**: Cannot go negative (except in specific penalty cases)
- **Chore Availability**: Time-based constraints apply
- **Assignment Types**: Strict validation for selected children
- **Daily Actions**: Can only run once per day
- **Point Conversion**: Minimum thresholds enforced