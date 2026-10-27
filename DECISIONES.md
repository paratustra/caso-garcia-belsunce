# DECISIONES de implementación (WP0–WP3)

Diferencias y precisiones respecto de `METODOLOGIA.md`. Fecha: 2026-10-27.

## Hallazgo: "PAGINA" del índice es página del PDF, no foja

Se cotejaron las 1.097 filas evaluables de `INDICE-por-cuerpos.tsv` con el texto OCR: en el 68 % las palabras del tema aparecen en la página del PDF indicada, y en otro 10 % a ±2 páginas (piezas que empiezan en la página anterior o siguiente). En las 12 filas cuyo número coincide con una foja detectada en otra página del mismo cuerpo, el tema no aparece en esa página. Además, las fojas de un cuerpo avanzado son números altos (Cuerpo 10 ≈ fs. 1.800–1.960) y el índice nunca supera las páginas del PDF del cuerpo. Ejemplo: "Acta de entrega de vivienda | 171 | cuerpo 1" = `exp-c01#p171` (título "ACTA ENTREGA DE VIVIENDA"). Conclusión: `filing.page` es página del PDF; `pid = doc_id#p<PAGINA>`.

## IDs

- `doc_id` se deriva del nombre del archivo (slug) en lugar de nombres cortos a mano: es determinista, no colisiona (p. ej. veredicto y sentencia del TOC1 del 2011-11-04) y cualquier agente lo reconstruye desde la ruta. Precio: algunos son largos (`fallo-2024-03-27-casacion-salai-causa-123391-pachelo-condena-perpetua`). Prefijo `fallo-` (como el diseño), no `fal-`.
- `vid-<id>` conserva mayúsculas del ID de YouTube.
- Textos sin paginación (prensa, blog, testimonios, evidencia, wikipedia, oficial, archive-org, 4 fallos): ancla `#s<N>`. Las secciones se cortan en encabezados (si la sección ya tiene ≥800 caracteres) y en párrafos al pasar 3.000. **No cambiar `MAX_SECTION`/`MIN_SECTION` en `ingest.py`**: renumeraría las anclas. Se descartó `#l<línea>` porque una línea no da contexto suficiente y la columna `page.line` ya da la línea de inicio.

## Esquema (`db/schema.sql`)

- `claim_id` es TEXT (no INTEGER): varios agentes en paralelo crean afirmaciones sin coordinar contadores. Convención `a:<tarea>-<n>`.
- Columnas agregadas: `document.text_path, n_text_pages, text_status, anchor`; `page.source_file, line`; `filing.original_volume, page_end, pid, doc_resolution, candidates`; `event.anchor_type`; `expert_report.modern_reexamination` (objetivo del usuario); `created_by` en tablas de capa 2.
- Tablas agregadas: `extraction`, `extraction_item` (tareas EXT), `statement_claim`, `relation_type`, `load_error`; vistas `entity_current`, `v_folio`; FTS auxiliar `page_vocab` (fts5vocab) para variantes ortográficas. `alias.type` admite `source_error` (b.4 lo menciona, b.3 no lo tenía).
- `relation_both` devuelve también la dirección inversa de relaciones asimétricas usando `relation_type.inverse`.
- Las claves foráneas no se imponen al cargar; `validate.py` corre `PRAGMA foreign_key_check`. Así una fila mala no impide compilar el resto.
- Trigram con `remove_diacritics 1` (SQLite ≥ 3.45; local 3.53).

## Capa 1

