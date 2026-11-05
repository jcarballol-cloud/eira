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
- **Para todas as persoas (v1.5):** botón «Escoitar» coa voz do dispositivo e «Alerta» en todos os perfís, co DESA e a ubicación para ditar ao 112.
- **Datos e legalidade (v1.5):** mapa de procedencia só agregado (n ≥ 10), documentos legais versionados (modelos de exemplo) e acreditación con menores sen gardar o certificado.
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

### A demo en 5 minutos

1. **Arrancar** (1–3 min): `docker compose up --build` (precisa Docker) ou, sen Docker,
   `python tools/tasks.py dev` (Python 3.12+; usa SQLite e carga a demo). Agarda a que diga que
   escoita no porto 8000.
2. **Entrar:** abre <http://localhost:8000>. Non hai contrasinais: escolle o concello (Vilardeiras ou
   Pontedouro, ficticios) e un perfil. Todas as persoas, correos e datos son inventados.
3. **Probar como veciña** (perfil *Uxía*): reserva unha franxa no pádel → paga no TPV simulado →
   recibe o código de acceso → abre a pechadura no simulador. Mira tamén *O meu carné* e *Incidencia
   ou seguridade*.
4. **Probar como concello** (perfil *Concello de Vilardeiras*): panel do día, axenda, incidencias,
   *Máis ferramentas → Rendemento*, *Enquisas (NPS)* e *Rexistro de auditoría*.
5. **Ver os correos e avisos** que enviaría Eira: na barra da demo, *Bandexa de correo* (`/dev/mailbox/`).
6. **Volver a empezar:** `python tools/tasks.py seed` rexenera os datos da demo.

O guión completo está en [docs/demo/guion-demo.md](docs/demo/guion-demo.md). Variables de contorno
en [.env.example](.env.example) (en local abonda con `EIRA_DEBUG=1`).

### Comprobar que todo está ben

```bash
python tools/tasks.py test      # tests unitarios e de integración
python tools/tasks.py e2e       # Playwright + axe (WCAG 2.1 AA), arranca un servidor propio
python tools/tasks.py lint      # ruff
python tools/tasks.py licenses  # licenzas das dependencias compatibles coa EUPL-1.2
```

## Documentación

- **[LEEME: uso e requisitos legais](LEEME.md)** ([en castelán](LEEME.es.md)): perfís, primeiros pasos,
  o que ten que facer o concello para despregala, que pasa se modificas Eira e aviso sobre os modelos de exemplo.
- [Visión xeral e arquitectura](docs/arquitectura/vision-xeral.md) · [Modelo de datos](docs/arquitectura/modelo-datos.md)
- [Códigos de acceso sen conexión](docs/access/offline-codes.md)
- [Interoperabilidade](docs/interoperabilidade.md) · [Seguridade e RXPD](docs/seguridade-rxpd.md)
- [Accesibilidade](docs/accesibilidade/criterios.md) · [Despregamento](docs/despregamento.md)
- [Guión da demostración](docs/demo/guion-demo.md)
- Para concellos: [modelo de ordenanza de prezos públicos e taxa](docs/concello/ordenanza-modelo.md) ·
  [plantilla de EIPD](docs/rxpd/eipd-plantilla.md) · [matriz de datos por perfil](docs/rxpd/matriz.md)

## Licenza

[EUPL-1.2](LICENSE) © Equipo Eira. Contribucións benvidas: le [CONTRIBUTING.md](CONTRIBUTING.md).

- **Licenza:** EUPL-1.2 (Licenza Pública da Unión Europea), compatible con GPL, AGPL, MPL e outras
  (ver o anexo da licenza). Podes usar, estudar, modificar e redistribuír Eira, tamén para
  prestar servizos; se distribúes versións modificadas, teñen que seguir baixo EUPL-1.2 (ou unha
  licenza compatible, nos casos do artigo 5 da EUPL).
- **Como contribuír:** [CONTRIBUTING.md](CONTRIBUTING.md) (pasos e requisitos técnicos),
  [GOVERNANCE.md](GOVERNANCE.md) (quen decide, contribucións de concellos e empresas, folla de ruta),
  [código de conduta](CODE_OF_CONDUCT.md) e [seguridade](SECURITY.md) para comunicar vulnerabilidades.
- **Metadatos para catálogos públicos:** [publiccode.yml](publiccode.yml) (validado co
  `publiccode-parser-go` oficial: `python tools/tasks.py publiccode`).
