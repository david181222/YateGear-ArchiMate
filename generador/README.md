# Generador de código desde el modelo ArchiMate

Este generador construye la primera versión de la aplicación de YateGear a partir del modelo de Archi (`../modelo/YateGear.archimate`) y de un archivo de especificaciones por contexto (`specs/*.yaml`). Es determinista: no usa IA ni red, y el mismo modelo con el mismo YAML da siempre los mismos archivos.

Genera un proyecto por cada contexto que tiene YAML en `specs/`, y los levanta todos en un solo programa (D1), comunicados por el bus entre contextos (G12). Hoy tienen YAML los cinco contextos del modelo, y `specs/entre-contextos.yaml` tiene los escenarios de punta a punta entre ellos (S4). Lo que falta, las decisiones y el reparto del trabajo están en [PENDIENTES.md](PENDIENTES.md).

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

`probar.ps1` compila y, para cada contexto (`salida/pruebas/<Proyecto>/escenarios.json`) y después para los escenarios entre contextos (`salida/pruebas/EntreContextos/escenarios.json`), levanta la aplicación, ejecuta sus escenarios y la detiene; termina con código 1 si algún paso falla. Con `-Contexto "<nombre del contexto o del proyecto>"` prueba solo ese, y con `-Contexto "entre contextos"`, solo los de punta a punta.

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
| Raíz, entidad y objeto de valor | Objeto de datos con `Tipo DDD`. La raíz compone a sus entidades y objetos de valor, y cada composición tiene `Cardinalidad`. La identidad de una entidad (uno de sus campos) se declara en el YAML. |
| Campos | Propiedades `Campo: <nombre>` con su tipo, en el orden del modelo. |
| Acceso | Acceso comando --> raíz. En el `.archimate`, un acceso sin atributo es escritura. |
| Eventos | Disparo comando --> evento de aplicación. |
| Política | Disparo evento --> comando, los dos del contexto. |
| Contrato | Comando o consulta --> realiza --> servicio de negocio con el mismo código --> asociación --> contrato. Su texto se separa en Entrada, Salida y Reglas. |

## Formato del YAML

Cada contexto que se quiere generar tiene un `specs/<contexto>.yaml`. El modelo dice qué elementos hay y cómo se relacionan; el YAML declara lo que el modelo no dice y el generador necesita. Las claves son los nombres exactos del modelo, y `specs.py` revisa cada una: si falta un elemento del contexto, se nombra uno que no existe o una clave no se conoce, el generador se detiene. Todo dato que no sale de la documentación lleva el comentario `# supuesto`.

**Tipos** (los mismos de los campos del modelo, V6-DEC-17): `string`, `int`, `decimal`, `bool`, `DateOnly`, `DateTime`, `List<tipo>`, el sufijo `?` para un dato opcional y `enum <Nombre>(valor, valor, ...)`. Además, en el YAML, `List<objeto de valor>`: una lista de un objeto de valor del contexto (por ejemplo `List<Daño encontrado>`), cuyos elementos se escriben `{campo: valor, ...}`. Las fechas de ejemplo van entre comillas.

**Regla de los datos:** un dato pasa de un lugar a otro por su nombre (ver "Reglas del generador"). Cuando un dato debe ir a un campo que se llama distinto, se declara con una correspondencia (`guarda: [{campo: dato}]`).