- El texto del expediente se toma de `<cuerpo>.ocr.md` (lo que se ve con grep); `.ocr.json` aporta confianza y tablas. **Ningún `.ocr.json` trae `confidence_scores`** (todos `null`, también en bloques): `ocr_conf` queda vacío. Para detectar OCR dudoso hoy solo sirve `v_coverage.near_empty_pages` (623 páginas con menos de 40 caracteres en todo el corpus, 596 en el expediente).
- `page.folio`: heurística (número aislado entre las primeras 4 líneas, aceptado solo si es coherente con un candidato anterior y uno posterior a ≤12 páginas, y luego con sus vecinas aceptadas). 1.739 de 11.189 páginas del expediente. Los dorsos (vta.) no llevan número, así que el máximo esperable ronda el 50 %. Es orientativa: verificar en la imagen (tarea QA-FOJA).
- Tablas (WP16): el `.ocr.md` de Mistral deja las tablas como marcador `[tbl-K.md](tbl-K.md)`; su contenido solo está en `pages[].tables` del `.ocr.json`. `ingest.py` reemplaza cada marcador por su tabla en markdown (`| a | b |`), tal cual, con sus errores de OCR (expediente: 1.411 tablas en 916 páginas; slideshare: 124 en 89). Anclas, `line` y `folio` no cambian (la foja se detecta antes de insertar las tablas). En esas páginas `page.text` ya no es idéntico al `.ocr.md`: para buscar dentro de tablas, usa `text/pages/` o `search.py`, no el `.ocr.md`. 16 frases de extracción EXT (en `extraction/` y su copia en `parts/`) que cruzaban un marcador se recortaron al tramo literal fuera de él.
- `INDICE-por-cuerpos.tsv` dice "cuerpo 36", pero existen 36a y 36b: se resolvió por coincidencia del tema con el texto de la página en cada candidato (17 filas); 13 quedan con `doc_id` vacío (`doc_resolution='ambiguous'`, `candidates` lista ambos). "31 - 35" se guarda como `page=31, page_end=35`.
- `filing_type` se asigna por palabras clave del tema (statement, expert_report, record, decision, brief, other): aproximado.
- Scribd: texto con `pdftotext` (poppler, herramienta del sistema, no dependencia de Python); el texto de Scribd viene con letras separadas ("Ma ría"). Fallos con PDF: se usa el `.txt.md` ya extraído. El `.doc` de 2009-06-19 se usa vía su `.txt.md` (sin paginar → `#s`).
- No se ingieren: `INDICE*.md` y `README.md`, `*.tsv`, `*.html` de archive-org (duplican el `.md`), `*.links.txt`, imágenes del blog.
- `source_level`: testimonies/ y evidence/ se marcan `secondary` porque son compilaciones hechas por otro agente a partir de fallos, blog y prensa, aunque citen fuentes primarias.
- Ingesta incremental: un documento se reprocesa solo si cambia el tamaño o la fecha de alguno de sus archivos; `--full` fuerza todo. El sha256 del original se reutiliza si el original no cambió. JSONL, manifest y base se escriben a un temporal y se renombran (los lectores no ven archivos a medias).

## Herramientas

- `build.py` llama a `ingest.py` (capa 0 → 1) y compila; `--no-ingest` solo compila.
- Normalización de citas: minúsculas, sin diacríticos, signos → espacio, espacios colapsados, palabra cortada por guion + salto de línea se une. Si solo coincide ignorando espacios, se acepta con advertencia.
- `search.py`: frase exacta por defecto; si no hay resultados, prueba variantes (fts5vocab + `difflib`) y luego subcadena (trigramas). Muestra variantes de cada palabra de ≥5 letras. Ordena primero las fuentes primarias.
- `tasks.py`: el diseño pedía editar `status` en `tasks.json` y reclamar con `mkdir`. Para evitar carreras al editar un JSON compartido, el estado vive solo en `work/claims/<id>/` y `tasks.json` queda como definición fija.
- No se creó `llms.txt`: el diseño (1.3) lo descarta en favor de `README.md`. `CLAUDE.md` lo escribe la sesión principal.

## Extracción por cuerpo (pedido del coordinador)

