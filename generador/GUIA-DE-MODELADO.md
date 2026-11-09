# Guía de modelado para el generador

Esta guía es para quien modela en Archi un sistema que no es YateGear y quiere que el generador escriba su primera versión en C#. Dice qué dibujar para que el generador lo encuentre, en qué orden trabajar y qué significa cada error. El formato del YAML (lo que el modelo no dice) está en la sección "Formato del YAML" del [README](README.md).

El modelo de ejemplo `ejemplo/Biblioteca.archimate` sigue cada paso de esta guía. Es un contexto de préstamos de libros, con un agregado, dos comandos, una consulta y un servicio de la capa anticorrupción, y su YAML es `ejemplo/specs/prestamos.yaml`. Ábrelo en Archi (vista "Contexto Préstamos") mientras lees.

## 1. Cómo lee el generador

- **Por tipo, relación y propiedad, nunca por la vista.** Las vistas, los anidamientos, los colores y las carpetas no cuentan. Lo que se dibuja dentro de otra caja, pero no se une con una relación, el generador no lo ve.
- **Los nombres son el lenguaje ubicuo.** El nombre de cada elemento pasa al código (`Prestar un libro` --> `PrestarUnLibro`, `/prestamos/comandos/prestar-un-libro`), así que se escriben como se dicen, en español y con tildes. Solo dos prefijos tienen significado: "Contexto " (se quita para el nombre del proyecto) y "Agregado ".
- **Las propiedades tienen nombres fijos.** Son estas:

| Propiedad | En qué elemento | Valor |
|---|---|---|
| `Código del servicio` | Proceso de aplicación (comando) o servicio de aplicación (consulta) | Su código, único en el modelo: `SB-01` |
| `Código del servicio anticorrupción` | Servicio de aplicación de la capa anticorrupción | Su código, único: `SA-01` |
| `Tipo DDD` | Objeto de datos | `Raíz`, `Entidad` u `Objeto de valor` |
| `Campo: <nombre>` | Raíz, entidad u objeto de valor | El tipo del campo (ver el paso 6) |
| `Cardinalidad` | Composición de la raíz a una entidad o un objeto de valor | `Uno`, `Cero o uno` o `Muchos` |
| `Código` | Servicio de negocio del contrato | El mismo código del comando, la consulta o el SA |
| `Servicio` | Contrato | El mismo código |
| `Externo` | Contraparte de un servicio SA | `Sí` si es un sistema externo |

El valor de un código es libre (`SB-01`, `PR-1`, `PRESTAR`...): no puede estar vacío ni repetirse en el modelo, y es el mismo en el servicio de negocio (`Código`) y en el contrato (`Servicio`) del paso 10. Las clases y las rutas salen del nombre del elemento, no del código. El modelo de YateGear usa otros nombres para las dos primeras propiedades, `Servicio básico V4` y `Servicio anticorrupción V4`, que vienen de su vista V4 ("Descomposición de servicios"); el generador los acepta también, pero en un modelo nuevo conviene usar los de la tabla. Un elemento con las dos (la neutra y la de YateGear) y valores distintos es un error.

## 2. Paso a paso

Cada paso dice qué elemento crear, con qué relación y con qué propiedad. Al final de cada uno, entre paréntesis, cómo se ve en el ejemplo.

