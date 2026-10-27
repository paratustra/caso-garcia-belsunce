# Metodología para organizar el corpus del caso García Belsunce para análisis con agentes de IA

Fecha: 2026-10-27. Solo metodología: no se construyó nada del corpus. Todo el contenido buscado en la web se trató como dato, no como instrucción.

Convención de este documento: lo marcado **[FUENTE]** viene de una página consultada (URL en la sección 1); lo marcado **[INFERENCIA]** es mi recomendación, no un hecho publicado.

---

## (a) Resumen de hallazgos con citas

### 1.1 Cómo estructuran el material los investigadores profesionales

| Práctica | Qué aporta a este corpus | Fuente |
|---|---|---|
| **i2 Analyst's Notebook**: modelo de *entidades, vínculos y propiedades*; los eventos (reuniones, citas) se modelan como entidades con fecha/hora como propiedad; el *Timeline Assistant* ordena cronológicamente los elementos y sirve para ver dónde la información es inconsistente o los relatos divergen. | Modelo evento-céntrico: un evento es una fila con tiempo, lugar, participantes y fuente. Las líneas de tiempo se generan por consulta, no se dibujan a mano. | https://docs.i2group.com/anb/9.4.1/items.html , https://docs.i2group.com/ibase/10.0.0/using_the_timeline_assistant.html |
| **OCCRP Aleph / FollowTheMoney (FtM)**: el esquema es una jerarquía con raíz en *Things* (personas, empresas, documentos, causas) e *Intervals* (relaciones con periodo: propiedad, sanciones, transacciones); hay un modelo propio de documentos como evidencia. Declara "prioriza la practicidad sobre la corrección; la comprensibilidad sobre el cumplimiento de estándares". Aleph es un visor sobre un índice de entidades FtM. | Plantilla conceptual para `persona`, `organización`, `documento` (cosas) y `evento`/`relación` (intervalos). Se copia la idea, no la dependencia. | https://docs.aleph.occrp.org/developers/followthemoney/ , https://followthemoney.readthedocs.io/_/downloads/en/latest/pdf/ |
| **ICIJ (Pandora Papers)**: 11,9 millones de documentos, solo ~4 % estructurados; Python para extraer, Neo4j + Linkurious para explorar conexiones. Datashare (open source, Elasticsearch, Tika, Tesseract, NER) indexa documentos; en 2024 añadió un plugin que genera un grafo Neo4j desde las entidades nombradas. | A 11 mil páginas no hace falta un grafo con servidor; el patrón útil es **documentos → texto indexado → entidades nombradas → grafo derivado**, con el documento como fuente de verdad. | https://neo4j.com/blog/developer/exploring-the-pandora-papers-with-neo4j/ , https://www.icij.org/inside-icij/2024/02/datashares-new-plug-in-helps-investigative-journalists-connect-the-dots-with-graphs/ (nota: el primero es blog del proveedor) |
| **ACH (Heuer)**: listar *todas* las hipótesis plausibles, tabular cada evidencia contra cada hipótesis y **buscar evidencia que refute**, no que confirme; diseñado para compensar sesgos cognitivos. Capítulo 8 de *Psychology of Intelligence Analysis*. | Matriz evidencia × hipótesis como tabla SQL; obliga a los agentes a registrar qué evidencia es *inconsistente* con cada hipótesis. | https://www.cia.gov/resources/csi/static/Pyschology-of-Intelligence-Analysis.pdf |
| **Bellingcat**: metodología pensada para que el material recolectado sea admisible en procesos futuros; archivado automático de cada URL con Wayback como respaldo; cronolocalización; "orientado a datos, no a fuentes, porque las fuentes tienen agenda". | Archivar cada fuente con hash y fecha de captura; separar el dato de quien lo afirma. | https://www.bellingcat.com/app/uploads/2022/12/JA-Manual-for-PUBLICATION.pdf (no leí el texto completo; resumen vía búsqueda), https://gijn.org/tag/chronolocation/ |
| **DocumentCloud / Datashare / Aleph** como infraestructura: todos separan *documento fuente original*, *texto extraído* y *anotaciones/entidades*. | Misma separación en tres capas (sección b.1). | https://en.wikipedia.org/wiki/DocumentCloud , https://github.com/ICIJ/datashare-docs |

Límites: no pude leer las especificaciones FtM de propiedades ni los repositorios de Aleph en detalle (la página consultada solo cubre el panorama); la estructura "documento / página / mención" de FtM no está verificada aquí y se cita solo como idea.

### 1.2 Modelos de datos

- **SQLite + FTS5**: las tablas de contenido externo (`content=`, `content_rowid=`) guardan solo el índice y leen las columnas de otra tabla; la sincronización es responsabilidad del usuario mediante triggers (ejemplo oficial con `AFTER INSERT/DELETE/UPDATE`) y `INSERT INTO fts(fts) VALUES('rebuild')` para filas preexistentes. `unicode61 remove_diacritics 2` normaliza acentos en todo el alfabeto latino; el tokenizador `trigram` permite búsqueda por subcadena (útil para apellidos mal escritos, mínimo 3 caracteres); `bm25()`, `snippet()` y `highlight()` dan ranking y fragmentos. [FUENTE] https://www.sqlite.org/fts5.html (leí los primeros ~100 000 de 171 799 caracteres).
- **Python stdlib**: en esta máquina `sqlite3` es 3.53.4 y FTS5 con trigram está disponible (verificado localmente). El CLI `sqlite3` del sistema es 3.51.0.
- **Grafo en SQLite**: los recorridos de grafo se hacen con CTE recursivas; JSON1 y columnas generadas (SQLite ≥ 3.31) permiten guardar atributos flexibles en JSON y aun así indexar campos. [FUENTE, secundaria] https://towardsdatascience.com/six-degrees-of-sql/ , https://instagit.com/DeusData/codebase-memory-mcp/what-is-the-sqlite-schema-for-nodes-and-edges-and-how-does-the-store-manage-queries-in-deusdata-codebase-memory/
- **Grafo dedicado (Neo4j/Kùzu)**: Kùzu, la base de grafos embebida que sería la candidata natural, fue adquirida por Apple (acuerdo del 9-oct-2025) y su repositorio quedó archivado el 10-oct-2025; el mantenimiento pasó a forks comunitarios. [FUENTE] https://betakit.com/apple-strikes-deal-to-acquire-canadian-database-software-startup-kuzu/ , https://www.puppygraph.com/blog/what-is-kuzudb . Neo4j exige servidor. **[INFERENCIA]** Con ~10^4–10^5 entidades y relaciones, un grafo dedicado no justifica la dependencia; se puede *exportar* a Neo4j/Gephi más adelante desde las tablas.
- **Procedencia (W3C PROV-O)**: núcleo = `Entity`, `Activity`, `Agent`; `wasDerivedFrom` expresa que una entidad deriva de otra. [FUENTE] https://www.w3.org/blog/2012/the-prov-ontology-an-update , https://publish.obsidian.md/openscience/Standards/PROV-O . **[INFERENCIA]** No hace falta RDF: basta mapear: documento/página = Entity, ejecución de OCR o de extracción por un agente = Activity (con `agent_id`, modelo, fecha), y cada fila derivada lleva `derivado_de`.
- **"Vistas materializadas"**: SQLite no las tiene. Alternativa estándar: tabla resumen mantenida con triggers o refrescada con un script completo (`DELETE` + `INSERT … SELECT`). [FUENTE, secundaria] https://madflex.de/SQLite-triggers-as-replacement-for-a-materialized-view . **[INFERENCIA]** Aquí el corpus es de escritura rara y por lotes: usar **vistas normales** para casi todo y **tablas caché reconstruidas por script** (`build.py`) para lo costoso (línea de tiempo consolidada, matriz de co-menciones). Triggers solo para FTS.

