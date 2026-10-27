# APLICABILIDAD: qué técnicas modernas podrían reexaminar la evidencia del caso

Elaborado el 2026-10-27. Referencias con clave Rnn: ver `README.md`. Hechos del caso: `sources/evidence/EVIDENCIA.md` y los hallazgos H-20261027-301 a 312 y 401 a 411 en `analysis/findings/`, que aquí se toman tal como los transmitió la sesión coordinadora (no se releyeron los originales).

## 0. Cómo leer este documento

Cada afirmación lleva una de tres etiquetas:

- **[ESTABLECIDO]**: respaldado por una revisión, un estudio de validación o una guía citada.
- **[PLAUSIBLE]**: se deduce de lo establecido, pero no hay un estudio que cubra este tipo exacto de muestra o escenario.
- **[ESPECULACIÓN]**: hipótesis de trabajo; no debe usarse como conclusión.

Límites de esta recopilación: no vi los informes periciales originales; no sé qué muestras físicas existen hoy; no encontré datos publicados sobre ADN de raspados ungueales de 20 años en frasco ni sobre éxito de recuperación en manchas de 20 años como tasa general. Donde falta ese dato lo digo.

## 1. Avances recientes, ordenados por impacto potencial en este caso

El orden pondera tres cosas: cuánta información nueva puede dar, cuán barato y rápido es, y cuántas precondiciones faltan.

| # | Avance | Por qué importa aquí | Precondición principal |
|---|---|---|---|
| 1 | Genotipado probabilístico (STRmix, EuroForMix, MaSTR, DNAStatistX) maduro y validado, 2016-2025 [R12, R15, R16, R17, R20] | Permite cuantificar con razón de verosimilitud (LR) mezclas y perfiles parciales que en 2003-2007 se informaron como "no concluyentes", "excluye" o "compatible". Se aplica a datos ya existentes. | Archivos crudos (.fsa/.hid) de los discos zip, o al menos tablas de picos con alturas |
| 2 | Búsqueda de haplotipos Y en YHRD y estadística de coincidencia con theta (SWGDAM) [R25, R26] | El perfil masculino de la palma (~12 Y-STR) solo se usó para excluir. Falta ponerlo en una base poblacional y calcular su rareza. | Reportar el haplotipo exacto (alelos por locus) y qué kit se usó |
| 3 | Secuenciación masiva y WGS de cabello sin raíz, incluso antiguo [R02, R03, R04] | Los "73 pelos" quedaron sin ADN mitocondrial. Hoy se obtiene ADN nuclear fragmentado de tallos sin raíz, con SNP aptos para identidad y parentesco. | Que los pelos existan, con cadena de custodia, y que se acepte consumirlos |
| 4 | Genealogía genética forense (FIGG/IGG) con paneles de miles de SNP o WGS [R35-R41] | Es la única vía técnica para pasar de "un varón desconocido" a candidatos si no hay coincidencia en bases de STR. | Un extracto o muestra con ADN suficiente para SNP densos; marco legal (ver sección 6) |
| 5 | Comparación objetiva 3D de estrías (topografía, CMC, bulletr, CMPS) y bases de características generales de estriado [R51-R57] | Permite reevaluar con medidas la afirmación de "misma arma" de 2003 y acotar los 69 modelos. | Acceso a los proyectiles originales; viabilidad con plomo deformado es incierta |
| 6 | Marco de proposiciones a nivel de actividad para ADN de transferencia [R30-R34, R31] | Es el criterio actual para evaluar si un ADN en una viga o bajo un cuadro es del autor o llegó por transferencia secundaria o contaminación. | Datos del caso sobre quién tocó qué y cuándo |
| 7 | Evaluación estadística de huellas con modelos de LR y evaluaciones NIST de AFIS con rasgos extendidos [R67, R66, R64, R65] | Las huellas de 2008 nunca se buscaron en bases después de esa fecha. | Imágenes originales en buena resolución; bases con huellas palmares |
| 8 | Barrido de elementos y química orgánica de residuos (SEM-EDS, ICP) y espectroscopía para recubrimientos [R58, R59, R62] | El estroncio y el PTFE son pistas químicas concretas sin interpretar. | Los portamuestras de carbono (stubs) y los proyectiles en buen estado |

Como prueba breve de que las técnicas 3 y 4 funcionan con material viejo (método y resultado, no repaso de casos):