| Sección y clave | Qué declara | Ejemplo |
|---|---|---|
| `contexto` | Nombre exacto del componente de aplicación del contexto. | `Contexto Calificaciones` |
| `raices > <raíz> > identidad` | Una raíz por agregado del contexto. `nombre` y `tipo` (string) de la identidad, y cómo se forma: un consecutivo con `prefijo` y `digitos`, o con datos, en orden, con `de`. En `de`, un campo de la raíz va sin tipo; un dato que no es campo lleva su tipo, y la raíz lo guarda como parte de su identidad. Las partes se unen con `/`; una parte puede ser `string`, `int`, `enum`, `DateOnly` o `DateTime` (las fechas, en formato fijo: `2026-03-10T10:00:00`). Con un solo dato que se llama como la identidad, la identidad es **recibida**: la trae el comando o el evento. | `prefijo: ARR-` y `digitos: 4`; `de: {número del arriendo: string, quién califica: }`; o `de: {identificador del yate: string}` |
| `raices > <raíz> > estado` | Los estados de la raíz, como `enum`. | `enum Estado del arriendo(reserva solicitada, ...)` |
| `raices > <raíz> > entidades > <entidad> > identidad` | G9: el campo de la entidad que es su identidad dentro de la raíz (string o int). Cada entidad del agregado lleva la suya. La raíz no admite dos con la misma (409). | `Cobro: {identidad: comprobante}` |
| `comandos > <comando> > entrada` | Datos que recibe. La identidad de la raíz se agrega sola, salvo en el que la crea. | `cliente: string` |
| `... > crea` | `true` si el comando crea la raíz: lleva `a` (estado inicial) y no lleva `desde` ni `resultados`; si la identidad es recibida, la trae en su entrada. `si_no_existe` si carga la raíz y, cuando no existe, la crea vacía con la identidad del comando y el primer estado de su lista (solo con identidad recibida, y si la raíz no tiene campos obligatorios). | `crea: true`; `crea: si_no_existe` |
| `... > valores` | Datos fijos del comando, para campos de la raíz o de sus objetos de valor. | `quién califica: cliente` |
| `... > requiere` | Eventos de otros contextos que deben haber llegado para la identidad del comando (se buscan con el dato que es su identidad). Si no, 409. Sus datos quedan disponibles para el comando y, si el evento solo se recuerda, también los de sus `correspondencias`. | `[Arriendo cerrado]`; `[Yate registrado]` |
| `... > usa` | Servicios SA que llama, en orden. Sus salidas quedan disponibles. Cada llamada puede ser `{SA: {con, entrada, salida, si, salvo}}`: `con` fija datos de la entrada del SA, `entrada` los toma de un dato con otro nombre (`{dato del SA: dato del comando}`), `salida` renombra lo que devuelve (`{dato del SA: nombre nuevo}`) y `si` o `salvo` la hacen solo si se cumple la condición (si no, su salida queda en null). Así un comando llama varias veces al mismo SA. Un dato opcional de la entrada del SA que el comando no tiene va en null. | `[Clientes del CRM]`; `- Cobros por la pasarela de pagos: {con: {tipo de orden: alquiler}, entrada: {valor: valor del alquiler}, salida: {comprobante: comprobante del alquiler}}` |
| `... > calculados` | Datos que salen de una regla y se escriben a mano, cada uno con su `tipo` y los datos de los que sale (`de`: datos por su nombre o una raíz que el comando tiene). Se calculan en cuanto están sus datos: antes de llamar a los SA, o después del SA que da el último. Quedan disponibles por su nombre para los SA que siguen, las condiciones, `guarda` y los eventos, y llegan a `ValidarReglas` en `datos`. | `valor del alquiler: {tipo: decimal, de: [días, precio por día]}` |
| `... > guarda` | Lo que escribe en la raíz: objetos de valor y campos por su nombre, o `{campo: dato}` para guardar un dato con otro nombre. En un objeto de valor o una entidad con Cardinalidad Muchos (una lista): `{lista: agregar}`, `{lista: {agregar: {campo: dato}, valores: {campo: valor}, si, salvo}}` (un elemento con datos de otro nombre, valores fijos y, si se pide, solo si se cumple la condición; puede repetirse), `{lista: {reemplazar: [claves]}}` (404 si ningún elemento tiene esa clave) o `{lista: {quitar: [claves]}}` (no falla si no había ninguno) o `{lista: {todos: dato}}` (la lista entera, con un dato `List<objeto de valor>`). Un campo de lista que el comando no tiene queda vacío. | `[Fechas del arriendo, calificado: propietario]`; `[Rango de fechas: {quitar: [número del arriendo]}]`; `- Cobro: {agregar: {valor: valor del seguro}, valores: {concepto: seguro}}` |
| `... > desde`, `a` | Estados desde los que se permite, y estado al que pasa. | `desde: [reserva solicitada]` |
| `... > sobre: todas`, `temporizador` | Un comando que revisa todas las raíces de su tipo: no escribe ni tiene identidad; el archivo manual elige las raíces (`Seleccionar`) y se publica un evento por cada una, con sus datos. `temporizador: {cada minutos, con, ahora}` lo corre solo cada N minutos, con los valores de `con` y la hora actual en el dato de `ahora`; su endpoint fuerza la revisión con un "ahora" fijo (D6). | `temporizador: {cada minutos: 5, con: {minutos sin lecturas: 30}, ahora: ahora}` |
| `... > eventos` | Los eventos que publica: exactamente los del modelo. | `[Reserva confirmada]` |
| `... > resultados` | En lugar de `eventos`: un evento por resultado, elegido con `si` (un dato y sus valores), con su propio `desde`, `a`, `valores` y `guarda`. | `Arriendo iniciado: {si: {nuevo estado: [en curso]}, a: en curso}` |
| `eventos > <evento> > datos`, `calculados` | Datos que lleva cada evento. Los `calculados` salen de una regla del contrato y los escribe el código a mano. | `inicio: DateOnly` |
| `consultas > <consulta> > entrada`, `salida`, `calculados` | Datos que recibe y devuelve. Por defecto lee una raíz (la que lee en el modelo) por su identidad. | `estado: enum ...` |
| `... > de` (sin `sobre`) | G5: una consulta por identidad que lee varias raíces dice con `de` por la identidad de cuál consulta. Las demás se cargan con la misma identidad (deben tener el mismo nombre de identidad) y pueden no existir: sus datos llegan opcionales y en `datos`, con `null` si no existe. | `de: Cuenta del arriendo` (SB-18 lee también el depósito) |
| `... > sobre: todas`, `de`, `filtro`, `filtro_manual`, `agrega`, `lista` | Consulta sobre todas las raíces (si lee varias, `de` dice cuál recorre; las demás le llegan en `datos`). `filtro` las compara por igualdad con datos de la entrada del mismo nombre, y `filtro_manual: true` agrega un filtro escrito a mano (`Incluir`, en el archivo manual). Con `agrega`, cada dato de la salida es una agregación: `conteo`, o `promedio`, `suma`, `mínimo` o `máximo` `de <dato de la raíz>` (sin raíces no hay promedio, mínimo ni máximo: esos van con `?`). Sin `agrega`, devuelve una lista llamada `lista`, con los datos de la salida de cada raíz, ordenada por los datos de `orden` (de menor a mayor). | `calificación promedio: promedio de calificación dada`; `lista: yates disponibles`; `orden: [hora de la lectura]` |
| `eventos_de_otros_contextos > <evento>` | `de` (contexto que lo publica), `datos` (con los nombres del contexto que lo publica, D2), e `identidad` si llega con un dato distinto de la identidad de la raíz (obligatoria si el contexto tiene varias raíces y el evento no dispara). Con `dispara`, ejecuta ese comando; si llega con otra identidad, la de la raíz debe venir en sus `datos`, por su nombre, y la del evento queda disponible para el comando. `con` fija valores de su entrada, `correspondencias` toma un dato del evento con otro nombre (`{dato de la entrada: dato del evento}`; con `junto_con` valen para todo el grupo) y `junto_con` espera a otros eventos. `dispara` también puede ser una lista de comandos o `{comando: {con, correspondencias, si, salvo, si_existe}}`: los corre en orden y si uno falla los siguientes no corren. Con `si_existe: true`, el comando corre solo si su raíz ya existe; si no, el evento no le aplica y no es un error (en Cobros, una reserva cancelada antes del contrato firmado). Sin `dispara`, solo se recuerda para los comandos que lo `requiere`n, y sus `correspondencias` valen para ellos (Gestión del arriendo toma `marina` de `identificador de la marina` en "Yate registrado"). Llega por el bus entre contextos (G12) y por su endpoint de prueba. | `Arriendo cerrado: {de: ..., identidad: número del arriendo}`; `correspondencias: {fecha y hora del cambio: hora de entrega}` |
| `politicas > <comando>` | G10 y D7: cómo disparan las políticas internas del modelo (evento --> comando del mismo contexto). Sin entrada, cada evento dispara el comando por su cuenta. Con `si` o `salvo`, solo si se cumple la condición sobre los datos del evento; con `con` y `correspondencias`, como en un evento de otro contexto. Con varios disparos: `junto_con` (deben llegar todos) y `uno_de` (y además uno de estos, cada uno con su `con`), que nombran, sin repetir, todos los eventos que disparan el comando en el modelo; el comando corre cuando llegan, para la misma identidad. Un comando que crea la raíz también puede dispararse por una política. | `Cerrar las cuentas del arriendo: {junto_con: [Cargos del cierre cobrados], uno_de: {Depósito liberado: {con: ...}, ...}}`; `Reclamar ...: {salvo: {valor que excede el depósito: [0]}}` |
| `servicios_sa > <servicio>` | Si YateGear lo llama: `entrada`, `salida`, `respuesta_por_defecto` y `casos` (con `si`) del sistema externo simulado, todo fijo (sin azar ni fecha de hoy); el modelo debe tener un flujo que entra (la respuesta). Si el sistema externo le envía datos a YateGear (G7): `recibe`, con los mensajes que llegan, cada uno con `dispara` (uno o varios comandos, como un evento de otro contexto), `datos`, `con` y `correspondencias`, y pueden crear la raíz. Si YateGear solo le envía datos, sin esperar respuesta (G11, lenguaje publicado): `envia`, con los mensajes que salen, cada uno con `cuando` (el evento del contexto que lo dispara) y `datos` (del evento, por su nombre). Un SA puede tener varias partes; con `recibe`, el modelo debe tener un flujo que entra por su interfaz, y con `envia`, uno que sale. | `respuesta_por_defecto: {nivel: medio}`; `recibe: {Lectura del proveedor: {dispara: ..., datos: ...}}`; `envia: {Arriendo cerrado para Finanzas: {cuando: Cuenta del arriendo cerrada, datos: ...}}` |
| `escenarios > <escenario>` | Lista de pasos (comando, consulta o evento de otro contexto), cada uno con `con` y `espera` (ver "Escenarios y pruebas"). | `- Cancelar la reserva: {espera: Reserva cancelada}` |
| `escenarios_entre_contextos` (en su propio YAML) | S4: escenarios de punta a punta. Un YAML con solo esta clave (`specs/entre-contextos.yaml`) no especifica un contexto: cada paso dice en qué contexto corre (`en`). Ver "Escenarios entre contextos". | `- Contrato del cliente firmado: {en: Contexto Cobros y depósito, espera: [Depósito bloqueado, Reserva confirmada]}` |

Cada YAML empieza con un comentario que explica sus secciones; `specs/gestion-del-arriendo.yaml` y `specs/calificaciones.yaml` sirven de ejemplo, y `specs/cobros-y-deposito.yaml` usa casi todas las claves.

## Qué genera cada elemento del modelo

