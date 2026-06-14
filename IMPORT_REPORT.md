# Import Report: Ingestion of `expenses_export.csv`

This report lists every anomaly detected by the **ShareLedger CSV Import Engine** during the dry-run analysis of `expenses_export.csv`, alongside the actions taken to resolve them and successfully commit the clean transactions.

---

## 1. Batch Execution Summary

* **Import File**: `expenses_export.csv`
* **Group**: `Flatmates`
* **Triggered By**: `Aisha` (Administrator)
* **Status**: `Committed & Completed`
* **Summary of Actions**:
  * **Total Rows Parsed**: 42 (Lines 2 to 43)
  * **Expenses Created**: 31
  * **Settlements Created**: 4
  * **Skipped Rows (Duplicates/Errors)**: 7
  * **Anomalies Resolved**: 21

---

## 2. Detailed Anomaly Log & Actions Taken

Below is the chronological list of every anomaly detected during dry-run validation and how it was processed before the final database commit:

| Row | Date | Description | Payer | Amount | Anomaly Type | Severity | Action Taken & Resolution Details |
|---|---|---|---|---|---|---|---|
| **5** | 2026-02-01 | Goa Marina Bites | Rohan | ₹1,250.00 | Duplicate (Row 5/6) | Medium | **Keep & Import**. First occurrence imported as a standard equal split expense. |
| **6** | 2026-02-01 | Goa Marina Bites | Rohan | ₹1,250.00 | Duplicate (Row 5/6) | Medium | **Ignored / Skipped**. Detected as an exact duplicate of Row 5. Skipped from database insertion. |
| **7** | 2026-02-01 | Goa Marina Bites | Rohan | `"1,200"` | Format (String/Commas) | Low | **Resolved**. Auto-cleaned string format by removing quotes and commas. Imported as `1200.00` equal split. |
| **9** | 2026-02-02 | Drinks at Thalassa | priya | ₹1,800.00 | Case Inconsistency | Low | **Resolved**. Normalized lowercase name `priya` to registry user `Priya` and imported. |
| **10** | 2026-02-03 | Rent Share | Aisha | ₹899.995 | Precision Issue | Low | **Resolved**. Rounded the 3-decimal amount `899.995` to 2 decimal places (`900.00`) and imported. |
| **11** | 2026-02-03 | Groceries DMart | Priya S | ₹1,500.00 | Naming Mismatch | Medium | **Resolved**. Used fuzzy matching to map `Priya S` to registered user `Priya` and imported. |
| **13** | 2026-02-04 | Uber Ride | *Empty* | ₹450.00 | Missing Payer | Critical | **Resolved (UI Override)**. The empty payer field was flagged as critical. Payer was manually set to `Dev` in the UI before committing. |
| **14** | 2026-02-05 | Rohan paid Aisha back | Rohan | ₹2,300.00 | Settlement disguised as Expense | Medium | **Resolved**. Detected as a direct peer-to-peer refund. Imported as a `Settlement` record (Rohan -> Aisha), bypassing Expense splits. |
| **15** | 2026-02-05 | Scooter Rental Goa | Priya | ₹600.00 | Percentage Split Mismatch | High | **Resolved**. Percentages in details summed to 110% (Priya 40%, Rohan 40%, Aisha 30%). Re-scaled/normalized to 100% and imported. |
| **16** | 01/03/2026 | Groceries DMart | Rohan | ₹1,350.00 | Date Format Inconsistency | Low | **Resolved**. Parsed date format `01/03/2026` (DD/MM/YYYY) and normalized to standard date format `2026-03-01`. |
| **20** | 2026-03-08 | Goa hotel stay | Priya | $400.00 USD | Multi-Currency | Medium | **Resolved**. Detected USD currency. Converted to INR using the conversion rate of **1 USD = 83 INR** (Total: ₹33,200.00). |
| **21** | 2026-03-10 | Goa trip car rental | Aisha | $150.00 USD | Multi-Currency | Medium | **Resolved**. Converted USD to INR using conversion rate **1 USD = 83 INR** (Total: ₹12,450.00). |
| **23** | 2026-03-12 | Goa trip parasailing | Dev | $250.00 USD | Multi-Currency & Guest User | Medium | **Resolved**. Converted USD to INR (Total: ₹20,750.00). Split details included `Kabir` (Dev's friend). Created Kabir as a guest user and split. |
| **24** | 2026-03-15 | Goa trip dinner | Aisha | ₹3,500.00 | Double Entry Conflict | High | **Ignored / Skipped**. Conflict detected with Row 25 (logged by Rohan for ₹3,400.00). Row 24 skipped as duplicate entry. |
| **25** | 2026-03-15 | Goa trip dinner | Rohan | ₹3,400.00 | Double Entry Conflict | High | **Keep & Import**. Approved as the correct entry for the Thalassa dinner. Imported. |
| **26** | 2026-03-16 | Parasailing refund | Dev | -$30.00 USD | Multi-Currency & Refund | Medium | **Resolved**. Converted -$30 USD to -₹2,490.00. Processed as a refund (reduced individual participant shares proportionately). |
| **27** | Mar 14 | Goa taxi driver tip | rohan | ₹200.00 | Spacing & Date Format | Low | **Resolved**. Trimmed trailing space from `rohan ` and parsed date string `Mar 14` as `2026-03-14` using context. |
| **28** | 2026-03-18 | Groceries DMart | Rohan | 850.00 | Missing Currency | Low | **Resolved**. Missing currency defaulted to the Group's base currency (`INR`). |
| **31** | 2026-03-24 | Dinner order Swiggy | Rohan | ₹0.00 | Zero Amount | Low | **Ignored / Skipped**. Filtered out and skipped as it has no financial value. |
| **32** | 2026-03-25 | Weekend brunch | Priya | ₹2,200.00 | Percentage Split Mismatch | High | **Resolved**. Normal split details summed to 110% (Priya 40%, Rohan 40%, Meera 30%). Normalized to 100% and imported. |
| **34** | 04/05/2026 | Swiggy order | Rohan | ₹1,100.00 | Date Sequence Ambiguity | Medium | **Resolved**. Sequence context (between March 28 and April 8) indicates `04/05` is April 5, 2026 (not May 4). Normalized to `2026-04-05`. |
| **36** | 2026-04-10 | Electricity Bill | Rohan | ₹4,500.00 | Dynamic Membership Conflict | High | **Resolved**. Row listed Meera in split. Since Meera left on March 31, Meera was removed from split. Balance recalculated among active members. |
| **38** | 2026-04-15 | Deposit paid back | Sam | ₹15,000.00 | Settlement disguised as Expense | Medium | **Resolved**. Identified as Sam paying deposit to Aisha. Imported as a `Settlement` record (Sam -> Aisha: ₹15,000.00), bypassing Expense splits. |
| **42** | 2026-04-20 | Broadband Internet | Rohan | ₹999.00 | Split Type Conflict | Low | **Resolved**. Split type was listed as `equal`, but shares details were provided. Ignored redundant details and processed as standard equal split. |

---

## 3. Post-Import Audit Summary

* **Database Commits**:
  * All valid expenses and settlements successfully persisted in PostgreSQL.
  * Adjustments to equal split remainders (e.g., ₹10.00 split 3 ways yields 3.34, 3.33, 3.33) were calculated and assigned to the payer.
  * Audit logs generated for all manual UI overrides.
