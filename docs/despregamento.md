# Despregamento

Eira está pensada para que a despregue **unha deputación ou mancomunidade** (moitos concellos nunha
instancia) ou un concello mediano no seu propio servidor. Non require servizos de pago nin contas
externas.

## Requisitos

- Servidor Linux con Docker (ou Python 3.12+ e PostgreSQL 14+).
- 1 vCPU e 1 GB de RAM abondan para varios concellos pequenos.
- Proxy inverso con HTTPS (nginx, Caddy ou o do CPD).

## Pasos con Docker

```bash
git clone <repositorio> eira && cd eira
cp .env.example .env
# Edita .env: EIRA_DEBUG=0, EIRA_SECRET_KEY (longa e aleatoria), EIRA_ALLOWED_HOSTS,
# EIRA_CSRF_TRUSTED_ORIGINS=https://deportes.deputacion.example, EIRA_DEMO_TOOLS=0,
# EIRA_SECURE_COOKIES=1, EIRA_BEHIND_PROXY=1, EIRA_HSTS_SECONDS=31536000,
# DATABASE_URL=postgres://… (contrasinal propio)
docker compose up -d --build
docker compose exec app python manage.py createsuperuser   # admin técnico
```

En produción **non** se activa `EIRA_SEED_DEMO`. O primeiro concello pódese crear desde o admin
técnico ou desde a vista de deputación (`/rexion/<slug>/novo-concello/`) tras crear a `Region` e
asignarlle unha persoa con `RegionMembership`.

## Dominios

- Un dominio para todos: `https://deportes.deputacion.example/c/<concello>/`.
- Subdominios: `EIRA_BASE_DOMAIN=deportes.deputacion.example` → `https://<concello>.deportes.deputacion.example/`.
- Dominio propio dun concello: campo «dominio propio» na configuración do concello.

## Tarefas periódicas (cron)

```cron
*/15 * * * *  docker compose exec -T app python manage.py booking_maintenance
0 5 * * *     docker compose exec -T app python manage.py generate_work_orders --days 14
```

## Integracións reais

| Integración | Variable | Notas |
|---|---|---|
| Correo | `EIRA_MAIL_ADAPTER=apps.integrations.mail.SmtpMailAdapter` + `EMAIL_HOST…` de Django | SMTP do concello |
| Cl@ve / Chave365 | `EIRA_IDENTITY_ADAPTER=…` | Implementar o esqueleto e tramitar a alta como provedor de servizo |
| Pagos | `EIRA_PAYMENT_ADAPTER=…RedsysAdapter` | TPV virtual da entidade do concello |
| Meteo | `EIRA_WEATHER_ADAPTER=…MeteoSixAdapter`, `EIRA_METEOSIX_API_KEY` | Clave gratuíta de MeteoGalicia |
| Mapa | `EIRA_TILE_URL`, `EIRA_TILE_ORIGIN` | Servidor de teselas propio ou OSM respectando a súa política de uso |
| IA (opcional) | `EIRA_AI_ADAPTER=…OpenAICompatibleAdapter`, `EIRA_AI_BASE_URL`, `EIRA_AI_MODEL` | llama.cpp/Ollama no CPD; desactivable con `EIRA_AI_ENABLED=0` |

## Ficheiros e copias

- Base de datos: copias de PostgreSQL (`pg_dump`) segundo a política do CPD.
- Ficheiros subidos: volume `media`. O proxy pode servir directamente `/media/facilities/` e `/media/tenants/` (públicos); `/media/incidents/` e `/media/workorders/` deben pasar á aplicación, que comproba permisos.
- Portabilidade: cada concello pode descargar a súa exportación íntegra en calquera momento.

## Actualizacións

```bash
git pull && docker compose up -d --build   # as migracións aplícanse ao arrancar
```
