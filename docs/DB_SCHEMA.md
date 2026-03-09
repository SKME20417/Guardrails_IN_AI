# Database Schema

## Database
Supabase (PostgreSQL)

---

## Domain Tables

### students
| Column          | Type         | Constraints                    | Description                  |
|-----------------|--------------|--------------------------------|------------------------------|
| id              | UUID         | PK, default gen_random_uuid() | Unique student identifier    |
| first_name      | VARCHAR(100) | NOT NULL                       | Student's first name         |
| last_name       | VARCHAR(100) | NOT NULL                       | Student's last name          |
| email           | VARCHAR(255) | UNIQUE, NOT NULL               | Student email address        |
| phone           | VARCHAR(20)  |                                | Contact phone number         |
| date_of_birth   | DATE         |                                | Student's date of birth      |
| gender          | VARCHAR(10)  |                                | Gender (Male/Female/Other)   |
| department      | VARCHAR(100) | NOT NULL                       | Department/major             |
| enrollment_date | DATE         | NOT NULL                       | Date of enrollment           |
| gpa             | DECIMAL(3,2) |                                | Current GPA (0.00–4.00)      |
| status          | VARCHAR(20)  | DEFAULT 'active'               | active, graduated, dropped   |
| created_at      | TIMESTAMPTZ  | DEFAULT now()                  | Record creation timestamp    |
| updated_at      | TIMESTAMPTZ  | DEFAULT now()                  | Record update timestamp      |

### courses
| Column          | Type         | Constraints                    | Description                  |
|-----------------|--------------|--------------------------------|------------------------------|
| id              | UUID         | PK, default gen_random_uuid() | Unique course identifier     |
| course_code     | VARCHAR(20)  | UNIQUE, NOT NULL               | Course code (e.g., CS101)    |
| title           | VARCHAR(255) | NOT NULL                       | Course title                 |
| description     | TEXT         |                                | Course description           |
| department      | VARCHAR(100) | NOT NULL                       | Offering department          |
| credits         | INTEGER      | NOT NULL                       | Number of credits            |
| instructor      | VARCHAR(200) | NOT NULL                       | Instructor name              |
| max_enrollment  | INTEGER      | DEFAULT 50                     | Maximum students allowed     |
| semester        | VARCHAR(20)  | NOT NULL                       | Semester (Fall 2025, etc.)   |
| is_active       | BOOLEAN      | DEFAULT true                   | Whether course is active     |
| created_at      | TIMESTAMPTZ  | DEFAULT now()                  | Record creation timestamp    |
| updated_at      | TIMESTAMPTZ  | DEFAULT now()                  | Record update timestamp      |

### transactions
| Column          | Type           | Constraints                    | Description                     |
|-----------------|----------------|--------------------------------|---------------------------------|
| id              | UUID           | PK, default gen_random_uuid() | Unique transaction identifier   |
| student_id      | UUID           | FK → students.id, NOT NULL     | Reference to the student        |
| course_id       | UUID           | FK → courses.id, NOT NULL      | Reference to the course         |
| amount          | DECIMAL(10,2)  | NOT NULL                       | Transaction amount              |
| currency        | VARCHAR(3)     | DEFAULT 'USD'                  | Currency code                   |
| payment_method  | VARCHAR(50)    |                                | credit_card, debit_card, bank_transfer, scholarship |
| payment_status  | VARCHAR(20)    | DEFAULT 'pending'              | pending, completed, failed, refunded |
| transaction_date| TIMESTAMPTZ    | NOT NULL                       | When the transaction occurred   |
| semester        | VARCHAR(20)    | NOT NULL                       | Semester of enrollment          |
| discount_pct    | DECIMAL(5,2)   | DEFAULT 0.00                   | Discount percentage applied     |
| notes           | TEXT           |                                | Additional notes                |
| created_at      | TIMESTAMPTZ    | DEFAULT now()                  | Record creation timestamp       |
| updated_at      | TIMESTAMPTZ    | DEFAULT now()                  | Record update timestamp         |

---

## Monitoring Table

### guardrail_logs
| Column              | Type         | Constraints                    | Description                                     |
|---------------------|--------------|--------------------------------|-------------------------------------------------|
| id                  | UUID         | PK, default gen_random_uuid() | Unique log entry identifier                     |
| session_id          | VARCHAR(100) |                                | Chat session identifier                         |
| timestamp           | TIMESTAMPTZ  | DEFAULT now()                  | When this event was logged                      |
| user_input          | TEXT         |                                | Raw user input                                  |
| sanitized_input     | TEXT         |                                | Input after sanitization/filtering              |
| input_guardrail     | JSONB        |                                | Input layer decisions (passed/blocked, reasons) |
| policy_guardrail    | JSONB        |                                | Policy layer decisions (allowed ops, blocked ops)|
| instructional_guardrail | JSONB    |                                | Instructional layer decisions                   |
| execution_guardrail | JSONB        |                                | Execution layer decisions (tool/SQL validation) |
| output_guardrail    | JSONB        |                                | Output layer decisions (hallucination check, filtering) |
| tools_allowed       | JSONB        |                                | List of tools that were permitted               |
| tools_blocked       | JSONB        |                                | List of tools that were denied                  |
| generated_sql       | TEXT         |                                | SQL query generated by the agent                |
| query_result_summary| TEXT         |                                | Summary of query results (row count, etc.)      |
| llm_response_raw    | TEXT         |                                | Raw LLM response before output guardrail        |
| final_response      | TEXT         |                                | Final response delivered to user                |
| hallucination_check | JSONB        |                                | Hallucination detection results                 |
| guardrails_triggered| JSONB        |                                | Which guardrail layers were triggered/activated |
| token_usage         | JSONB        |                                | Token counts (prompt, completion, total)        |
| latency_ms          | INTEGER      |                                | Total processing time in milliseconds           |
| error_details       | TEXT         |                                | Error information if any layer failed           |
| status              | VARCHAR(20)  | DEFAULT 'success'              | success, blocked, error                         |
| created_at          | TIMESTAMPTZ  | DEFAULT now()                  | Record creation timestamp                       |

---

## Relationships
- `transactions.student_id` → `students.id` (many-to-one)
- `transactions.course_id` → `courses.id` (many-to-one)
- A student can have many transactions.
- A course can have many transactions.

## Indexes
- `students`: index on `department`, `status`, `email`
- `courses`: index on `department`, `course_code`, `semester`
- `transactions`: index on `student_id`, `course_id`, `payment_status`, `transaction_date`
- `guardrail_logs`: index on `session_id`, `timestamp`, `status`

## Seeding
- Minimum 1,000 records distributed across students, courses, and transactions.
- Realistic fake data with varied departments, semesters, amounts, statuses.
- Seeding script located at `backend/db/seed.py`.

## Core Rules
- Domain tables (students, courses, transactions) are READ-ONLY through the chat interface.
- The agent must never execute INSERT, UPDATE, DELETE, DROP, ALTER, or TRUNCATE on domain tables.
- The guardrail_logs table is APPEND-ONLY (insert by the monitoring layer only).
- All tables include `created_at` timestamps.
- UUIDs are used as primary keys for all tables.