- Cabello de más de 100 años de reliquias Romanov: se recuperó el genoma mitocondrial y SNP autosómicos con secuenciación Illumina de tallos sin raíz [R03]. En cabello de unos 50 años, el ADN nuclear fue el 88% o más de las lecturas humanas [R02].
- Un homicidio de hace un siglo, con restos momificados hallados en 1979 y 1991, se identificó en 2019 con FGG [R47].
- Cabello sin raíz con 1,4 millones de SNP subidos a GEDmatch condujo a una identificación en 2020 (resumen AAFS, solo vi el resumen en buscador; no verificado en el original).
- Aviso: el estudio de Kapp 2026 [R04] usó cabellos de 50 voluntarios actuales, no envejecidos; no demuestra rendimiento a 20 años. Varios autores trabajan para la empresa que comercializa el método.

## 2. Evidencia biológica, ítem por ítem

### 2.1 Perfil masculino de la palma, la viga junto a la bañera y bajo el cuadro (2003-2007)

Hechos transmitidos: unos 13-15 STR autosómicos y unos 12 Y-STR, informado como una sola fuente, usado solo para descartar sospechosos uno a uno, nunca buscado en bases.

**Corrección de la revisión del caso (H-20261027-001-revision):** el vínculo "mismo varón en la palma, la viga y la antesala" es más débil de lo informado al principio. En FGA la viga (Sobre 2) muestra 21 frente a 23-24 en la palma; en D13S317, 11 frente a 8-11. Unirlos exige suponer pérdida de alelos (dropout), y los Y-STR compartidos son muy comunes. Debe leerse como "compatible, no demostrado". Otra muestra (S2-IV-B) corresponde a un varón distinto. En el perfil de la palma, D21S11 es 29 (no 29-30) y DYS385 figura como "13?" en una página (exp-c33#p94) y como 14 en otra (exp-c33#p130). Este documento no asume que haya un único varón en los tres lugares.

**a) Qué agrega YHRD [ESTABLECIDO]**
- YHRD es la base de referencia mundial de haplotipos Y. En noviembre de 2018 contenía 265.324 haplotipos mínimos de 9 loci, 205.059 de Yfiler y 42.506 de Yfiler Plus [R25]. Un haplotipo de 12 loci es consultable al menos en su subconjunto de 9 loci mínimos.
- SWGDAM acepta contar frecuencias en la base y corregir con theta para obtener una probabilidad condicional de coincidencia; YHRD está admitido para poblaciones distintas de la estadounidense [R25]. Con cero coincidencias en n haplotipos, el límite superior al 95% ronda 3/n (material docente de Univ. Washington, citado en búsqueda; confirmar con la guía SWGDAM antes de usar).
- Valor probatorio: el haplotipo Y no individualiza. Lo comparten todos los parientes patrilineales. Sirve para excluir (si un acusado no coincide, queda fuera como fuente) y para decir qué tan rara es una coincidencia en una población. Si ningún acusado coincide, la búsqueda aporta poco más que la exclusión ya hecha.
- Discrepancia en DYS385: la búsqueda debe usar el haplotipo de exp-c33#p130 (DYS385 = 14, según la sesión del caso) y declarar que otra página lo lee "13?". DYS385 es un locus multicopia (dos alelos) y por lo general se informa como par; un valor único o dudoso hace que la consulta no sea comparable con haplotipos completos. No verifiqué cómo trata YHRD un locus incierto; hay que consultarlo en su manual. Hasta entonces, conviene buscar con el haplotipo mínimo sin ese locus y con el valor dudoso por separado, y reportar ambas versiones. Si la discrepancia no se resuelve contra el electroferograma crudo, la estimación de rareza hereda esa incertidumbre.
- Los Y-STR compartidos entre la viga y la palma son muy comunes en la población, de modo que su coincidencia no basta para unir ambas muestras.
- La cobertura de YHRD para Argentina: no pude verificar cuántos haplotipos argentinos contiene ni su representatividad. Es una verificación pendiente que condiciona cualquier estimación de rareza.
- En un perfil único de Y-STR, la rareza real depende de la subpoblación. Las estimaciones de bases de países distantes pueden ser engañosas [PLAUSIBLE].

