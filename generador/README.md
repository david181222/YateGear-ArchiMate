# Generador de código desde el modelo ArchiMate

Este generador construye la primera versión de la aplicación de YateGear a partir del modelo de Archi (`../modelo/YateGear.archimate`) y de un archivo de especificaciones por contexto (`specs/*.yaml`). Es determinista: no usa IA ni red, y el mismo modelo con el mismo YAML da siempre los mismos archivos.

Genera un proyecto por cada contexto que tiene YAML en `specs/`, y los levanta todos en un solo programa (D1). Hoy tiene YAML el piloto, **"Contexto Gestión del arriendo"**; los otros cuatro contextos se agregan escribiendo su YAML. Lo que falta, las decisiones pendientes y el reparto del trabajo están en [PENDIENTES.md](PENDIENTES.md).

## Tecnología

El proyecto generado es C# con una API web de ASP.NET Core (API mínima) sobre .NET 8. Es una decisión del equipo.

## Requisitos

| Qué | Versión | Para qué |
|---|---|---|
| PowerShell | Windows: Windows PowerShell 5.1 o PowerShell 7. Linux: PowerShell 7 (`pwsh`). | Ejecutar `generar.ps1`, `ejecutar.ps1` y `probar.ps1`. |
| Python | 3.13. Windows: con el lanzador `py`. Linux: `python3.13` en el PATH, o el que instala `uv python install 3.13`. | El generador. `generar.ps1` crea el entorno virtual `.venv` e instala `requirements.txt` si no existen; solo ese paso usa la red. |
| .NET SDK | cualquier 8.0.x | Compilar y correr el proyecto generado. `salida/global.json` fija el SDK 8 (`8.0.100` con `rollForward: latestFeature`). En Linux, si existe `~/.dotnet/dotnet`, los scripts usan ese, para no depender del `dotnet` del sistema. |
| Archi | 5.x. Windows: en `C:\Program Files\Archi`. Linux: `Archi` en el PATH, `~/.local/opt/Archi/Archi` o `/opt/Archi/Archi`. | Exportar el modelo con su línea de comandos (ACLI). Funciona aunque Archi esté abierto, pero exporta lo guardado en disco. Otra ruta: `-Archi <ruta del ejecutable de Archi>`. |

Las librerías de Python tienen versión fija en `requirements.txt`: pyArchimate 2.0.0, Jinja2 3.1.6, PyYAML 6.0.3 y sus dependencias.

En Linux todo se instala en la carpeta del usuario, sin sudo: el SDK con `dotnet-install.sh --channel 8.0 --install-dir ~/.dotnet`, Python con `uv python install 3.13`, y PowerShell y Archi descomprimiendo sus `.tar.gz` en `~/.local/opt` (con `pwsh` enlazado en `~/.local/bin`). Probado en Ubuntu 26.04 con .NET 8.0.427, PowerShell 7.6.9 y Archi 5.10: genera exactamente los mismos archivos que en Windows (misma huella).

## Cómo ejecutarlo

Desde la carpeta `generador`:

```powershell
powershell -ExecutionPolicy Bypass -File .\generar.ps1     # exporta, lee, valida, genera y compila
powershell -ExecutionPolicy Bypass -File .\ejecutar.ps1    # levanta la aplicación (Ctrl+C para detenerla)
powershell -ExecutionPolicy Bypass -File .\probar.ps1      # ejecuta los escenarios y marca cada paso con ✓ o ✗
```

En Linux, lo mismo con `pwsh`:

```bash
pwsh ./generar.ps1
pwsh ./ejecutar.ps1
pwsh ./probar.ps1      # la salida de la aplicación queda en salida/intermedio/aplicacion*.log
```

Las herramientas de Python se llaman con `.\.venv\Scripts\python.exe` en Windows y con `./.venv/bin/python` en Linux.

`generar.ps1` se detiene en el primer paso que falle y dice cuál. Sus parámetros, todos con valor por defecto, son `-Modelo` (por defecto, el único `.archimate` de `../modelo`), `-Specs` (por defecto, todos los `specs/*.yaml`; para generar solo algunos: `-Specs specs/uno.yaml,specs/otro.yaml`) y `-Archi`. Ojo: `salida/` queda con exactamente los contextos que se generan, así que con `-Specs` se borran los archivos generados de los demás (nunca su código a mano); vuelven al generar todo.

`ejecutar.ps1` levanta la aplicación (el host, con todos los contextos) desde `salida/`, para que `dotnet` use el SDK 8 de `salida/global.json`. Con la aplicación arriba, cada `salida/pruebas/<Proyecto>/pruebas.http` se puede ejecutar llamada por llamada con la extensión REST Client de VS Code o con Visual Studio.

`probar.ps1` compila, levanta la aplicación, ejecuta los escenarios de cada contexto (`salida/pruebas/<Proyecto>/escenarios.json`), la detiene y termina con código 1 si algún paso falla. Con `-Contexto "<nombre del contexto o del proyecto>"` prueba solo ese.

Los dos leen de `salida/contextos.json` qué proyecto levantar, en qué puerto y qué contextos hay, así que no tienen escrito ningún nombre del modelo.