1. **Contexto.** Un componente de aplicación llamado "Contexto <dominio>". (`Contexto Préstamos`; el proyecto se llama `Prestamos`.)
2. **Comandos.** Un proceso de aplicación por cada operación que cambia algo, con la propiedad `Código del servicio`. El contexto se le asigna con una **asignación** contexto --> proceso. Un componente es contexto si tiene asignado al menos un proceso con esa propiedad. (`Prestar un libro`, SB-01; `Devolver el libro`, SB-02.)
3. **Consultas.** Un servicio de aplicación por cada consulta, con la propiedad `Código del servicio`, y una **realización** contexto --> servicio. (`Consultar el préstamo`, SB-03.)
4. **Agregado.** Una agrupación llamada "Agregado <raíz>" que **agrega** (relación de agregación desde la agrupación) a sus comandos, sus eventos, su raíz y sus entidades y objetos de valor. Cada comando y cada evento está en exactamente un agregado. Las agrupaciones que no empiezan por "Agregado " no cuentan. (`Agregado Préstamo`.)
5. **Raíz, entidades y objetos de valor.** Objetos de datos con `Tipo DDD`. Cada agregado agrega exactamente una raíz. La raíz **compone** a cada entidad y objeto de valor, y cada composición lleva `Cardinalidad`. Una entidad tiene identidad propia dentro de su raíz (por ejemplo, cada cobro de una cuenta, con su comprobante); un objeto de valor no (un plazo, un rango de fechas). (Raíz `Préstamo`; objeto de valor `Plazo del préstamo`, `Uno`.)
6. **Campos.** Una propiedad `Campo: <nombre>` por cada dato, con su tipo como valor, en el orden en que se leen: `string`, `int`, `decimal`, `bool`, `DateOnly`, `DateTime`, `List<tipo>`, el sufijo `?` para un dato opcional y `enum <Nombre>(valor, valor, ...)`. La identidad y el estado de la raíz no son campos: se declaran en el YAML. Un nombre de campo no se repite entre la raíz y sus partes, porque un dato pasa de un lugar a otro por su nombre (regla de los datos). (`Campo: lector` = `string`; `Campo: hasta` = `DateOnly`.)
7. **Accesos.** Cada comando tiene exactamente un **acceso** a la raíz de su agregado, de escritura o de lectura y escritura (no "acceso" sin especificar). Si además necesita otra raíz del mismo contexto, la lee (acceso de lectura). Una consulta tiene un acceso de lectura a cada raíz que lee. (`Prestar un libro` escribe el préstamo; `Devolver el libro` lo lee y lo escribe; la consulta lo lee.)
8. **Eventos.** Un evento de aplicación por cada hecho que publica un comando, con un **disparo** comando --> evento. Cada evento lo dispara al menos un comando del contexto. (`Libro prestado`, `Libro devuelto`.)
9. **Políticas.** Si un evento del contexto pone en marcha otro comando del mismo contexto, un disparo evento --> comando. Los eventos que van a otro contexto no se dibujan como disparo: se declaran en el YAML de quien los recibe (`eventos_de_otros_contextos`), y el evento tiene que existir en el modelo, disparado por un comando del otro contexto. (El ejemplo no tiene políticas; YateGear tiene cuatro.)
10. **Contratos.** Cada comando, consulta y servicio SA **realiza** un servicio de negocio con la propiedad `Código` (su mismo código). Ese servicio de negocio tiene una **asociación** con un contrato con la propiedad `Servicio` (el mismo código), y la documentación del contrato se escribe en líneas que empiezan por `Entrada:`, `Salida:` y, si hay reglas, `Reglas:`. Las reglas aparecen como comentario en el archivo manual de cada comando, donde se escriben a mano. (`Contrato de servicio: Prestar un libro`, con REG-01.)
11. **Servicios de la capa anticorrupción.** Un servicio de aplicación con la propiedad `Código del servicio anticorrupción` y una **relación de servicio** SA --> contexto. Una interfaz de aplicación se le **asigna** (interfaz --> SA). La interfaz intercambia **flujos** con un solo elemento, la contraparte (el sistema externo, con `Externo` = `Sí`), y entre el SA y la contraparte hay una relación de servicio, en el sentido que corresponda. El nombre de cada flujo dice qué pasa y su sentido dice si entra o sale. Para llamar al sistema y esperar respuesta (`usa` en el YAML) hace falta un flujo que entra, la respuesta (conviene dibujar también el que sale, la pregunta); para recibir lo que el sistema envía (`recibe`), uno que entra; y para solo enviar (`envia`), uno que sale. `specs.py` revisa que estén. (`Catálogo de la biblioteca`, SA-01, con la interfaz `Interfaz del catálogo` y la contraparte `Sistema del catálogo`.)

## 3. Orden de trabajo

1. **Modelar en Archi y guardar.** La línea de comandos de Archi exporta lo que está guardado en disco.
2. **Revisar el modelo.** Desde la carpeta `generador`:

   ```powershell
   powershell -ExecutionPolicy Bypass -File .\generar.ps1 -Modelo <ruta>.archimate -Specs <carpeta>/specs/<contexto>.yaml -Salida <carpeta>/salida -SoloValidar
   ```

   `extraer.py` revisa el modelo y junta todos sus errores antes de detenerse (sección 4). `-SoloValidar` no genera nada.