| Elemento del modelo | Qué genera en `salida/` |
|---|---|
| Contexto (con YAML) | Un proyecto biblioteca, `<Proyecto>/<Proyecto>.csproj`, con `Registro.g.cs` (servicios, políticas y endpoints), su referencia en el host y su entrada en la `.sln`. El nombre del proyecto sale del contexto sin "Contexto ": "Contexto Gestión del arriendo" --> `GestionDelArriendo`. |
| Modelo | La solución `<Modelo>.sln`, el host `<Modelo>/` (un solo programa que registra todos los contextos, con un solo puerto) y `contextos.json`, que dice a los scripts qué hay. |
| Agregado y raíz | Clase parcial con su identidad, su `Estado` (enum) y sus campos, y una propiedad por composición: Uno --> `T`, Cero o uno --> `T?`, Muchos --> `List<T>`. Si la identidad se forma con datos que no son campos, también una propiedad por cada uno. |
| Objeto de valor | `sealed record` con sus campos. |
| Entidad (G9) | `sealed record` con sus campos que implementa `IEntidad` con su identidad. La raíz la guarda en una lista y `Entidades.Agregar` responde 409 si ya hay una con la misma identidad. |
| Tipos `enum` (del modelo o del YAML) | `enum` de C#. En JSON viaja como texto, por ejemplo `"Medio"` o `"EnCurso"`. |
| Comando sobre todas (G8) | El manejador recorre todas las raíces (y las demás que lee), y el archivo manual trae `Seleccionar`. Con `temporizador`, además, una clase `BackgroundService` que lo corre cada N minutos (`AddHostedService`). |
| Comando | El record del comando, un manejador parcial (`.g.cs`), un endpoint `POST /<contexto>/comandos/<comando>` (por ejemplo `/gestion-del-arriendo/comandos/confirmar-la-reserva`) y un archivo manual (`.cs`). |
| Contrato | Comentarios XML en el manejador (entrada, salida y reglas). Sus reglas aparecen además como comentario en `ValidarReglas`, en el archivo manual. |
| Evento | Record del evento, con la identidad y sus datos. |
| Política | Una suscripción en el bus de eventos, en `Politicas.g.cs`; con `si` o `salvo`, dentro de un `if`. Con varios disparos (G10), un método por comando que anota cada evento en `EsperaDeEventos` y corre el comando cuando llegaron los de `junto_con` y uno de `uno_de`. |
| Consulta | Records de entrada y salida, un manejador, un endpoint `GET /<contexto>/consultas/<consulta>/{identidad}` y un archivo manual. Con `sobre: todas`, el endpoint no lleva identidad (`GET /<contexto>/consultas/<consulta>?dato=valor`) y el manejador recorre las raíces que cumplen el filtro. |
| Servicio SA | Si YateGear lo llama: interfaz, records de entrada y salida, y una implementación simulada que responde con los valores del YAML. Si recibe (G7): un receptor con un record y un método por mensaje (lee el JSON, revisa los datos obligatorios y dispara el comando o los comandos), y un endpoint `POST /<contexto>/sa/<servicio>/<mensaje>`. Si envía (G11): `Anticorrupcion/EmisorDe<SA>.g.cs`, con un record por mensaje, la interfaz `IEmisorDe<SA>` y un emisor simulado que anota cada envío en la bitácora ("envío por servicio SA"); la suscripción al evento que lo dispara va en `Politicas.g.cs`. |
| Interfaz, contraparte y flujos | Comentarios en el servicio SA y filas en la trazabilidad del contexto. |
| Evento de otro contexto (del YAML) | Record del evento, un método en `ReceptorDeEventosExternos` que lo lee desde JSON y revisa sus datos obligatorios, una suscripción en el bus entre contextos (G12, en `Registro.g.cs`) y un endpoint `POST /<contexto>/eventos-externos/<evento>` para las pruebas. Si un comando lo requiere, se guarda en `MemoriaDeEventos`; sin `dispara`, solo se guarda. |

Además se generan, por contexto, `pruebas/<Proyecto>/pruebas.http` y `pruebas/<Proyecto>/escenarios.json` (desde los escenarios del YAML) y `trazabilidad/<Proyecto>.csv`; para toda la solución, `global.json`, el proyecto `Integracion` (bus entre contextos) y la infraestructura de cada contexto; y, si hay escenarios entre contextos, `pruebas/EntreContextos/pruebas.http` y `escenarios.json`.

### Comunicación entre contextos (D1)

Todos los contextos corren en un solo programa. Cada uno publica sus eventos en su bus y, además, en el **bus entre contextos** (`Integracion/BusEntreContextos.g.cs`), por su nombre en el modelo y en JSON. Ningún proyecto de contexto referencia a otro: solo el host los conoce a todos, y cada contexto lee los eventos que le llegan con sus propios records de `EventosExternos`.

Un evento de otro contexto, venga por su endpoint de prueba o por el bus, se lee con `LectorDeEventos`: si le falta un dato obligatorio (o llega en `null`), responde 422 con "Falta el dato ..." y el nombre del dato en el modelo. Así se nota de inmediato si el contexto que publica lo llama distinto (D2).

Cada contexto se suscribe en el bus a los eventos de su sección `eventos_de_otros_contextos`, por el nombre del contexto que lo publica y el nombre del evento (G12): un evento publicado en un contexto dispara el comando del otro sin pasos a mano. El receptor lee los datos con los nombres del contexto que publica (D2) y, si quien recibe llama a la identidad de otra forma, el bus se la pone también con su nombre. Un evento se entrega primero a los demás contextos y después a las políticas del contexto que lo publica. Si el receptor falla (le falta un dato, la raíz no existe o una regla lo rechaza), el error queda en el bus y no deshace el comando que publicó el evento (GEN-SUP-04).

`GET /eventos-entre-contextos` muestra los eventos que pasaron por el bus y los errores de sus suscriptores; `GET /contextos`, los contextos que levantó el programa.

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

1. Revisar que llegue la identidad (422 si falta) y cargar la raíz (404 si no existe). Con `crea: si_no_existe`, si no existe se arma vacía, y se guarda recién en el paso 6. El comando que crea la raíz la arma en el paso 6.
2. Revisar que el estado actual esté en su `desde` (409 si no). Se revisa antes de llamar a los SA, para que una raíz en un estado inválido no consulte a sistemas externos.
3. Buscar los eventos de otros contextos de `requiere` por su identidad (409 si alguno no ha llegado), cargar las otras raíces que el comando lee en el modelo por el dato con el nombre de su identidad (404 si no existen, G6) y llamar a los servicios SA de `usa`, en orden (una llamada con `si` o `salvo`, solo si se cumple). Los `calculados` del comando se calculan, a mano, en cuanto están sus datos: antes de la primera llamada o después de la que da el último.
4. Elegir el resultado con la condición `si`, y revisar el `desde` de ese resultado (409).
5. `ValidarReglas`, en el archivo manual (422 si se incumple una regla).
6. Escribir lo de `guarda` y el nuevo estado (`a`), y guardar la raíz. Si la identidad es un consecutivo, el repositorio se lo asigna al guardar una raíz nueva (ARR-0001, ARR-0002, ...), así que una solicitud rechazada no gasta número. Si se forma con datos, la raíz nueva se agrega con ella, y responde 409 si ya existe.
7. Publicar los eventos.

### Capas

| Capa | Qué hace |
|---|---|
| 1. Estructura | Todo lo de la tabla anterior: compila, corre y recorre el flujo. |
| 2. Transiciones | `desde` y `a` del YAML: 409 si el estado no lo permite, y cambio de estado al guardar. |
| 3. Eventos de otros contextos | Suscripción en el bus entre contextos (G12) y endpoint de prueba por evento. Con `junto_con`, los eventos que ya llegaron se guardan en memoria por número del arriendo; mientras falte alguno la respuesta es 202, y cuando llega el último se dispara el comando con los datos de todos. |

### Qué borra el generador

El generador recuerda lo que escribió en la generación anterior (`salida/intermedio/archivos-generados.txt`, que se versiona) y borra lo que ya no genera: por ejemplo, los archivos de un comando que se quitó del modelo, o los de un contexto cuyo YAML se quitó (o que se dejó fuera con `-Specs`). También borra los `.g.cs` sueltos en las carpetas de los proyectos. Nunca borra un archivo manual: si queda sin su `.g.cs`, o en la carpeta de un contexto que ya no se genera, avisa al final ("AVISO manual huérfano" o "AVISO ... tiene código a mano de un contexto que ya no se genera"). Qué hacer con el aviso: rescatar del archivo lo que sirva (por ejemplo, una regla escrita a mano) y borrarlo a mano, o volver a poner el elemento en el modelo o el YAML.

