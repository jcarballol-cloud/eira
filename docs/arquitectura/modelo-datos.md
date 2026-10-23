# Modelo de datos

Todas as entidades dun concello levan `municipality` (illamento multi-concello). Diagrama
simplificado (só campos principais).

```mermaid
erDiagram
  REGION ||--o{ MUNICIPALITY : agrupa
  MUNICIPALITY ||--o{ PARISH : ten
  MUNICIPALITY ||--o{ FACILITY : xestiona
  MUNICIPALITY ||--o{ MEMBERSHIP : "roles"
  USER ||--o{ MEMBERSHIP : ten
  USER ||--o{ REGION_MEMBERSHIP : "region_admin"
  REGION ||--o{ REGION_MEMBERSHIP : ""
  USER ||--o{ RESIDENCY : "empadroamento validado"
  MUNICIPALITY ||--o{ RESIDENCY_INVITATION : emite
  USER ||--o| HOUSEHOLD : "responsable"
  HOUSEHOLD ||--o{ DEPENDENT : "menores"
  DEPENDENT ||--o{ CONSENT : "revogables, con data"

  PARISH ||--o{ FACILITY : ""
  FACILITY ||--o{ OPENING_HOURS : horario
  FACILITY ||--o{ TARIFF : "por colectivo"
  FACILITY ||--o{ RULES_VERSION : "normas versionadas"
  FACILITY ||--o{ CLOSURE : "peches (ou todo o concello)"
  FACILITY ||--o| LOCK_DEVICE : "niveis 2 e 3"

  FACILITY ||--o{ BOOKING : ""
  USER ||--o{ BOOKING : ""
  RULES_VERSION ||--o{ BOOKING : "aceptada"
  BOOKING ||--o| KEY_HANDOVER : "nivel 1"
  BOOKING ||--o{ ACCESS_EVENT : ""
  FACILITY ||--o{ ACCESS_EVENT : ""

  FACILITY ||--o{ INCIDENT : ""
  BOOKING ||--o{ INCIDENT : "checklist de peche"
  INCIDENT ||--o{ WORK_ORDER : ""
  FACILITY ||--o{ MAINTENANCE_PLAN : ""
  MAINTENANCE_PLAN ||--o{ MAINTENANCE_TASK : ""
  MAINTENANCE_TASK ||--o{ WORK_ORDER : "xera"
  WORK_ORDER ||--o{ WORK_ORDER_PHOTO : ""

  ACTIVITY ||--o{ GROUP : ""
  GROUP ||--o{ ENROLLMENT : ""
  USER ||--o{ ENROLLMENT : ""
  DEPENDENT ||--o{ ENROLLMENT : ""
  GROUP ||--o{ SESSION : ""
  SESSION ||--o{ ATTENDANCE : ""
  ENROLLMENT ||--o{ ATTENDANCE : "presenza, RPE, minutos"
  FITNESS_BATTERY ||--o{ FITNESS_TEST : ""
  ENROLLMENT ||--o{ FITNESS_RESULT : ""

  USER ||--o{ NOTIFICATION : ""
  USER ||--o{ AUDIT_LOG : "actor"

  MUNICIPALITY {
    string slug
    string accent_color
    json modules "feature flags"
    int cancellation_hours
    int late_cancel_penalty_pct
    int max_advance_days
  }
  USER {
    string email "único dato obrigatorio"
    int birth_year "opcional (tarifas)"
    string identity_subject "HMAC opaco de Cl@ve"
  }
  FACILITY {
    string kind
    int access_level "0-3"
    int capacity
    int slot_minutes
    bool step_free
    string checkin_token "QR nivel 0"
  }
  BOOKING {
    string reference
    datetime start
    datetime end
    string status "pending_payment|confirmed|cancelled|used|no_show"
    int price_cents
    datetime rules_accepted_at
    datetime checked_in_at
    bool close_door_ok
  }
  LOCK_DEVICE {
    string kind "offline|connected"
    string secret "HOTP, sensible"
    int step_minutes
    int tolerance_minutes
    int lockout_count
  }
  ENROLLMENT {
    string status "active|pending_payment|waitlist|cancelled"
    string pseudonym "HMAC para o observatorio"
  }
```

## Notas

- **Normas versionadas:** `RulesVersion` é inmutable; cada reserva garda a versión aceptada e a data.
- **Datos de menores:** só nome e ano; inscrición só co consentimento `data`; o esforzo e as probas
  só co consentimento `performance`.
- **Auditoría:** `AuditLog` rexistra as accións sensibles (pagos, cancelacións, cambios de normas,
  exportacións, aperturas remotas, consentimentos).
- **Táboas de integración simulada** (`DevMail`, `OutboundMessage`, `FakePayment`) só se usan en
  desenvolvemento/demostración.
