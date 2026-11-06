<!-- SPDX-License-Identifier: EUPL-1.2 -->
# Demo pública

Eira en modo produción (`EIRA_DEBUG=0`) en `https://eira.engramlab.es`, para ver a aplicación cun
clic e sen instalar nada. Só leva **datos ficticios**, que se rexeneran cada noite, e ferramentas de
demostración: bandexa de correo, TPV, Cl@ve e simulador de pechadura.

Ficheiros, en [`deploy/demo/`](../deploy/demo/):

| Ficheiro | Para que serve |
|---|---|
| `docker-compose.demo.yml` | Base: app, PostgreSQL, bucles e Caddy propio en 80/443 |
| `docker-compose.tras-proxy.yml` | Variante para un servidor que xa ten un proxy en 80/443 |
| `Caddyfile`, `Caddyfile.tras-proxy` | Entrada de cada variante |
| `sitio.caddy` | Regras comúns: `robots.txt`, admin pechado, vídeos, ficheiros públicos e proxy á app |
| `.env.example` | Modelo do `.env`, que nunca vai ao repositorio |
| `videos/` | Os vídeos da portada, que tampouco van ao repositorio |

## Servizos

| Servizo | Función | Límite | RAM medida |
|---|---|---|---|
| `eira-web` | Caddy: vídeos, `robots.txt`, ficheiros públicos e proxy á app | 96–128 MB | 22–44 MiB |
| `app` | Django + Gunicorn (2 workers); migra e carga a demo no primeiro arranque | 512 MB | 154–174 MiB |
| `db` | PostgreSQL 16 | 256 MB | 44–122 MiB |
| `reseed` | Rexenera a demo ás 04:00 de Madrid; tarefas periódicas cada 15 min | 384 MB | 3 MiB, pico 99 MiB |
| `notices` | `send_notices` cada 5 min, só cara aos simuladores | 192 MB | 3–7 MiB |
| **Total** | | | **≈ 320 MiB en repouso, ≈ 450 MiB no pico nocturno** |

Medido con `docker stats` en local (Docker Desktop, Windows 11), con PostgreSQL e sen IA.

## Que a fai segura como demo aberta

- **Sen envíos reais.** Os adaptadores están fixados aos simuladores no compose, por riba do `.env`.
  Ademais, a app, a base de datos e os bucles están nunha rede de Docker **sen saída a Internet**.
- **`EIRA_PUBLIC_DEMO=1`** activa o aviso «Demo con datos ficticios. Restáurase cada noite.» e os
  vídeos na portada, quita a ruta da administración de Django e rexeita correos que non sexan
  `*.example`, porque a bandexa `/dev/mailbox/` é pública. Cada rexeneración borra todas as contas.
- **Administración de Django:** 404 en Caddy e sen ruta na aplicación.
- **Límite no inicio de sesión:** 5 envíos por correo e 20 por IP á hora, e 5 intentos por código.
  Coa IP real da visita: `client_ip()` só cre o valor que engade o proxy, e cada Caddy substitúe o
  que mande o cliente. Sen isto, todas as visitas compartirían o límite da IP do proxy.
- **Indexación:** `robots.txt` con `Disallow: /` e `Noindex: /`, e cabeceira
  `X-Robots-Tag: noindex, nofollow`. Os buscadores xa non fan caso da liña `Noindex:` en
  `robots.txt`: quen impide a indexación son as outras dúas.
- **Vídeos:** ficheiros locais servidos por Caddy, sen servizos externos. As páxinas con mapa si
  piden as teselas a OpenStreetMap desde o navegador da visita, como na aplicación normal.
- **Copias de seguridade:** non fan falta, porque a demo rexenérase.

**Non se evita:** alguén pode escribir un dato real nun campo de texto libre (nome, comentario). Por
iso o aviso da portada, e por iso todo se borra cada noite.

## Rexeneración nocturna

`tools/demo-reseed-loop.sh` executa `seed_demo` ás 04:00 de Madrid (`TZ=Europe/Madrid`,
`EIRA_RESEED_HOUR`) e borra os ficheiros subidos con máis de 23 horas. A carga vai nunha transacción:
a demo segue respondendo mentres dura. Lanzala a man:

```bash
docker compose -f docker-compose.demo.yml -f docker-compose.tras-proxy.yml exec reseed python /app/manage.py seed_demo
```

Unha carga ás 04:00 deixaría sen exemplos a quen entrase pola tarde: a reserva de ximnasio de Uxía
remataba pola mañá e a de pádel ás 19:00. Por iso, con `EIRA_PUBLIC_DEMO`, Uxía ten tamén esas dúas
reservas o día seguinte. Compróbao `test_examples_last_all_day_after_the_night_reseed`.

Todas as visitas comparten as mesmas contas, así que o máximo de reservas activas por persoa
bloquearía axiña ao xurado. Con `EIRA_PUBLIC_DEMO`, a carga súbeo a 100 en cada concello.

## Despregar detrás dun proxy que xa existe

É o caso de `pruebas-gestor`, onde o Caddy do gestor documental ten os portos 80 e 443.

Só `eira-web` entra na rede dese proxy, sen portos publicados; a app e a base de datos seguen illadas.
Non se precisan credenciais de GitHub no servidor: a imaxe constrúese en local e cópiase.

```powershell
# En local, en D:\Eira\deploy\demo: construír e copiar a imaxe e os ficheiros
docker compose -f docker-compose.demo.yml build app
docker save eira-demo-app:local -o eira-demo-app.tar
scp eira-demo-app.tar pruebas-gestor:/srv/eira-demo/
```

```bash
# No servidor, en /srv/eira-demo
docker load -i eira-demo-app.tar && rm eira-demo-app.tar
cp .env.example .env && chmod 600 .env   # encher os segredos
docker compose -f docker-compose.demo.yml -f docker-compose.tras-proxy.yml up -d
```

Despois, **engadir só esta entrada** ao Caddyfile do proxy, cun `>>` (é un ficheiro montado: se se
substitúe o ficheiro, o contedor segue vendo o vello), e recargar sen reiniciar:

```caddyfile
eira.engramlab.es {
	reverse_proxy eira-web:80
}
```

```bash
docker exec engram-gestor-caddy-1 caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
docker exec engram-gestor-caddy-1 caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile
```

**Ao actualizar o gestor** hai que comprobar que a entrada segue no Caddyfile. Se se perde, Eira deixa
de responder, pero o gestor non se ve afectado.

## Despregar nun servidor só para a demo

```bash
cd deploy/demo && cp .env.example .env   # encher os segredos
docker compose -f docker-compose.demo.yml up -d --build
```

## Comprobar a demo

```bash
python tools/check_demo_online.py https://eira.engramlab.es
```

Comproba o certificado, a entrada con cada perfil, unha reserva completa, a reprodución dos vídeos, a
PWA, axe en seis pantallas e o rexeitamento de correos reais. Con `--rate-limit` proba tamén o límite
de acceso, e gasta o da IP que fai a proba durante unha hora.

## Parar ou borrar a demo

Parala, conservando todo:

```bash
cd /srv/eira-demo && docker compose -f docker-compose.demo.yml -f docker-compose.tras-proxy.yml stop
```

Borrala por completo despois do certame:

1. Quitar a entrada `eira.engramlab.es` do Caddyfile do proxy e executar `caddy reload`.
2. `docker compose -f docker-compose.demo.yml -f docker-compose.tras-proxy.yml down -v`
3. `docker image rm eira-demo-app:local postgres:16-alpine`
4. `sudo rm -r /srv/eira-demo`
5. Quitar os rexistros A e AAAA de `eira` na zona `engramlab.es`.

## Probas en local

**Verificado:** as dúas variantes con `EIRA_DOMAIN=localhost`. A de detrás dun proxy, cun Caddy diante
que imita ao do gestor. En ambas, `tools/check_demo_online.py --insecure --rate-limit` dá 31 de 31:
12 perfís, reserva completa, vídeos, PWA, axe, límite no envío 21 e sen saltalo falsificando
`X-Forwarded-For`. A app non chega a Internet. Na rexeneración forzada, desaparecen unha conta real
simulada e un ficheiro vello e `missing()` queda baleiro (17 s).

**Non verificado en local:** certificado real de Let's Encrypt, instalación da PWA nun móbil real,
reprodución do MP4 (o Chromium das probas usa o WebM) e funcionamento continuado varios días.
