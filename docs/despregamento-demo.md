# Demo pública nun VPS pequeno

Preparado e probado en local (sen despregar en ningún servidor). Levanta Eira en modo produción
(`EIRA_DEBUG=0`) con HTTPS automático, datos **ficticios** que se rexeneran cada noite e as
ferramentas de demostración activadas (bandexa de correo, TPV e simulador de pechadura).

Ficheiros: [`deploy/demo/docker-compose.yml`](../deploy/demo/docker-compose.yml),
[`deploy/demo/Caddyfile`](../deploy/demo/Caddyfile), [`deploy/demo/.env.example`](../deploy/demo/.env.example),
[`tools/demo-reseed-loop.sh`](../tools/demo-reseed-loop.sh).

## Arquitectura

| Servizo | Imaxe | Función | Límite de memoria |
|---|---|---|---|
| `caddy` | `caddy:2-alpine` | HTTPS (Let's Encrypt), compresión, ficheiros públicos de `/media/` | 128 MB |
| `app` | Dockerfile do proxecto | Django + gunicorn (2 workers, non root), migra e carga a demo no primeiro arranque | 512 MB |
| `reseed` | a mesma imaxe | Bucle sen cron: rexenera a demo ás 04:00 UTC e executa as tarefas periódicas cada 15 min | 256 MB |
| `db` | `postgres:16-alpine` | Base de datos | 256 MB |

## Consumo medido (sen IA)

Medido con `docker stats` en local (Docker Desktop, Windows 11) tras navegar 33 páxinas como
administración, incluídos os indicadores de 8 semanas:

| Servizo | RAM |
|---|---|
| app (2 workers gunicorn) | **139 MiB** |
| db (PostgreSQL 16, ~8.000 reservas) | 52–59 MiB |
| caddy | 12–15 MiB |
| reseed (en espera) | 3 MiB |
| reseed (pico durante a rexeneración) | ~83 MiB (mostraxe cada 1 s; pode ser algo maior) |
| **Total en repouso** | **≈ 210 MiB** |
| **Total no pico nocturno** | **≈ 300 MiB** |

Recomendación: **VPS de 1 GB de RAM e 1 vCPU** (de sobra); 512 MB funcionaría axustado. Sen IA:
o adaptador queda en `FakeAIAdapter` (resumo por regras, sen modelo).

## Pasos

1. VPS con Debian/Ubuntu e Docker (`apt install docker.io docker-compose-plugin`).
2. Un rexistro DNS `A` (e `AAAA` se hai IPv6) apuntando ao VPS, p. ex. `demo.eira.example`.
3. Abrir os portos 80 e 443 no cortalumes.
4. No servidor:
   ```bash
   git clone <repositorio> eira && cd eira/deploy/demo
   cp .env.example .env
   python3 -c "import secrets;print(secrets.token_urlsafe(50))"   # → EIRA_SECRET_KEY
   python3 -c "import secrets;print(secrets.token_urlsafe(20))"   # → POSTGRES_PASSWORD
   nano .env      # EIRA_DOMAIN, ACME_EMAIL, EIRA_SECRET_KEY, POSTGRES_PASSWORD
   docker compose up -d --build
   docker compose logs -f app     # «Demo lista…» e «Listening at…»
   ```
5. Abrir `https://<dominio>/` e entrar cun perfil de demostración.

Variables opcionais en `.env`: `EIRA_RESEED_HOUR_UTC` (hora da rexeneración, por defecto 4);
`HTTP_PORT`/`HTTPS_PORT` (só para probas locais se 80/443 están ocupados).

## Seguranza da demo

- `EIRA_DEBUG=0`, cookies `Secure`, HSTS, CSP estrita, `X-Robots-Tag: noindex`.
- Todos os datos son ficticios e bórranse cada noite; calquera cambio das persoas visitantes desaparece.
- **A bandexa `/dev/mailbox/` é pública na demo:** calquera pode ver os códigos de acceso
  enviados. Por iso a demo só debe usarse cos perfís ficticios; non hai que introducir correos reais.
  Nunca activar `EIRA_DEMO_TOOLS` nunha instalación real.
- As fotos de incidencias (privadas) pasan pola aplicación; Caddy só serve directamente `facilities/` e `tenants/`.

## Probas feitas en local (verificado)

- `docker compose up -d --build` con `EIRA_DOMAIN=localhost` e portos 18080/18443: HTTPS co
  certificado interno de Caddy, `200` en portada, concello, estáticos e simulador; `302` na xestión
  sen sesión; HTTP → HTTPS con `308`; cabeceiras HSTS e `noindex`.
- Acceso cun perfil de demo por HTTPS (CSRF e cookie segura) e 33 páxinas con `200`.
- Rexeneración: forzando `EIRA_RESEED_HOUR_UTC` á hora actual, o bucle rexenera a demo; as cargas
  simultáneas (primeiro arranque + rexeneración) serialízanse cun bloqueo consultivo de PostgreSQL.

## Non verificado

- Emisión dun certificado real de Let's Encrypt (require dominio público).
- Funcionamento continuado varios días nun VPS real.
