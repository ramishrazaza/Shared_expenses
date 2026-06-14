# DECISIONS.md: Engineering Decisions Log

This document records the major technical design decisions made during the architecture and implementation of the Shared Expenses App, detailing the options considered, trade-offs, and final justifications.

---

## 1. CSV Processing: Dry-run & Review vs. Auto-Correction

* **Problem**: The import CSV contains messy data (missing values, typos, duplicate entries, currency errors). How should the importer handle these anomalies?
* **Options Considered**:
  1. **Option A: Full Auto-Correction**: Use regex and heuristics to clean data silently and import immediately.
  2. **Option B: Crash on Error**: Reject the entire CSV if any anomaly is found, requiring the user to fix the file manually.
  3. **Option C: Dry-run Anomaly Engine with UI Approvals (Chosen)**: Parse the CSV, log all errors in a staging table (`ImportAnomaly`), display a report in the frontend, let the user resolve/ignore issues, and then commit to the main database.
* **Trade-offs**:
  * **Option A**:
    * *Pros*: Zero friction for the user.
    * *Cons*: "Silent guesses" can lead to incorrect balances. Violates Meera's requirement ("I want to approve anything the app deletes or changes").
  * **Option B**:
    * *Pros*: Easiest to implement.
    * *Cons*: Terrible user experience. Users have to edit raw CSV rows in text editors.
  * **Option C (Chosen)**:
    * *Pros*: Meets all constraints. Gives users full control and audit visibility (Meera's duplicate approval). Prevents database contamination.
    * *Cons*: Higher backend and frontend engineering complexity.
* **Justification**: Giving the user control over imports while auto-detecting anomalies balances data integrity and product usability.

---

## 2. Dynamic Membership Validation

* **Problem**: How to handle expenses where participants were not members of the group at the time of the transaction (e.g., March electricity charging Sam who joined in April, or April groceries charging Meera who left in March)?
* **Options Considered**:
  1. **Option A: Static Memberships**: Assume all users in the system belong to the group for all expenses.
  2. **Option B: Group-Date Membership Checking (Chosen)**: Model group membership as a time-range table (`GroupMembership` with `joined_at` and `left_at`). During expense split calculations, verify if the date of the expense falls within each participant's membership duration.
* **Trade-offs**:
  * **Option A**:
    * *Pros*: Simple query logic.
    * *Cons*: Leads to Sam's complaint ("Why would March electricity affect my balance?") and incorrect charges for Meera.
  * **Option B (Chosen)**:
    * *Pros*: Accurately tracks user balances over time. Fully addresses Sam's and Meera's complaints.
    * *Cons*: More complex database queries and membership checks on splits.
* **Justification**: A relational schema modeling joining/leaving dates is the only correct way to enforce dynamic memberships over time.

---

## 3. Debt Simplification Algorithm

* **Problem**: How to simplify debts so that the number of transactions required to settle up is minimized (Aisha's requirement: "I just want one number per person").
* **Options Considered**:
  1. **Option A: Pairwise Debts**: Leave debts as-is (if A owes B ₹100, and B owes A ₹50, show A owes B ₹50).
  2. **Option B: Flow Minimization (Chosen)**: Calculate the net balance of each user (credits minus debits). Sort users into debtors and creditors, and greedily match the largest debtor with the largest creditor (greedy min-transfers algorithm).
* **Trade-offs**:
  * **Option A**:
    * *Pros*: Trivial to compute.
    * *Cons*: Members have to perform dozens of individual transfers. Doesn't fulfill Aisha's request.
  * **Option B (Chosen)**:
    * *Pros*: Fulfills Aisha's request perfectly. Reduces the number of settlement transfers to a maximum of $N-1$ where $N$ is the number of members.
    * *Cons*: Harder to compute and explain.
* **Justification**: The greedy min-transfers flow algorithm is the industry standard (used by Splitwise) for simplifying debts in shared groups.

---

## 4. Database Audit Trail & Soft Delete

* **Problem**: How to ensure balance calculations are explainable and verifiable (Rohan's requirement: "No magic numbers. I want to see exactly which expenses make that up") while supporting corrections?
* **Options Considered**:
  1. **Option A: Hard Delete**: When an expense is edited or deleted, remove it from the DB.
  2. **Option B: Soft Delete and Audit Trail (Chosen)**: Use an `is_deleted` flag on Expenses, store all changes in an `AuditLog` table with old/new JSON payloads, and offer a ledger trace endpoint.
* **Trade-offs**:
  * **Option A**:
    * *Pros*: Simple database maintenance.
    * *Cons*: Auditing balance calculations is impossible if records are gone.
  * **Option B (Chosen)**:
    * *Pros*: Fulfills Rohan's audit requirement. Provides history log of corrections. Excellent security practice.
    * *Cons*: Higher storage requirements.
* **Justification**: An audit log coupled with soft-delete is essential for a production-grade financial tracking system where every balance modification must be explainable.