**b) Y-STR para genealogía [PLAUSIBLE / ESPECULACIÓN]**
- Se demostró que Y-STR más bases genealógicas públicas permitían inferir apellidos de varones anónimos [R29, 2013]. Hoy las bases de Y-STR genealógicas son menos comprehensivas que las de SNP autosómicos y están sesgadas hacia EE. UU. y Europa. Para un apellido hispano el método existe en teoría, pero no encontré un estudio de rendimiento en Argentina. Tratar como [ESPECULACIÓN] hasta tener datos.

**c) Reinterpretación con genotipado probabilístico**
- Si el perfil de la palma fue una sola fuente, el genotipado probabilístico agrega poco para el STR autosómico. Agrega si hay componentes menores ocultos o picos bajo el umbral analítico de 2003-2007 [PLAUSIBLE].
- Qué cuenta realmente: a nivel de actividad, ¿cómo llegó ese ADN a tres lugares distintos? El marco de la comisión ISFG [R31] y los estudios de transferencia [R30, R32, R33] dicen que un perfil masculino sin identificar no basta sin datos de prevalencia de fondo (ADN de personas de la casa, visitas, sanitarios, policías).
- Esto lleva a la pieza que falta: ninguna muestra de eliminación (ver 2.8).

**d) Viabilidad de reanalizar los discos zip**
- El archivo .fsa/.hid (datos crudos del analizador genético) es lo ideal: permite aplicar umbral analítico, modelo de stutter y degradación de la época. Con solo impresiones o tablas de picos se pierde el ruido de fondo; EuroForMix y STRmix aceptan tablas de picos, pero la validez baja y no hay estudios que cuantifiquen esa pérdida en un reanálisis retrospectivo [PLAUSIBLE].
- Los kits de 2003-2007 (típicamente Identifiler, PowerPlex 16, PowerPlex Y o Yfiler) están soportados por los programas en general; verificar kit por kit en la validación del laboratorio que lo haga. Para mezclas de Y-STR las herramientas de LR están menos maduras que para STR autosómico [PLAUSIBLE]; confirmar con el desarrollador.
- Dos estudios de reanálisis de casos reales con EuroForMix contra métodos previos (hoja de cálculo, LRmix Studio) dieron LR comparables o mejores [R15, R16]. Son validaciones modestas, de laboratorios brasileños, no estudios sobre datos de 20 años.
- Los medios (discos zip) son un riesgo físico. [ESTABLECIDO por sentido común, sin cita]: copiar y hashear los archivos antes de cualquier otra acción.
- Riesgo de dependencia: un LR cambia con las proposiciones, el número de contribuyentes y el modelo. La NIST advierte sobre la variabilidad entre métodos [R20], y PCAST pide validar la aplicación al caso concreto [R22]. Hay que reportar sensibilidad, no un solo número.

### 2.2 Mezcla de dos varones en el hisopado de la viga junto a la bañera; dos sobres nunca abiertos (alféizar, azulejos)

- El hisopado de la viga (Sobre 2) ya se informó como mezcla de dos varones; otra muestra (S2-IV-B) es de un varón distinto. Con ADN autosómico y software continuo, un LR para cada candidato frente a "desconocido" es el estándar [R12]. Este es un buen caso de uso: la pregunta "¿es el mismo varón de la palma, con pérdida de alelos en la viga (FGA 21 frente a 23-24, D13S317 11 frente a 8-11), o es otro?" es exactamente la que el genotipado probabilístico modela, con dropout y dropin explícitos [R12, R21]. Se calcula un LR con las proposiciones "el contribuyente es el perfil de la palma" frente a "es un varón desconocido no emparentado", y variantes con un pariente. Cuidado: los modelos de dropout dependen de la calidad de los datos crudos y, con picos bajos, el LR puede ser cercano a 1 o inestable; informar la sensibilidad. Si el 2003-2007 usó CPI/RMNE, el resultado puede cambiar al pasar a LR [R19, R21].
- Los sobres sin abrir son la mejor oportunidad de tener material nuevo no consumido ni contaminado por el manejo posterior [PLAUSIBLE]. Un hisopado de 2002 conservado en seco puede dar perfil; no encontré una tasa publicada para hisopos de 20 años. Hay que tratarlo como incierto.
- Precondiciones: confirmar que los sobres existen, su estado, quién los custodió, y reservar parte de la muestra para contraperitaje. Extracción optimizada para ADN degradado [R01], kits de STR de amplicones cortos y, si falla, secuenciación masiva [R08, R11].
- Riesgo: contaminación por manejo a lo largo de 20 años. Los controles negativos y las muestras de eliminación son parte del diseño, no un adorno.