### Archivos manuales

Cada comando y cada consulta tiene un archivo `.cs` que el generador crea **una sola vez** y nunca sobrescribe. Trae:
- `ValidarReglas`, vacío, con el texto de cada regla de su contrato como comentario;
- un valor provisional para cada dato calculado, marcado `PENDIENTE` y con la regla de la que sale.

El código generado va en los `.g.cs`, que el generador sí reescribe. Ejemplo: REG-01 está escrita a mano en `salida/GestionDelArriendo/Comandos/ConfirmarLaReserva.cs` y sobrevive a la regeneración.

Si un manual queda sin su `.g.cs` (por ejemplo, porque se quitó un comando), el generador no lo borra: avisa al final y lo saca de la compilación en el `.csproj`, con un comentario que dice cuál es y por qué. Los `.g.cs` que ya no corresponden sí se borran.

### Bitácora

`GET /<contexto>/bitacora` (por ejemplo `/gestion-del-arriendo/bitacora`) muestra en orden los eventos publicados, los eventos recibidos de otros contextos, las llamadas a los servicios SA simulados y los errores de las políticas. Es **infraestructura del piloto y no sale del modelo**: sirve para ver el flujo y la usa `probar.ps1`. También son infraestructura el repositorio en memoria, el bus de eventos y la espera de eventos.

## Escenarios y pruebas

La sección `escenarios` del YAML define pruebas de punta a punta. Un paso es un comando, una consulta, un evento de otro contexto o un mensaje que recibe un SA. `con` fija valores de su entrada, y `espera` dice el resultado: un evento, un código HTTP (409, 422, 404 o 202), un rechazo con su motivo (`{código: 422, regla: REG-02}`; los campos que se pueden afirmar son `regla`, `requiere`, `identidad`, `operación` y `estado actual`, los de la respuesta de error) o, en una consulta, `{dato de la salida: valor, ...}` (en una lista, cuántos elementos tiene). Sin `espera`, el paso debe responder 2xx. Conviene afirmar el motivo de cada rechazo a propósito: dos rechazos distintos pueden tener el mismo código (en Calificaciones, los dos 409).

Cada paso tiene su identidad. Un comando que crea la raíz recibe la siguiente (el consecutivo, que una solicitud rechazada no gasta, o la que se forma con sus datos), y se revisa que la respuesta la traiga; los demás pasos la toman de `con` o, si no, de la última identidad con el mismo nombre de dato en el escenario (regla de los datos: el calendario de un yate tiene la identidad del yate). Un evento de otro contexto que llega con su propia identidad la toma de `con`. Los consecutivos siguen de un escenario al siguiente, en orden, porque todos corren contra la misma aplicación. Por eso **los escenarios dependen de su orden**: "Calificar dos veces" responde 409 porque "Calificaciones mutuas" corrió antes. Reordenarlos o correr uno solo puede cambiar sus resultados. El generador avisa (sin detenerse) cuando un paso crea una identidad que ya creó otro paso anterior sin esperar el 409, o usa una raíz que ningún paso anterior creó sin esperar el 404.

`specs.py` revisa que los escenarios estén bien escritos: que los nombres existan, que los valores de `con` sean válidos y que `espera` sea un evento que ese paso puede publicar, un código permitido o datos de la salida de la consulta con valores válidos (una lista, por cuántos elementos tiene). No simula los datos. De los escenarios salen `pruebas/<Proyecto>/pruebas.http` y `escenarios.json`, y `probar.ps1` los ejecuta.

`probar.ps1` prueba cada contexto, y después los escenarios entre contextos, con la aplicación recién levantada: con la integración (G12) un evento de un contexto llega a los demás, y así los escenarios de uno no cambian los de otro. Los eventos que un contexto publica en sus propios escenarios también llegan a los demás contextos; ahí pueden fallar (por ejemplo, porque el arriendo no existe en Gestión del arriendo), y ese error queda en el bus sin cambiar el resultado del paso. En los escenarios entre contextos, en cambio, un error en el bus hace fallar el paso (ver abajo).

Gestión del arriendo:

| Escenario | Arriendo | Qué prueba |
|---|---|---|
| Principal hasta el cierre | ARR-0001 | Llega "Yate registrado" (se recuerda la copia del yate); solicitud con esa copia, riesgo aceptable, los dos eventos de Cobros (`junto_con`: el primero responde 202), confirmación con REG-01 activa, aviso por la política, entrega, devolución y cierre. |
| Riesgo alto | ARR-0002 | El cliente de prueba `CLI-RIESGO-ALTO` termina en "no realizado por riesgo alto". |
| Cancelación | ARR-0003 | Cancelar, y luego registrar el avance de un arriendo cancelado: 409 a propósito. |
| Confirmar sin riesgo evaluado | ARR-0004 | Confirmar sin evaluar el riesgo: 422 por REG-01, escrita a mano. |
| Yate fuera del inventario | - | Una solicitud para un yate del que no llegó "Yate registrado": 409 a propósito (`requiere`), sin gastar consecutivo. |

Calificaciones:

| Escenario | Qué prueba |
|---|---|
| Calificaciones mutuas | Llega "Arriendo cerrado" (se recuerda); el cliente califica al propietario (`ARR-0001/Cliente`) y el propietario al cliente (`ARR-0001/Propietario`); el promedio del propietario es 5 con 1 calificación. |
| Promedio de varias | Otro arriendo del mismo propietario: el promedio de 5 y 2 es 3.5, con 2 calificaciones. |
| Calificar sin arriendo cerrado | No llegó "Arriendo cerrado" de ARR-0099: 409 a propósito (`requiere`). |
| Calificar dos veces | El cliente ya calificó ARR-0001: 409 a propósito (la identidad ya existe). |
| Sin calificaciones | Un propietario sin calificaciones: 0, y sin promedio. |

Disponibilidad de yates:

| Escenario | Qué prueba |
|---|---|
| Registro y ocupación | Se registra YATE-0001; bloquear fechas crea su calendario (`si_no_existe`); "Reserva solicitada" (llega con el número del arriendo y trae el yate) aparta y "Reserva confirmada" ocupa; la consulta lo excluye en esas fechas y lo incluye en otras; bloquear fechas ocupadas da 422 (REG-02) y apartar fechas de otro arriendo, 422 (REG-01); "Reserva cancelada" suelta y el yate vuelve a estar disponible; desbloquear. |
| Registro rechazado | Sin contrato firmado (INT-CON) y con los documentos vencidos (NOR-01): 422 a propósito, sin gastar consecutivo. |
| Otra marina | YATE-0002 en otra marina; confirmar fechas que nunca se apartaron da 404 (`reemplazar`); "Arriendo no realizado por riesgo alto" suelta las fechas. |

Operación del arriendo:

| Escenario | Qué prueba |
|---|---|
| Entrega, seguimiento y devolución | Llega "Reserva confirmada" (se recuerda); la marina envía el acta de entrega por SA-05; el proveedor, dos lecturas por SA-07 (identidad `YATE-0001/2026-03-10T10:00:00`); el recorrido tiene 2 lecturas; la revisión de la señal no avisa a los 20 minutos y avisa a la hora; la inspección con un daño dispara SB-24 por la política; después el recorrido da 422, porque el arriendo ya no está en curso. |
| Actas rechazadas | Sin reserva confirmada (409, `requiere`), un acta repetida (409), un acta sin fotos (422, H-13), y SB-24 sin acta de entrega (404, G6). |

Los valores calculados de "Diferencias determinadas" (combustible consumido, horas adicionales y valor de los daños) se comprobaron a mano en la bitácora, y el temporizador se probó corriendo cada minuto.

Cobros y depósito (los eventos de Gestión del arriendo y de Operación del arriendo llegan por sus endpoints de prueba):

