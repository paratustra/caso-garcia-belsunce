-- Schema of db/case.sqlite. The database is a BUILD ARTIFACT: build.py regenerates it
-- from text/ (layer 1) and analysis/ (layer 2). Do not write to it: write to the files.
-- Foreign keys document relations; they are not enforced on load: validate.py checks them
-- (PRAGMA foreign_key_check) so that one bad row does not stop the rest from building.
-- Differences from METODOLOGIA.md b.3: see DECISIONES.md.

-- ===== LAYER 1: sources and text =====
CREATE TABLE document (
  doc_id TEXT PRIMARY KEY,           -- exp-c05, fallo-2024-03-27-..., blog-2003-01-10-...
  type   TEXT NOT NULL CHECK (type IN
    ('case_file','ruling','press','testimony','blog','video','official','evidence','other')),
  title TEXT, date TEXT, original_path TEXT NOT NULL,   -- original_path = original file in sources/
  text_path TEXT,                    -- file the text comes from (.ocr.md, .txt.md, .md, .pdf)
  sha256 TEXT,                       -- of the original file
  source_url TEXT, captured_at TEXT,
  source_level TEXT CHECK (source_level IN ('primary','official_derivative','secondary','party')),
  n_pages INTEGER,                   -- pages of the original (case file: 'total' from source.json)
  n_text_pages INTEGER,              -- pages or sections with text in layer 1
  text_status TEXT,                  -- complete|partial|pending_ocr|no_text|pending_transcription
  anchor TEXT                        -- 'p' = PDF page, 's' = stable section (unpaginated text)
);
CREATE TABLE page (
  pid TEXT PRIMARY KEY,              -- exp-c05#p100 (PDF page) or prensa-...#s2 (section)
  doc_id TEXT NOT NULL REFERENCES document,
  n INTEGER NOT NULL,                -- PDF page / section number
  folio TEXT,                        -- printed folio (foja) detected automatically (heuristic: check the image)
  text TEXT NOT NULL,                -- text as is (OCR and source errors not corrected)
  ocr_conf REAL,                     -- mean OCR confidence if available (today: NULL, Mistral did not provide it)
  source_file TEXT,                  -- layer-0 file the text comes from
  line INTEGER,                      -- line of that file where the page starts (for grep/sed)
  t_start INTEGER,                   -- video only: second of the video where chunk #sN starts (= (N-1)*300)
  UNIQUE (doc_id, n)
);
CREATE VIRTUAL TABLE page_fts USING fts5(
  text, content='page', content_rowid='rowid',
  tokenize='unicode61 remove_diacritics 2');
CREATE VIRTUAL TABLE page_tri USING fts5(        -- substrings / misspelled names (>= 3 letters)
  text, content='page', content_rowid='rowid', tokenize='trigram remove_diacritics 1');
CREATE VIRTUAL TABLE page_vocab USING fts5vocab(page_fts, 'row');   -- term, doc, cnt

CREATE TABLE filing (               -- INDICE-por-cuerpos.tsv (1,110 rows); PAGINA = PDF page
  filing_id INTEGER PRIMARY KEY, subject TEXT NOT NULL, original_volume TEXT,
  doc_id TEXT REFERENCES document,   -- NULL if the volume is ambiguous ('cuerpo 36' -> 36a/36b) and was not resolved
  page INTEGER, page_end INTEGER, pid TEXT,
  filing_type TEXT,                  -- statement|expert_report|record|decision|brief|other (by keywords)
  doc_resolution TEXT,               -- direct|by_text|ambiguous
  candidates TEXT
);

-- ===== Extraction per volume (EXT-* tasks; files analysis/extraction/<doc_id>.jsonl) =====
-- Only lines that pass validation get in; the rest go to db/rejected/<doc_id>.jsonl.
CREATE TABLE extraction (
  ext_id TEXT PRIMARY KEY,           -- <doc_id>:<line number in the file>
  doc_id TEXT NOT NULL REFERENCES document, page_start INTEGER NOT NULL, page_end INTEGER NOT NULL,
  folio TEXT, type TEXT NOT NULL, date TEXT, summary TEXT NOT NULL,
  evidence_pid TEXT REFERENCES page, evidence_quote TEXT,
  agent TEXT, file TEXT
);
CREATE TABLE extraction_item (
  ext_id TEXT NOT NULL REFERENCES extraction,
  kind TEXT NOT NULL CHECK (kind IN ('person','place','object','time','date')),
  text TEXT NOT NULL,                -- literal form as it appears on the page
  role TEXT,                         -- person: role if the page states it
  value TEXT,                        -- time 'HH:MM' or interpreted ISO date
  pid TEXT NOT NULL REFERENCES page, quote TEXT NOT NULL
);
CREATE INDEX extraction_item_text ON extraction_item(kind, text);