### 2.3 Mancha de sangre en un recorte de alfombra de la antesala (perfil masculino nuevo, 2018)

- No tengo el informe. Si el perfil es de buena calidad, el análisis es el mismo de 2.1: búsqueda en YHRD si hay Y-STR; LR frente a las hipótesis. Una sangre masculina sobre alfombra puede ser del propio agresor herido o de personal que ingresó después [ESPECULACIÓN]; solo las muestras de eliminación y la cronología pueden decidir.
- Conseguir el informe 2018 es prerrequisito de todo lo demás.

### 2.4 Raspados ungueales (recogidos, nunca analizados; frasco conservado desde dic. 2003)

- Ese es el tipo de muestra donde un perfil masculino podría ser más probatorio: contacto físico agresor-víctima. Un estudio actual con parejas voluntarias encontró que los hisopos de punta fina recuperan mejor el perfil masculino que el recorte de uñas [R06]. Eso es para recolección fresca y no se puede aplicar a un frasco ya almacenado.
- Si el contenido del frasco es material ungueal con descomposición avanzada: no encontré datos sobre éxito de tipificación en raspados de 20 años [laguna]. El ADN de la víctima va a dominar. Para el componente masculino son relevantes los Y-STR (fondo femenino) y la secuenciación masiva. Un resumen de validación de laboratorio (no revisado por pares) informó haplotipos Y completos hasta proporciones hombre:mujer de 1:1000 y recomendó cautela por debajo de 1:1000 (ASCLD, validación Yfiler Plus, vista en búsqueda; no descargada). Con ADN degradado y mucho fondo femenino ese límite probablemente se aplica peor [PLAUSIBLE].
- Si hay nuclear insuficiente, el ADN mitocondrial de uña/cabello es posible: se logró secuenciar el mitogenoma completo con unas 2.000 copias [R05]. Pero el ADN mitocondrial no individualiza; solo excluye linajes maternos.
- Precondiciones: que el frasco siga en custodia, intacto, con documentación de cuándo y quién lo cerró. Sin eso, cualquier resultado será impugnable por contaminación.

### 2.5 Cabellos ("73 pelos") sin ADN mitocondrial

- La mayoría de los cabellos caídos no tiene raíz. El ADN nuclear está presente, pero fragmentado en piezas muy cortas, por lo que el STR clásico falla y la secuenciación masiva de fragmentos cortos sí lo capta [R02, R03, R04]. Un método STR modificado para tallos sin raíz fue publicado [R07].
- El ADN mitocondrial de cabello varía incluso entre cabellos de la misma persona (heteroplasmia) [R05, R09]; hay que interpretarlo con prudencia.
- Rendimiento realista: con 20 años de almacenamiento, el mitogenoma probablemente sea recuperable; SNP autosómicos con cobertura baja pueden servir para decidir "es/no es" frente a un candidato y para un panel de parentesco [R03, R04, R36]. No hay estudio con cabello de 20 años de cadena de custodia de un escenario criminal. [PLAUSIBLE]
- El cabello se consume. Hay que decidir cuáles, qué se guarda para contraperitaje y documentar el orden.
- Selección previa: examen microscópico para descartar cabello de la víctima y de personas de la casa antes de gastar muestra. Es una decisión de perito.

### 2.6 Manchas de sangre, luminol 2002 no fotografiado, BPA

- Las fotografías de 2002 sin escala ni ángulo de cámara limitan la reconstrucción. Con modelos de dinámica de fluidos se mejoró unas cuatro veces la estimación del origen frente a la aproximación de línea recta, pero en patrones creados en laboratorio, con volumen y velocidad medidos por escáner 3D [R49]. Eso no se puede replicar desde fotos antiguas [ESPECULACIÓN].
- Fiabilidad del campo: la NRC 2009 afirmó que "las incertidumbres asociadas con el análisis de patrones de manchas de sangre son enormes" (p. 179) [R23]. Un estudio ciego con 75 analistas halló 11,2% de respuestas erróneas en patrones de causa conocida y 7,8% de respuestas contradichas por otros analistas [R48; resumen NIJ en `web/`]. PCAST 2016 no evaluó este campo; solo lo menciona entre los que necesitan una base estadística mejor [R22].
- Hay una línea de trabajo estadístico (LR para BPA) todavía en etapa de investigación [R50].
- Conclusión práctica: el BPA sobre fotos viejas sirve, como mucho, para hipótesis; no para afirmar una secuencia de hechos. El mayor valor está en las manchas con ADN, no en la forma.
- Pendiente: la mancha detrás del cuadro y el recorte de alfombra son fuentes de ADN, y eso es lo reexaminable.