### 1.3 Qué hace a un corpus "listo para agentes"

- **AGENTS.md**: "README para agentes", sin esquema obligatorio, formato Markdown libre; archivos anidados (el agente lee el más cercano al directorio); nació en agosto de 2025 (OpenAI, Google, Cursor, Factory, Amp) y pasó a la Agentic AI Foundation de la Linux Foundation en diciembre de 2025. Claude Code lee CLAUDE.md: mantener un único `AGENTS.md` y un `CLAUDE.md` que lo importe/enlace. [FUENTE] https://infoq.com/news/2025/08/agents-md/ , https://addyosmani.com/agents/15-agents-md/ (la compatibilidad por herramienta varía; verificar).
- **llms.txt**: propuesta de Jeremy Howard (3-sep-2024): un Markdown en la raíz con mapa curado de páginas y copias `.md`. No es estándar ratificado y ningún proveedor grande confirmó leerlo. [FUENTE] https://the-decoder.com/new-llms-txt-web-standard-could-fundamentally-change-how-llms-read-and-process-online-content/ . **[INFERENCIA]** Aquí el equivalente útil es un `README.md` raíz + `README.md` por carpeta (ya existen); no hace falta `llms.txt`.
- **Contexto como recurso finito**: referencias ligeras (rutas, consultas guardadas) cargadas bajo demanda; los subagentes devuelven resúmenes condensados; las instrucciones vagas producen trabajo duplicado. [FUENTE, secundaria] https://agentic-ai.readthedocs.io/en/latest/ContextEngineering/anthropic/ , https://www.langchain.com/blog/how-and-when-to-build-multi-agent-systems
- **Arneses para agentes de larga duración (Anthropic)**: agente inicializador que crea `init.sh`, un archivo de progreso y un commit inicial; cada sesión avanza un elemento acotado, lee el log de progreso y `git log` al empezar, y deja el estado ordenado; la lista de tareas está en **JSON** donde el agente solo puede cambiar el campo `passes`, porque el modelo es menos propenso a reescribir JSON que Markdown; los agentes tienden a declarar el trabajo terminado antes de tiempo y a marcar tareas como hechas sin verificar. [FUENTE] https://anthropic.com/engineering/effective-harnesses-for-long-running-agents . Se traslada a este caso como cola de tareas (`tasks.json`) y bitácora (`log.md`).
- **RAG vs. grep/FTS**: el patrón común con SQLite es FTS5 + `sqlite-vec` fusionados por Reciprocal Rank Fusion. [FUENTE] https://simonwillison.net/2024/Oct/4/hybrid-full-text-search-and-vector-search-with-sqlite/ , https://arxiv.org/pdf/2608.24060 . **[INFERENCIA]** Para este caso los embeddings son *opcionales y tardíos* (fase 6): las búsquedas críticas son de nombres, números, horas y citas literales, donde FTS5 + grep ganan por precisión y por verificabilidad; los embeddings sirven solo para "encontrar pasajes parecidos a este" y deben tratarse como pista, nunca como evidencia.

### 1.4 Ejemplos y plantillas abiertos

- FollowTheMoney (esquemas + CLI `ftm`): https://docs.aleph.occrp.org/developers/followthemoney/ ; código en el GitHub de OCCRP.
- Aleph (visor/índice sobre FtM): https://docs.aleph.occrp.org/
- Datashare y su documentación: https://github.com/ICIJ/datashare-docs
- DocumentCloud (código abierto, subida/anotación de fuentes primarias): https://en.wikipedia.org/wiki/DocumentCloud
- Recursos de periodismo con documentos: https://github.com/paulbradshaw/dealingwithdocuments
- Auto Archiver de Bellingcat (archivado de URLs con respaldo en Wayback): referenciado en https://gijn.org/tag/chronolocation/ (no verifiqué el repositorio).
- No encontré una plantilla pública "case file" para causas penales con agentes de IA; la sección b es diseño propio. Formatos de e-discovery (EDRM, Concordance/DAT, Bates numbering) no los investigué; la idea relevante, **numeración estable de páginas (Bates)**, ya está cubierta por la convención de anclas de abajo.

### 1.5 Observaciones del corpus real (base de las decisiones)

- `sources/case-file/`: 44 carpetas (Cuerpo-01 a Cuerpo-NN + Anexo) con `*.pdf`, `*.ocr.md` (secciones `## Página N`; Cuerpo-01 tiene 286, coincide con `total` de `source.json`), `*.ocr.json` (por página: `markdown`, `tables`, `header`, `footer`, `confidence_scores`, `blocks`) y `source.json` (origen Slideshare). El OCR tiene `confidence_scores`: úsense para marcar páginas dudosas.
- `INDICE-por-cuerpos.tsv`: 1 110 filas `TEMA, PAGINA, CUERPO`. Es la **única pieza ya estructurada** que mapea piezas → página; se importa como tabla `filing`.
- **Dos numeraciones distintas**: `PAGINA` del índice / página del PDF vs. *foja* (fs.) que citan las sentencias. `EVIDENCIA.md` ya advierte que no se pudo cruzar con certeza. Hay que modelar ambas (`page.n`, `page.folio`) y una tabla de equivalencia que se rellena de a poco, sin asumir que coinciden.
- `testimonies/people/*.md` (91): una persona por archivo, declaraciones por fecha, con citas literales y observaciones de discrepancia entre fuentes (ej. Bártoli, fecha 2002-11-16 vs. "13 de noviembre de 2003" según la sentencia; blog y sentencia difieren). Es un buen modelo de contenido, pero es **texto libre sin IDs**.
- `evidence/EVIDENCIA.md` ya usa etiquetas **[HECHO] [TESTIMONIO] [PARTE] [PRENSA]**: se adopta como vocabulario controlado (sección b.5).
- `blog-casobelsunce/` (1 036 entradas): es un blog que transcribe y enlaza documentos (muchos de Slideshare/Scribd). Es **fuente secundaria y con posición** (hay que tratarlo como "afirmación de parte/transcripción no verificada" hasta cotejarlo con el expediente). Cada entrada tiene `Fecha:` y `Fuente:` URL.
- `rulings/`: 33 resoluciones, algunas PDF con texto y algunas `.md` (SCBA/JUBA con encabezado `Fuente:`).
- `audiovisual/catalog.csv`: 489 videos con `id, platform, url, title, date, duration, people`; transcripciones pendientes (cada transcripción necesitará marcas de tiempo `mm:ss` como "ancla").
- Los nombres de carpeta/archivo no tienen un ID estable único entre tipos de fuente (cuerpos con guion, fallos con fecha_tribunal_causa, prensa con fecha_medio_slug). Se resuelve con `doc_id` (b.2).

---

## (b) Arquitectura recomendada para ESTE corpus

### Principio rector

Tres capas, de la más inmutable a la más interpretativa; cada capa solo puede citar hacia abajo:

1. **Capa 0, fuentes (inmutables)**: `sources/` tal como está. Nadie la edita. Se agregan solo `manifest` y hashes.
2. **Capa 1, texto y estructura derivados (regenerables)**: texto por página con ID estable, índice FTS, tabla de piezas. Se puede borrar y reconstruir con scripts.
3. **Capa 2, análisis (escrito por agentes y humanos, con procedencia)**: personas, alias, eventos, declaraciones, afirmaciones, hipótesis, hallazgos. Es lo único que no se regenera, por eso vive como **archivos de texto versionados** (JSONL/Markdown) y la base SQLite se **reconstruye a partir de ellos**.

**Decisión central [INFERENCIA]: la base `case.sqlite` es un artefacto de compilación, no la fuente de verdad.** La verdad está en (a) los PDFs/OCR y (b) los archivos de análisis en texto (`analysis/**/*.jsonl|md`). Así hay diffs legibles, historia en git, y varios agentes pueden escribir en archivos separados sin bloquear una base única. `build.py` recompila la base en segundos.

Justificación frente a alternativas: solo-Markdown no permite joins ni agregaciones (cronología, quién dijo qué cuándo); solo-SQLite concentra escrituras concurrentes y esconde el historial; grafo dedicado agrega servidor/dependencia sin necesidad a esta escala (ver 1.2). Híbrido texto-versionado + SQLite compilada es lo más simple y durable.

### b.1 Disposición de carpetas

```
mariamarta/
  AGENTS.md                  # instrucciones para agentes (CLAUDE.md = "ver AGENTS.md")
  METODOLOGIA.md             # este documento
  README.md                  # mapa de una pantalla: qué hay y dónde
  sources/                   # CAPA 0 (solo lectura; no tocar)
  text/                      # CAPA 1 (regenerable)
    pages/<doc_id>.jsonl     # una línea por página: {pid, doc_id, page, text, conf}
    manifest.tsv             # doc_id, original_path, type, sha256, n_pages, text_status
  db/
    schema.sql               # esquema versionado y comentado (documentación viva)
    case.sqlite              # artefacto compilado (en .gitignore o git-lfs)
    queries/*.sql            # consultas guardadas con nombre (timeline_oct27.sql, ...)
  analysis/                  # CAPA 2 (fuente de verdad de lo interpretado)
    entities/personas.jsonl        # un registro por persona canónica
    entities/alias.jsonl           # alias -> persona, con fuente
    entities/organizaciones.jsonl, lugares.jsonl, objetos.jsonl
    events/<yyyy-mm>.jsonl         # eventos con tiempo, lugar, participantes, fuentes
    statements/<persona_id>.jsonl
    claims/<lote>.jsonl            # claims atómicos con fuente y calidad
    evidence/<item_id>.md          # ficha por pieza (autopsia, balística...) + cadena de custodia en jsonl
    hypotheses/H<nn>.md + matriz.jsonl  # ACH
    findings/                      # lo que los agentes reportan (append-only, ver b.8)
  work/
    tasks.json               # cola de tareas (solo cambian estado/claim)
    log.md                   # append-only, una línea por evento de trabajo
    review/                  # lotes propuestos por agentes, pendientes de fusionar
  tools/
    build.py  search.py  cite.py  validate.py  (stdlib de Python; sin dependencias)
```

Cada carpeta de la capa 1 y 2 lleva un `README.md` de 10 líneas (formato, ejemplo, quién escribe). Archivos pequeños y autodescriptivos: un agente que abre un archivo aislado debe entender qué es.

### b.2 IDs y anclas de página (la pieza más importante)

- `doc_id`: minúsculas, estable y legible, **nunca se renombra**. `exp-c01`..`exp-c44`, `exp-anexo-sepelio`, `fallo-2022-toc4`, `prensa-2002-12-14-pagina12-belsunce`, `testim-bartoli-guillermo`, `blog-2002-11-13-testimonial-bartoli`, `vid-nQ6klTwrET0`. Reglas: prefijo por tipo; fecha ISO cuando aplica; ID natural cuando existe (el de YouTube).
- **Ancla de página `pid`** = `doc_id#p<N>` con N de la sección `## Página N` del OCR, sin ceros. Ejemplo: `exp-c05#p100`. Para fallos con texto sin páginas, `doc_id#l<línea>` o `doc_id#s<sección>`; para videos, `vid-XXXX#t=00:12:34`.
- **Distinguir página y foja**: `exp-c05#p100` es siempre "página N del PDF digitalizado". La foja (`fs.`) se guarda aparte en `page.folio` cuando se conoce; **nunca se mezcla en el ID**. Es la fuente típica de citas erróneas en el caso (el índice de cuerpos usa página del PDF; las sentencias usan fojas).
- **Cita canónica** (formato único, parseable con regex, escrita en prosa y en datos): `[[exp-c05#p100]]`; con cita textual: `[[exp-c05#p100|"escaso depósito compatible con pólvora"]]`. Rango: `[[exp-c05#p100-102]]`. `tools/cite.py` valida que el pid existe y que la frase textual aparece (tras normalizar espacios, mayúsculas y diacríticos) en esa página; falla si no.
- **Cita siempre a la fuente primaria más cercana**. Si un dato viene del blog que transcribe una declaración del cuerpo 1, se cita `blog-…` y, si se cotejó, además `exp-c01#p64`, con `verified=1` solo cuando alguien miró el original.
- **Bidireccionalidad por construcción**: nunca se escribe un vínculo a mano en dos sitios. Los vínculos viven en tablas `mention`/`relation` con dos claves foráneas; las vistas dan ambas direcciones (b.3). En Markdown, los enlaces `[[…]]` se extraen en `build.py` a la tabla `link(source, target)`, y la vista `backlinks` los invierte.

### b.3 Esquema SQLite

Convenciones: `TEXT` para IDs legibles; fechas ISO-8601 en texto; toda fila de capa 2 tiene `source_pid` (o tabla puente) y `created_by` (agente/humano + fecha). Nada se borra: se marca `status='discarded'` con motivo.