- Esquema cerrado por pieza (AGENTS.md §8) con frase literal + página en cada campo no trivial, validable automáticamente. Una pieza sin texto (página en blanco o solo imagen) puede llevar `evidence: null` solo si todas sus páginas tienen menos de 30 caracteres normalizados.
- Una línea con un solo error se rechaza entera (a `db/rejected/`): es más simple de auditar y obliga a corregir.
- `build.py` vuelca las personas extraídas a `mention` con `ent_id NULL, status='auto'`; WP5/WP7 las vinculan a entidades.
- Auditoría: muestra determinista del 5 % (mínimo 3 líneas, semilla = nombre del archivo); umbral de rehacer: >10 % de líneas con error o cualquier contenido inventado.
- `sources/slideshare/` (en curso): cada carpeta es un documento `slide-<slug>` tipo `case_file`, `source_level='primary'` (es el escaneo del documento), aunque llegó vía el blog casobelsunce (`source.json.blog_post_file`). Sin `.ocr.md` queda `pending_ocr`; al aparecer el OCR, `build.py` lo ingiere sin tocar lo demás. Puede duplicar páginas de los cuerpos: verificar antes de contar dos veces una pieza (tarea WP3-SLIDE). La foja no se detecta en estos documentos.

## Transcripciones de video (capa 1)

- Cada `sources/audiovisual/transcripts/<id>.md` se adjunta al documento `vid-<id>` que ya crea `catalog.csv` (título, fecha y URL siguen saliendo del catálogo). Sin `.md` (o con `.fail`) el video queda `pending_transcription`; al aparecer el `.md`, `build.py` lo ingiere sin tocar lo demás (la firma incluye `.md` y `.json`).
- Ancla: se reutiliza `#s<N>` con N = tramo fijo de 5 minutos (`VIDEO_WINDOW = 300` en `ingest.py`, **no cambiar**): `#sN` cubre `[(N-1)*300 s, N*300 s)`. Se descartó un ancla nueva (`#t0300`) porque obligaba a tocar `RE_CITATION`/`RE_PID`, `validate.py` y la lógica de rangos (que exige números consecutivos); con `#s` los rangos `#s6-7` y la verificación funcionan sin cambios. Se descartó cortar por turno de hablante: el número dependería de la diarización y un turno llega a durar 25 minutos.
- `page.t_start` (columna nueva) guarda el segundo de inicio del tramo; la UI enlaza a `<url>&t=<t_start>s`. `page.line` es la línea del `.md` donde empieza el primer turno del tramo (si el tramo empieza a mitad de un turno, la línea de ese turno).
- Un turno de hablante va al tramo donde empieza; si cruza el límite, se corta según los tiempos por palabra del `.json` (misma agrupación que `scripts/acquisition/transcribe.py`). La continuación va sin encabezado `**[H:MM:SS] speaker_N:**`, así el rango `#sN-M` reproduce el párrafo seguido. Si el `.json` falta o no coincide con el `.md`, el turno entero va al tramo donde empieza. Se emiten todos los tramos hasta el último, aunque alguno quede vacío, para que `#sN` signifique siempre el mismo minuto.
- El encabezado del `.md` (título, Fuente, Canal, Fecha, Duración, nota) no entra al texto de las páginas. Los `[H:MM:SS]` y `speaker_N` quedan en el texto tal cual (son parte de la fuente) y entran en la búsqueda.
- `sha256` y `original_path` de un video siguen siendo los del catálogo (vacío / `catalog.csv`); el texto está en `text_path`.

## Citas de eventos y varias frases por página (sesión principal, tras WP10)

- `citation` pasa a tener clave `(claim_id, pid, role, quote)`: una afirmación puede citar varias frases de la misma página (WP10 lo necesitó en 1.175 casos).
- Nueva tabla `event_citation (ev_id, pid, quote, role)`, cargada desde el anidado `event.citations`. `validate.py` verifica estas frases igual que las de `citation`, y un evento con `event_citation` ya no cuenta como "evento sin cita".
- Los roles de cita fuera de la lista (`relata`, `sustento`, `refiere`, `cita`) se normalizaron a `sostiene` (hoy `supports`) en los archivos de WP10.
- `validate.py <archivo>` no revisa las citas anidadas de afirmaciones y eventos; para eso hay que correr `build.py` y después `validate.py` sin argumentos.