### 2.7 Transferencia, contaminación y manejo en la escena

- Los estudios actuales muestran que el ADN puede transferirse por contacto indirecto y que quien deposita ADN no es siempre quien lo "tocó" [R30, R33]. La evaluación correcta usa proposiciones de actividad [R31] y redes bayesianas [R32].
- En un escenario donde médicos, familiares y policías entraron antes de preservar la escena (según la información del caso), la contaminación de la escena es una explicación a evaluar para cada perfil masculino. Repito: sin muestras de eliminación no se puede cerrar [PLAUSIBLE].

### 2.8 Muestras de eliminación

- Ni ADN ni huellas de médicos, paramédicos, policías, fiscal. Es la omisión más fácil de reparar en principio y la más difícil en la práctica (20 años; algunos habrán fallecido).
- Práctica actual: bases de eliminación de personal que interviene en la escena. La Ley 27.759 prevé justamente descartar "huellas de todo personal que interviene directamente en la escena" y almacenar perfiles del personal policial y judicial [L1, art. 3 c) y art. 4 f)], aunque aplica de aquí en adelante y a la fuerza federal.
- Para el caso: la solicitud de muestras voluntarias a quienes intervinieron en 2002, con consentimiento y orden judicial si hace falta. Los perfiles de personal que no coincidan descartan fuentes; los que coincidan cambian la interpretación de lo anterior.

## 3. Huellas y palma

- Hechos: 3 huellas y 1 fragmento de palma aptas (pericia 771/2008); sin búsqueda AFIS posterior a 2008.
- Valor y límites [ESTABLECIDO]: la comparación de huellas latentes es considerada fundacionalmente válida por PCAST, con tasa de falsos positivos "sustancial", hasta 1 error en 306 casos según el estudio del FBI y 1 en 18 según otro laboratorio [R22]. Los examinadores repitieron el 89% de sus decisiones de individualización a los 7 meses [R65]. La variabilidad se concentra en si la información es suficiente.
- Búsqueda automatizada: NIST midió que el uso de rasgos extendidos marcados por el examinador sube la precisión en rango 1 de 66,7% a 71,4% entre dos evaluaciones, con una galería grande (dato obtenido de resúmenes en búsqueda; el tamaño de galería no quedó claro, confirmar en NISTIR 7775/7859 [R67]). Las latentes de calidad media se recuperan mejor hoy que en 2008, pero el límite lo pone la imagen original y la base consultada [PLAUSIBLE].
- Obstáculo central: las palmas rara vez están en bases AFIS; casi todo son decadactilares. Una huella palmar sin base palmar tiene poco que buscar [PLAUSIBLE]. La búsqueda en una base nacional de huellas digitales y de documentos de identidad requiere definir qué bases accesibles hay en Argentina y bajo qué orden; no lo verifiqué.
- Hay que mantener la separación entre las huellas y el perfil de ADN de la palma: la huella sirve para decir de quién, el ADN de la palma para qué fuente biológica contactó la zona; no son equivalentes.
- Recomendación de método: análisis documentado de la latente antes de ver cualquier exemplar [R22] y comparación contra eliminación (2.8).

## 4. Armas y proyectiles

Datos del caso: 5 proyectiles de plomo .32 del cráneo más 1 del tanque séptico; estriado levógiro leve, 6 campos/estrías, ancho de campo 2,4 mm, 69 modelos posibles (Gendarmería 2007); la conclusión "misma arma" proviene de una pericia de 2003 sin mediciones; Gendarmería dijo que el estado impedía determinar marca y modelo.

### 4.1 Acotar los 69 modelos con el archivo de características generales de estriado (GRC)