### Puerto

La aplicación usa el puerto **5080**. Si está ocupado:

- Para una sola vez: `.\ejecutar.ps1 -Puerto 5090` o `.\probar.ps1 -Puerto 5090`. Si usas un `pruebas.http`, cambia también su línea `@base`.
- Para cambiarlo siempre: cambia `PUERTO` en `src/generar.py` y vuelve a generar. De ahí salen `salida/<Host>/Properties/launchSettings.json`, `salida/contextos.json` y los `pruebas.http`. No se editan a mano, porque el generador los reescribe.

## Cómo funciona

```
modelo/YateGear.archimate
   |  ACLI de Archi: --loadModel ... --xmlexchange.export ...
   v
salida/intermedio/<modelo>.xml          formato de intercambio (Open Exchange); no se versiona
   |  src/extraer.py (pyArchimate): lee, valida el modelo y toma todos sus contextos
   v
salida/intermedio/modelo-ddd.json  <--  specs/*.yaml (uno por contexto)
   |  src/specs.py: revisa cada YAML contra el JSON
   |  src/generar.py + plantillas/*.j2 (Jinja2)
   v
salida/   solución C# (.NET 8): un proyecto por contexto con YAML, el host y el bus entre contextos;
          contextos.json, y pruebas/ y trazabilidad/ por contexto
   |  dotnet build
   v
ejecutar.ps1 / probar.ps1
```

Se lee el XML de intercambio y no el `.archimate` directo, porque los dos dan lo mismo. `src/comparar_lectura.py` lo comprueba: compara el `.archimate` leído sin pyArchimate, el `.archimate` leído con pyArchimate y el XML leído con pyArchimate. Coinciden en totales, IDs, nombres, documentación, propiedades, tipos de acceso, origen y destino de cada relación, y cajas y líneas de cada vista. Antes de comparar se normaliza solo la forma de escribir: los nombres de tipo, las uniones y los códigos de acceso.

### Carpetas

| Carpeta o archivo | Qué es |
|---|---|
| `generar.ps1`, `ejecutar.ps1`, `probar.ps1` | Los tres comandos. Van en UTF-8 con BOM, porque Windows PowerShell 5.1 lee sin BOM como ANSI y rompería la "ó" de "Gestión". |
| `src/` | El generador en Python: `leer.py`, `tipos.py`, `extraer.py`, `specs.py`, `nombres.py`, `generar.py`, y las herramientas de prueba `comparar_lectura.py`, `huella.py`, `revisar_trazabilidad.py` y `probar.py`. |
| `plantillas/` | Una plantilla Jinja2 por tipo de archivo generado. |
| `specs/` | Un YAML de especificaciones por contexto. Su comentario inicial explica cada sección. |
| `salida/` | Lo generado. Se versiona todo, salvo `bin/`, `obj/`, el XML exportado (`intermedio/*.xml`) y los registros de la aplicación (`intermedio/*.log`). |

## Qué se lee del modelo

Todo se busca por tipo y por relación, nunca solo por nombre, porque hay nombres repetidos entre capas (por ejemplo, el objeto de negocio y el objeto de datos "Arriendo"). El único nombre que se usa para buscar es el del contexto. No se leen los anidamientos de las vistas: los objetos de valor se dibujan dentro de su raíz, pero lo que cuenta es su composición.

| Concepto | Cómo se encuentra en el modelo |
|---|---|
| Contexto | Componente de aplicación "Contexto `<dominio>`". |
| Comandos | Asignación contexto --> proceso de aplicación con la propiedad `Servicio básico V4`. |
| Consultas | Realización contexto --> servicio de aplicación con `Servicio básico V4`. |
| Servicios SA | Servicio SA --> servicio --> contexto, con la propiedad `Servicio anticorrupción V4`. Su interfaz es la que se le asigna. Su contraparte es el único elemento con el que esa interfaz intercambia flujos, y entre los dos hay una relación de servicio en cualquier sentido (en SA-08 el SA le sirve a la contraparte). |
| Agregado | Agrupación cuyo nombre empieza por "Agregado " y que agrega exactamente un objeto de datos con `Tipo DDD` = Raíz. Las agrupaciones del canvas de la V11 no cuentan. |
| Raíz, entidad y objeto de valor | Objeto de datos con `Tipo DDD`. La raíz compone a sus entidades y objetos de valor, y cada composición tiene `Cardinalidad`. |
| Campos | Propiedades `Campo: <nombre>` con su tipo, en el orden del modelo. |
| Acceso | Acceso comando --> raíz. En el `.archimate`, un acceso sin atributo es escritura. |
| Eventos | Disparo comando --> evento de aplicación. |
| Política | Disparo evento --> comando, los dos del contexto. |
| Contrato | Comando o consulta --> realiza --> servicio de negocio con el mismo código --> asociación --> contrato. Su texto se separa en Entrada, Salida y Reglas. |

## Formato del YAML