-- ===== LAYER 2: entities and aliases =====
CREATE TABLE entity (
  ent_id TEXT PRIMARY KEY,           -- p:carrascosa-carlos, o:emernort, l:casa-carmel, x:arma-calibre-32
  kind TEXT NOT NULL CHECK (kind IN ('person','organization','place','object','phone_line')),
  canonical_name TEXT NOT NULL, role_summary TEXT, notes TEXT,
  merged_into TEXT REFERENCES entity(ent_id),      -- duplicate found: never delete
  created_by TEXT
);
CREATE VIEW entity_current AS        -- resolves merge chains
  WITH RECURSIVE c(ent_id, current, step) AS (
    SELECT ent_id, ent_id, 0 FROM entity WHERE merged_into IS NULL
    UNION ALL
    SELECT e.ent_id, c.current, c.step + 1 FROM entity e JOIN c ON e.merged_into = c.ent_id
    WHERE c.step < 50)
  SELECT ent_id, current FROM c;
CREATE TABLE alias (
  alias_id INTEGER PRIMARY KEY,
  ent_id TEXT NOT NULL REFERENCES entity,
  alias TEXT NOT NULL, alias_norm TEXT NOT NULL,   -- build.py computes it if missing
  type TEXT CHECK (type IN ('variant','ocr_error','source_error','press_error','nickname','other_name','possible_homonym')),
  source_pid TEXT REFERENCES page, confidence TEXT CHECK (confidence IN ('high','medium','low')),
  created_by TEXT,
  UNIQUE (ent_id, alias_norm)
);
CREATE INDEX alias_norm_idx ON alias(alias_norm);

CREATE TABLE mention (               -- where an entity appears (or a form with no entity yet)
  mention_id INTEGER PRIMARY KEY,
  pid TEXT NOT NULL REFERENCES page, ent_id TEXT REFERENCES entity,   -- ent_id NULL = unresolved
  literal_text TEXT NOT NULL,        -- as it appears (typo included)
  status TEXT CHECK (status IN ('auto','confirmed','doubtful','rejected')),
  candidates TEXT,                   -- ambiguous alias or possible_homonym: possible ent_ids separated by spaces (ent_id NULL)
  quote TEXT,                        -- literal context from the page (verifiable as citation [[pid|"quote"]])
  created_by TEXT                    -- 'extraction:<ext_id>' (build.py, from EXT) or 'WP7/mentions.py' (alias sweep)
);
CREATE INDEX mention_pid ON mention(pid);
CREATE INDEX mention_ent ON mention(ent_id);

-- ===== relations (bidirectional through a view) =====
CREATE TABLE relation_type (type TEXT PRIMARY KEY, inverse TEXT);
CREATE TABLE relation (
  rel_id INTEGER PRIMARY KEY,
  a TEXT NOT NULL REFERENCES entity, b TEXT NOT NULL REFERENCES entity,
  type TEXT NOT NULL, symmetric INTEGER NOT NULL DEFAULT 0,
  since TEXT, until TEXT, claim_id TEXT REFERENCES claim, created_by TEXT
);
CREATE VIEW relation_both AS         -- always query this view
  SELECT rel_id, a AS ent, b AS other, type, since, until, claim_id FROM relation
  UNION ALL
  SELECT r.rel_id, r.b, r.a, CASE WHEN r.symmetric = 1 THEN r.type ELSE coalesce(t.inverse, 'inverse_of:' || r.type) END,
         r.since, r.until, r.claim_id
  FROM relation r LEFT JOIN relation_type t ON t.type = r.type;

-- ===== events =====
CREATE TABLE event (
  ev_id TEXT PRIMARY KEY,            -- e:2002-10-27T1855-llamada-ambulancia
  t_start TEXT, t_end TEXT,          -- ISO, Argentina local time
  precision TEXT CHECK (precision IN ('minute','hour','day','month','year','approx')),
  t_start_min TEXT, t_start_max TEXT,   -- uncertainty window
  type TEXT, anchor_type TEXT,       -- anchor_type: registro_automatico|acta|declaracion|prensa
  place_id TEXT REFERENCES entity, description TEXT NOT NULL,
  status TEXT CHECK (status IN ('established','disputed','hypothetical','discarded')) DEFAULT 'disputed',
  created_by TEXT
);
CREATE TABLE event_participant (
  ev_id TEXT REFERENCES event, ent_id TEXT REFERENCES entity, role TEXT,
  PRIMARY KEY (ev_id, ent_id, role)
);