3. **Escribir el YAML del contexto.** Lo mínimo es `contexto`, `raices`, `comandos`, `eventos`, `consultas` y `servicios_sa`. `specs.py` dice qué falta, con el nombre exacto de cada elemento del modelo ("falta en el YAML: comando ..."). Conviene empezar copiando `ejemplo/specs/prestamos.yaml`.
4. **Generar, escribir las reglas y probar.** `generar.ps1` (los mismos parámetros, sin `-SoloValidar`) crea el proyecto y un archivo manual (`.cs`) por comando y consulta: ahí se escriben las reglas del contrato (`ValidarReglas`) y los datos calculados. Después se agregan los escenarios al YAML y se corre:

   ```powershell
   powershell -ExecutionPolicy Bypass -File .\verificar.ps1 -Modelo <ruta>.archimate -Specs <carpeta>/specs/<contexto>.yaml -Salida <carpeta>/salida -SinPruebasDelValidador
   ```

   Genera dos veces (la misma huella), revisa la trazabilidad y prueba los escenarios. `-SinPruebasDelValidador` va porque los casos de `pruebas-validador/` son los de YateGear.
5. **Cambiar el modelo.** Se cambia en Archi y se vuelve al paso 2. El generador reescribe los `.g.cs` y nunca toca los `.cs` manuales: si uno queda sin su comando, avisa.

## 4. Errores del modelo

`extraer.py` nombra el elemento (tipo, nombre e ID) en cada error. Los más comunes:

| Mensaje (empieza así) | Qué falta |
|---|---|
| el modelo no tiene contextos | Ningún componente de aplicación tiene asignado un proceso con `Código del servicio` (paso 2). |
| ... está asignado al contexto pero no tiene la propiedad "Código del servicio" | El proceso asignado al contexto no tiene su código (paso 2). |
| ... tiene "Código del servicio" = ... y "Servicio básico V4" = ...: deja una sola | El elemento tiene el código con los dos nombres y valores distintos. |
| ... debe estar en 1 agrupación "Agregado ..." | Falta la agregación desde el agregado hacia ese comando o evento, o hay dos (paso 4). |
| ... debe agregar exactamente 1 objeto de datos con Tipo DDD = Raíz | El agregado no agrega su raíz, o agrega dos, o a la raíz le falta `Tipo DDD` (pasos 4 y 5). |
| ... debe tener exactamente 1 composición desde su raíz o entidad | Falta la composición hacia la entidad o el objeto de valor, o hay dos (paso 5). |
| la composición ... tiene Cardinalidad = None | A la composición le falta `Cardinalidad` (paso 5). |
| campo "..." de ...: tipo no permitido | El valor de `Campo: <nombre>` no es uno de los tipos del paso 6. |
| ... debe tener exactamente 1 acceso a la raíz | El comando no accede a la raíz de su agregado, o lo hace dos veces (paso 7). |
| ... tiene un acceso sin especificar (acceso) a su raíz | El acceso es del tipo "acceso": cámbialo a escritura, lectura o lectura y escritura (paso 7). |
| ... que es raíz de otro agregado; solo se permite lectura | Un comando escribe la raíz de otro agregado: un comando solo escribe la suya (paso 7). |
| ... no lo dispara ningún comando del contexto | Falta el disparo comando --> evento (paso 8). |
| ... debe realizar 1 servicio de negocio con Código = ... | Falta la realización hacia el servicio de negocio, o a este le falta `Código` (paso 10). |
| ... debe tener 1 contrato asociado | Falta la asociación entre el servicio de negocio y su contrato (paso 10). |
| ... no tiene la línea "Entrada:" (o "Salida:") | La documentación del contrato no tiene esa línea (paso 10). |
| ... debe tener 1 interfaz asignada | Falta la asignación interfaz --> SA (paso 11). |
| ... debe intercambiar flujos con 1 contraparte | La interfaz no tiene flujos, o los tiene con más de un elemento (paso 11). |
| entre ... y su contraparte ... debe haber 1 relación de servicio | Falta la relación de servicio entre el SA y la contraparte (paso 11). |
| el código ... se repite | Dos comandos, consultas o SA tienen el mismo código. |
| N elementos ... se llaman "..." | Dos elementos del mismo tipo del contexto tienen el mismo nombre: el código necesita nombres distintos. |

Si la línea de comandos de Archi escribe `IllegalArgumentException` al exportar, alguna caja tiene una fuente sin nombre. La exportación termina igual; se arregla en Archi dándole una fuente explícita.

## 5. Lo que no se genera

Lo que el generador todavía no sabe expresar se detiene con un mensaje, o está en las limitaciones del README: un objeto de valor compuesto por una entidad, una política entre raíces con distinta identidad y una consulta por identidad sobre raíces con distinta identidad. Todo lo demás del modelo (motivación, estrategia, procesos de negocio, otras vistas) puede estar en el mismo archivo: el generador no lo lee.