Cada contexto que se quiere generar tiene un `specs/<contexto>.yaml`. El modelo dice qué elementos hay y cómo se relacionan; el YAML declara lo que el modelo no dice y el generador necesita. Las claves son los nombres exactos del modelo, y `specs.py` revisa cada una: si falta un elemento del contexto, se nombra uno que no existe o una clave no se conoce, el generador se detiene. Todo dato que no sale de la documentación lleva el comentario `# supuesto`.

**Tipos** (los mismos de los campos del modelo, V6-DEC-17): `string`, `int`, `decimal`, `bool`, `DateOnly`, `DateTime`, `List<tipo>`, el sufijo `?` para un dato opcional y `enum <Nombre>(valor, valor, ...)`. Las fechas de ejemplo van entre comillas.

**Regla de los datos:** un dato pasa de un lugar a otro por su nombre (ver "Reglas del generador"). Cuando un dato debe ir a un campo que se llama distinto, se declara con una correspondencia (`guarda: [{campo: dato}]`).

| Sección y clave | Qué declara | Ejemplo |
|---|---|---|
| `contexto` | Nombre exacto del componente de aplicación del contexto. | `Contexto Calificaciones` |
| `raices > <raíz> > identidad` | `nombre` y `tipo` (string) de la identidad, y cómo se forma: un consecutivo con `prefijo` y `digitos`, o con datos, en orden, con `de`. En `de`, un campo de la raíz va sin tipo; un dato que no es campo lleva su tipo, y la raíz lo guarda como parte de su identidad. Las partes se unen con `/`. | `prefijo: ARR-` y `digitos: 4`; o `de: {número del arriendo: string, quién califica: }` |
| `raices > <raíz> > estado` | Los estados de la raíz, como `enum`. | `enum Estado del arriendo(reserva solicitada, ...)` |
| `comandos > <comando> > entrada` | Datos que recibe. La identidad de la raíz se agrega sola, salvo en el que la crea. | `cliente: string` |
| `... > crea` | `true` si el comando crea la raíz. Lleva `a` (estado inicial) y no lleva `desde` ni `resultados`. | `crea: true` |
| `... > valores` | Datos fijos del comando, para campos de la raíz o de sus objetos de valor. | `quién califica: cliente` |
| `... > requiere` | Eventos de otros contextos que deben haber llegado para la identidad del comando (se buscan con el dato que es su identidad). Si no, 409. Sus datos quedan disponibles para el comando. | `[Arriendo cerrado]` |
| `... > usa` | Servicios SA que llama, en orden. Sus salidas quedan disponibles. | `[Clientes del CRM]` |
| `... > guarda` | Lo que escribe en la raíz: objetos de valor y campos por su nombre, o `{campo: dato}` para guardar un dato con otro nombre. | `[Fechas del arriendo, calificado: propietario]` |
| `... > desde`, `a` | Estados desde los que se permite, y estado al que pasa. | `desde: [reserva solicitada]` |
| `... > eventos` | Los eventos que publica: exactamente los del modelo. | `[Reserva confirmada]` |
| `... > resultados` | En lugar de `eventos`: un evento por resultado, elegido con `si` (un dato y sus valores), con su propio `desde` y `a`. | `Arriendo iniciado: {si: {nuevo estado: [en curso]}, a: en curso}` |
| `eventos > <evento> > datos`, `calculados` | Datos que lleva cada evento. Los `calculados` salen de una regla del contrato y los escribe el código a mano. | `inicio: DateOnly` |
| `consultas > <consulta> > entrada`, `salida`, `calculados` | Datos que recibe y devuelve. Por defecto lee una raíz por su identidad. | `estado: enum ...` |
| `... > sobre: todas`, `filtro`, `agrega` | Consulta sobre todas las raíces: `filtro` las compara por igualdad con datos de la entrada del mismo nombre, y cada dato de la salida es una agregación de `agrega`: `conteo`, o `promedio`, `suma`, `mínimo` o `máximo` `de <dato de la raíz>`. Sin raíces no hay promedio, mínimo ni máximo: esos van con `?`. | `calificación promedio: promedio de calificación dada` |
| `eventos_de_otros_contextos > <evento>` | `de` (contexto que lo publica), `datos`, e `identidad` si llega con un dato distinto de la identidad de la raíz. Con `dispara`, ejecuta ese comando; `con` fija valores de su entrada y `junto_con` espera a otros eventos. Sin `dispara`, solo se recuerda para los comandos que lo `requiere`n. | `Arriendo cerrado: {de: ..., identidad: número del arriendo}` |
| `servicios_sa > <servicio>` | `entrada`, `salida`, `respuesta_por_defecto` y `casos` (con `si`) del sistema externo simulado. Todo fijo: sin azar ni fecha de hoy. | `respuesta_por_defecto: {nivel: medio}` |
| `escenarios > <escenario>` | Lista de pasos (comando, consulta o evento de otro contexto), cada uno con `con` y `espera` (ver "Escenarios y pruebas"). | `- Cancelar la reserva: {espera: Reserva cancelada}` |

Cada YAML empieza con un comentario que explica sus secciones; `specs/gestion-del-arriendo.yaml` y `specs/calificaciones.yaml` sirven de ejemplo.

## Qué genera cada elemento del modelo