| Escenario | Arriendo | Qué prueba |
|---|---|---|
| Reserva pagada y cierre sin daños | ARR-0001 | El contrato firmado (SA-02) bloquea el depósito y cobra el alquiler (3 días a 500) y el seguro: dos cobros. "Diferencias determinadas" sin daños cobra el combustible y 15 horas adicionales, libera el depósito (`si`) y, con los cargos y la decisión sobre el depósito (`junto_con` y `uno_de`), cierra la cuenta: 4 movimientos, cada uno con la fecha de la orden que confirmó la pasarela, comisión 300 y 1200 para el propietario. |
| Daños mayores que el depósito | ARR-0002 | Daños por 1500 con un depósito de 1000: se descuenta todo (`salvo`), el excedente de 500 se reclama a la aseguradora (la política con `salvo`) y la cuenta se cierra; sin horas adicionales no hay cobro del tiempo adicional (la llamada con `si`). |
| Cancelación con anticipación | ARR-0003 | "Reserva cancelada" 9 días antes (el contrato pide 7): se libera el depósito y se reembolsa el alquiler; la cuenta queda cerrada con 3 movimientos. |
| Cancelación tardía | ARR-0004 | 2 días antes: "Cancelación no reembolsada". |
| Cancelación antes del pago | ARR-0008 | Una reserva cancelada sin contrato firmado: no hay depósito ni cuenta, así que no se libera ni se devuelve nada (`si_existe`), y responde 2xx. |
| Cobros rechazados | ARR-0005 a 0007 | La pasarela rechaza la tarjeta: 422 (INT-PAG). El bloqueo vencería antes del cierre: 422 (V4-SUP-07). El depósito de ARR-0001 ya existe: 409. Cerrar las cuentas sin cargos del cierre: 422 (E2E-01). Cargos sin evidencia: 422 (V1). Una cuenta que no existe: 404. |

### Escenarios entre contextos

`specs/entre-contextos.yaml` tiene escenarios de punta a punta (S4). Cada paso es un comando, una consulta o un mensaje de un SA del contexto que dice `en`; los eventos entre contextos no se envían a mano: llegan por el bus (G12). `con` fija datos de su entrada, y un dato que no está en `con` y se llama como una identidad ya creada en el escenario toma su valor (regla de los datos): así el yate YATE-0001 y el arriendo ARR-0001 pasan de un contexto a otro. `espera` es un evento o una lista de eventos de cualquier contexto, y de mensajes que envía un SA (G11), que deben ocurrir durante el paso (se buscan en `GET /eventos-entre-contextos` y en la bitácora del contexto que envía). Un paso falla también si durante él falla un suscriptor del bus (los `errores` de `GET /eventos-entre-contextos`), y `probar.py` dice al final cuántos hubo; o un código, o datos de una consulta. `specs.py` revisa el archivo contra los YAML de los contextos de la misma carpeta, y de él salen `pruebas/EntreContextos/pruebas.http` y `escenarios.json`.

| Escenario | Qué prueba |
|---|---|
| Del inventario al envío a Finanzas | Se registra el yate (Gestión del arriendo recuerda su copia) y está disponible; la solicitud aparta las fechas; con el riesgo aceptable, SA-02 envía los datos para el contrato; el contrato firmado bloquea el depósito y cobra, Gestión del arriendo confirma, Disponibilidad ocupa las fechas y sale el aviso a la marina; la marina entrega el yate y Gestión inicia el arriendo; llega una lectura y el recorrido la muestra; una hora sin lecturas, Operación avisa la pérdida de señal y SA-05 envía la alerta a la marina; la inspección con daños dispara la devolución, las diferencias, los cargos del cierre, el descuento del depósito, el reclamo a la aseguradora, el cierre de las cuentas, el arriendo cerrado y el envío a Finanzas (SA-08); el arriendo queda cerrado y el cliente califica al propietario. |
| Cancelación con reembolso | Otro arriendo del mismo yate se paga y se cancela 9 días antes: Disponibilidad suelta las fechas y Cobros libera el depósito y devuelve el alquiler. |
| Riesgo alto | El cliente de prueba de riesgo alto: no se arrienda y las fechas se sueltan. |
| Cancelación antes del pago | Una solicitud se cancela antes del contrato firmado: Disponibilidad suelta las fechas, y en Cobros no aplica (`si_existe`), sin errores en el bus. |

Entre los cuatro pasan los 11 eventos entre dominios de la V6 (Reserva solicitada, confirmada y cancelada, Arriendo no realizado por riesgo alto, Riesgo aceptable obtenido, Alquiler y seguro cobrados, Depósito bloqueado, Yate entregado al cliente, Inspección de devolución registrada, Diferencias determinadas y Cuenta del arriendo cerrada), además de "Arriendo cerrado" hacia Calificaciones y "Yate registrado" hacia Gestión del arriendo. En la prueba no queda ningún error en el bus, y `probar.py` lo comprueba.

## Reproducibilidad y trazabilidad

- El mismo modelo y el mismo YAML dan los mismos archivos. Para comprobarlo: `.\.venv\Scripts\python.exe src\huella.py salida`, después de generar dos veces, o con dos carpetas para compararlas.
- Todo se ordena por nombre o por ID. Hay dos excepciones, porque ahí el orden tiene significado: los campos van en el orden del modelo, y los pasos de las pruebas en el orden del YAML.
- Sin fechas ni horas en lo generado. Todo en UTF-8 sin BOM y con fin de línea LF. `.gitattributes` (`* text=auto eol=lf`) hace que git entregue LF en todas las máquinas.
- Cada archivo generado empieza con `// Generado desde ArchiMate: <tipo> "<nombre>" (<código>, <ID>).`. En `.csproj` y `.sln` va en la segunda y en la tercera línea, porque su formato lo exige. Los `.json` y el `.csv` no admiten comentarios.
- `salida/trazabilidad/<Proyecto>.csv` tiene una fila por cada elemento o relación del contexto. El proyecto `Integracion` (el bus entre contextos) no tiene filas, porque es infraestructura y no sale de ningún elemento del modelo, y tampoco `pruebas/EntreContextos/`, que sale de los escenarios; el host sí aparece, en la fila del contexto que registra. Las columnas son ID ArchiMate, tipo, nombre, archivo generado y clase. Para revisarlo: `.\.venv\Scripts\python.exe src\revisar_trazabilidad.py salida\intermedio\modelo-ddd.json salida`.
- El código generado compila con cero advertencias.

## Validaciones

Si una falla, el generador se detiene y dice cuál, con el nombre y el ID del elemento.

