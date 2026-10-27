# Auditoría para a publicación do repositorio

**Última revisión: 27/10/2026 (v1.3)**, primeira sección. A auditoría orixinal segue debaixo.

**Data:** 23/10/2026 · **Alcance:** ficheiros versionados, historial completo de git (todas as
ramas), metadatos de imaxes e vídeos, catálogos de tradución e configuración do repositorio.
**Resultado:** apto para publicar tras os cambios desta auditoría. **Non fai falla reescribir o historial.**


## Revisión v1.3 (27/10/2026): todo o historial de git

**Alcance:** os 65 commits de todas as referencias (`master`, `origin/master` e as etiquetas
`v1.0-certame`, `v1.1-certame`, `v1.2-certame`), con `git log --all -p` (todas as liñas engadidas en
cada commit, tamén as que despois se borraron), os nomes de todos os ficheiros que existiron
(`git rev-list --all --objects`), as mensaxes de commit e as anotacións das etiquetas.
**Resultado:** **non hai segredos, nin documentos alleos, nin rutas locais reais, nin correos reais.**
Hai catro cousas que o equipo debe decidir antes de publicar (táboa 2). **Non se reescribiu nada.**

### 1. Que se buscou

| Busca | Método | Resultado |
|---|---|---|
| Segredos (claves de API `sk-`, `ghp_`, `github_pat_`, `xox…`, `AKIA…`, `AIza…`, chaves privadas, `password/secret/token = "…"`) | expresións regulares sobre `git log --all -p` | **0 reais.** Só `EIRA_TELEGRAM_TOKEN = "proba-non-real"` nun test (`0091769`, `apps/notifications/tests/test_notices.py`) e os valores de exemplo da sección 3 da auditoría anterior ✅ |
| Documentos alleos (`.docx`, `.doc`, `.odt`, `.pdf`, `.xlsx`, `.pptx`, `.eml`, `.msg`, `.key`, `.pem`, `.env`, `.sqlite3`) | nomes de todos os obxectos do historial | **0.** A carta de interese dun concello que hai na carpeta de traballo **nunca se versionou**; desde a v1.3, `.gitignore` ignora `*.docx`, `*.doc`, `*.odt` e `*.pdf` (agás en `docs/`) ✅ |
| Mencións ao concello da carta | `git log --all -p` | 0 ✅ |
| Rutas locais de Windows (unidade + `Users`, a carpeta do proxecto, `AppData`, `Temp/claude`) | expresións regulares | Só no propio texto da auditoría anterior (lista de patróns buscados, `41a3f1b`). Ningunha ruta real ✅ |
| Nome de usuario do sistema, apelidos e correo persoal | expresións regulares (usuario de Windows, apelido, `gmail`, `hotmail`, `outlook`, `yahoo`, `icloud`) | Ningún correo persoal. Ver 2.c (un apelido común na lista de apelidos ficticios) |
| Correos fóra de dominios reservados (RFC 2606 e 6761) | todos os enderezos do historial | Só `LL@li.org` (marcador da plantilla de gettext) e os enderezos antigos do subdominio `demo` de `eira.gal` (ver 2.a) |
| DNI, teléfonos móbiles, IBAN | expresións regulares | DNI de exemplo (`12345678Z`, `00000001R`…) e teléfono `600000000`: ficticios e documentados como tales. 0 IBAN ✅ |
| IPs privadas | `192.168.*`, `10.*` | 0 ✅ |
| Autoría dos commits | `git log --all --format="%an <%ae> \| %cn <%ce>"` | Os 65: `Equipo Eira <equipo@eira.invalid>` ✅ |
| Metadatos das imaxes | Pillow (`info` e EXIF) das 674 PNG versionadas | 0 con metadatos ✅ |
| Vídeos | nomes de obxectos | Ningún vídeo no historial (están en `.gitignore`) ✅ |

### 2. O que apareceu e proposta de limpeza (NON executada)