| Elemento del modelo | Qué genera en `salida/` |
|---|---|
| Contexto (con YAML) | Un proyecto biblioteca, `<Proyecto>/<Proyecto>.csproj`, con `Registro.g.cs` (servicios, políticas y endpoints), su referencia en el host y su entrada en la `.sln`. El nombre del proyecto sale del contexto sin "Contexto ": "Contexto Gestión del arriendo" --> `GestionDelArriendo`. |
| Modelo | La solución `<Modelo>.sln`, el host `<Modelo>/` (un solo programa que registra todos los contextos, con un solo puerto) y `contextos.json`, que dice a los scripts qué hay. |
| Agregado y raíz | Clase parcial con su identidad, su `Estado` (enum) y sus campos, y una propiedad por composición: Uno --> `T`, Cero o uno --> `T?`, Muchos --> `List<T>`. Si la identidad se forma con datos que no son campos, también una propiedad por cada uno. |
| Objeto de valor | `sealed record` con sus campos. |
| Tipos `enum` (del modelo o del YAML) | `enum` de C#. En JSON viaja como texto, por ejemplo `"Medio"` o `"EnCurso"`. |
| Comando | El record del comando, un manejador parcial (`.g.cs`), un endpoint `POST /<contexto>/comandos/<comando>` (por ejemplo `/gestion-del-arriendo/comandos/confirmar-la-reserva`) y un archivo manual (`.cs`). |
| Contrato | Comentarios XML en el manejador (entrada, salida y reglas). Sus reglas aparecen además como comentario en `ValidarReglas`, en el archivo manual. |
| Evento | Record del evento, con la identidad y sus datos. |
| Política | Una suscripción en el bus de eventos, en `Politicas.g.cs`. |
| Consulta | Records de entrada y salida, un manejador, un endpoint `GET /<contexto>/consultas/<consulta>/{identidad}` y un archivo manual. Con `sobre: todas`, el endpoint no lleva identidad (`GET /<contexto>/consultas/<consulta>?dato=valor`) y el manejador recorre las raíces que cumplen el filtro. |
| Servicio SA | Interfaz, records de entrada y salida, y una implementación simulada que responde con los valores del YAML. |
| Interfaz, contraparte y flujos | Comentarios en el servicio SA y filas en la trazabilidad del contexto. |
| Evento de otro contexto (del YAML) | Record del evento, un método en `ReceptorDeEventosExternos` que lo lee desde JSON y revisa sus datos obligatorios, y un endpoint `POST /<contexto>/eventos-externos/<evento>`. Si un comando lo requiere, se guarda en `MemoriaDeEventos`; sin `dispara`, solo se guarda. |

Además se generan, por contexto, `pruebas/<Proyecto>/pruebas.http` y `pruebas/<Proyecto>/escenarios.json` (desde los escenarios del YAML) y `trazabilidad/<Proyecto>.csv`; y para toda la solución, `global.json`, el proyecto `Integracion` (bus entre contextos) y la infraestructura de cada contexto.

### Comunicación entre contextos (D1)

Todos los contextos corren en un solo programa. Cada uno publica sus eventos en su bus y, además, en el **bus entre contextos** (`Integracion/BusEntreContextos.g.cs`), por su nombre en el modelo y en JSON. Ningún proyecto de contexto referencia a otro: solo el host los conoce a todos, y cada contexto lee los eventos que le llegan con sus propios records de `EventosExternos`.

Un evento de otro contexto, venga por su endpoint de prueba o por el bus, se lee con `LectorDeEventos`: si le falta un dato obligatorio (o llega en `null`), responde 422 con "Falta el dato ..." y el nombre del dato en el modelo. Así se nota de inmediato si el contexto que publica lo llama distinto (D2).

`GET /eventos-entre-contextos` muestra los eventos que pasaron por el bus y los errores de sus suscriptores; `GET /contextos`, los contextos que levantó el programa. Las suscripciones entre contextos todavía no se conectan: se hacen en G12.

## Reglas del generador

### Generalidad: el generador no conoce YateGear

El generador debe servir para cualquier modelo ArchiMate que siga las convenciones de diagramación de la tabla "Qué se lee del modelo", no solo para este. Por eso:

- El código del generador (`src/`, `plantillas/` y los `.ps1`) solo conoce las convenciones: tipos de elemento, relaciones y propiedades. Nunca nombres de contextos, raíces, campos ni datos de un modelo en particular.
- Lo que el modelo dice se lee del modelo. Lo que el modelo no dice o deja ambiguo (datos de entrada y salida, estados, transiciones, identidades, respuestas simuladas) se **declara** en el YAML del contexto, con `# supuesto` cuando no sale de la documentación.
- Si a un contexto le falta algo que el código no puede inferir ni declarar en el YAML, se amplía el formato del YAML (y `specs.py` lo revisa) y se documenta. No se escribe a mano en el generador.
- Si el modelo tiene un error o le falta un dato, se corrige el modelo en Archi, no el generador. Las correcciones quedan en "Discrepancias encontradas".

Los nombres del modelo que antes estaban escritos en los scripts (el proyecto, el contexto, el YAML y el XML del piloto) se quitaron en G1: hoy salen del modelo, de `specs/` o de `salida/contextos.json`.