- [ESTABLECIDO] El archivo GRC del FBI reúne datos documentados de estriado de armas conocidas para comparar cuando no hay arma. Se entra con calibre, número de campos y estrías, dirección de torsión y anchos de impresión de campo y estría. Devuelve una lista de armas posibles, no una identificación; el examinador refina los parámetros con criterio [R51].
- Con el proyectil deformado, el número de campos puede reconstruirse a partir de calibre y anchos medibles, y se necesita al menos un campo y una estría medibles [R51].
- Lo que hay: la lista de 69 modelos ya salió de ese tipo de búsqueda. Lo nuevo sería: (i) repetir con mediciones independientes de los seis proyectiles y reportar incertidumbre; (ii) cruzar la lista con lo que circulaba en Argentina en la época (armas legalmente registradas en RENAR y su base histórica), que no pude verificar; (iii) tomar nota de que el GRC es de armas comercializadas sobre todo en EE. UU.; las armas europeas y antiguas pueden estar incompletas [PLAUSIBLE].
- Conocimiento general no verificado en esta sesión: hay fabricantes históricos de revólveres con torsión a izquierda, por ejemplo Colt. Si el perito lo confirma, eso reduce la lista; no usar como dato hasta confirmarlo.

### 4.2 Topografía 3D y comparación virtual para sostener o refutar "misma arma"

- [ESTABLECIDO] Existen algoritmos abiertos y validados en datos de laboratorio para comparar estrías de balas: correlación cruzada de perfiles, `bulletr` (aprendizaje con características de estrías sobre el conjunto Hamby), CMPS/CMC del NIST [R52, R53, R54, R55]. Son útiles como apoyo objetivo (puntajes que se pueden convertir en LR [R57]).
- [ESTABLECIDO] Los estudios de campo con examinadores muestran errores bajos, pero con más de una quinta parte de decisiones "inconclusas"; estas se asocian con fuentes distintas [R56]. PCAST juzgó en 2016 que la disciplina "no alcanzaba" los criterios de validez fundacional: solo había un estudio bien diseñado, con tasa de falsos positivos estimada en 1 de 66 (cota hasta 1 de 46) [R22]. Se publicaron estudios posteriores, entre ellos [R56].
- [PLAUSIBLE → ESPECULACIÓN] Los algoritmos se validaron sobre balas encamisadas poco dañadas. Proyectiles de plomo blando deformados tras atravesar hueso y alojarse en cráneo tienen estrías parciales, aplastadas. No encontré validación en ese estado. La pregunta útil es empírica: ¿hay superficie con estrías medibles? Si la hay, un escaneo 3D permitiría comparar los seis entre sí con una métrica explícita. Si no la hay, la conclusión de 2003 no puede sostenerse ni refutarse con ninguna técnica.
- Precondición: acceso a los proyectiles originales, escaneo sin dañarlos y registro de la cadena de custodia. Todo el análisis debe ser ciego respecto del resultado de 2003.

### 4.3 Estroncio alto en los orificios y portamuestras de carbono que conserva Gendarmería

- [ESTABLECIDO] SEM-EDS de partículas de residuo con norma ASTM E1588 distingue tipos de munición por la composición del fulminante [R58, R59]; estudios recientes muestran diferencias entre marcas y municiones "no tóxicas" y también las limitaciones de la clasificación vigente.
- El estroncio aparece en algunos fulminantes sin plomo/bario/antimonio, según resúmenes de congresos (AAFS 2013 A109, solo resumen, sin verificar) [R63]. Pero el estroncio es un elemento común en yesos, pinturas, cerámicas y materiales de construcción [conocimiento general, sin cita]. Sin muestras de control del mismo muro, un "estroncio alto" en un agujero no es una huella de munición [PLAUSIBLE].
- Los stubs: los de carbono bien guardados en seco conservan las partículas durante años, pero no encontré un estudio sobre estabilidad a 20 años [laguna]. Si Gendarmería los conserva, reanalizar con SEM-EDS automatizado (búsqueda de partículas características) es barato frente a otras opciones.
- ICP-MS o isótopos de plomo para "caracterizar la bala": hay literatura en resúmenes, no encontré validación revisada por pares aplicable. La comparación de composición del plomo de balas para vincular lotes fue desacreditada por el informe NRC 2004 (conocimiento general, no verificado aquí); tratar toda conclusión de ese tipo como [ESPECULACIÓN].

### 4.4 PTFE en 2 de los 5 proyectiles del cráneo