-- ===== claims =====
CREATE TABLE claim (
  claim_id TEXT PRIMARY KEY,         -- text, e.g. 'a:WP8-bartoli-0001' (unique without coordinating integers)
  text TEXT NOT NULL,                -- ONE atomic proposition, in the third person
  subject_id TEXT REFERENCES entity, ev_id TEXT REFERENCES event,
  asserted_by TEXT REFERENCES entity,
  modality TEXT NOT NULL CHECK (modality IN
    ('documentary_fact','testimony','party','press','inference')),
  verified INTEGER NOT NULL DEFAULT 0,
  confidence TEXT CHECK (confidence IN ('high','medium','low')),
  stated_at TEXT,
  status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','corroborated','contradicted','withdrawn')),
  created_by TEXT NOT NULL
);
CREATE TABLE event_citation (
  ev_id TEXT REFERENCES event, pid TEXT REFERENCES page,
  quote TEXT,                        -- literal; same rule as citation.quote
  role TEXT DEFAULT 'supports',
  PRIMARY KEY (ev_id, pid, quote)
);
CREATE TABLE citation (
  claim_id TEXT REFERENCES claim, pid TEXT REFERENCES page,
  quote TEXT,                        -- literal; validate.py looks for it in page.text
  role TEXT CHECK (role IN ('supports','contradicts','context')) DEFAULT 'supports',
  PRIMARY KEY (claim_id, pid, role, quote)  -- a claim can cite several quotes from the same page
);
CREATE TABLE claim_link (
  a TEXT REFERENCES claim, b TEXT REFERENCES claim,
  type TEXT CHECK (type IN ('contradicts','corroborates','derives_from','reiterates','qualifies')),
  note TEXT, created_by TEXT, PRIMARY KEY (a, b, type)
);

-- ===== statements =====
CREATE TABLE statement (
  stmt_id TEXT PRIMARY KEY,          -- d:bartoli-guillermo-2002-11-16-testimonial
  ent_id TEXT NOT NULL REFERENCES entity,
  date TEXT NOT NULL, venue TEXT, capacity TEXT,
  pid_start TEXT REFERENCES page, pid_end TEXT REFERENCES page,
  source_level TEXT,                 -- directa|citada_en_fallo|citada_en_prensa|blog
  created_by TEXT
);
CREATE TABLE statement_claim (stmt_id TEXT REFERENCES statement, claim_id TEXT REFERENCES claim,
  PRIMARY KEY (stmt_id, claim_id));
CREATE TABLE topic (topic_id TEXT PRIMARY KEY, description TEXT);
CREATE TABLE claim_topic (claim_id TEXT REFERENCES claim, topic_id TEXT REFERENCES topic,
  PRIMARY KEY (claim_id, topic_id));

-- ===== evidence and chain of custody =====
CREATE TABLE evidence_item (
  item_id TEXT PRIMARY KEY, type TEXT, description TEXT NOT NULL,
  object_ent TEXT REFERENCES entity, created_by TEXT
);
CREATE TABLE custody (
  item_id TEXT REFERENCES evidence_item, seq INTEGER, t TEXT, action TEXT,
  from_ent TEXT REFERENCES entity, to_ent TEXT REFERENCES entity,
  place_id TEXT REFERENCES entity, source_pid TEXT REFERENCES page, created_by TEXT,
  PRIMARY KEY (item_id, seq)
);
CREATE TABLE expert_report (
  report_id TEXT PRIMARY KEY, item_id TEXT REFERENCES evidence_item,
  expert_id TEXT REFERENCES entity, t TEXT, method TEXT,
  literal_conclusion TEXT, source_pid TEXT REFERENCES page,
  limitations TEXT,                  -- what the report can NOT assert
  modern_reexamination TEXT,         -- which current technique could reexamine it and with what material
  created_by TEXT
);

-- ===== hypotheses (ACH) =====
CREATE TABLE hypothesis (h_id TEXT PRIMARY KEY, statement TEXT, status TEXT, created_by TEXT);
CREATE TABLE ach (
  claim_id TEXT REFERENCES claim, h_id TEXT REFERENCES hypothesis,
  value TEXT CHECK (value IN ('consistent','inconsistent','neutral','very_inconsistent')),
  weight TEXT CHECK (weight IN ('high','medium','low')), note TEXT, created_by TEXT,
  PRIMARY KEY (claim_id, h_id)
);

-- ===== traceability =====
CREATE TABLE activity (act_id TEXT PRIMARY KEY, agent TEXT, model TEXT, t TEXT, task_id TEXT, description TEXT);
CREATE TABLE link (source TEXT, target TEXT);       -- [[...]] extracted from analysis/**/*.md
CREATE VIEW backlinks AS SELECT target, source AS referenced_by FROM link;
CREATE TABLE load_error (file TEXT, line INTEGER, error TEXT);   -- validate.py fails if it is not empty

