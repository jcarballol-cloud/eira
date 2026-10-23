# Aprendizaxes de dous proxectos xa probados con persoas reais

Revisión en **modo só lectura** (23/10/2026) de dúas aplicacións do equipo. Leuse código, estilos
e documentación de deseño e requisitos; **non** se abriron bases de datos, copias, capturas, `.env`
nin carpetas de produción, e **non** se copiou ningún dato persoal, nome, imaxe, fonte nin texto con
licenza propia. Eira só incorpora **patróns**; o código novo escríbese desde cero baixo EUPL-1.2.

---

## 1. «AFS +50»: tableta de asistencia e esforzo (usada con maiores e con nenos)

### Fluxo que funciona no campo

1. **Inicio**: rexilla A–Z coa **inicial do primeiro apelido**.
   - As letras con persoas resáltanse e levan un contador; as baleiras quedan atenuadas e desactivadas.
   - Hai tamén un buscador global, que actúa a partir de 2 caracteres e ignora os acentos.
2. **Letra**: lista de nomes con esa inicial, ordenada por apelido (apelidos en negra, nome en normal).
   - Leva un filtro só se hai máis de 6 nomes.
   - Quen xa rexistrou hoxe aparece con «✓ hoxe».
3. **Esforzo**:
   - O nome vese moi grande e hai un botón «**Non son eu**» para volver.
   - A pregunta está visible («Canto che custou a sesión de hoxe?»).
   - Hai **11 botóns** de cor progresiva: verde suave no 0 e terracota suave no 10.
   - **Gárdase ao pulsar**, sen botón de confirmar.
4. **Grazas**:
   - Mostra nome, valor e hora, e un botón «Seguinte persoa».
   - **Volve só ao inicio aos 3 s**, cunha barra de progreso que se baleira.

Regras:
- Un rexistro por persoa e día; se se repite, vale o último.
- Ningunha acción destrutiva a menos de dous toques.
- Sen xestos: só toques.

### Tamaños e ritmo
- Obxectivo táctil mínimo de **80 px** no quiosco (48 px no resto da app).
- Texto base **22 px**, nomes **24–26 px**, letras **52 px**, números da escala **44 px** e titular **32 px**.
- Contraste AAA (7:1) no texto do quiosco. Ritmo: unha decisión por pantalla.
- Escala de esforzo:
  - Cores calculadas en OKLCH (L 0,86 e C 0,07, de 150° a 30°), con texto escuro ≥ 7:1 en todos os pasos.
  - Etiquetas **CR-10 modificada de Foster**: 0 Repouso, 1 Moi moi doado, 2 Doado, 3 Moderado, 4 Algo duro, 5 Duro, 7 Moi duro, 10 Máximo. Os pasos 6, 8 e 9 van sen etiqueta.
  - Carga = RPE × minutos.

### Quen mete os nomes
- A **administración** dá de alta ás persoas: unha por liña ou importando un CSV, sen duplicados por nome normalizado.
- A tableta **vincúlase a un grupo cun código** e recibe a lista do servidor.
- Sen conexión garda nunha cola e envía despois.
- As baixas ocúltanse da lista pero conservan o historial.

### Como o aplico en Eira
- **Tableta da monitora** (fases 1 e 4):
  - Asistencia por **inicial do apelido** ou nomes grandes segundo o tamaño do grupo.
  - Escala de esforzo **unha persoa tras outra**: nome grande, 11 botóns de 80 px como mínimo, cores progresivas, gardado ao pulsar, «Non son eu» e avance automático tras a confirmación.
  - OMNI (caras graduadas) para a infancia e CR-10 coas súas etiquetas para persoas adultas.
- **A monitora pode engadir unha persoa** (por exemplo, alguén que vén probar), que queda **pendente de validar** pola administración.
- As inscricións normais chegan da administración e da app.

---

## 2. «LifeGuarPro»: app móbil de hidratación e saúde

### Estilo de app
- **Un só color de marca sobre neutros cálidos.** A elegancia vén do aire e da tipografía, non das sombras.
- Tarxetas con bordo fino e sen sombra (só o que flota leva sombra mínima). Raio de 16 px en tarxetas e 12 px en controis.
- **Navegación inferior fixa** con 4–5 ítems: icona de liña e etiqueta pequena, activo na cor de marca. Respecta `safe-area-inset-bottom`.
- Cabeceira compacta (56–64 px). Botón principal de 48 px de alto, como moito un por pantalla.
- **Tarxeta métrica**: etiqueta en versalita pequena e número grande (34–38 px, `tabular-nums`).
- **Iconas de liña, nunca emoji.**
- Avisos con fondo tenue da cor semántica. O risco de hiponatremia vai en ámbar, non en vermello.
- Instalación da PWA:
  - Botón «Instalar app» se o navegador ofrece `beforeinstallprompt`.
  - En iOS, instrucións específicas («Compartir → Engadir á pantalla de inicio»).
  - Non se mostra nada se xa está instalada (`display-mode: standalone`).

### Como dá as recomendacións
- **Concretas e con cantidade.** Cada fila leva icona, título, explicación curta e **cantidade á dereita** (por exemplo, «Antes · 350 ml · 2 h antes»).
- Personalizadas co peso, a idade, a duración, a intensidade, a temperatura, a humidade, o sol e o vento.
- **Rangos e non cifras falsamente exactas**: a suor varía moito entre persoas.
- **Aviso explícito de non beber de máis** (hiponatremia): guiarse pola sede e pola cor do ouro.
- Os hidratos durante o esforzo só se recomendan con esforzo sostido de máis de 60–90 min. O sodio na bebida só en esforzos longos con moita suor.
- Estrés térmico estimado (aproximación ao WBGT) **etiquetado como estimación**.
- Cada fórmula leva a súa fonte nun comentario do código e hai un documento de auditoría científica.

### Como o aplico en Eira (fases 4 e 6)
- **App da veciñanza en formato móbil** con barra de lapelas inferior (Inicio, Reservar, As miñas, Familia, Saúde) e tarxetas sen sombra.
- **Recomendacións por reserva** («Para o teu partido do sábado ás 18:00»), en filas antes / durante / despois / comida / calor-frío-UV / sinais de alarma, con cantidades e rangos.
- Calculadas co peso, a idade, a **duración real da reserva**, se é cuberta ou exterior e a **previsión da franxa**.
- Só se usan regras **con fonte publicada**: ACSM 2007, AAP 2011 (menores), Thomas et al. 2016 (alimentación), OMS (UV e actividade) e EFSA.
- **Non** copio o modelo propio de taxa de suor de LifeGuarPro: os seus coeficientes son unha heurística interna sen fonte publicada, e a regra é non inventar cálculos.
- Instalación da PWA co mesmo patrón (botón ou instrucións iOS/Android), na páxina de axuda e no correo de alta.

---

## 3. Que non se reutiliza
- Ningún código literal. As ideas de fluxo e deseño reescríbense en Django, HTML e CSS propios baixo EUPL-1.2.
- Nin fontes tipográficas incrustadas (Eira segue coa tipografía do sistema), nin imaxes, iconas, marcas ou textos legais.
- Ningún nome, dato de participante nin captura.
