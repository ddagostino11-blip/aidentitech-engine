# ⚡ Pharma Pre-Compliance Demo

## What this is

This demo shows how a system evaluates real operational data before a regulatory audit.

It simulates a pharma validation process under an active regulatory regime.

---

## How to run

python3 pharma_demo.py

---

## Demo Flow

When you run the demo, choose:

1 → Operational pre-compliance case  
2 → Regulatory governance case  

---

## Operational Pre-Compliance (Core)

The system analyzes input data and produces one of four outcomes.

---

## Outcomes

INSUFFICIENT DATA
- Missing mandatory inputs  
- Evaluation is blocked  

---

NOT APPROVED
- Invalid or implausible data  
- Immediate rejection  

---

RISK ANALYSIS REQUIRED
- Valid data with compliance issues  
- Risks identified and explained  
- No dossier release  

---

AUDIT READY DOSSIER
- Fully compliant input  
- Case validated  
- Dossier ready  

---

## What to test (quick demo)

Run multiple times using custom input.

---

Case 1 — Missing data  
Leave fields empty  
Result: INSUFFICIENT DATA

---

Case 2 — Invalid data  
Example:
temperature = 999  
GMP = invalid  

Result: NOT APPROVED

---

Case 3 — Risk case  
Example:
GMP = NO  
temperature = 15  

Result: RISK ANALYSIS REQUIRED

---

Case 4 — Clean case  
Example:
GMP = YES  
temperature = 5  

Result: AUDIT READY DOSSIER

---

## Audit Trail

Each run generates a trace showing:

- input received  
- regulatory regime  
- decision  
- system action  

All steps are fully traceable.

---

## Regulatory Governance

Second mode simulates:

- detection of a regulatory change  
- creation of a new rule version  
- legal approval gate  

The system enforces controlled activation of new regulations.

---

## Key Idea

This is not post-audit validation.

This is:

- pre-audit compliance  
- deterministic decisioning  
- traceable execution  

The system prevents errors before they happen.
