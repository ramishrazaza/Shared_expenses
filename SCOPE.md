# SCOPE.md: CSV Import Anomalies & Database Schema Document

This document outlines the CSV anomalies found in `expenses export.csv`, their detection rules, the resolution handling strategies implemented in the backend parser, and the database schema.

---

## 1. CSV Anomaly Log & Detection Policies

The system identifies and logs **21 distinct anomalies across 12 core categories** from `expenses export.csv`. Each anomaly is categorized by its severity and mapped to a detection policy.

### Anomaly Summary & Handling Policies

| Row(s) | Anomaly Type | Severity | Impact | Detection Logic | Handling Strategy |
|---|---|---|---|---|---|
| **5 & 6** | Duplicate Record | Medium | Double-counts Marina Bites dinner | Matches rows with identical date, amount, payer, split members, and splits. | Flagged in UI. Default resolution keeps Row 5 and ignores/skips Row 6. |
| **7** | Format Issue | Low | String quotes and comma in `"1,200"` | Identifies string quotes/commas in the amount field. | Auto-cleans quotes/commas, parsing it as `1200.00` decimal. |
| **9** | Case Inconsistency | Low | Lowercase `priya` mismatch | Case-insensitive match on user registry. | Normalizes to capitalized name `Priya` to match DB record. |
| **10** | Precision Issue | Low | Three decimal places `899.995` | Checks if decimal places exceed two digits. | Rounds amount to two decimal places: `900.00` or `899.99`. |
| **11** | Naming Mismatch | Medium | Paid by `Priya S` | Payer string doesn't match a direct username. | Uses fuzzy matching to map `Priya S` to `Priya`. |
| **13** | Missing Payer | Critical | `paid_by` field is empty | Checks for empty or null payer. | **Blocker**. Flags as critical error. User must select payer before importing. |
| **14** | Settlement disguised as Expense | Medium | Rohan paid Aisha back | Empty `split_type` and split list contains single user. | Parses and stores as a `Settlement` record, bypassing Expense table. |
| **15** | Percentage Split Mismatch | High | Split sum exceeds 100% (110%) | Sums percentage values in `split_details`. | Flags mismatch. Normalizes percentages or requests manual override. |
| **16** | Date Format Inconsistency | Low | `01/03/2026` vs `2026-02-01` | Attempts to parse using `YYYY-MM-DD`, falls back to `DD/MM/YYYY`. | Standardizes date to date object (`2026-03-01`) before DB save. |
| **20, 21, 23, 26** | Multi-Currency | Medium | USD transactions in a rupee app | Checks if `currency == 'USD'`. | Auto-converts to INR using conversion rate (default 83.0). |
| **23** | External/Unknown User | Medium | Split includes `Kabir` | Participant name not in group membership history. | Shadow/guest user `Kabir` created for the day or charged to `Dev`. |
| **24 & 25** | Double Entry Conflict | High | Dinner logged twice with different payer/amounts | Matches same date and similar description but different payer/amount. | Flags conflict. User chooses correct row (Row 25) and skips the other. |
| **26** | Negative Amount | Medium | Parasailing refund `-30 USD` | Checks if amount is less than 0. | Processed as a refund: negative share distributed to participants. |
| **27** | Trailing Spacing | Low | Name has spacing `rohan ` | Checks for leading/trailing whitespaces in user fields. | Trims whitespaces from name before matching. |
| **28** | Missing Currency | Low | Currency is empty for Groceries DMart | Checks for empty currency field. | Defaults to Group's base currency (INR). |
| **31** | Zero Amount | Low | Swiggy order amount is `0` | Checks if amount is exactly zero. | Skip importing row or flags as zero-amount. |
| **32** | Percentage Split Mismatch | High | Weekend brunch percentages sum to 110% | Sums percentages in `split_details`. | Flags mismatch; requests user confirmation to normalize. |
| **34** | Date Ambiguity | Medium | `04/05/2026` out of chronological sequence | Checks sequential flow (Mar 28 -> 04/05/2026 -> Apr 1). | Flags date ambiguity (Is it April 5 or May 4?); resolves to April 5. |
| **36** | Membership Conflict | High | Meera charged in April after leaving | Checks participant status against membership left_at. | Flags conflict. Excludes Meera from split; re-calculates shares. |
| **38** | Settlement disguised as Expense | Medium | Sam paid deposit to Aisha | empty `split_type` and single target. | Imports as a `Settlement` record (Sam -> Aisha: 15000). |
| **42** | Split Type Conflict | Low | Split type `equal` but details has shares | Checks if details are provided for equal split. | Ignores split_details since splits are equal (1:1:1:1); uses equal parser. |

---

## 2. Database Schema Explanation

We implemented a relational database schema using Django ORM to model the requirements.

### Entity Relationship Diagram
```text
  +-------------+          +-------------------+          +-------------+
  |    User     | <------- |  GroupMembership  | -------> |    Group    |
  +-------------+          +-------------------+          +-------------+
     |       |                       |                       |      |
     |       |                       |                       |      |
     |       |                       |                       |      |
     v       v                       v                       v      v
  +-------------+          +-------------------+          +-------------+
  |   Expense   | <------- |ExpenseParticipant |          | Settlement  |
  +-------------+          +-------------------+          +-------------+
```

### Table Details

1. **`User`**: Custom user model extending Django's default auth user. Serves as authentication and audit registry.
2. **`Group`**: Holds group information, including its base currency (defaults to INR).
3. **`GroupMembership`**: Stores dynamic membership records, containing `joined_at` and `left_at` fields. This is used to validate whether a user should be charged for an expense on a given date (e.g. Sam joining in April, Meera leaving in March).
4. **`Expense`**: Stores individual expense items (description, total amount, base currency amount, paid_by, date). Supports soft delete via `is_deleted` flag to satisfy audit trails.
5. **`ExpenseParticipant`**: Bridges expenses to users, storing their computed share amount and original split detail values.
6. **`Settlement`**: Records peer-to-peer debt payments (e.g., Rohan paid Aisha back, Sam's deposit to Aisha).
7. **`ImportBatch`**: Tracks CSV imports, storing raw CSV text and batch processing status (`pending_review`, `completed`).
8. **`ImportAnomaly`**: Logs detected anomalies, their type, severity, raw row data, status (`detected`, `resolved`, `ignored`), and resolution overrides.
9. **`AuditLog`**: Logs creations, updates, soft-deletions, and anomaly resolutions with user attribution and old/new JSON payloads.
