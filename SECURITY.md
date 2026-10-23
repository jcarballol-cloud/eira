# Política de seguridade

## Comunicar unha vulnerabilidade

Non abras unha incidencia pública. Escribe ao equipo mantedor (canle privada que se publicará co
repositorio) indicando a versión, os pasos para reproducir e o impacto. Responderemos en 5 días
hábiles e coordinaremos a publicación da corrección.

## Versións con soporte

| Versión | Soporte |
|---|---|
| 0.x (prototipo) | Correccións na rama principal |

## Medidas principais

Resumo en [docs/seguridade-rxpd.md](docs/seguridade-rxpd.md): acceso sen contrasinal con códigos dun
só uso (só se garda o seu HMAC), límite de envíos, CSP estrita, CSRF, cookies seguras, permisos por
rol e por concello con tests, limpeza de metadatos nas fotos, rexistro de auditoría e ningún segredo no
repositorio.