```sql
PRAGMA foreign_keys = ON;

-- ===== CAPA 1: fuentes y texto =====
CREATE TABLE document (
  doc_id TEXT PRIMARY KEY,           -- exp-c05, fallo-2022-toc4
  type   TEXT NOT NULL CHECK (type IN
    ('case_file','ruling','press','testimony','blog','video','official','evidence','other')),
  title TEXT, date TEXT, original_path TEXT NOT NULL, sha256 TEXT,
  source_url TEXT, captured_at TEXT,
  source_level TEXT CHECK (source_level IN ('primary','official_derivative','secondary','party')),
  n_pages INTEGER
);
CREATE TABLE page (
  pid TEXT PRIMARY KEY,              -- exp-c05#p100
  doc_id TEXT NOT NULL REFERENCES document,
  n INTEGER NOT NULL,                -- pagina del PDF
  folio TEXT,                        -- fs. si se conoce (puede ser rango/"vta")
  text TEXT NOT NULL,
  ocr_conf REAL,                     -- minimo/medio de confidence_scores
  UNIQUE (doc_id, n)
);
CREATE VIRTUAL TABLE page_fts USING fts5(
  text, content='page', content_rowid='rowid',
  tokenize='unicode61 remove_diacritics 2');
CREATE VIRTUAL TABLE page_tri USING fts5(        -- subcadenas / nombres mal escritos
  text, content='page', content_rowid='rowid', tokenize='trigram');
-- (triggers de sincronizacion como en la doc oficial de FTS5; como la base se reconstruye,
--  basta INSERT ... ; INSERT INTO page_fts(page_fts) VALUES('rebuild') en build.py)

CREATE TABLE filing (               -- importa INDICE-por-cuerpos.tsv (1.110 filas)
  filing_id INTEGER PRIMARY KEY, subject TEXT NOT NULL, doc_id TEXT REFERENCES document,
  page INTEGER, filing_type TEXT    -- statement|expert_report|record|brief|decision|... (se clasifica luego)
);

-- ===== CAPA 2: entidades y alias =====
CREATE TABLE entity (
  ent_id TEXT PRIMARY KEY,           -- p:carrascosa-carlos, o:emernort, l:casa-carmel-lote-xx, x:arma-calibre-32
  kind TEXT NOT NULL CHECK (kind IN ('person','organization','place','object','phone_line')),
  canonical_name TEXT NOT NULL, role_summary TEXT, notes TEXT,
  merged_into TEXT REFERENCES entity(ent_id)       -- si se descubre un duplicado: nunca borrar
);
CREATE TABLE alias (
  alias_id INTEGER PRIMARY KEY,
  ent_id TEXT NOT NULL REFERENCES entity,
  alias TEXT NOT NULL, alias_norm TEXT NOT NULL,   -- minusculas, sin tildes, sin signos
  type TEXT CHECK (type IN ('variant','ocr_error','press_error','nickname','other_name','possible_homonym')),
  source_pid TEXT REFERENCES page, confidence TEXT CHECK (confidence IN ('high','medium','low')),
  UNIQUE (ent_id, alias_norm)
);
CREATE INDEX alias_norm_idx ON alias(alias_norm);

-- mention: donde una entidad aparece en una pagina (la puente entity <-> texto)
CREATE TABLE mention (
  mention_id INTEGER PRIMARY KEY,
  pid TEXT NOT NULL REFERENCES page, ent_id TEXT REFERENCES entity,
  literal_text TEXT NOT NULL,        -- tal cual aparece (con la errata)
  status TEXT CHECK (status IN ('auto','confirmed','doubtful','rejected')),
  created_by TEXT
);

-- ===== relaciones (bidireccionales por vista) =====
CREATE TABLE relation (
  rel_id INTEGER PRIMARY KEY,
  a TEXT NOT NULL REFERENCES entity, b TEXT NOT NULL REFERENCES entity,
  type TEXT NOT NULL,                -- conyuge_de, vecino_de, empleado_de, llamo_a, estuvo_con...
  symmetric INTEGER NOT NULL DEFAULT 0,
  since TEXT, until TEXT, claim_id INTEGER REFERENCES claim
);
CREATE VIEW relation_both AS                -- se consulta siempre esta vista
  SELECT rel_id, a AS ent, b AS other, type, since, until, claim_id FROM relation
  UNION ALL
  SELECT rel_id, b, a, type, since, until, claim_id FROM relation WHERE symmetric = 1;
-- relaciones asimetricas: usar tipos inversos explicitos ("empleador_de"/"empleado_de") en una tabla relation_type(type, inverse).

-- ===== eventos (modelo i2/FtM: Interval) =====
CREATE TABLE event (
  ev_id TEXT PRIMARY KEY,                     -- e:2002-10-27T1855-llamada-ambulancia
  t_start TEXT, t_end TEXT,                   -- ISO; hora local Argentina (UTC-3) siempre
  precision TEXT CHECK (precision IN ('minute','hour','day','month','year','approx')),
  t_start_min TEXT, t_start_max TEXT,         -- ventana de incertidumbre (ACH necesita esto)
  type TEXT,                                  -- llamada|ingreso|egreso|pericia|resolucion|declaracion|...
  place_id TEXT REFERENCES entity, description TEXT NOT NULL,
  status TEXT CHECK (status IN ('established','disputed','hypothetical','discarded')) DEFAULT 'disputed',
  created_by TEXT
);
CREATE TABLE event_participant (
  ev_id TEXT REFERENCES event, ent_id TEXT REFERENCES entity,
  role TEXT, PRIMARY KEY (ev_id, ent_id, role)
);

-- ===== afirmaciones (nucleo de la trazabilidad) =====
CREATE TABLE claim (
  claim_id INTEGER PRIMARY KEY,
  text TEXT NOT NULL,                -- UNA proposicion atomica, en tercera persona
  subject_id TEXT REFERENCES entity, -- a quien se refiere
  ev_id TEXT REFERENCES event,       -- evento al que pertenece (opcional)
  asserted_by TEXT REFERENCES entity, -- persona/organismo/medio que la sostiene
  modality TEXT NOT NULL CHECK (modality IN
    ('documentary_fact',   -- consta en documento oficial (protocolo, acta, informe)
     'testimony',          -- declaracion de testigo o perito
     'party',              -- afirmacion de una parte (fiscalia, defensa, familia)
     'press',              -- lo reporta un medio sin citar el documento
     'inference')),        -- razonamiento del analista, NUNCA se presenta como dato
  verified INTEGER NOT NULL DEFAULT 0,     -- 1 solo si alguien miro la fuente primaria
  confidence TEXT CHECK (confidence IN ('high','medium','low')),
  stated_at TEXT,                    -- cuando se dijo/escribio (distinto de t_start del hecho)
  status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','corroborated','contradicted','withdrawn')),
  created_by TEXT NOT NULL
);
CREATE TABLE citation (              -- una afirmacion puede tener N fuentes
  claim_id INTEGER REFERENCES claim, pid TEXT REFERENCES page,
  quote TEXT,                        -- literal, validada contra page.text por validate.py
  role TEXT CHECK (role IN ('supports','contradicts','context')),
  PRIMARY KEY (claim_id, pid, role)
);
CREATE TABLE claim_link (            -- contradicciones / corroboraciones / derivaciones
  a INTEGER REFERENCES claim, b INTEGER REFERENCES claim,
  type TEXT CHECK (type IN ('contradicts','corroborates','derives_from','reiterates','qualifies')),
  note TEXT, created_by TEXT, PRIMARY KEY (a, b, type)
);

-- ===== declaraciones (misma persona a lo largo de los años) =====
CREATE TABLE statement (
  stmt_id TEXT PRIMARY KEY,          -- d:bartoli-guillermo-2002-11-16-testimonial
  ent_id TEXT NOT NULL REFERENCES entity,
  date TEXT NOT NULL, venue TEXT,    -- testimonial|indagatoria|juicio|entrevista_prensa|careo
  capacity TEXT,                     -- testigo|imputado|perito|querellante (cambia con los anios!)
  pid_start TEXT REFERENCES page, pid_end TEXT REFERENCES page,
  source_level TEXT                  -- directa (acta) | citada_en_fallo | citada_en_prensa | blog
);
-- cada proposicion de una declaracion es una fila de 'claim' con asserted_by = la persona y
-- tabla puente statement_claim(stmt_id, claim_id); el tema se etiqueta con 'topic' para comparar.
CREATE TABLE topic (topic_id TEXT PRIMARY KEY, description TEXT);  -- p. ej. hora_salida_carrascosa
CREATE TABLE claim_topic (claim_id INTEGER REFERENCES claim, topic_id TEXT REFERENCES topic,
  PRIMARY KEY (claim_id, topic_id));

-- ===== evidencia y cadena de custodia =====
CREATE TABLE evidence_item (
  item_id TEXT PRIMARY KEY,          -- ev:proyectil-1, ev:autopsia-protocolo, ev:alarma-log
  type TEXT,                         -- autopsia|balistica|adn|telefonia|acustica|alarma|huella|video|...
  description TEXT NOT NULL, object_ent TEXT REFERENCES entity
);
CREATE TABLE custody (
  item_id TEXT REFERENCES evidence_item, seq INTEGER,
  t TEXT, action TEXT,               -- hallado|secuestrado|entregado|periciado|devuelto|perdido|exhumado
  from_ent TEXT REFERENCES entity, to_ent TEXT REFERENCES entity,
  place_id TEXT REFERENCES entity, source_pid TEXT REFERENCES page,
  PRIMARY KEY (item_id, seq)
);
CREATE TABLE expert_report (
  report_id TEXT PRIMARY KEY, item_id TEXT REFERENCES evidence_item,
  expert_id TEXT REFERENCES entity, t TEXT, method TEXT,
  literal_conclusion TEXT, source_pid TEXT REFERENCES page,
  limitations TEXT                   -- p. ej. "autolisis impide ..." (lo que la pericia NO puede decir)
);

-- ===== hipotesis (ACH) =====
CREATE TABLE hypothesis (h_id TEXT PRIMARY KEY, statement TEXT, status TEXT);
CREATE TABLE ach (                   -- matriz evidencia x hipotesis
  claim_id INTEGER REFERENCES claim, h_id TEXT REFERENCES hypothesis,
  value TEXT CHECK (value IN ('consistent','inconsistent','neutral','very_inconsistent')),
  weight TEXT CHECK (weight IN ('high','medium','low')), note TEXT, created_by TEXT,
  PRIMARY KEY (claim_id, h_id)
);

-- ===== trazabilidad del trabajo (PROV simplificado) =====
CREATE TABLE activity (              -- una corrida de OCR, un barrido de un agente
  act_id TEXT PRIMARY KEY, agent TEXT, model TEXT, t TEXT, task_id TEXT, description TEXT
);
-- 'created_by' de las filas apunta a act_id; 'derives_from' en claim_link/citation cubre PROV:wasDerivedFrom.

CREATE TABLE link (source TEXT, target TEXT);   -- [[...]] extraidos de los .md
CREATE VIEW backlinks AS SELECT target, source AS referenced_by FROM link;
```