| Dónde | Qué revisa |
|---|---|
| `extraer.py` (modelo) | La regla del agregado. Cada objeto de valor tiene exactamente una composición desde su raíz o entidad, con Cardinalidad. Cada `Campo:` tiene un tipo permitido. No hay nombres repetidos dentro del mismo tipo entre los elementos del contexto. Cada comando tiene exactamente un acceso a la raíz de su agregado; además puede leer otras raíces del contexto, y escribir otra raíz es error. Cada evento lo dispara al menos un comando del contexto. Cada comando, consulta y servicio SA tiene un solo contrato. |
| `specs.py` (YAML) | Cada comando, evento, consulta y servicio SA del contexto está en el YAML, y el YAML no nombra nada que no exista. Hay claves conocidas y no repetidas, tipos permitidos y estados de la lista cerrada. Los eventos de cada comando son exactamente los del modelo. Se cumple la regla de los datos. Las políticas, `junto_con` y `con` están completos. La identidad es un consecutivo o se forma con datos que el comando que crea tiene; los `valores` son válidos; cada evento de `requiere` está declarado y el comando tiene su identidad; las correspondencias de `guarda` tienen el mismo tipo; un evento sin `dispara` lo requiere algún comando; las consultas sobre todas filtran por datos de su entrada y sus agregaciones tienen el tipo correcto; una lista tiene nombre y sus datos son de la raíz. Con varios agregados, cada comando, evento y consulta se revisa contra la raíz de su agregado; `crea: si_no_existe` necesita una identidad recibida; las operaciones sobre listas tienen claves que son campos de la lista; un evento que dispara con otra identidad trae la de la raíz en sus datos. Un mensaje de un SA cubre la entrada del comando que dispara (y trae la identidad si el comando no crea); un SA que recibe tiene en el modelo un flujo que entra; un comando sobre todas no escribe y su temporizador cubre su entrada; `List<objeto de valor>` nombra un objeto de valor del contexto; `orden` usa datos de la raíz. Desde Cobros y depósito: la identidad de cada entidad es uno de sus campos; los `calculados` de un comando salen de datos que el comando tiene (antes o después de sus SA); en `usa`, `con`, `entrada` y `salida` nombran datos del SA, y un SA al que se llama tiene en el modelo un flujo que entra (uno que solo sale va con `envia`, G11); `agregar` con correspondencias nombra campos de la lista; `si` y `salvo` usan datos disponibles; `correspondencias` toman datos que llegan; los comandos de un mensaje o de un evento existen y usan la misma identidad; `politicas` nombra comandos con políticas en el modelo, y `junto_con` y `uno_de` todos sus eventos, sin repetir; `envia` sale con un evento del contexto que trae sus datos; una consulta por identidad que lee varias raíces dice con `de` cuál, y las demás tienen la misma identidad. Los escenarios están bien escritos, y los escenarios entre contextos, contra los YAML de sus contextos. **Contratos entre contextos (D2):** lo que un YAML declara recibir de otro contexto llega en el evento tal como lo publica el YAML de ese contexto: el dato con que llega, cada dato con el mismo tipo, y ningún dato obligatorio que se publique como opcional. Se revisa contra los YAML de la misma carpeta, en `specs.py` y en `generar.py` antes de escribir nada. |

## Discrepancias encontradas

| # | Qué | Dónde | Estado |
|---|---|---|---|
| 1 | SB-11 "Verificar los requisitos del cliente": el contrato de la V4 pide como entrada el cliente, la licencia y la autorización, pero la documentación del servicio en el modelo dice que revisa la ficha del cliente que guarda el arriendo. | Contrato SB-11 (V4) y servicio de aplicación SB-11 (V8). | **Cerrada sin cambios (D3, 4 nov 2026).** No es un error, sino un refinamiento entre niveles: la V4 dice qué se verifica, y la V6 decidió dónde viven esos datos (la ficha es la copia que guarda cada arriendo, V6-SUP-01). La consulta recibe solo el número del arriendo y lee la ficha de la raíz. |
| 2 | SA-02: la salida de su contrato no mencionaba la referencia del contrato firmado, aunque la raíz Arriendo la guarda con fuente SA-02 y V8-SUP-03 dice que SA-02 la entrega. | Contrato SA-02 (V4). | **Corregida en el modelo (D3, 4 nov 2026):** la salida del contrato incluye la referencia del contrato firmado, en Archi y en el README principal. |
| 3 | El mismo dato tiene nombres distintos entre contextos. Cobros dice "código de autorización de la pasarela" y Gestión del arriendo, "autorización del bloqueo del depósito". Operación dice "hora de entrega" y "hora de regreso", y Gestión del arriendo, "fecha y hora del cambio". Cobros guarda un "comprobante" por cobro. La Cuenta del arriendo no tiene la hora del cierre. | Campos de las raíces de la V6 y eventos entre dominios. | **Cerrada sin cambiar el modelo (G12, D2, 7 nov 2026).** Quien recibe declara los datos con los nombres de quien publica y, donde no calzan con la entrada de su comando, una correspondencia (`correspondencias`). Cobros publica los dos comprobantes con su concepto en el nombre (renombra la salida de cada llamada a la pasarela) y la hora del cierre en el evento, aunque la cuenta no la guarde (GEN-SUP-73). |
| 4 | La raíz Calificación no decía a quién se califica, pero SB-30 calcula el promedio de un cliente o de un propietario. | Raíz Calificación (V6). | **Corregida en el modelo (4 nov 2026):** campo `calificado` (string), en Archi y en el README principal. |
| 5 | Ningún campo unía un yate con su arriendo en Operación: la Lectura se identifica por el yate y el Acta de entrega por el arriendo. SB-27 revisa "las lecturas de un yate con arriendo en curso" y SB-26 devuelve el recorrido del yate arrendado. | Raíz Acta de entrega (V6), contrato SB-22 (V4). | **Corregida en el modelo (4 nov 2026):** campo `identificador del yate` (string) en el Acta de entrega, y la entrada del contrato SB-22 lo incluye. |
| 6 | El Yate no guardaba a su propietario, aunque el contrato de SB-01 lo recibe y Gestión del arriendo lo copia del inventario (V8-DEC-04). | Raíz Yate (V6). | **Corregida en el modelo (4 nov 2026):** campo `propietario` (string). |
| 7 | El campo "estado" del Rango de fechas se llamaba igual que el estado de la raíz, y la regla de los datos lo prohíbe. | Objeto de valor Rango de fechas (V6). | **Corregida en el modelo (4 nov 2026):** se llama `estado de la fecha`, como su enum "Estado de la fecha". |
| 8 | El campo "arriendo" del Rango de fechas tenía otro nombre que en Gestión del arriendo ("número del arriendo"), y SB-05 recibe los eventos de Gestión del arriendo (D2). | Objeto de valor Rango de fechas (V6). | **Corregida en el modelo (4 nov 2026):** se llama `número del arriendo`. |
| 9 | SB-26 y SB-27 solo actúan con un arriendo en curso (V8), pero en el modelo solo leían la Lectura: no tenían cómo saber qué arriendos están en curso. | Accesos de SB-26 y SB-27 (V6, V8). | **Corregida en el modelo (5 nov 2026):** SB-26 y SB-27 leen también el Acta de entrega y el Acta de inspección (un arriendo está en curso si tiene la primera y no la segunda). |
| 10 | SA-08 envía a Finanzas, por cada arriendo cerrado, el propietario y el yate, pero la Cuenta del arriendo no los guardaba y Cobros y depósito no los recibe de nadie. | Raíz Cuenta del arriendo (V6.2), contrato SA-08 (V4). | **Corregida en el modelo (7 nov 2026):** campos `identificador del yate` y `propietario` (string) en la Cuenta del arriendo, que llegan con el contrato del cliente firmado (SB-13), en Archi y en el README principal. |
| 11 | El reclamo a la aseguradora (SB-16) lleva el número de la póliza, que guarda la Cuenta del arriendo, pero SB-16 solo accedía al Reclamo. | Accesos de SB-16 (V6.2). | **Corregida en el modelo (7 nov 2026):** SB-16 lee también la Cuenta del arriendo (G6), en Archi y en el README principal. |
| 12 | SB-18 devuelve "movimientos con fecha, concepto, valor y evidencia", pero el Cobro no tiene fecha. | Contrato SB-18 (V4) y entidad Cobro (V6.2). | **Corregida en el modelo (9 nov 2026):** campo `fecha` (DateOnly) en la entidad Cobro, la fecha de la orden que confirma la pasarela; la salida del contrato de SA-06 la incluye, en Archi y en el README principal. SB-18 devuelve los movimientos por fecha. |
| 13 | La V8 dice que Disponibilidad de yates le da a Gestión del arriendo el yate, su propietario y su marina para registrar la solicitud (SB-06), y el objeto de valor "Yate del arriendo" los copia del inventario; pero ningún evento entre dominios de la V6 los llevaba y el contrato de SB-06 no los pide. El YAML los recibía de quien llama (GEN-SUP-09 a 11), así que el precio por día lo fijaba quien hacía la solicitud. | V8 (Disponibilidad de yates y Gestión del arriendo), contrato SB-06 (V4) y "Yate del arriendo" (V6.1). | **Corregida (9 nov 2026), sin cambiar el modelo:** Gestión del arriendo recuerda los "Yate registrado" que publica Disponibilidad (que ahora lleva también el propietario), y SB-06 los `requiere` por el identificador del yate: 409 si el yate no está en el inventario. La marina llega con una correspondencia (D2). En el README principal, la relación de la V8 nombra el evento. GEN-SUP-09 a 11 se retiraron. |

