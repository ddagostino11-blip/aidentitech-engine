# Aidentitech Mapping Template

## Obiettivo
Mappare i dati del sistema cliente nel payload standard Aidentitech.

---

## Esempio MES → Aidentitech

| Sistema Cliente | Campo Aidentitech        |
|----------------|--------------------------|
| material_code  | entity.product_id        |
| batch_id       | entity.batch             |
| temp_sensor    | data.temperature         |
| gmp_flag       | data.gmp_compliant       |
| review_status  | data.batch_record_reviewed |
| deviation_flag | data.deviation_open      |
| capa_flag      | data.capa_open           |

---

## Note
- Il mapping NON è nel core Aidentitech
- Il mapping è responsabilità del cliente / integration layer
- Il payload finale deve rispettare lo schema standard

---

## Output richiesto
Payload JSON conforme a:

- context
- entity
- data
- metadata (opzionale)