-- ===== views =====
CREATE VIEW v_folio AS               -- page -> detected folio mapping (case file)
  SELECT doc_id, n AS page, folio, pid FROM page WHERE folio IS NOT NULL;

CREATE VIEW v_timeline AS
  SELECT e.ev_id, e.t_start, e.t_end, e.precision, e.t_start_min, e.t_start_max, e.type, e.anchor_type,
         e.description, e.status,
         (SELECT group_concat(ent_id || ':' || coalesce(role, ''), ' ') FROM event_participant p WHERE p.ev_id = e.ev_id) AS participants,
         (SELECT group_concat(c.pid, ' ') FROM claim a JOIN citation c USING (claim_id) WHERE a.ev_id = e.ev_id) AS citations
  FROM event e ORDER BY e.t_start;

CREATE VIEW v_statements_by_person AS
  SELECT d.ent_id, d.date, d.venue, d.capacity, d.source_level, a.claim_id, a.text, a.modality,
         (SELECT group_concat(topic_id, ' ') FROM claim_topic t WHERE t.claim_id = a.claim_id) AS topics
  FROM statement d JOIN statement_claim da USING (stmt_id) JOIN claim a USING (claim_id)
  ORDER BY d.ent_id, d.date;

CREATE VIEW v_contradictions AS      -- classified + candidates (same person, same topic)
  SELECT a1.asserted_by, t1.topic_id, a1.claim_id AS a, a2.claim_id AS b, a1.text AS text_a, a2.text AS text_b,
         a1.stated_at AS date_a, a2.stated_at AS date_b,
         (SELECT group_concat(type, ' ') FROM claim_link v
           WHERE (v.a = a1.claim_id AND v.b = a2.claim_id) OR (v.a = a2.claim_id AND v.b = a1.claim_id)) AS link,
         EXISTS (SELECT 1 FROM claim_link v
           WHERE (v.a = a1.claim_id AND v.b = a2.claim_id) OR (v.a = a2.claim_id AND v.b = a1.claim_id)) AS classified
  FROM claim a1 JOIN claim_topic t1 ON t1.claim_id = a1.claim_id
  JOIN claim_topic t2 ON t2.topic_id = t1.topic_id AND t2.claim_id > a1.claim_id
  JOIN claim a2 ON a2.claim_id = t2.claim_id AND a2.asserted_by = a1.asserted_by AND a2.text <> a1.text;

CREATE VIEW v_uncited AS
  SELECT claim_id, text, created_by FROM claim a WHERE NOT EXISTS (SELECT 1 FROM citation c WHERE c.claim_id = a.claim_id);

CREATE VIEW v_ambiguous_aliases AS
  SELECT alias_norm, group_concat(ent_id, ' ') AS entities FROM alias
  WHERE coalesce(type, '') <> 'possible_homonym' GROUP BY alias_norm HAVING count(DISTINCT ent_id) > 1;

CREATE VIEW v_coverage AS
  SELECT d.doc_id, d.type, d.n_pages, d.n_text_pages, d.text_status,
         (SELECT count(*) FROM page p WHERE p.doc_id = d.doc_id AND length(trim(p.text)) < 40) AS near_empty_pages,
         (SELECT count(*) FROM page p WHERE p.doc_id = d.doc_id AND p.folio IS NOT NULL) AS pages_with_folio,
         (SELECT count(DISTINCT m.pid) FROM mention m JOIN page p ON p.pid = m.pid WHERE p.doc_id = d.doc_id) AS pages_with_mention,
         (SELECT count(*) FROM page p WHERE p.doc_id = d.doc_id AND NOT EXISTS
            (SELECT 1 FROM extraction x WHERE x.doc_id = d.doc_id AND p.n BETWEEN x.page_start AND x.page_end)) AS pages_without_extraction
  FROM document d;

CREATE VIEW v_custody_gaps AS
  SELECT c.item_id, c.seq, c.action, c.t, c.to_ent,
         CASE WHEN c.t IS NULL THEN 'no_date' WHEN c.to_ent IS NULL AND c.action = 'delivered' THEN 'no_recipient'
              WHEN NOT EXISTS (SELECT 1 FROM custody c2 WHERE c2.item_id = c.item_id AND c2.seq = c.seq - 1) AND c.seq > 1
              THEN 'sequence_gap' END AS gap
  FROM custody c
  WHERE c.t IS NULL OR (c.to_ent IS NULL AND c.action = 'delivered')
     OR (c.seq > 1 AND NOT EXISTS (SELECT 1 FROM custody c2 WHERE c2.item_id = c.item_id AND c2.seq = c.seq - 1));