| # | Que | Commit(s) e ficheiro(s) | Risco | Proposta |
|---|---|---|---|---|
| a | Correos ficticios no subdominio `demo` de `eira.gal` (dominio que podería ser dun terceiro), antes do cambio a `demo.eira.example` | de `ca22205` a `41a3f1b` (23/10/2026): `apps/tenants/management/commands/seed_demo.py`, `apps/integrations/demo.py`, `tests/e2e/test_screenshots.py` e outros | Baixo: non son persoas reais, pero se `eira.gal` ten dono, o historial ten enderezos dese dominio | Opcional: `git filter-repo --replace-text` cara a `demo.eira.example` (feito na copia pública da v1.4) |
| b | Nome de pila dunha persoa real que fixo propostas para a v1.2 | `bf6b51d` e `db4a681`: `docs/DECISIONS.md`, `docs/INFORME_MANANA.md`, `docs/PLAN_V2.md`, `docs/PROGRESS.md`; mensaxe de `db4a681` e anotación da etiqueta `v1.2-certame` | Baixo (só o nome de pila), pero é un dato persoal dun terceiro | Confirmar que está de acordo en aparecer. Se non: substituír por «a persoa colaboradora» nos documentos (cambio normal). Como estes commits **aínda non están en `origin`**, a mensaxe e a etiqueta pódense corrixir antes de subilos, sen tocar nada xa subido |
| c | Un apelido galego común na lista de apelidos ficticios da demo | `a51fe58`: `apps/activities/demo.py` (lista `SURNAMES`) | Moi baixo: lista de apelidos frecuentes combinados ao chou; ningunha persoa da demo é real | Ningunha, salvo que o equipo prefira cambialo |
| d | Tamaño do historial | 616 capturas PNG en `docs/capturas/` (109 MB no árbore actual); o *pack* de git ocupa uns 330 MB porque cada rexeneración das capturas engade versións novas (a maior, 4,9 MB, ten tres versións) | Clonar é lento; non é un risco de privacidade | Antes de publicar: ou mover as capturas a *release assets* ou Git LFS e publicar a partir dun historial novo (*squash*), ou aceptar o tamaño. **As dúas primeiras reescriben ou cortan o historial: decisión do equipo** |

**Remoto xa configurado:** o repositorio local ten un remoto `origin` nun servizo de aloxamento de
código, e `origin/master` apunta a `5181c06` (24/10/2026). Polo tanto, **o historial ata ese commit
xa se subiu** fóra desta sesión (as entradas a e c están aí; b non). **Non verificado:** se ese
repositorio é público ou privado, e que etiquetas ten (non se consultou a rede). O nome da conta
aparece na URL do remoto (`.git/config`, que non se publica co repositorio); para unha publicación
institucional convén unha organización e non unha conta persoal.

Procedemento proposto se o equipo decide limpar (**NON executado**; facelo antes da publicación e
avisando a quen xa clonase):

```bash
pip install git-filter-repo                                   # MIT
printf 'demo.eira.%s==>demo.eira.example
' gal > substitucions.txt
git filter-repo --replace-text substitucions.txt               # 2.a
git filter-repo --replace-message substitucions-mensaxes.txt   # 2.b (mensaxes de commit)
git filter-repo --path docs/capturas --invert-paths            # 2.d (se as capturas van a release assets)
```

### 3. README e publiccode.yml

| Comprobación | Resultado |
|---|---|
| README: arrancar a demo en 5 minutos | Engadidas «A demo en 5 minutos» (Docker ou Python, perfís sen contrasinal, que probar, bandexa de correo, rexenerar) e «Comprobar que todo está ben» ✅ |
| README: licenza | EUPL-1.2: que permite, que obriga e ligazón a `LICENSE` ✅ |
| README: como contribuír | `CONTRIBUTING.md`, o novo `GOVERNANCE.md`, o código de conduta e `SECURITY.md` ✅ |
| `publiccode.yml` | **Válido** co validador oficial `italia/publiccode-parser-go` 5.4.3 en Docker, sen rede (`python tools/tasks.py publiccode`, saída 0). Control negativo: cun campo inventado, o validador falla (saída 1) ✅ |
| Pendente (non verificado) | Validación **con rede** (comproba a URL do repositorio e o logo) cando exista a URL definitiva; `url` segue sendo `https://example.org/eira.git` |

### 4. Pendente antes de publicar

- Decidir 2.a–2.d.
- URL definitiva en `publiccode.yml` e no README; validar con rede.
- Canle privada para avisos de seguridade en `SECURITY.md`.
- Persoas mantedoras con nome (ou organización) en `GOVERNANCE.md` e `publiccode.yml`.

---

## Auditoría anterior (23/10/2026)

## 1. Que se buscou e como