## Veredicto de 2007 ("toc1") (WP10)

- El archivo/doc_id del veredicto de 2007 se llama `fallo-2007-...toc1...`, pero el tribunal que lo dictó es el Tribunal en lo Criminal N° 6 de San Isidro (`o:toc6-san-isidro`), no el TOC 1. El doc_id se mantiene por estabilidad de las citas.

## Barrido de menciones (WP7)

- WP7 se hizo con un script determinista (`tools/mentions.py`, stdlib) en lugar de un agente por documento: lee las entidades vigentes y sus alias de `db/case.sqlite` (más el `canonical_name` como alias implícito) y todas las páginas de `text/pages/`. Escribe `analysis/mentions/<doc_id>.jsonl` (solo documentos con alguna mención), no `work/review/WP7/`: es salida regenerable, no un borrador para revisar a mano. Es idempotente (solo reescribe archivos que cambian y borra los de documentos que ya no tienen menciones) y tarda ~12 s. Si cambian alias o páginas: `build.py`, `mentions.py`, `build.py --no-ingest`.
- Esquema: `mention` gana `quote` (contexto literal de hasta 6 palabras a cada lado, verificable como `[[pid|"frase"]]`; comillas dobles pasan a `'`, `|` y corchetes se reemplazan, como pide §4 de AGENTS.md) y `candidates`; índices por `pid` y `ent_id`. Las menciones que `build.py` deriva de la extracción EXT llevan `created_by='extraction:<ext_id>'` y ahora también su `quote`; las del barrido, `created_by='WP7/mentions.py'`. No se deduplican entre sí.
- Coincidencia: `common.normalize_map` (la misma de las citas), palabras completas, gana el alias más largo y las coincidencias no se solapan. Una fila por página, entidad (o grupo de candidatos) y alias; la primera aparición da `literal_text` y `quote`.
- Ambiguas: si el alias normalizado pertenece a más de una entidad o alguna de sus filas es `possible_homonym`, la mención queda con `ent_id NULL`, `status='doubtful'` y `candidates` = los ent_id separados por espacio. Nunca se vincula sola. Se usa `doubtful` (ya en el CHECK) en vez de un estado nuevo; "ambigua" = `ent_id IS NULL AND candidates IS NOT NULL`.
- Reglas contra ruido: (1) si todas las formas del alias empiezan con mayúscula, la forma en el texto también; (2) un alias de una palabra escrito todo en minúscula (sustantivo común: dormitorio, escalera, antesala, bañera, jogging, casete) no se barre, salvo que sea `nickname` ("pituto"); (3) un alias de una palabra con menos de 4 caracteres no se barre; (4) un apodo de persona de una palabra ("Dino", "John", "Pichi", "Canela", "Bety", "Marialita") o un `possible_homonym` de una palabra que no comparte las 4 primeras letras con ningún token del ent_id ("Betty", "Beti", "Fayt") solo cuenta si el apellido de la entidad (primer token del ent_id) aparece en la misma página.
- Precisión medida a ojo en una muestra aleatoria de 50 (semilla fija, `mentions.py --sample 50`): 48/50 correctas. Errores: "los PIAZZA" (la familia, vinculado a Diego Piazza) y "LUIS A. PAEZ" (otra persona, propuesta como candidato de p:paez-juan, pero sin vincular).
- Ruido conocido que depende de los alias de WP5/WP6, no del barrido: "Sala I" (o:casacion-sala-i) también coincide con salas de la Cámara de Apelación; "Policía de la Provincia" (o:policia-bonaerense) con policías de otras provincias; "Libro de Guardia" (x:camaras-seguridad-acceso) con libros de guardia de comisarías; "Emernort" y "Paramedic" quedan siempre ambiguas porque son alias de dos organizaciones. Falta el apellido solo de varias personas centrales ("Carrascosa", 6.825 páginas): `work/review/WP7/alias-propuestos.tsv` lista para WP5 los apellidos (primer token del ent_id) que no son alias, con su número de páginas en el corpus.
