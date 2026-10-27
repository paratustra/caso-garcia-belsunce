# analysis/ (capa 2, fuente de verdad de lo interpretado)

- `extraction/<doc_id>.jsonl`: salida de las tareas EXT (esquema en AGENTS.md sección 8). Un archivo por cuerpo, un dueño.
- Resto de `*.jsonl`: una fila por línea con `"_table"` + columnas de `db/schema.sql` + `created_by`.
- `findings/H-<aaaammdd>-<n>.md`: un hallazgo por archivo, con citas `[[pid|"frase"]]`.
`build.py` carga todo esto en la base; `validate.py` debe dar 0 errores antes de dar algo por terminado.
