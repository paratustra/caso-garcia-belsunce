# Caso García Belsunce: el material completo, listo para revisar

María Marta García Belsunce murió el 27 de octubre de 2002 en su casa del Country Carmel, en Pilar. Más de veinte años después, la causa acumula varios juicios y fallos que revocaron condenas y absoluciones anteriores. El material está disperso en PDFs escaneados, blogs, notas de diarios y horas de televisión.

Este repositorio junta ese material en texto plano, página por página, con un identificador fijo para cada página. Sirve para que una persona o un agente de IA lo recorra entero, encuentre lo que se pasó por alto y lo cite con la página y la frase exactas.

## Qué hay

| Material | Documentos | Páginas o secciones |
|---|---:|---:|
| Expediente judicial (OCR de los 37 cuerpos y de 287 piezas sueltas) | 331 | 13.825 |
| Fallos, de la instrucción a la Corte Suprema | 33 | 2.056 |
| Transcripciones de video (noticieros, entrevistas, juicios) | 476 | 1.720 |
| Blog casobelsunce (escrito por la defensa de Carrascosa) | 1.033 | 1.641 |
| Prensa y testimonios publicados | 230 | 744 |
| Compilaciones de evidencia y bibliografía forense | 60 | 153 |
| Wikipedia, documentos oficiales y Archive.org | 40 | 86 |

En total son 20.225 páginas y unos 38 millones de caracteres. Las 1.739 páginas del expediente con la foja ("fs.") detectada la tienen anotada aparte del número de página del PDF.

## Tres formas de leerlo

**1. Directamente, sin instalar nada.** Todo está en Markdown dentro de `sources/`. Cada página del expediente empieza con `## Página N`:

```bash
grep -rn "pozo ciego" sources/case-file/
```

**2. Con la base de búsqueda.** Requiere Python 3.12 o superior y nada más. La compilación tarda unos 10 segundos:

```bash
python3 tools/build.py                        # arma db/case.sqlite
python3 tools/search.py "pozo ciego"          # sin acentos ni mayúsculas; devuelve citas listas para pegar
python3 tools/search.py CAZAFUS --variants    # tolera errores de OCR: encuentra Casafus, Cazafus, Casfus...
python3 tools/cite.py 'exp-c04#p5' "pozo ciego"   # comprueba que la frase está en esa página
python3 tools/ui.py                           # navegador local en http://127.0.0.1:8766
```

La base es SQLite con búsqueda de texto completo, así que también se puede consultar con SQL. El esquema comentado está en `db/schema.sql`.

**3. Con un agente de IA.** `AGENTS.md` tiene las reglas de trabajo: cómo citar, qué modalidad asignar a cada afirmación y cómo validar. Un encargo típico:

> Clona este repositorio, corre `python3 tools/build.py` y lee `AGENTS.md`. Busca en el expediente todas las horas que se declararon para la llegada de la ambulancia y arma una tabla con quién dijo cada una, cuándo y con qué cita. Marca las que no coinciden.

## Cómo se cita

Cada página tiene un identificador permanente: `exp-c05#p100` es la página 100 del PDF del cuerpo 5, `fallo-...#p3` es una página de un fallo y `vid-<id>#s4` es el tramo de 5 minutos que empieza en el minuto 15 de un video. Una cita completa lleva la frase literal:

```
[[exp-c04#p5|"pozo ciego"]]
```

`python3 tools/validate.py` rechaza toda cita cuya frase no esté en esa página. Recompilar no cambia los identificadores, así que una cita escrita hoy sigue siendo válida mañana.

## Por dónde conviene empezar

La prioridad son las pericias técnicas y los datos crudos, porque ahí la ciencia forense cambió más desde 2002: autopsia, balística, ADN, telefonía y antenas, acústica, y los registros de alarma y de guardia del country.

- `sources/evidence/EVIDENCIA.md`: qué pericias se hicieron, sobre qué material y con qué resultado, con citas.
- `sources/science/APLICABILIDAD.md`: qué técnicas actuales podrían reexaminar cada evidencia y qué haría falta para aplicarlas.
- `sources/case-file/INDICE-por-cuerpos.md`: índice de las 1.110 piezas del expediente, con la página de cada una.

## Límites del material

- **OCR:** el texto del expediente salió de escaneos y tiene errores. Ante una cita dudosa, revisa la imagen original. El `source.json` de cada cuerpo enlaza a SlideShare.
- **Fojas:** se detectaron automáticamente y conviene verificarlas en la imagen antes de citarlas.
- **Fuentes de parte:** el blog casobelsunce y el sitio de Fernando Díaz Cantón son material de la defensa de Carlos Carrascosa. Son útiles, pero tienen una postura.
- **Transcripciones:** son automáticas y los hablantes figuran como `speaker_N`, sin identificar.
- **Lo que no se incluye:** PDFs, imágenes y audio, por peso y por derechos (cada fuente enlaza a su original). Tampoco se incluyen dos documentos de Scribd ni el análisis propio del autor.

## Estructura

```
sources/              material original, solo lectura; cada carpeta tiene un README con su origen
tools/                compilación, búsqueda, citas, validación e interfaz web (solo biblioteca estándar)
db/schema.sql         esquema de la base: documentos, páginas, piezas, entidades, eventos, afirmaciones
analysis/             lugar para el análisis propio, en JSONL (formato en analysis/README.md)
scripts/acquisition/  scripts con los que se bajó, se pasó por OCR y se transcribió el material
```

El diseño completo está en `METODOLOGIA.md`, y las decisiones tomadas al implementarlo, en `DECISIONES.md`.

## Contribuir

Los hallazgos, las correcciones de OCR y las fuentes nuevas son bienvenidos como issue o pull request. Un hallazgo tiene que traer sus citas en el formato de arriba y pasar `python3 tools/validate.py`. El repositorio registra contradicciones y cambios de versión con su cita, pero no concluye culpabilidades.

## Derechos y datos personales

El código está bajo licencia [MIT](LICENSE). El material de `sources/` pertenece a sus autores (tribunales, medios, el blog casobelsunce, canales de video) y se reproduce con fines de investigación.

El expediente contiene datos personales de personas que siguen vivas. Si eres una de ellas, o titular de algún material, y quieres que se quite algo, abre un issue y se quita.
