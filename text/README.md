# text/ (capa 1, regenerable)

Lo genera `tools/ingest.py` (lo llama `build.py`). No edites nada aquí: se sobrescribe.
- `manifest.tsv`: un documento por fila (doc_id, type, source_level, rutas, sha256, n_pages, text_status, anchor, signature).
- `pages/<doc_id>.jsonl`: `{"pid","doc_id","n","folio","ocr_conf","source_file","line","text"}` por página (`#p`) o sección (`#s`).
- `filings.tsv`: `INDICE-por-cuerpos.tsv` con doc_id/pid resueltos y `filing_type` por palabras clave.
`folio` es una detección heurística; `ocr_conf` está vacío porque el OCR no trajo puntajes.