- Un póster (AAFS 2011) identificó PTFE como recubrimiento/lubricante de balas de cobre Barnes XLC con IR y Py-GC-MS, y halló que el recubrimiento persiste tras el disparo [R62; sin descargar, visto en buscador].
- Preguntas de trabajo: (1) ¿Las balas eran de plomo .32 con algún recubrimiento comercial, o se contaminaron con PTFE al manipularse o almacenarse (cinta, recipientes, pinzas, lubricantes de armas)? (2) ¿Por qué solo 2 de 5? Las dos explicaciones (recubrimiento de un lote específico frente a contaminación) predicen cosas distintas: un recubrimiento es una capa con distribución sobre la superficie y presente en la parte no deformada; la contaminación es irregular.
- Método: FTIR o Raman en microescala y/o mapeo de flúor por SEM-EDS, más Py-GC-MS si hay material. Control: blancos de los envases y herramientas usados en 2002-2003.
- Es una vía de interés porque puede apuntar a un tipo de munición, pero hoy no tengo evidencia de que sea concluyente. [ESPECULACIÓN]

### 4.5 Impacto en la chimenea del dormitorio (35,5 cm sobre el piso)

- Una muestra se envió a un laboratorio de química de La Plata, sin resultado en el expediente. Lo reexaminable es la muestra, si existe, o la documentación (fotos, medidas). Si fue un disparo, la trayectoria se podría reconstruir con la ubicación del impacto; sin la posición de la víctima, solo da una línea. [PLAUSIBLE]

## 5. Cuerpo, exhumación y tiempo de muerte

- Un reexamen tras exhumación aporta poco sobre el tiempo de muerte: la revisión sistemática de degradación de ADN como marcador del intervalo post mortem concluye que los resultados son mixtos y que faltan modelos validados en humanos [R10]. No hay método consolidado de tiempo de muerte a 5 semanas de exhumación.
- Balística de heridas: los trabajos de tiros de prueba con simulantes y TC muestran cómo cambia la morfología con la distancia y el tejido [R60, R61]. Para reconstruir distancia o trayectoria desde los datos de la autopsia de 2002 hacen falta fotografías, mediciones y radiografías originales; no hay TC de 2002. Lo reexaminable es la documentación, no el cuerpo [PLAUSIBLE].
- Precondición que no conozco: si los restos existen hoy.
- Histopatología de heridas de bala para edad de la herida: no encontré revisión reciente abierta para este escenario; quedó fuera.

## 6. Datos de telefonía (celdas Movicom 215 y 394)

- [ESTABLECIDO, nivel de práctica] Los registros de celdas muestran una zona general, no una posición; la cobertura se solapa y un teléfono no siempre usa la torre más cercana [R71]. La cobertura se estima con estudios de campo (drive tests), que se discuten porque la intensidad de señal varía con el tiempo [R71].
- No hay revisión revisada por pares recuperada en esta búsqueda; es una laguna.
- Utilidad para evaluar la evidencia que condenó a Pachelo: pedir los datos de ingeniería de red de 2002 (azimut, apertura, potencia, vecinas, sectorización) a la operadora sucesora, y analizar si los dos sectores distinguen las hipótesis en disputa. Si esos datos históricos no se conservan, no se puede reconstruir la cobertura de entonces [PLAUSIBLE].
- Un drive test de hoy no reproduce las condiciones de 2002; no usarlo como prueba directa.

## 7. Audio de la llamada a OSDE

- [ESTABLECIDO] El estándar actual para comparación de voz es el marco de LR y la validación con datos de condiciones similares [R24, R68, R69, R70]. Es una minoría que lo aplica, y los sistemas automáticos dependen de la calidad y de la coincidencia de idioma y canal [R68].
- Límite práctico: una llamada de emergencia breve, con ruido y con locutores emocionados, aporta poco para identificar voz. Sirve más una mejora del audio para transcribir y para eventos de fondo, ya hecha por Gendarmería (peritación 29183) [PLAUSIBLE]. Una nueva comparación de voz requeriría grabaciones de referencia de los hablantes en condiciones similares; no hay base para esperar un resultado fuerte.

## 8. Marco legal para la genealogía genética (precondición, una nota)

La Ley 27.759 (BO 14-10-2024) sustituyó el art. 1 de la Ley 26.879 y amplió el Registro Nacional de Datos Genéticos de delitos sexuales a la "investigación criminal"; prevé una sección de "autores de delitos no individualizados" donde puede ingresarse la evidencia biológica atribuible al autor (art. 7), pero también prohíbe el intercambio de información genética con bancos o registros genéticos privados (art. 8) y limita el uso del registro a lo previsto en la ley [L1]. Eso apunta a que la consulta de bases comerciales de genealogía (GEDmatch, FamilyTreeDNA y similares) no tiene amparo expreso en la norma; lo debe definir el fiscal o juez y un asesor jurídico antes de cualquier subida. Dado que el hecho ocurrió en la provincia de Buenos Aires, el ingreso al registro nacional requiere convenio provincial según la misma ley, y no verifiqué si existe. Lo que sí hay en el derecho comparado son guías técnicas y de política para programas de FIGG [R40, R41] y análisis de legitimidad de un método sin ley habilitante [R46]. No investigué jurisprudencia argentina ni casos nacionales, por instrucción.