Si la ACLI de Archi escribe `IllegalArgumentException` al exportar, alguna caja tiene una fuente sin nombre (como `|9|1`). La exportación termina y valida igual, y solo se pierde esa fuente, que el generador no usa; se arregla en Archi dándole una fuente explícita. Así se arreglaron las 6 agrupaciones de área de la V2 (D8).

## Supuestos

GEN-SUP-01 se retiró: la tecnología (C# con API) es una decisión del equipo y no un supuesto (sección "Tecnología"). Su número no se reutiliza.

GEN-SUP-20 a 24 se retiraron en G12 (7 nov 2026): los datos de los eventos entre contextos ya no se suponen; se declaran con los nombres del contexto que los publica, con correspondencias donde hace falta (discrepancia 3, D2). GEN-SUP-19 se cumplió: los datos se revisaron al generar los cinco contextos. Sus números no se reutilizan.

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
| GEN-SUP-09 | Registrar la solicitud de reserva > entrada | Retirado (discrepancia 13): el propietario llega con "Yate registrado". |
| GEN-SUP-10 | Registrar la solicitud de reserva > entrada | Retirado (discrepancia 13): el precio por día llega con "Yate registrado". |
| GEN-SUP-11 | Registrar la solicitud de reserva > entrada | Retirado (discrepancia 13): la marina llega con "Yate registrado", con una correspondencia. |
| GEN-SUP-12 | Obtener el nivel de riesgo del cliente > desde | Solo se evalúa un arriendo en "reserva solicitada"; el README no lista los estados. |
| GEN-SUP-13 | Confirmar la reserva > desde | Solo se confirma desde "reserva solicitada", por el orden del ciclo de vida de la V6.1. |
| GEN-SUP-14 | Cancelar la reserva > desde | Tampoco se cancela un arriendo cancelado o no realizado. Que no se cancela si ya empezó es de EXC-02. |
| GEN-SUP-15 | Cancelar la reserva > entrada | "Quién cancela" es texto; lo inicia el cliente (V6). |
| GEN-SUP-16 | Registrar el avance del arriendo > entrada | El enum se llama "Avance del arriendo"; sus valores son los avances de SB-09 en la V6.1. |
| GEN-SUP-17 | Registrar el avance del arriendo > Yate devuelto | Solo se devuelve desde "en curso", por el orden del ciclo de vida de la V6.1. |
| GEN-SUP-18 | eventos > Riesgo aceptable obtenido | Los "valores" que pide el contrato de SA-02 son el precio por día. |
| GEN-SUP-19 | eventos_de_otros_contextos | En un Partnership, los dos contextos acuerdan los datos del evento (V8-SUP-02); se revisan al generar el otro contexto. |
| GEN-SUP-20 | Alquiler y seguro cobrados > datos | Retirado en G12: Cobros publica los dos comprobantes con su concepto en el nombre. |
| GEN-SUP-21 | Depósito bloqueado > datos | Retirado en G12: llega "código de autorización de la pasarela", con una correspondencia. |
| GEN-SUP-22 | Yate entregado al cliente > datos | Retirado en G12: llega "hora de entrega", con una correspondencia. |
| GEN-SUP-23 | Inspección de devolución registrada > datos | Retirado en G12: llega "hora de regreso", con una correspondencia. |
| GEN-SUP-24 | Cuenta del arriendo cerrada > datos | Retirado en G12: llega "hora del cierre", con una correspondencia (Cobros la toma de la hora de regreso, GEN-SUP-73). |
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
| GEN-SUP-48 | `crea: si_no_existe` crea la raíz con el primer estado de su lista, y solo la guarda si el comando termina bien. | Una solicitud rechazada no debe dejar rastro (como el consecutivo que no gasta número). |
| GEN-SUP-59 | Un arriendo está en curso si tiene acta de entrega y todavía no tiene acta de inspección. | Es lo que Operación sabe por sí misma; Gestión del arriendo tiene el estado, pero cada contexto guarda su propia copia (V8-DEC-04). |

Del YAML de Calificaciones. Cada uno está marcado como supuesto en `specs/calificaciones.yaml`:

| ID | Dónde | Supuesto |
|---|---|---|
| GEN-SUP-37 | raices > Calificación > identidad | El dato se llama "identificador de la calificación". |
| GEN-SUP-38 | raices > Calificación > estado | Tiene un solo estado, "registrada", porque una calificación no cambia después (V6). |
| GEN-SUP-39 | Consultar calificaciones promedio > salida | Sin calificaciones no hay promedio: la "calificación promedio" es opcional (null). |
| GEN-SUP-40 | eventos_de_otros_contextos > Arriendo cerrado | Los datos llegan con los nombres que publica Gestión del arriendo (Partnership, V8-SUP-02; D2). |

Del YAML de Disponibilidad de yates. Cada uno está marcado como supuesto en `specs/disponibilidad-de-yates.yaml`, salvo GEN-SUP-46, que está en el archivo manual de SB-03:

| ID | Dónde | Supuesto |
|---|---|---|
| GEN-SUP-41 | raices > Yate > identidad | El consecutivo tiene 4 dígitos (YATE-0001). |
| GEN-SUP-42 | raices > Yate y Calendario del yate > estado | Cada uno tiene un solo estado ("registrado" y "activo"): el modelo no les da ciclo de vida. |
| GEN-SUP-43 | Definir las fechas bloqueadas del yate y Gestionar la ocupación del calendario > entrada | Los enums se llaman "Acción sobre el bloqueo" y "Acción sobre la ocupación". |
| GEN-SUP-44 | Definir las fechas bloqueadas del yate > Fechas desbloqueadas | Se desbloquea el mismo rango que se bloqueó (mismas fechas). |
| GEN-SUP-45 | Consultar yates disponibles > entrada | Se consulta por la marina elegida; la ubicación del cliente no se usa. |
| GEN-SUP-46 | `DefinirLasFechasBloqueadasDelYate.cs` | E2E-02 (solo el propietario cambia sus fechas) no se revisa: la aplicación no autentica a quien llama. |
| GEN-SUP-47 | Contratos con propietarios y clientes > respuesta_por_defecto y casos | Valores de prueba: CONP-0001 firmado; el propietario de prueba PROP-SIN-CONTRATO no tiene contrato firmado. |

Del YAML de Operación del arriendo y sus archivos manuales:

| ID | Dónde | Supuesto |
|---|---|---|
| GEN-SUP-49 | Determinar las diferencias > requiere y `DeterminarLasDiferenciasEntreEntregaYDevolucion.cs` | La "fecha y hora de fin acordadas" es el final del día de fin de la reserva confirmada que Operación recibió de Gestión del arriendo. |
| GEN-SUP-50 | `DetectarLaPerdidaDeSenal.cs` | Un yate en curso que nunca envió lecturas no se avisa: no tiene "última lectura conocida". |
| GEN-SUP-51 | `DetectarLaPerdidaDeSenal.cs` | Se avisa en cada revisión mientras no lleguen lecturas nuevas. |
| GEN-SUP-52 | raices > Acta de entrega, Acta de inspección y Lectura de ubicación y combustible > estado | Cada una tiene un solo estado, "registrada": no cambian después (V6). |
| GEN-SUP-53 | raices > Lectura de ubicación y combustible > identidad | El dato se llama "identificador de la lectura". |
| GEN-SUP-54 | Detectar la pérdida de señal > entrada | La hora de la revisión ("ahora") llega en la entrada, para que la prueba no dependa del reloj; el temporizador usa la hora actual. |
| GEN-SUP-55 | Detectar la pérdida de señal > temporizador | Se revisa cada 5 minutos y se avisa desde 30 minutos sin lecturas (D6; el tiempo lo fija Operaciones, V4-SUP-04). |
| GEN-SUP-56 | Consultar ubicación y combustible del yate | La última posición es el último elemento del recorrido; quién consulta no se revisa (GEN-SUP-46). |
| GEN-SUP-57 | servicios_sa > Avisos y actas de las marinas > recibe | La marina envía las actas con los datos del arriendo; no hay traducción de formato. |
| GEN-SUP-58 | servicios_sa > Ubicación y combustible del proveedor > recibe | El proveedor envía el yate; la asociación dispositivo-yate queda para cuando exista un inventario de dispositivos. |

Del generador, desde Cobros y depósito y la integración (G9 a G12):

| ID | Supuesto | Por qué |
|---|---|---|
| GEN-SUP-60 | Un evento o un mensaje que dispara varios comandos los corre en orden; si uno falla, los siguientes no corren y la respuesta es la de ese error (los anteriores ya ocurrieron y publicaron sus eventos). | Es predecible y deja ver cuál falló. En el contrato firmado, si el depósito no se bloquea, no se cobra nada. |
| GEN-SUP-61 | Los eventos de una política con varios disparos (`junto_con`, `uno_de`) esperan en memoria, por identidad, y se pierden al reiniciar. | Como los de otros contextos (capa 3) y GEN-SUP-02. |
| GEN-SUP-62 | Cada contexto y los escenarios entre contextos se prueban con la aplicación recién levantada. | Con la integración, un evento de los escenarios de un contexto llega a los demás. |
| GEN-SUP-63 | Un evento se entrega primero a los demás contextos y después a las políticas del contexto que lo publica. | Así, con la inspección, Gestión del arriendo registra la devolución antes de que lleguen las cuentas cerradas, que la necesitan. |
| GEN-SUP-64 | Una llamada a un SA que no cumple su condición (`si`, `salvo`) no se hace, y su salida queda en null. | Un dato que falta se nota: si se usa sin la condición, responde 422 por el dato faltante. |

Del YAML de Cobros y depósito y sus archivos manuales:

| ID | Dónde | Supuesto |
|---|---|---|
| GEN-SUP-65 | raices > Cuenta del arriendo y Depósito para daños > estado | Los enums se llaman "Estado de la cuenta" y "Estado del depósito"; los estados son los de la V6.2. |
| GEN-SUP-66 | raices > Reclamo a la aseguradora > identidad | El número de reclamo es un consecutivo de 4 dígitos (REC-0001). |
| GEN-SUP-67 | raices > Reclamo a la aseguradora > estado | Tiene un solo estado, "enviado": la aplicación no sigue el reclamo después de enviarlo. |
| GEN-SUP-68 | `LiquidarYCobrarLosCargosDelCierre.cs` | Tarifas de prueba: 10 por punto del nivel de combustible y 50 por hora adicional. |
| GEN-SUP-69 | servicios_sa > Cobros por la pasarela de pagos > entrada | El medio de pago es opcional: en el cierre y en el depósito la pasarela usa el que el cliente dio al reservar. |
| GEN-SUP-70 | `ReembolsarUnaCancelacion.cs` | Se devuelve lo cobrado por el alquiler; el seguro no, porque la póliza ya se emitió. |
| GEN-SUP-71 | Reembolsar una cancelación > resultados | La cuenta de un arriendo cancelado se cierra con la decisión sobre el reembolso. |
| GEN-SUP-72 | `LiberarElDeposito.cs` | El depósito se libera el día de la devolución o el de la cancelación. |
| GEN-SUP-73 | Cerrar las cuentas del arriendo > entrada y politicas | La hora del cierre es la hora de regreso: en la aplicación todo el cierre ocurre con la inspección. |
| GEN-SUP-74 | `CerrarLasCuentasDelArriendo.cs` | La comisión es el 20 % del alquiler (valor de prueba; la fija el contrato con el propietario). |
| GEN-SUP-75 | Cerrar las cuentas del arriendo > entrada | El enum se llama "Decisión sobre el depósito". |
| GEN-SUP-76 | servicios_sa > Contratos con propietarios y clientes > salida | Las condiciones de cancelación se traducen a "días mínimos para el reembolso"; 7, de prueba. |
| GEN-SUP-77 | servicios_sa > Contratos con propietarios y clientes > recibe | El contrato del cliente firmado trae el arriendo con sus valores (yate, propietario, cliente, fechas, días, precio por día, seguro, depósito y medio de pago). Primero se bloquea el depósito y después se cobra. |
| GEN-SUP-78 | servicios_sa > Pólizas y reclamos de la aseguradora | Una entrada para las dos solicitudes (enum "Solicitud a la aseguradora"); valores de prueba: póliza POL-0001 por 120 y reclamo SIN-0001 recibido. |
| GEN-SUP-79 | `ConsultarElEstadoDeCuentaDelArriendo.cs` | Quién consulta no se revisa: la aplicación no autentica (como GEN-SUP-46). |
| GEN-SUP-80 | servicios_sa > Cobros por la pasarela de pagos | El enum se llama "Tipo de orden". Valores de prueba: un comprobante y una fecha de la orden por tipo de orden, el medio de pago TARJETA-RECHAZADA se rechaza y el bloqueo vence el 2026-03-29 (28 días, V4-SUP-07). |
| GEN-SUP-81 | eventos_de_otros_contextos > Reserva cancelada | Una reserva cancelada antes del contrato firmado no tiene depósito ni cuenta: no hay nada que liberar ni devolver, y SB-20 y SB-15 no corren (`si_existe`). |

De la integración en los YAML de los otros contextos:

| ID | Dónde | Supuesto |
|---|---|---|
| GEN-SUP-82 | gestion-del-arriendo.yaml: servicios_sa > Contratos con propietarios y clientes > envia | Con "Riesgo aceptable obtenido", SA-02 envía los datos para el contrato del cliente (arriendo, cliente, yate, fechas y precio por día); la gestión de contratos está simulada. |
| GEN-SUP-83 | operacion-del-arriendo.yaml: Diferencias determinadas, y `DeterminarLasDiferenciasEntreEntregaYDevolucion.cs` | El evento lleva la hora de regreso y la evidencia: las fotos del acta de entrega y las del acta de inspección. |
| GEN-SUP-84 | operacion-del-arriendo.yaml: servicios_sa > Avisos y actas de las marinas > envia | La alerta de pérdida de señal lleva el yate y su última lectura; SA-05 la lleva a la marina que guarda el yate, porque Operación del arriendo no guarda la marina. |

## Limitaciones conocidas

- Una entidad solo puede estar compuesta por la raíz, y un objeto de valor compuesto por una entidad no se genera (`specs.py` lo dice).
- Las demás raíces de una consulta por identidad deben tener el mismo nombre de identidad que la raíz por la que se consulta.
- Los comandos que dispara un evento o un mensaje no forman una sola operación: si uno falla, los anteriores no se deshacen (GEN-SUP-60).
- Cada comando calcula sus valores con sus propias tarifas de prueba (archivos manuales); no hay una tabla de tarifas compartida.
- Un mensaje que recibe un SA llega con los nombres de los datos del arriendo: la traducción del formato propio del sistema externo (SA-05, SA-07) no se genera. La alerta de pérdida de señal sale por SA-05 cuando ocurre el evento "Pérdida de señal del yate" (`envia`); el comando no llama al SA.
- Una política interna entre raíces con distinta identidad todavía no se genera (`specs.py` lo dice).
- Los servicios SA se llaman antes de `ValidarReglas`, porque las reglas usan sus respuestas (REG-01 necesita el estado del contrato). Por eso una solicitud rechazada por una regla ya consultó al CRM simulado.
- Los escenarios de cada contexto siguen enviando los eventos de otros contextos por sus endpoints de prueba; el recorrido completo por el bus se prueba en los escenarios entre contextos.
- Si se quita el YAML de un contexto, el generador borra sus archivos generados pero no su código a mano: avisa que esa carpeta quedó suelta.
