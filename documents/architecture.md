# Chore App Architecture

## Overview

The Chore App is a Django-based web application designed to manage household chores and reward systems for parents and children. The application implements a point-based system where children earn points for completing chores, which can be converted to pocket money, with various bonuses and penalties applied automatically.

## System Architecture

```mermaid
graph TB
    subgraph "Client Layer"
        B[Browser]
    end

    subgraph "Web Layer"
        D[Django Web Server]
        T[Templates]
        S[Static Files<br/>CSS/JS]
    end

    subgraph "Application Layer"
        V[Views<br/>Business Logic]
        M[Models<br/>Data Layer]
        F[Forms<br/>Validation]
        U[Utils<br/>Helper Functions]
        C[Cron Jobs<br/>Scheduled Tasks]
    end

    subgraph "Data Layer"
        DB[(SQLite Database)]
    end

    B --> D
    D --> V
    V --> M
    V --> F
    V --> U
    C --> M
    M --> DB
    D --> T
    D --> S
```

## Component Details

### Models (Data Layer)

```mermaid
classDiagram
    class User {
        +role: CharField (Parent/Child)
        +points_balance: DecimalField
        +pocket_money: DecimalField
        +place_1, place_2, place_3: IntegerField
    }

    class Chore {
        +name: CharField
        +points: DecimalField
        +assignment_type: CharField
        +available: BooleanField
        +daily: BooleanField
        +early_bonus: BooleanField
        +bonus_end_time: IntegerField
        +available_time: IntegerField
    }

    class ChoreClaim {
        +chore: ForeignKey
        +user: ForeignKey
        +approved: DecimalField
        +points: DecimalField
        +comment: CharField
    }

    class PointLog {
        +user: ForeignKey
        +points_change: DecimalField
        +reason: CharField
        +chore: CharField
        +penalty: DecimalField
        +date_recorded: DateTimeField
    }

    class Settings {
        +key: CharField
        +name: CharField
        +value: DecimalField
    }

    class Text {
        +key: CharField
        +text: TextField
        +enabled: BooleanField
    }

    class RunLog {
        +job_code: CharField
        +run_date: DateField
    }

    User ||--o{ ChoreClaim : claims
    User ||--o{ PointLog : logs
    Chore ||--o{ ChoreClaim : claimed_by
    Chore ||--o{ User : assigned_to
    User ||--o{ PointLog : approver
```

### Views (Business Logic Layer)

```mermaid
graph TD
    subgraph "Authentication Views"
        A1[register]
        A2[login/logout]
        A3[profile]
    end

    subgraph "Parent Views"
        P1[parent_profile]
        P2[create_chore]
        P3[edit_chore]
        P4[settings]
        P5[messages]
        P6[point_adjustment]
        P7[pocket_money_adjustment]
        P8[daily_action]
        P9[approve_chore_claim]
        P10[reject_chore_claim]
    end

    subgraph "Child Views"
        C1[child_profile]
        C2[claim_chore]
        C3[return_chore]
        C4[convert_points_to_money]
        C5[child_chore]
    end

    subgraph "Utility Views"
        U1[toggle_availability]
        U2[delete_chore]
        U3[penalise_chore]
    end
```

### Cron Jobs (Scheduled Tasks)

```mermaid
graph TD
    A[NightlyAction<br/>23:30 daily] --> B[auto_approve<br/>Auto-approve pending chores]
    A --> C[apply_daily_bonus<br/>Add daily points to children]
    A --> D[incomplete_chore_penalty<br/>Penalize for incomplete chores]
    A --> E[apply_leaderboard_scoring<br/>Award leaderboard prizes]
    A --> F[reset_daily_chores<br/>Reset daily chores]

    B --> G[Update PointLog<br/>Create approval entries]
    C --> G
    D --> G
    E --> G
```

## Data Flow

```mermaid
sequenceDiagram
    participant Child
    participant Browser
    participant Django
    participant Database
    participant Cron

    Child->>Browser: Access child_profile
    Browser->>Django: GET /child_profile/
    Django->>Database: Query available chores
    Database-->>Django: Return chore data
    Django-->>Browser: Render profile page

    Child->>Browser: Claim chore
    Browser->>Django: POST /claim_chore/<id>/
    Django->>Database: Create ChoreClaim
    Django->>Database: Update Chore availability
    Django-->>Browser: Success message

    Parent->>Browser: Approve chore
    Browser->>Django: POST /approve_chore_claim/<id>/<penalty>/
    Django->>Database: Update ChoreClaim.approved
    Django->>Database: Update User.points_balance
    Django->>Database: Create PointLog entry

    Cron->>Django: NightlyAction (23:30)
    Django->>Database: Run penalty calculations
    Django->>Database: Apply daily bonuses
    Django->>Database: Calculate leaderboard
    Django->>Database: Reset daily chores
```

## Security & Authentication

- Django's built-in authentication system
- Role-based access control (Parent/Child roles)
- CSRF protection on forms
- Session-based authentication
- Login required decorators on sensitive views

## Deployment Considerations

- SQLite database (development)
- Static file serving
- Cron job scheduling via django-cron
- Time zone: Australia/Melbourne
- Environment variable configuration for production settings