**Vistas útiles** (viven en `db/schema.sql`, se prueban en `validate.py`):

- `v_timeline`: `event` unido a participantes y a sus afirmaciones/citas, ordenado por `t_start`; incluye `precision` y ventana de incertidumbre.
- `v_statements_by_person`: declaraciones + afirmaciones por `ent_id`, `topic`, `stated_at`, `capacity`.
- `v_contradictions`: pares de `claim_link` con tipo `contradicts`, más los pares **candidatos** (misma persona, mismo `topic`, distinto texto) aún no clasificados.
- `v_uncited`: afirmaciones sin ninguna fila en `citation` (debe estar vacía; `validate.py` falla si no lo está).
- `v_ambiguous_aliases`: `alias_norm` asociado a más de una entidad.
- `v_coverage`: por `doc_id`, páginas con y sin menciones, páginas de OCR dudoso (`ocr_conf` bajo).
- `v_custody_gaps`: ítems de evidencia con saltos en `custody` (sin destinatario del traslado, o sin fecha).

**Vistas materializadas**: no usar triggers para nada salvo FTS. `build.py` reconstruye `cache_timeline` y `cache_comentions` (`DROP` + `CREATE TABLE … AS SELECT`) al final de cada compilación; si un agente escribe análisis nuevo, la base se recompila (segundos, porque la capa 2 son archivos pequeños y la capa 1 se carga de JSONL). Justificación: SQLite no tiene vistas materializadas nativas y la alternativa estándar es una tabla resumen refrescada por trigger o por script (https://madflex.de/SQLite-triggers-as-replacement-for-a-materialized-view); como el corpus no cambia en tiempo real, el refresco por script es más simple y verificable.

### b.4 Resolución de entidades y alias

Problema real: `Casafús` / `CAZAFUS`; `Paez Juan Marcelo` / `Juan Pablo`; `Bártoli`/`Bartoli`; `Moreira`/`Moreyra`; errores de OCR sobre manuscritos.

1. **Entidad canónica primero, alias después, nunca al revés.** Cada persona tiene un `ent_id` y una lista de alias con tipo y fuente. La tabla `alias` es el diccionario que usan todos los agentes.
2. **Normalización** (`alias_norm`): minúsculas, sin tildes, `z/s/c` no se unifican automáticamente (se hace por similitud, no por regla ciega), sin puntuación, apellido-nombre y nombre-apellido ambos indexados.
3. **Generar candidatos, no decisiones.** `search.py --variants` usa `page_tri` (trigram) y distancia de edición (`difflib` de la stdlib) para proponer variantes de cada alias en todo el texto; el resultado entra a `mention` con `status='auto'` o `'doubtful'`.
4. **Confirmar con contexto.** Una mención solo pasa a `confirmed` si en la misma página hay otra pista que la ancla (rol, domicilio, lote, parentesco, repetición del nombre completo). Casos como `Juan Marcelo` vs. `Juan Pablo` Paez se registran como **`possible_homonym`**, no se fusionan: el agente deja una nota con la evidencia a favor y en contra, y la decisión de fusionar queda para revisión humana.
5. **Fusión reversible.** Dos entidades se unen con `merged_into`; nunca se borra la fila. Toda consulta usa la vista `entity_current` que resuelve la cadena.
6. **Dos tipos de error distintos:** `ocr_error` (la página dice otra cosa que la imagen) y `source_error` (el documento original escribe mal el nombre). Se distinguen mirando la imagen de la página; un agente de OCR no debe "corregir" errores de la fuente, solo anotarlos.
7. Existe NER/ML (Datashare) para extraer entidades de documentos grandes, pero **[INFERENCIA]** con 11 mil páginas y una lista cerrada de personas (~cientos), la lista de alias semilla (`testimonies/people/` ya tiene 91 personas) más búsqueda por trigram da mejor precisión y es auditable. Un LLM puede *proponer* menciones, siempre con `status='auto'`.

### b.5 Hecho vs. afirmación de parte

Dos ejes separados que no se deben mezclar:

- **Modalidad** (quién lo dice y cómo consta): `documentary_fact`, `testimony`, `party`, `press`, `inference`. Reutiliza los marcadores [HECHO]/[TESTIMONIO]/[PARTE]/[PRENSA] de `EVIDENCIA.md` y agrega `inference` para razonamiento propio.
- **Estado de verificación**: `verified` (0/1: alguien cotejó la fuente primaria) y `status` (`open/corroborated/contradicted/withdrawn`).

Reglas: (1) un "hecho" que solo está en una sentencia citado de segunda mano es `documentary_fact` con `source_level='citada_en_fallo'`, no verificado hasta ubicar el original; (2) el blog `casobelsunce` y los resúmenes de prensa nunca suben de `press`/`party` por sí solos; (3) una sentencia es fuente primaria de lo que *el tribunal concluyó*, no de lo que *ocurrió*: se registra "el TOC4 sostuvo que X" con `asserted_by = TOC4`; (4) "Texto de una afirmación" siempre en tercera persona y atómico ("Bártoli declaró que Carrascosa se fue después del primer gol de Independiente"), con una sola proposición.

### b.6 Cronología y modelo de contradicciones

**Tiempo.** Todos los tiempos en hora local de Argentina (UTC-3, sin horario de verano en octubre de 2002; **verificar**: Argentina tuvo horario de verano en distintos años y 2002 no debe asumirse). Se guarda `t_start` y la ventana `t_start_min/max`; "como a las siete menos cinco" es `precision='approx'` con ventana. Para cada evento clave del 27-oct-2002 se mantienen, en filas separadas, **las versiones de cada fuente** (el mismo hecho con distintas horas según la declaración, el registro telefónico, el log de alarma, el partido de fútbol). El evento "verdadero" es una síntesis posterior, marcada `status='disputed'` hasta que haya un anclaje instrumental (registros de antena, log de alarma, ambulancia, transmisión del partido).

**Anclas instrumentales:** jerarquizar las fuentes de tiempo: (1) registros automáticos (telefonía, alarma, llamadas a emergencias, hora del partido); (2) actas con hora; (3) declaraciones con hora; (4) prensa. La vista `v_timeline` incluye una columna `anchor_type`.

**Cronología procesal 2002–2025**: mismos `event`s con `type='resolucion'`, ligados al fallo (`doc_id`) y a una instancia (`venue` en un campo o tabla `causa`/`tribunal`), para encadenar recursos y nulidades.

**Contradicciones.** Tres niveles:
1. *Candidatas automáticas* (`v_contradictions`): misma persona + mismo `topic_id`, distinto contenido, ordenadas por `stated_at`. Un agente las revisa y las clasifica.
2. *Clasificadas* en `claim_link`: `contradicts` / `qualifies` / `reiterates`. **Distinguir cambio genuino de diferencia de forma:** un `qualifies` (más detalle) no es un `contradicts`.
3. *Explicadas*: cada contradicción lleva `note` con una hipótesis de explicación (cambio de condición procesal, error del acta, transcripción de segunda mano, otro momento del día). Esto es lo que alimenta ACH.

La condición procesal (`capacity` en `statement`) cambia: testigo en 2002, imputado después; el sesgo del declarante cambia con ella, y debe verse en cualquier comparación.

### b.7 Procedencia y formato de cita

- Toda fila de capa 2 tiene `created_by` → `activity`(agent, model, t, task_id). Los hallazgos de agentes entran como `status='auto'`/`verified=0`.
- Cita en prosa y datos: `[[pid]]` o `[[pid|"frase"]]` (b.2).
- `validate.py` (estricto, falla el build): pid inexistente; frase textual que no aparece en la página; afirmación sin cita; fecha mal formada; `alias_norm` duplicado en dos entidades; evento sin ninguna cita; ciclo en `merged_into`.
- Cada fuente externa tiene `sha256` y `captured_at` (la práctica de Bellingcat: archivar la fuente, no confiar en que la URL siga viva).

### b.8 Cómo consultan los agentes

Orden recomendado (de lo más barato y verificable a lo más caro):

1. `README.md` y `db/schema.sql` (el esquema está comentado: es la documentación).
2. **grep exacto** sobre `text/pages/*.jsonl` o `sources/**/*.ocr.md` para números, horas, nombres propios.
3. **FTS5** para frases y proximidad.
4. **SQL** para cruzar entidades, eventos y declaraciones.
5. (Opcional, fase 6) búsqueda semántica con `sqlite-vec`, solo como pista.

Ejemplos (se prueban con `sqlite3 db/case.sqlite`):

```sql
-- Buscar una frase con proximidad, con página citable
SELECT p.pid, snippet(page_fts, 0, '[', ']', '...', 20)
FROM page_fts JOIN page p ON p.rowid = page_fts.rowid
WHERE page_fts MATCH 'NEAR(ambulancia llamado, 8)' ORDER BY rank LIMIT 20;

-- Variantes de un apellido por subcadena (trigram)
SELECT p.pid, snippet(page_tri,0,'[',']','...',12)
FROM page_tri JOIN page p ON p.rowid = page_tri.rowid
WHERE page_tri MATCH 'zafus OR zaphus OR casaf';

-- Todo lo que dijo una persona sobre un tema, en orden temporal, con condicion procesal
SELECT d.date, d.capacity, a.text, group_concat(c.pid, ' ')
FROM statement d
JOIN statement_claim da USING(stmt_id) JOIN claim a USING(claim_id)
JOIN claim_topic t USING(claim_id) LEFT JOIN citation c USING(claim_id)
WHERE d.ent_id='p:bartoli-guillermo' AND t.topic_id='hora_salida_carrascosa'
GROUP BY a.claim_id ORDER BY d.date;

-- Minuto a minuto del 27-oct-2002 con todas las versiones y sus fuentes
SELECT t_start, precision, description, status FROM v_timeline
WHERE t_start BETWEEN '2002-10-27T15:00' AND '2002-10-27T23:59' ORDER BY t_start;

-- Quien se vincula con una persona (ambas direcciones, un salto)
SELECT other, type FROM relation_both WHERE ent='p:hurtig-irene';

-- Contradicciones candidatas todavia sin clasificar
SELECT * FROM v_contradictions WHERE classified = 0;

-- Hallazgo de huecos: items de evidencia sin cadena completa
SELECT * FROM v_custody_gaps;
```

```bash
# grep exacto, citando archivo y número de linea
grep -rn --include='*.ocr.md' -i 'ambulancia' sources/case-file/Cuerpo-02 | head
# herramienta: busqueda con cita lista para pegar
python3 tools/search.py "primer gol de Independiente" --type case_file
python3 tools/cite.py "exp-c01#p64" "Carlos se fue despues del primer gol"   # valida la cita
```

**Coordinación multiagente** (basado en el patrón de Anthropic y en el principio de escritor único por archivo):

- **Una cola**: `work/tasks.json` con `{id, title, inputs, outputs, status: pending|claimed|done|blocked, agent, depends_on}`. El agente solo cambia `status`/`agent` (como el campo `passes` del arnés de Anthropic). Para evitar carreras al reclamar, cada agente reclama creando un archivo `work/claims/<tarea_id>.lock` con `mkdir` (atómico), no editando el JSON compartido.
- **Escritura**: cada agente escribe **solo en su carpeta de salida** (`work/review/<tarea_id>/…` o el archivo del que es dueño según la tabla de paquetes). Un paso `fusionar` único (humano o agente integrador) mueve lotes aprobados a `analysis/` tras `validate.py`.
- **Bitácora append-only**: `work/log.md`, una línea por evento (`2026-11-02T10:14 | agente-3 | tarea WP4 | terminé cuerpos 5-8 | 412 afirmaciones | pendientes: …`). Se escribe con `>>` (apéndice).
- **Hallazgos**: `analysis/findings/H-<aaaammdd>-<n>.md`, un archivo por hallazgo, con: enunciado, citas `[[pid|"frase"]]`, qué hipótesis apoya o refuta, qué se verificó y qué no, y qué diría que lo refutaría. Nunca se editan; se reemplazan con otro que lo referencia.
- Instrucciones precisas a subagentes (entradas, salidas, criterio de "hecho", prohibido tocar X): sin eso, las tareas se duplican (ver contexto multiagente arriba).

### b.9 Esquema de AGENTS.md (esquema a escribir en la raíz)

1. **Propósito y principios** (5 líneas): corpus de un caso real; objetivo = encontrar detalles pasados por alto *con citas verificables*; no se afirma nada sin `[[pid]]`.
2. **Mapa del repositorio** (el árbol de b.1, con "quién escribe qué").
3. **Reglas duras**: `sources/` es de solo lectura; todo dato lleva cita; distinguir modalidad (b.5); no corregir errores de la fuente; hora local UTC-3; no inventar fojas ni páginas; no fusionar entidades homónimas sin evidencia.
4. **Cómo buscar** (orden de b.8, con 3 ejemplos).
5. **IDs y citas** (formato exacto, validador).
6. **Cómo contribuir**: reclamar tarea, escribir solo en tu carpeta, correr `validate.py`, anotar en bitácora, formato de hallazgo.
7. **Qué NO hacer** (resumen de la sección d).
8. **Glosario argentino-procesal**: cuerpo, foja (fs.), vta., indagatoria (art. 308 CPP), testimonial, careo, TOC, SCBA, CSJN, Casación, querella, falta de mérito, sobreseimiento.
9. **Contexto mínimo del caso** (10 líneas neutrales: quién, cuándo, dónde, principales etapas procesales), sin conclusiones.
10. **Convenciones de salida**: español neutro, citas literales entre comillas, incertidumbre explícita ("no consta", "no verificado").

---

## (c) Plan por fases y paquetes de trabajo (independientes y paralelizables)

Regla: un paquete = una carpeta de salida propia; ningún paquete edita archivos de otro. Dependencias explícitas. `Pn` = fase.

**P0, cimientos (secuencial, pequeño; lo hace un solo agente antes de abrir el resto)**

- **WP0 – Manifiesto, IDs y esqueleto.** Entrada: `sources/**`. Salida: `text/manifest.tsv` (doc_id, original_path, type, sha256, n_pages, source_level), `db/schema.sql`, `AGENTS.md`, `README.md`, `tools/build.py|validate.py|cite.py|search.py` (stdlib), `work/tasks.json`. Criterio: `build.py` corre vacío y `validate.py` pasa.

**P1, capa de texto (paralelizable por tipo de fuente; dependen solo de WP0)**

- **WP1 – Expediente → páginas.** Entrada: `sources/case-file/*/*.ocr.json|md` (cuando termine el OCR). Salida: `text/pages/exp-c*.jsonl` con `pid`, `n`, `text`, `ocr_conf` (de `confidence_scores`); lista de páginas con OCR dudoso. Criterio: n páginas de cada JSONL = `total` del PDF; QA por muestreo 20 páginas/cuerpo comparando con la imagen.
- **WP2 – Índice de piezas.** Entrada: `INDICE-por-cuerpos.tsv`, `INDICE-alfabetico.tsv`. Salida: `analysis/filings.tsv` (filing_id, subject, doc_id, page, filing_type clasificado). Criterio: 1 110 filas y cada `doc_id#pN` existe.
- **WP3 – Fallos, prensa, testimonios, blog, oficial, wikipedia, archive-org, scribd → páginas/secciones.** Una subtarea por carpeta (independientes). Salida: `text/pages/<prefijo>-*.jsonl` + metadatos (fecha, medio, tribunal, url, `source_level`). Fallos largos: ancla `#s<sección>`/`#l<línea>` y, si tiene paginación, `#p`. Criterio: todo documento en `manifest.tsv` tiene páginas.
- **WP4 – Video (después, cuando haya transcripciones).** Entrada: `audiovisual/catalog.csv` + transcripciones. Salida: `text/pages/vid-*.jsonl` con segmentos y `t=`.

**P2, entidades (paralelizable por clase; dependen de WP1–WP3 para detectar menciones)**

- **WP5 – Personas semilla y alias.** Entrada: `testimonies/people/*.md` (91), `testimonies/README.md`, `evidence/EVIDENCIA.md`. Salida: `analysis/entities/personas.jsonl`, `alias.jsonl` con tipo/fuente/confianza. Criterio: toda persona con ≥1 declaración tiene `ent_id`; los homónimos dudosos marcados `possible_homonym`.
- **WP6 – Organizaciones, lugares, objetos, líneas telefónicas.** Entrada: los mismos + fallos. Salida: `analysis/entities/{organizaciones,lugares,objetos}.jsonl`.
- **WP7 – Barrido de menciones.** Entrada: WP1/WP3 + WP5/WP6. Salida: `work/review/WP7/menciones-<doc_id>.jsonl` (un archivo por documento, así N agentes en paralelo sin conflicto); modo `auto/doubtful`. Criterio: reporte de alias nuevos descubiertos por trigram, para revisión de WP5.

**P3, extracción de afirmaciones y declaraciones (paralelizable por persona o por cuerpo)**

- **WP8 – Declaraciones por persona.** Una subtarea por persona/grupo. Entrada: página(s) del expediente según `filing` + fallos que las citan + `testimonies/people/<x>.md`. Salida: `analysis/statements/<persona_id>.jsonl` (decl + afirmaciones atómicas con cita textual y `topic`). Criterio: `validate.py` verde; cada declaración con `capacity` y `source_level`.
- **WP9 – Pericias y evidencia física.** Entrada: autopsia, balística, ADN, telefonía/antenas, pericia acústica, logs de alarma (expediente + `extractos_*_pericias.md` + sentencias). Salida: `analysis/evidence/<item_id>.md` + `evidence_item.jsonl`, `custody.jsonl`, `expert_report.jsonl`. Criterio: cada pericia con `limitations` y `literal_conclusion`.
- **WP10 – Sentencias: qué sostuvo cada tribunal.** Una subtarea por fallo. Salida: `analysis/claims/fallo-*.jsonl` (`asserted_by = tribunal`, `modality='documentary_fact'` solo para lo que el fallo cita de actas; el resto `party`/`inference`). Y `analysis/events/procesal.jsonl` con la cronología 2002–2025.

**P4, cronología (depende de P3)**

- **WP11 – Cronología del 27-oct-2002.** Entrada: WP8/WP9 + expediente. Salida: `analysis/events/2002-10.jsonl` (eventos con ventana de incertidumbre, una fila por versión de cada fuente + una de síntesis `disputed`) y consulta `db/queries/timeline_oct27.sql`. Criterio: cada evento con ≥1 cita; anclas instrumentales marcadas.
- **WP12 – Cronología procesal consolidada.** Entrada: WP10 + `rulings/`. Salida: `analysis/events/procesal-*.jsonl`.

**P5, análisis (depende de P3–P4; aquí se buscan los "detalles pasados por alto")**

- **WP13 – Contradicciones y cambios de versión.** Entrada: `v_contradictions`. Salida: `analysis/claims/vinculos-<persona>.jsonl`, un informe `findings/` por cambio relevante. Criterio: separar `contradicts` de `qualifies` con nota.
- **WP14 – Matriz ACH.** Entrada: hipótesis redactadas por humano (≥3, incluyendo las contradictorias entre sí) + afirmaciones. Salida: `analysis/hypotheses/*.md` + `matriz.jsonl`. Criterio: por cada hipótesis, la lista de evidencia *inconsistente* con ella, no solo la que la apoya.
- **WP15 – Auditoría independiente.** Un agente distinto, sin ver las conclusiones: re-verifica por muestreo 5 % de citas y todos los hallazgos de alto impacto contra el original. Salida: `work/review/auditoria-*.md`. Es el control contra citas inventadas.
- **WP16 – Huecos y cobertura.** Entrada: `v_coverage`, `v_custody_gaps`. Salida: lista de páginas nunca mencionadas, piezas del índice sin analizar, huecos de custodia. Realimenta la cola.

**P6, opcional**

- **WP17 – Búsqueda semántica (`sqlite-vec` + RRF).** Solo si el grep/FTS demuestra insuficiencia. Justificación de la dependencia: permite encontrar pasajes parecidos con otras palabras; cargarla es una extensión (`pip install sqlite-vec`); se mantiene fuera del camino crítico y se marca "pista, no evidencia". Salida: `db/vec.sqlite` separado (no toca la base principal).
- **WP18 – Exportación a grafo (Gephi/Neo4j) y visualización.** Solo lectura desde SQLite.

**Orden y paralelismo:** WP0 → {WP1, WP2, WP3} en paralelo → {WP5, WP6} → WP7 (N agentes, uno por documento) y {WP8, WP9, WP10} (N agentes) → {WP11, WP12} → {WP13, WP14} → WP15/WP16 en continuo.

Cuellos de botella: el OCR de los 44 cuerpos (WP1 espera) y la revisión humana de fusiones de entidades (WP5/WP7). Planificar un revisor humano para `possible_homonym` y para aprobar la fusión a `analysis/`.

---

## (d) Riesgos y qué NO hacer

**Riesgos**
1. **Citas inventadas o mal ubicadas por LLM.** Mitigación: `cite.py` verifica que la frase aparezca en la página; auditoría independiente (WP15); `verified=0` por defecto.
2. **Confundir página con foja.** Mitigación: dos columnas, nunca en el ID; las citas de sentencias se registran como `folio` y no se convierten a página sin evidencia.
3. **Errores de OCR sobre manuscritos y sellos** (nombres, horas, cifras). Mitigación: `ocr_conf`, revisión visual de la imagen para toda cifra/hora que sostenga un hallazgo, distinguir `ocr_error` de `source_error`. Un hallazgo que dependa de un número leído por OCR debe citar que se verificó en la imagen.
4. **Fuentes con posición tratadas como hechos.** El blog `casobelsunce`, la prensa, las partes. Mitigación: modalidad obligatoria y `source_level`.
5. **Sesgo de confirmación del agente** (el riesgo que ACH existe para combatir): pedir explícitamente evidencia inconsistente y varias hipótesis rivales; que un agente auditor no vea la conclusión.
6. **Fusión errónea de homónimos** (Juan Marcelo/Juan Pablo Paez) o separación errónea de variantes. Mitigación: fusión reversible y revisión humana.
7. **Cadena de custodia reconstruida con huecos.** El hueco es información: se registra el hueco, no se rellena por inferencia.
8. **Dependencias efímeras:** Kùzu, p. ej., fue archivado a las pocas semanas de su adquisición (ver 1.2). Mantener la fuente de verdad en archivos de texto y SQLite estándar.
9. **Datos personales y sensibles** (menores, víctimas, imputados fallecidos, testigos): el corpus es de fuentes públicas, pero los análisis derivados pueden difamar si afirman más de lo que consta. Mitigación: modalidad estricta, "no consta", y no publicar análisis sin revisión humana. (Consulta legal local aparte, fuera de alcance de este documento.)
10. **Costo y volumen:** 11 200 páginas × múltiples pasadas de LLM es costoso (los sistemas multiagente de investigación consumen muchos más tokens que un chat único, según los resúmenes de Anthropic citados arriba, cifra no verificada en la fuente original). Mitigación: grep/FTS primero; LLM solo sobre páginas candidatas; priorizar cuerpos por la tabla de piezas.

**Qué NO hacer**
- No editar `sources/` ni renombrar archivos o `doc_id` (se rompen todas las citas).
- No hacer de la base SQLite la única copia del análisis; no permitir que varios agentes escriban en ella a la vez.
- No guardar afirmaciones largas, mezcladas o sin fuente; una proposición por fila.
- No usar embeddings como sustituto de lectura; no citar un fragmento recuperado por similitud sin leer la página.
- No "limpiar" el texto de la fuente (ortografía, nombres) en la capa 1; las normalizaciones van en columnas aparte (`alias_norm`).
- No poner vínculos a mano en dos lugares; no escribir una relación sin su inversa derivada por vista.
- No adoptar Neo4j/Elasticsearch/Datashare/Aleph como dependencia inicial; son útiles para volúmenes mucho mayores (millones de documentos). Reconsiderar solo si se necesita una interfaz de búsqueda para humanos no técnicos (Datashare/Aleph) o análisis de redes grandes (exportar).
- No declarar "terminado" un paquete sin que `validate.py` pase (el arnés de Anthropic documenta que los agentes tienden a dar por terminado el trabajo antes de tiempo y a marcar tareas como completadas sin verificar).
- No presentar una inferencia como dato ni una sentencia como prueba de lo que relata.

---

### Lista de URLs consultadas

- https://docs.aleph.occrp.org/developers/followthemoney/
- https://followthemoney.readthedocs.io/_/downloads/en/latest/pdf/
- https://docs.aleph.occrp.org/users/getting-started/key-terms
- https://www.icij.org/inside-icij/2024/02/datashares-new-plug-in-helps-investigative-journalists-connect-the-dots-with-graphs/
- https://neo4j.com/blog/developer/exploring-the-pandora-papers-with-neo4j/
- https://github.com/ICIJ/datashare-docs
- https://docs.i2group.com/anb/9.4.1/items.html
- https://docs.i2group.com/ibase/10.0.0/using_the_timeline_assistant.html
- https://www.cia.gov/resources/csi/static/Pyschology-of-Intelligence-Analysis.pdf
- https://www.bellingcat.com/app/uploads/2022/12/JA-Manual-for-PUBLICATION.pdf
- https://gijn.org/tag/chronolocation/
- https://www.sqlite.org/fts5.html
- https://simonwillison.net/2024/Oct/4/hybrid-full-text-search-and-vector-search-with-sqlite/
- https://arxiv.org/pdf/2608.24060
- https://madflex.de/SQLite-triggers-as-replacement-for-a-materialized-view
- https://towardsdatascience.com/six-degrees-of-sql/
- https://betakit.com/apple-strikes-deal-to-acquire-canadian-database-software-startup-kuzu/
- https://www.puppygraph.com/blog/what-is-kuzudb
- https://www.w3.org/blog/2012/the-prov-ontology-an-update
- https://infoq.com/news/2025/08/agents-md/
- https://addyosmani.com/agents/15-agents-md/
- https://the-decoder.com/new-llms-txt-web-standard-could-fundamentally-change-how-llms-read-and-process-online-content/
- https://anthropic.com/engineering/effective-harnesses-for-long-running-agents
- https://agentic-ai.readthedocs.io/en/latest/ContextEngineering/anthropic/
- https://www.langchain.com/blog/how-and-when-to-build-multi-agent-systems
- https://en.wikipedia.org/wiki/DocumentCloud
- https://github.com/paulbradshaw/dealingwithdocuments

Nota de honestidad: varias fuentes se leyeron solo vía resumen de búsqueda (Bellingcat, Heuer, i2, W3C PROV, AGENTS.md, llms.txt); solo FtM (parcial), FTS5 (parcial) y el artículo de Anthropic sobre arneses se abrieron directamente. La compatibilidad real de cada herramienta con AGENTS.md y la zona horaria/horario de verano de octubre de 2002 en Argentina deben verificarse antes de construir.
