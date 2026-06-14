# AI_USAGE.md: AI Collaboration & Correction Log

This document records the interaction with the AI assistant during the implementation of the Shared Expenses App, specifically highlighting prompts used, errors made by the AI, and how they were corrected.

---

## 1. AI Tools & Models Used

* **AI Coding Agent**: Antigravity (powered by Gemini 3.5 Flash)
* **Usage**: Collaborative planning, database design, backend services code generation, React components implementation, and markdown documentation drafting.

---

## 2. Important Prompts & Workflows

1. **Architecture & Schema Planning**:
   "Act like a Staff Engineer. Analyze the Spreetail Shared Expenses App requirements, design a relational DB schema that handles memberships over time, duplicate CSV anomalies, and simplified balances, and write a PRD."
2. **CSV Anomaly Rules**:
   "Define code rules to detect duplicates, format spacing typos, missing payer fields, settlement items, currency issues, negative amounts, and membership conflicts. Log them in an ImportAnomaly table for user review."
3. **simplified Debt Flow**:
   "Implement a greedy min-transfers algorithm to simplify debts in a shared group. Return a list of who pays whom."
4. **Balance Audit Trail (Rohan's Trace)**:
   "Generate a chronological ledger of all user credits, debits, and settlements so that the running balance is verifiable with no magic numbers."

---

## 3. Concrete Cases of AI Errors & Resolutions

### Case 1: Incorrect ForeignKey Argument in Django Models
* **AI Generates**:
  ```python
  group = models.ForeignKey(Group, on_name='group', on_delete=models.CASCADE, related_name='memberships')
  ```
* **How Detected**:
  When creating database migrations, Django threw a compilation error: `TypeError: __init__() got an unexpected keyword argument 'on_name'`.
* **How Corrected**:
  The developer caught this during compilation, realized `on_name` was an AI hallucination of the database model, removed it, and kept the standard `on_delete=models.CASCADE` constraint.

### Case 2: Incorrect Path for Artifact Generation
* **AI Generates**:
  The AI tried to save the `implementation_plan.md` using the path:
  `C:\Users\ASUS\antigravity\brain\<conv_id>\implementation_plan.md`
* **How Detected**:
  The file writing tool returned an error stating that the path was invalid because it lacked the `.gemini` folder structure (which is where conversation artifacts are stored on the host system).
* **How Corrected**:
  The path was corrected to the correct sandboxed path:
  `C:\Users\ASUS\.gemini\antigravity\brain\<conv_id>/implementation_plan.md` and successfully written.

### Case 3: Incomplete Date Parsing logic
* **AI Generates**:
  The AI initially wrote the date parser assuming all dates were in `YYYY-MM-DD` or `DD/MM/YYYY` format. It forgot to handle the abbreviation format in the CSV like `Mar 14`.
* **How Detected**:
  When reviewing the CSV data, the developer noticed row 27 had `Mar 14`. Running a quick test on the parser revealed it returned `Unrecognized date format` and would reject the row.
* **How Corrected**:
  We modified the `parse_date` method in `import_service.py` to support `'%b %d'` (abbreviated month name and day) and set the default year to `2026` based on the sequence timeline.
