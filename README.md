# Eira

**Eira · Software libre para a xestión deportiva municipal.** Reservas, acceso ás instalacións, mantemento e actividades deportivas do concello, nunha soa plataforma.

Eira é unha plataforma de software libre para que os concellos —sobre todo os pequenos— xestionen as
súas instalacións deportivas durante todo o ciclo: **atopar → reservar → pagar → acceder → usar →
pechar e avisar → manter → medir**. Funciona tamén nas parroquias sen conserxe: a chave custodiada
nun bar, un teclado con código que non necesita internet ou unha pechadura conectada.

> Na aldea, a *eira* era o espazo común de pedra onde se xuntaba a veciñanza. Este proxecto quere ser iso para o deporte municipal.

## Que inclúe

- **Veciñanza:** consulta sen rexistro (lista accesible e mapa), grella semanal clara (libre, ocupada,
  recomendada), reserva en tres pasos con aceptación expresa das normas, pagamento, cambios e
  cancelacións con regras, historial, recibos, calendario `.ics` e avisos.
- **Acceso por niveis:** 0) QR de entrada; 1) chave custodiada con aviso á custodia; 2) **código temporal
  sen conexión** válido só durante a franxa; 3) pechadura conectada con botón «Abrir» e luces.
- **Pechar e avisar:** checklist de peche e avisos de avaría con foto en 30 segundos.
- **Concello:** panel do día, alta asistida de instalacións con plantillas, horarios, festivos e bloqueos
  con aviso automático, tarifas e normas versionadas, reserva por teléfono/mostrador, indicadores con
  táboas accesibles e CSV.
- **Mantemento:** plans preventivos, ordes de traballo, calendario compartido e app do operario que funciona sen cobertura.
- **Multi-concello:** cada concello illado e configurable; vista de deputación para comparar e dar de alta concellos.
- **Soberanía:** exportación íntegra en formatos abertos, API OpenAPI 3.1, datos abertos DCAT-AP, IA opcional só autoaloxada.

## Probalo

Con Docker:

```bash
docker compose up --build
```

Sen Docker (Python 3.12+):

```bash
python -m venv .venv && . .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
python tools/tasks.py dev                           # ou: make dev
```

Abre <http://127.0.0.1:8000> e escolle un perfil de demostración (persoas ficticias).

## Documentación

- [Visión xeral e arquitectura](docs/arquitectura/vision-xeral.md) · [Modelo de datos](docs/arquitectura/modelo-datos.md)
- [Códigos de acceso sen conexión](docs/access/offline-codes.md)
- [Interoperabilidade](docs/interoperabilidade.md) · [Seguridade e RXPD](docs/seguridade-rxpd.md)
- [Accesibilidade](docs/accesibilidade/criterios.md) · [Despregamento](docs/despregamento.md)
- [Guión da demostración](docs/demo/guion-demo.md)

## Licenza

[EUPL-1.2](LICENSE) © Equipo Eira. Contribucións benvidas: le [CONTRIBUTING.md](CONTRIBUTING.md).