| Comprobación | Método | Resultado |
|---|---|---|
| Identidade dos commits (autor e committer) | `git log --format="%an <%ae> \| %cn <%ce>"` | Todos os commits: `Equipo Eira <equipo@eira.invalid>` ✅ |
| Configuración local do repo | `.git/config` (non se publica, pero revisouse) | Só `user.name`/`user.email` do equipo ✅ |
| Rutas locais (`D:\`, `D:/Eira`, `C:\Users`, `C:/Users`, `Temp/claude`) | `git grep` nos ficheiros e `git log --all -p -S…` no historial | 0 aparicións ✅ |
| Nome de usuario do sistema e apelidos/correo persoal | `git grep` e `git log --all -p -S…` (nome de usuario de Windows, apelido, `gmail`) | 0 aparicións ✅ |
| IPs da rede local (`192.168.`) | ídem | 0 aparicións ✅ (o script que arranca o servidor na LAN está fóra do repositorio) |
| Segredos (`sk-`, `BEGIN PRIVATE`, `password=`, `secret`, `token`) | ídem + revisión manual | Ningún segredo real. As coincidencias son código (`password=None`) ou valores de exemplo marcados (ver 3) ✅ |
| Correos | `git grep` de todos os enderezos | Só dominios reservados RFC 2606 (`example.org`, `*.example`, `*.invalid`) tras o cambio da sección 2 ✅ |
| Metadatos das capturas PNG | Pillow: `info` e EXIF de `docs/capturas/*.png` e `static/img/*.png` | Sen metadatos ✅ |
| Metadatos dos vídeos WebM | `ffprobe` | Só `ENCODER`, `DURATION`, `language` e `creation_time` (data da gravación). Nada persoal ✅ |
| Cabeceiras dos `.po` | revisión | Tiñan os marcadores de plantilla `FIRST AUTHOR <EMAIL@ADDRESS>` → substituídos por «Equipo Eira» ✅ |
| Datos persoais de persoas reais | revisión de seed, docs e capturas | Persoas, concellos e enderezos ficticios. Só aparecen autores de referencias bibliográficas publicadas (ACSM, EFSA, OMS, Ruiz et al., Rikli e Jones) ✅ |

## 2. Cambios feitos nesta auditoría

1. **Dominio dos perfís de demostración:** subdominio `demo` de `eira.gal` → `demo.eira.example`. `eira.gal` podería
   ser un dominio real dun terceiro; `.example` está reservado (RFC 2606). Afecta a seed, tests e perfís.
2. **Cabeceiras dos catálogos `.po`:** sen marcadores persoais; `tools/compile_messages.py` reescríbeas sempre.
3. Revisión de nomes ficticios: ver [DECISIONS.md](DECISIONS.md) (sen coincidencias reais nos tres nomes principais).

## 3. Valores de exemplo que NON son segredos (pero hai que cambiar en produción)

| Onde | Valor | Uso |
|---|---|---|
| `eira/settings.py` | `dev-insecure-key-only-for-local-use` | Só con `EIRA_DEBUG=1`; sen `EIRA_SECRET_KEY` en produción a app non arranca |
| `docker-compose.yml` | `eira-local-only`, `local-demo-key-change-me-in-production-…` | Demo local. A demo pública (`deploy/demo/`) esixe valores en `.env` |
| `.github/workflows/ci.yml` | contrasinal `eira` de PostgreSQL | Base de datos efémera da CI |
| `Dockerfile` | `EIRA_SECRET_KEY=build-only` | Só para `collectstatic` durante a construción |

Os ficheiros `.env` (raíz e `deploy/demo/`) están en `.gitignore` e non hai ningún no historial.

## 4. Historial de git

Non hai datos persoais, rutas locais nin segredos en ningún commit (comprobado con `git log --all -p -S`
para cada patrón). **Non se reescribe o historial.**

Se no futuro aparecese algo que eliminar, o procedemento proposto (NON executado) sería:

```bash
pip install git-filter-repo                         # MIT
git filter-repo --replace-text expresions.txt       # liñas «texto==>[ELIMINADO]»
git filter-repo --mailmap mailmap.txt               # se houbese que cambiar autorías
```

## 5. Pendente antes de publicar (non verificado)

- Elixir a URL definitiva do repositorio e actualizar `publiccode.yml` (`url`) e o README.
- Executar `python tools/tasks.py publiccode` **con rede** (sen `-no-network`) unha vez publicado, para validar a URL.
- Os vídeos ocupan ~24 MB no repositorio. Valorar publicalos como *release asset* e non en git.
- `CLAUDE.md` describe as regras da sesión de desenvolvemento asistido: é inocuo, pero o equipo pode decidir se o publica.