### Regla de los datos

Un dato pasa de un lugar a otro por su **nombre** y su **tipo**, que son los del lenguaje ubicuo. Si la entrada de un comando trae "inicio" y el objeto de valor "Fechas del arriendo" tiene el campo "inicio", es el mismo dato. Así no hace falta escribir correspondencias, y `specs.py` puede revisar cada dato. Si un nombre puede ir a más de un destino dentro de un comando, o puede venir de dos campos de la raíz, `specs.py` lo marca como error y dice cuáles son.

**Prioridad cuando un dato llega de varios orígenes:** gana el más reciente. Primero la respuesta del servicio SA (si hay varios, el último que se llamó), luego la entrada del comando y al final la raíz. Así, el valor nuevo que trae un comando reemplaza al que ya estaba guardado. `specs.py` lista estos casos; en el piloto son seis, todos en "Confirmar la reserva" y en "Obtener el nivel de riesgo del cliente".

### Pasos de un comando

1. Cargar la raíz (404 si no existe). El comando que crea la raíz la arma en el paso 6.
2. Revisar que el estado actual esté en su `desde` (409 si no). Se revisa antes de llamar a los SA, para que una raíz en un estado inválido no consulte a sistemas externos.
3. Buscar los eventos de otros contextos de `requiere` por su identidad (409 si alguno no ha llegado), y llamar a los servicios SA de `usa`, en orden.
4. Elegir el resultado con la condición `si`, y revisar el `desde` de ese resultado (409).
5. `ValidarReglas`, en el archivo manual (422 si se incumple una regla).
6. Escribir lo de `guarda` y el nuevo estado (`a`), y guardar la raíz. Si la identidad es un consecutivo, el repositorio se lo asigna al guardar una raíz nueva (ARR-0001, ARR-0002, ...), así que una solicitud rechazada no gasta número. Si se forma con datos, la raíz nueva se agrega con ella, y responde 409 si ya existe.
7. Publicar los eventos.

### Capas

| Capa | Qué hace |
|---|---|
| 1. Estructura | Todo lo de la tabla anterior: compila, corre y recorre el flujo. |
| 2. Transiciones | `desde` y `a` del YAML: 409 si el estado no lo permite, y cambio de estado al guardar. |
| 3. Eventos de otros contextos | Endpoint por evento. Con `junto_con`, los eventos que ya llegaron se guardan en memoria por número del arriendo; mientras falte alguno la respuesta es 202, y cuando llega el último se dispara el comando con los datos de todos. |

### Archivos manuales

Cada comando y cada consulta tiene un archivo `.cs` que el generador crea **una sola vez** y nunca sobrescribe. Trae:
- `ValidarReglas`, vacío, con el texto de cada regla de su contrato como comentario;
- un valor provisional para cada dato calculado, marcado `PENDIENTE` y con la regla de la que sale.

El código generado va en los `.g.cs`, que el generador sí reescribe. Ejemplo: REG-01 está escrita a mano en `salida/GestionDelArriendo/Comandos/ConfirmarLaReserva.cs` y sobrevive a la regeneración.

Si un manual queda sin su `.g.cs` (por ejemplo, porque se quitó un comando), el generador no lo borra: avisa al final y lo saca de la compilación en el `.csproj`, con un comentario que dice cuál es y por qué. Los `.g.cs` que ya no corresponden sí se borran.

### Bitácora

`GET /<contexto>/bitacora` (por ejemplo `/gestion-del-arriendo/bitacora`) muestra en orden los eventos publicados, los eventos recibidos de otros contextos, las llamadas a los servicios SA simulados y los errores de las políticas. Es **infraestructura del piloto y no sale del modelo**: sirve para ver el flujo y la usa `probar.ps1`. También son infraestructura el repositorio en memoria, el bus de eventos y la espera de eventos.

## Escenarios y pruebas

La sección `escenarios` del YAML define pruebas de punta a punta. Un paso es un comando, una consulta o un evento de otro contexto. `con` fija valores de su entrada, y `espera` dice el resultado: un evento, un código HTTP (409, 422, 404 o 202) o, en una consulta, `{dato de la salida: valor, ...}`. Sin `espera`, el paso debe responder 2xx.

Cada paso tiene su identidad. Un comando que crea la raíz recibe la siguiente (el consecutivo, que una solicitud rechazada no gasta, o la que se forma con sus datos), y se revisa que la respuesta la traiga; los demás pasos usan la de la última raíz creada en el escenario. Un evento de otro contexto que llega con su propia identidad la toma de `con`. Los consecutivos siguen de un escenario al siguiente, en orden, porque todos corren contra la misma aplicación.

`specs.py` revisa que los escenarios estén bien escritos: que los nombres existan, que los valores de `con` sean válidos y que `espera` sea un evento que ese paso puede publicar, un código permitido o datos de la salida de la consulta con valores válidos. No simula los datos. De los escenarios salen `pruebas/<Proyecto>/pruebas.http` y `escenarios.json`, y `probar.ps1` los ejecuta.

Gestión del arriendo:

| Escenario | Arriendo | Qué prueba |
|---|---|---|
| Principal hasta el cierre | ARR-0001 | Solicitud, riesgo aceptable, los dos eventos de Cobros (`junto_con`: el primero responde 202), confirmación con REG-01 activa, aviso por la política, entrega, devolución y cierre. |
| Riesgo alto | ARR-0002 | El cliente de prueba `CLI-RIESGO-ALTO` termina en "no realizado por riesgo alto". |
| Cancelación | ARR-0003 | Cancelar, y luego registrar el avance de un arriendo cancelado: 409 a propósito. |
| Confirmar sin riesgo evaluado | ARR-0004 | Confirmar sin evaluar el riesgo: 422 por REG-01, escrita a mano. |

Calificaciones:

| Escenario | Qué prueba |
|---|---|
| Calificaciones mutuas | Llega "Arriendo cerrado" (se recuerda); el cliente califica al propietario (`ARR-0001/Cliente`) y el propietario al cliente (`ARR-0001/Propietario`); el promedio del propietario es 5 con 1 calificación. |
| Promedio de varias | Otro arriendo del mismo propietario: el promedio de 5 y 2 es 3.5, con 2 calificaciones. |
| Calificar sin arriendo cerrado | No llegó "Arriendo cerrado" de ARR-0099: 409 a propósito (`requiere`). |
| Calificar dos veces | El cliente ya calificó ARR-0001: 409 a propósito (la identidad ya existe). |
| Sin calificaciones | Un propietario sin calificaciones: 0, y sin promedio. |

## Reproducibilidad y trazabilidad

- El mismo modelo y el mismo YAML dan los mismos archivos. Para comprobarlo: `.\.venv\Scripts\python.exe src\huella.py salida`, después de generar dos veces, o con dos carpetas para compararlas.
- Todo se ordena por nombre o por ID. Hay dos excepciones, porque ahí el orden tiene significado: los campos van en el orden del modelo, y los pasos de las pruebas en el orden del YAML.
- Sin fechas ni horas en lo generado. Todo en UTF-8 sin BOM y con fin de línea LF. `.gitattributes` (`* text=auto eol=lf`) hace que git entregue LF en todas las máquinas.
- Cada archivo generado empieza con `// Generado desde ArchiMate: <tipo> "<nombre>" (<código>, <ID>).`. En `.csproj` y `.sln` va en la segunda y en la tercera línea, porque su formato lo exige. Los `.json` y el `.csv` no admiten comentarios.
- `salida/trazabilidad/<Proyecto>.csv` tiene una fila por cada elemento o relación del contexto, con las columnas ID ArchiMate, tipo, nombre, archivo generado y clase. Para revisarlo: `.\.venv\Scripts\python.exe src\revisar_trazabilidad.py salida\intermedio\modelo-ddd.json salida`.
- El código generado compila con cero advertencias.

## Validaciones

Si una falla, el generador se detiene y dice cuál, con el nombre y el ID del elemento.

| Dónde | Qué revisa |
|---|---|
| `extraer.py` (modelo) | La regla del agregado. Cada objeto de valor tiene exactamente una composición desde su raíz o entidad, con Cardinalidad. Cada `Campo:` tiene un tipo permitido. No hay nombres repetidos dentro del mismo tipo entre los elementos del contexto. Cada comando tiene exactamente un acceso a la raíz de su agregado; además puede leer otras raíces del contexto, y escribir otra raíz es error. Cada evento lo dispara al menos un comando del contexto. Cada comando, consulta y servicio SA tiene un solo contrato. |
| `specs.py` (YAML) | Cada comando, evento, consulta y servicio SA del contexto está en el YAML, y el YAML no nombra nada que no exista. Hay claves conocidas y no repetidas, tipos permitidos y estados de la lista cerrada. Los eventos de cada comando son exactamente los del modelo. Se cumple la regla de los datos. Las políticas, `junto_con` y `con` están completos. La identidad es un consecutivo o se forma con datos que el comando que crea tiene; los `valores` son válidos; cada evento de `requiere` está declarado y el comando tiene su identidad; las correspondencias de `guarda` tienen el mismo tipo; un evento sin `dispara` lo requiere algún comando; las consultas sobre todas filtran por datos de su entrada y sus agregaciones tienen el tipo correcto. Los escenarios están bien escritos. |

## Discrepancias encontradas

