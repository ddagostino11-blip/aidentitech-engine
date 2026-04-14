# Aidentitech Integration Guide

## Overview
Aidentitech è un decision layer che si integra sopra sistemi esistenti:

- MES
- QMS
- ERP
- IoT

## Architettura

Client System → Mapping Layer → Aidentitech API (/validate)

## Payload Standard

Il sistema accetta payload strutturati:

- context → informazioni origine
- entity → entità (prodotto, batch)
- data → dati operativi
- metadata → opzionale

## Integrazione minima

1. Estrarre dati dal sistema cliente
2. Mappare i campi nel formato Aidentitech
3. Inviare a:

POST /validate

## Sicurezza

- autenticazione via API key
- tenant isolation
- audit trail completo

## Output

Aidentitech restituisce:

- decisione
- spiegazione
- audit trail
- hash ledger

## Posizionamento

Aidentitech NON sostituisce sistemi esistenti.
Opera come layer sopra per:

- decisioni
- compliance
- audit