## 9. Viabilidad de la genealogía con un perfil de ~15 STR más Y-STR

- [ESTABLECIDO] La FIGG funciona con cientos de miles de SNP (microarreglo o WGS) o paneles dirigidos de miles de SNP [R35, R36, R37, R38]. Un perfil STR de 13-15 loci no contiene esa información y no puede convertirse en SNP.
- Con solo STR, lo posible es la búsqueda familiar en bases de STR nacionales (que Argentina no tiene de forma comparable) o la búsqueda de haplotipo Y en YHRD y bases de Y-STR genealógicas, ya discutida en 2.1.
- Qué hace falta [ESTABLECIDO en lo técnico]:
  1. Un extracto de ADN del perfil masculino con suficiente cantidad: o la muestra original remanente, o los cabellos [R03, R04], o el sobre aún cerrado.
  2. Rendimiento: con ADN muy degradado el panel dirigido FORCE recuperó en promedio 44,4% de los SNP a 10x en huesos, y predijo parentesco de primer a quinto grado con LR por encima de 10.000 en 5 casos con referencias [R36]. Para parentesco lejano, bajar de unos 164.000 SNP perjudica a varios métodos y los errores de genotipado por encima de 1% también [R37].
  3. Referencias de parientes y base con parientes lejanos del varón desconocido: la probabilidad de hallar un pariente de tercer grado o más en una base comercial depende del tamaño de la base en el país; no tengo cifras para Argentina. [ESPECULACIÓN]
  4. Una vez que se llega a un candidato, la identidad se confirma con STR de referencia contra la evidencia original. La genealogía genera pistas, no pruebas [R44].
  5. El panel debe estar validado, con control de contaminación y de calidad. Las guías NTVIC dan los criterios [R40, R41].
- Riesgo mayor: que el perfil de la palma sea de contaminación o de personal de la escena. Un linaje genético resuelto de alguien que tocó la escena después sería una pista falsa; por eso 2.8 es previa.

## 10. Las cinco vías más prometedoras (resumen)

1. Reinterpretar con genotipado probabilístico los datos de los discos zip y llevar el haplotipo Y a YHRD (2.1). Costo bajo, sin consumir muestra. Precondición: archivos crudos o tablas de picos, haplotipo exacto, copia forense de los discos.
2. Analizar los dos sobres sin abrir y los hisopados (2.2) con kits modernos y LR. Precondición: que existan, con cadena de custodia, y reservar mitad para contraperitaje.
3. Muestras de eliminación del personal de 2002 (2.8). Precondición: orden judicial o consentimiento; sin esto ninguna coincidencia masculina es interpretable.
4. Cabellos y raspados ungueales con secuenciación masiva de fragmentos cortos (2.4, 2.5). Precondición: que los frascos y bolsas existan y sean consumibles. Rendimiento incierto a 20 años.
5. Comparación objetiva 3D de los proyectiles, acotamiento con GRC y barrido SEM-EDS de los stubs (4.1 a 4.4). Precondición: acceso a proyectiles y stubs; el valor depende de que queden estrías medibles.

La genealogía genética (sección 9) queda condicionada a que alguna de estas vías produzca ADN suficiente y a la aclaración legal (sección 8).

## 11. Qué no se puede esperar

- Tiempo de muerte por exhumación, BPA sobre fotos viejas, comparación de voz en una llamada breve, o reconstrucción de la cobertura de 2002 con pruebas de campo actuales: rendimiento bajo o no demostrado.
- Cualquier resultado nuevo puede discutirse por contaminación, cadena de custodia y transferencia; el valor de un perfil sin identificar depende de las muestras de eliminación.
- Para las vías 1 y 2 el estándar es el LR con proposiciones explícitas; para la 5, la comparación se reporta con incertidumbre. Resultados con esas formas son defendibles; un "coincide" sin medidas, no.