| # | Qué | Dónde | Estado |
|---|---|---|---|
| 1 | SB-11 "Verificar los requisitos del cliente": el contrato de la V4 pide como entrada el cliente, la licencia y la autorización, pero la documentación del servicio en el modelo dice que revisa la ficha del cliente que guarda el arriendo. | Contrato SB-11 (V4) y servicio de aplicación SB-11 (V8). | **Cerrada sin cambios (D3, 4 nov 2026).** No es un error, sino un refinamiento entre niveles: la V4 dice qué se verifica, y la V6 decidió dónde viven esos datos (la ficha es la copia que guarda cada arriendo, V6-SUP-01). La consulta recibe solo el número del arriendo y lee la ficha de la raíz. |
| 2 | SA-02: la salida de su contrato no mencionaba la referencia del contrato firmado, aunque la raíz Arriendo la guarda con fuente SA-02 y V8-SUP-03 dice que SA-02 la entrega. | Contrato SA-02 (V4). | **Corregida en el modelo (D3, 4 nov 2026):** la salida del contrato incluye la referencia del contrato firmado, en Archi y en el README principal. |
| 3 | El mismo dato tiene nombres distintos entre contextos. Cobros dice "código de autorización de la pasarela" y Gestión del arriendo, "autorización del bloqueo del depósito". Operación dice "hora de entrega" y "hora de regreso", y Gestión del arriendo, "fecha y hora del cambio". Cobros guarda un "comprobante" por cobro. La Cuenta del arriendo no tiene la hora del cierre. | Campos de las raíces de la V6 y eventos entre dominios. | Abierta. Los eventos que llegan se declaran con los nombres de Gestión del arriendo (supuesto). Se alinean en G12 (D2). |
| 4 | La raíz Calificación no decía a quién se califica, pero SB-30 calcula el promedio de un cliente o de un propietario. | Raíz Calificación (V6). | **Corregida en el modelo (4 nov 2026):** campo `calificado` (string), en Archi y en el README principal. |
| 5 | Ningún campo unía un yate con su arriendo en Operación: la Lectura se identifica por el yate y el Acta de entrega por el arriendo. SB-27 revisa "las lecturas de un yate con arriendo en curso" y SB-26 devuelve el recorrido del yate arrendado. | Raíz Acta de entrega (V6), contrato SB-22 (V4). | **Corregida en el modelo (4 nov 2026):** campo `identificador del yate` (string) en el Acta de entrega, y la entrada del contrato SB-22 lo incluye. |

Si la ACLI de Archi escribe `IllegalArgumentException` al exportar, alguna caja tiene una fuente sin nombre (como `|9|1`). La exportación termina y valida igual, y solo se pierde esa fuente, que el generador no usa; se arregla en Archi dándole una fuente explícita. Así se arreglaron las 6 agrupaciones de área de la V2 (D8).

## Supuestos

