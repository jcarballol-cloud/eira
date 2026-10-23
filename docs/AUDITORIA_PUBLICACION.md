# Auditoría para a publicación do repositorio

**Data:** 23/10/2026 · **Alcance:** ficheiros versionados, historial completo de git (todas as
ramas), metadatos de imaxes e vídeos, catálogos de tradución e configuración do repositorio.
**Resultado:** apto para publicar tras os cambios desta auditoría. **Non fai falla reescribir o historial.**

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

1. **Dominio dos perfís de demostración:** `demo.eira.example` → `demo.eira.example`. `eira.gal` podería
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
