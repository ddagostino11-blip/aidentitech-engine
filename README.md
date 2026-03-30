# 🔒 Master Pharma Validation System

Sistema di validazione documentale con integrità crittografica, firma digitale e prova temporale.

---

## 🎯 Obiettivo

Garantire che ogni dossier:

- non sia modificabile
- sia firmato
- sia tracciabile nel tempo
- sia verificabile da terze parti

---

## ⚙️ Componenti principali

### 1. Validazione dossier
- hashing canonico JSON
- firma RSA (OpenSSL)
- verifica automatica

Script:
- `run_validation.py`
- `verify_dossier.py`

---

### 2. Chain (tipo blockchain)
- ogni dossier contiene `previous_hash`
- garantisce integrità sequenziale

Script:
- `verify_chain.py`

---

### 3. Ledger append-only
- registro completo degli eventi
- hash-linked
- non modificabile senza rottura

File:
- `ledger.jsonl`

Script:
- `verify_ledger.py`

---

### 4. Firma del ledger
- hash del ledger firmato con chiave privata
- verifica con chiave pubblica

File:
- `ledger.sig`

Script:
- `verify_ledger_signature.py`

---

### 5. Timestamp esterno (TSA)
- prova temporale certificata
- tramite servizio `freetsa.org`

File:
- `timestamps/ledger_timestamp.tsr`

---

### 6. Client proof package
Pacchetto verificabile dal cliente contenente:
- dossier
- firma
- chiave pubblica

Cartella:
- `client_proof/`

Script:
- `client_proof/verify.py`

---

## 🚀 Esecuzione

### Generazione completa

```bash
python3 run_validation.py