GEN-SUP-01 se retiró: la tecnología (C# con API) es una decisión del equipo y no un supuesto (sección "Tecnología"). Su número no se reutiliza.

Del piloto:

| ID | Supuesto | Por qué |
|---|---|---|
| GEN-SUP-02 | Los datos se guardan en memoria y se pierden al reiniciar. | El piloto prueba la estructura y el flujo, no la persistencia. |
| GEN-SUP-03 | Los sistemas externos están simulados y responden con valores fijos del YAML. | Así el flujo es repetible y no depende de sistemas que no controlamos. |
| GEN-SUP-04 | El bus de eventos es síncrono y en memoria. Si un suscriptor falla, el error queda en la bitácora y no deshace el comando que publicó el evento. | El evento ya ocurrió; deshacerlo cambiaría el hecho que registra. |

Del YAML del piloto. Cada uno está marcado `# supuesto` en `specs/gestion-del-arriendo.yaml`:

| ID | Dónde | Supuesto |
|---|---|---|
| GEN-SUP-05 | raices > Arriendo > identidad | El número del arriendo es texto, como las demás referencias (V6-SUP-02). |
| GEN-SUP-06 | raices > Arriendo > identidad | Es un consecutivo predecible: ARR-0001, ARR-0002, ... |
| GEN-SUP-07 | raices > Arriendo > identidad | Tiene 4 dígitos. |
| GEN-SUP-08 | raices > Arriendo > estado | El enum se llama "Estado del arriendo"; los estados son los de la V6.1. |
| GEN-SUP-09 | Registrar la solicitud de reserva > entrada | En el piloto, quien llama envía la copia del yate (propietario), porque el Contexto Disponibilidad de yates todavía no se genera (V8-DEC-04). |
| GEN-SUP-10 | Registrar la solicitud de reserva > entrada | Igual para el precio por día. |
| GEN-SUP-11 | Registrar la solicitud de reserva > entrada | Igual para la marina. |
| GEN-SUP-12 | Obtener el nivel de riesgo del cliente > desde | Solo se evalúa un arriendo en "reserva solicitada"; el README no lista los estados. |
| GEN-SUP-13 | Confirmar la reserva > desde | Solo se confirma desde "reserva solicitada", por el orden del ciclo de vida de la V6.1. |
| GEN-SUP-14 | Cancelar la reserva > desde | Tampoco se cancela un arriendo cancelado o no realizado. Que no se cancela si ya empezó es de EXC-02. |
| GEN-SUP-15 | Cancelar la reserva > entrada | "Quién cancela" es texto; lo inicia el cliente (V6). |
| GEN-SUP-16 | Registrar el avance del arriendo > entrada | El enum se llama "Avance del arriendo"; sus valores son los avances de SB-09 en la V6.1. |
| GEN-SUP-17 | Registrar el avance del arriendo > Yate devuelto | Solo se devuelve desde "en curso", por el orden del ciclo de vida de la V6.1. |
| GEN-SUP-18 | eventos > Riesgo aceptable obtenido | Los "valores" que pide el contrato de SA-02 son el precio por día. |
| GEN-SUP-19 | eventos_de_otros_contextos | En un Partnership, los dos contextos acuerdan los datos del evento (V8-SUP-02); se revisan al generar el otro contexto. |
| GEN-SUP-20 | Alquiler y seguro cobrados > datos | El evento trae los dos comprobantes con su concepto en el nombre; en Cobros cada Cobro tiene un "comprobante". |
| GEN-SUP-21 | Depósito bloqueado > datos | El evento trae "autorización del bloqueo del depósito"; en Cobros es "código de autorización de la pasarela". |
| GEN-SUP-22 | Yate entregado al cliente > datos | El evento trae "fecha y hora del cambio"; en Operación es "hora de entrega". |
| GEN-SUP-23 | Inspección de devolución registrada > datos | El evento trae "fecha y hora del cambio"; en Operación es "hora de regreso". |
| GEN-SUP-24 | Cuenta del arriendo cerrada > datos | El evento trae la hora del cierre, aunque la Cuenta del arriendo no tiene ese campo. |
| GEN-SUP-25 | Clientes del CRM > respuesta_por_defecto | Valores de prueba (CRM-0001). |
| GEN-SUP-26 | Clientes del CRM > casos | `CLI-RIESGO-ALTO` es el cliente de prueba para el camino de riesgo alto de SB-12 (CRM-0002). |
| GEN-SUP-27 | Contratos con propietarios y clientes > entrada | El contrato del cliente se consulta por su arriendo. |
| GEN-SUP-28 | Contratos con propietarios y clientes > salida | El enum se llama "Estado del contrato". |
| GEN-SUP-29 | Contratos con propietarios y clientes > respuesta_por_defecto | Valores de prueba: contrato CON-0001, "firmado". |
| GEN-SUP-30 | Nivel de riesgo de la evaluadora > entrada | Los datos autorizados del cliente se identifican con su referencia al CRM. |
| GEN-SUP-31 | Nivel de riesgo de la evaluadora > respuesta_por_defecto | Valores de prueba: nivel "medio". |
| GEN-SUP-32 | Nivel de riesgo de la evaluadora > casos | El cliente de prueba (CRM-0002) sale con riesgo alto. |
| GEN-SUP-33 | Avisos y actas de las marinas > entrada | El aviso lleva también la marina a la que va. |
| GEN-SUP-34 | Avisos y actas de las marinas > respuesta_por_defecto | Valor de prueba: AVISO-RECIBIDO. |

Del generador, desde Calificaciones:

| ID | Supuesto | Por qué |
|---|---|---|
| GEN-SUP-35 | Los eventos de otros contextos que un comando requiere (`requiere`, D5) se guardan en memoria, por su nombre y su identidad, y se pierden al reiniciar; si llega otro igual, reemplaza al anterior. | Cada contexto guarda su propia copia de lo que recibe (V8-DEC-04), y el piloto no prueba la persistencia (GEN-SUP-02). |
| GEN-SUP-36 | Una identidad formada con datos une sus partes con `/`, en el orden del YAML; un enum va con su nombre de C# (por ejemplo `ARR-0001/Cliente`). | Es legible, es estable y no choca con los prefijos de los consecutivos. |

Del YAML de Calificaciones. Cada uno está marcado como supuesto en `specs/calificaciones.yaml`:

| ID | Dónde | Supuesto |
|---|---|---|
| GEN-SUP-37 | raices > Calificación > identidad | El dato se llama "identificador de la calificación". |
| GEN-SUP-38 | raices > Calificación > estado | Tiene un solo estado, "registrada", porque una calificación no cambia después (V6). |
| GEN-SUP-39 | Consultar calificaciones promedio > salida | Sin calificaciones no hay promedio: la "calificación promedio" es opcional (null). |
| GEN-SUP-40 | eventos_de_otros_contextos > Arriendo cerrado | Los datos llegan con los nombres que publica Gestión del arriendo (Partnership, V8-SUP-02; D2). |

## Limitaciones conocidas

- Un solo agregado por contexto (G2). Las entidades (G9) y los objetos de valor con Cardinalidad Muchos en `guarda` (G4) todavía no se generan; el generador se detiene con un mensaje claro si los encuentra.
- Un evento de otro contexto que dispara un comando debe llegar con la identidad de la raíz de este contexto; disparar con otra identidad se agrega con Disponibilidad de yates (G3). Un evento que solo se recuerda (`requiere`) sí puede llegar con otra.
- Las consultas sobre todas las raíces devuelven agregaciones; las listas (SB-04, SB-26) vienen después (G5).
- Los servicios SA se llaman antes de `ValidarReglas`, porque las reglas usan sus respuestas (REG-01 necesita el estado del contrato). Por eso una solicitud rechazada por una regla ya consultó al CRM simulado.
- Los eventos que un contexto publica llegan al bus entre contextos, pero nadie se suscribe todavía (G12). Mientras tanto, los eventos de otros contextos se prueban con sus endpoints.
- Si se quita el YAML de un contexto, el generador borra sus archivos generados pero no su código a mano: avisa que esa carpeta quedó suelta.
