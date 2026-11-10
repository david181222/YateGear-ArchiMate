# Generador de código desde el modelo ArchiMate

Este generador construye la primera versión de una aplicación a partir de un modelo ArchiMate hecho en Archi y de un archivo de especificaciones por contexto (YAML). En este repositorio genera la de YateGear, desde `../modelo/YateGear.archimate` y `specs/*.yaml`. Es determinista: no usa IA ni red, y el mismo modelo con el mismo YAML da siempre los mismos archivos.

Genera un proyecto por cada contexto que tiene YAML en `specs/`, y los levanta todos en un solo programa (D1), comunicados por el bus entre contextos (G12). Hoy tienen YAML los cinco contextos del modelo, y `specs/entre-contextos.yaml` tiene los escenarios de punta a punta entre ellos (S4). La aplicación generada documenta su API con OpenAPI y Swagger.

El generador no conoce YateGear: sirve para cualquier modelo que siga sus convenciones. La [guía de modelado](GUIA-DE-MODELADO.md) dice qué dibujar en Archi y en qué orden trabajar, y `ejemplo/` tiene un modelo mínimo de otro dominio (una biblioteca) que se genera y se prueba igual que YateGear. Lo que es propio de YateGear (sus escenarios, las discrepancias encontradas en su modelo y los supuestos de sus YAML) está en [YATEGEAR.md](YATEGEAR.md).

Los códigos como G12, D2 o S4 que aparecen en este documento, en los comentarios del código y en lo generado nombran capacidades y decisiones del generador: están en [Códigos](#códigos).

## Índice

Para generar y levantar la API por primera vez: [Paso a paso](#paso-a-paso-del-modelo-a-la-api-corriendo). Para modelar otro sistema: [GUIA-DE-MODELADO.md](GUIA-DE-MODELADO.md).

- [Tecnología](#tecnología)
- [Requisitos](#requisitos)
- [Paso a paso: del modelo a la API corriendo](#paso-a-paso-del-modelo-a-la-api-corriendo)
- [Los comandos y sus parámetros](#los-comandos-y-sus-parámetros)
  - [Puerto](#puerto)
- [Cómo funciona](#cómo-funciona)
  - [Carpetas](#carpetas)
- [Qué se lee del modelo](#qué-se-lee-del-modelo)
- [Formato del YAML](#formato-del-yaml)
- [Qué genera cada elemento del modelo](#qué-genera-cada-elemento-del-modelo)
  - [Comunicación entre contextos (D1)](#comunicación-entre-contextos-d1)
  - [Documentación de la API (OpenAPI y Swagger)](#documentación-de-la-api-openapi-y-swagger)
- [Reglas del generador](#reglas-del-generador)
  - [Generalidad: el generador no conoce YateGear](#generalidad-el-generador-no-conoce-yategear)
  - [Regla de los datos](#regla-de-los-datos)
  - [Nombres de C#](#nombres-de-c)
  - [Pasos de un comando](#pasos-de-un-comando)
  - [Capas](#capas)
  - [Qué borra el generador](#qué-borra-el-generador)
  - [Archivos manuales](#archivos-manuales)
  - [Bitácora](#bitácora)
- [Escenarios y pruebas](#escenarios-y-pruebas)
  - [Escenarios entre contextos](#escenarios-entre-contextos)
- [Reproducibilidad y trazabilidad](#reproducibilidad-y-trazabilidad)
- [Validaciones](#validaciones)
- [Supuestos](#supuestos)
- [Fuera de alcance](#fuera-de-alcance)
- [Limitaciones conocidas](#limitaciones-conocidas)
- [Códigos](#códigos)

## Tecnología

El proyecto generado es C# con una API web de ASP.NET Core (API mínima) sobre .NET 10, la versión con soporte largo vigente (.NET 8 sale de soporte en noviembre de 2026). Es una decisión del equipo. La versión está en un solo lugar del generador (`NET` y `SDK` en `src/generacion/constantes.py`), junto con los dos paquetes NuGet del host, de versión fija: `Microsoft.AspNetCore.OpenApi` (el documento OpenAPI) y `Swashbuckle.AspNetCore.SwaggerUI` (la página Swagger).

## Requisitos

| Qué | Versión | Para qué |
|---|---|---|
| PowerShell | Windows: Windows PowerShell 5.1 o PowerShell 7. Linux: PowerShell 7 (`pwsh`). | Ejecutar `generar.ps1`, `ejecutar.ps1` y `probar.ps1`. |
| Python | 3.13. Windows: con el lanzador `py`. Linux: `python3.13` en el PATH, o el que instala `uv python install 3.13`. | El generador. `generar.ps1` crea el entorno virtual `.venv` e instala `requirements.txt` si no existen; ese paso usa la red. |
| .NET SDK | cualquier 10.0.x | Compilar y correr el proyecto generado. `salida/global.json` fija el SDK 10 (`10.0.100` con `rollForward: latestFeature`). La primera compilación descarga de NuGet los dos paquetes de la documentación de la API, así que también usa la red. En Linux, si existe `~/.dotnet/dotnet`, los scripts usan ese, para no depender del `dotnet` del sistema. |
| Archi | 5.x. Windows: en `C:\Program Files\Archi`. Linux: `Archi` en el PATH, `~/.local/opt/Archi/Archi` o `/opt/Archi/Archi`. | Exportar el modelo con su línea de comandos (ACLI). Funciona aunque Archi esté abierto, pero exporta lo guardado en disco. Otra ruta: `-Archi <ruta del ejecutable de Archi>`. |

Las librerías de Python tienen versión fija en `requirements.txt`: pyArchimate 2.0.0, Jinja2 3.1.6, PyYAML 6.0.3 y sus dependencias.

En Linux todo se instala en la carpeta del usuario, sin sudo: el SDK con `dotnet-install.sh --channel 10.0 --install-dir ~/.dotnet`, Python con `uv python install 3.13`, y PowerShell y Archi descomprimiendo sus `.tar.gz` en `~/.local/opt` (con `pwsh` enlazado en `~/.local/bin`). En Linux se probó con la versión anterior, que generaba para .NET 8 (Ubuntu 26.04, .NET 8.0.427, PowerShell 7.6.9 y Archi 5.10: los mismos archivos que en Windows, con la misma huella); con .NET 10 se ha probado en Windows (SDK 10.0.202) y todavía no en Linux.

## Paso a paso: del modelo a la API corriendo

En Windows, desde cero. En Linux es igual, con `pwsh ./<comando>.ps1` en lugar de `powershell -ExecutionPolicy Bypass -File .\<comando>.ps1`.

**1. Instalar los requisitos** de la tabla anterior y comprobarlos:

```powershell
py -3.13 --version                              # Python 3.13
dotnet --list-sdks                              # debe aparecer una versión 10.0.x
Test-Path "C:\Program Files\Archi\Archi.exe"    # True
```

**2. Clonar el repositorio y entrar a la carpeta del generador:**

```powershell
git clone https://github.com/david181222/YateGear-ArchiMate.git
cd YateGear-ArchiMate\generador
```

**3. Generar la solución .NET:**

```powershell
powershell -ExecutionPolicy Bypass -File .\generar.ps1
```

La primera vez crea el entorno de Python (`.venv`) e instala sus librerías, y al compilar descarga de NuGet los paquetes de la documentación de la API; son los dos momentos en que usa la red. Después exporta el modelo con Archi, lo revisa, revisa los YAML, genera la solución y la compila. Termina con "Listo."; si algo falla, se detiene y dice en qué paso. Lo generado queda en `salida/`: `YateGear.sln`, con un proyecto por contexto, el host `YateGear` (el programa que se ejecuta) y `Integracion` (el bus entre contextos).

**4. Levantar la API:**

```powershell
powershell -ExecutionPolicy Bypass -File .\ejecutar.ps1
```

Escribe la dirección de la página de inicio y la de cada contexto, y se queda corriendo en `http://localhost:5080` hasta que se detiene con Ctrl+C. Déjala abierta y sigue en el navegador o en otra terminal. Los datos viven en memoria: al detenerla se pierden.

**5. Verla en el navegador.** Empieza por la página de inicio. Las consultas y las rutas de infraestructura son GET, así que se abren directamente y devuelven JSON:

| Qué | Dirección |
|---|---|
| La página de inicio: todas las rutas de cada contexto, con su método y el elemento del modelo del que salen | http://localhost:5080/ |
| La documentación de la API (Swagger): cada endpoint agrupado por contexto, con su contrato, y un botón para probarlo | http://localhost:5080/swagger |
| El documento OpenAPI, para importarlo en otra herramienta | http://localhost:5080/openapi/v1.json |
| Los contextos que levantó el programa | http://localhost:5080/contextos |
| Los eventos que pasaron entre contextos, y los errores del bus | http://localhost:5080/eventos-entre-contextos |
| La bitácora de un contexto: sus eventos, las llamadas a los SA simulados y los errores | http://localhost:5080/gestion-del-arriendo/bitacora |
| Una consulta sobre todas las raíces (con filtros en la dirección) | http://localhost:5080/disponibilidad-de-yates/consultas/consultar-yates-disponibles?identificadorDeLaMarina=MAR-01&inicio=2026-03-10&fin=2026-03-12 |
| Una consulta por identidad | http://localhost:5080/gestion-del-arriendo/consultas/consultar-el-arriendo/ARR-0001 |

Al levantarla no hay datos: las listas salen vacías y una consulta por identidad responde 404 hasta que un comando cree esa raíz (paso 6). En la página de inicio, las rutas que se pueden abrir directo son enlaces; las que llevan datos en la ruta (`{numeroDelArriendo}`) o en la consulta (`?dato=...`) se escriben a mano en la barra. La dirección de cada contexto (por ejemplo http://localhost:5080/gestion-del-arriendo) lleva a su parte de la página.

**6. Enviar comandos.** Los comandos, los eventos de otros contextos y los mensajes de los SA son POST con un cuerpo JSON, así que no se escriben en la barra del navegador. Hay cuatro formas:

- Swagger (http://localhost:5080/swagger): abre el endpoint, "Try it out", completa el cuerpo JSON de ejemplo y "Execute".
- Los archivos `salida/pruebas/<Proyecto>/pruebas.http` tienen una llamada por cada paso de los escenarios del contexto, con su cuerpo. Se abren en VS Code con la extensión REST Client ("Send Request" encima de cada llamada) o en Visual Studio 2022.
- PowerShell. Por ejemplo, registrar un yate:

  ```powershell
  $yate = @{ propietario = "PROP-0001"; identificadorDeLaMarina = "MAR-01"; nombre = "Brisa"; matricula = "CB-123"
             capacidad = 8; precioPorDia = 500; documentosAlDiaAnteLaDIMAR = $true } | ConvertTo-Json
  Invoke-RestMethod -Method Post http://localhost:5080/disponibilidad-de-yates/comandos/registrar-yate-en-el-inventario `
      -ContentType "application/json; charset=utf-8" -Body ([Text.Encoding]::UTF8.GetBytes($yate))
  ```

  Responde `identidad: YATE-0001` y `eventos: Yate registrado`. Después, la consulta de yates disponibles del paso 5 ya lo muestra, y `/eventos-entre-contextos` muestra el evento con el que Gestión del arriendo guarda su copia del yate. Los datos del JSON se llaman como en el modelo, en camelCase y sin tildes: "precio por día" es `precioPorDia`.
- Todos los escenarios de una vez, con `probar.ps1` (paso 8).

**7. Detener la API** con Ctrl+C en la terminal de `ejecutar.ps1`. Si después la compilación dice que `YateGear.exe` "está siendo usado por otro proceso", quedó viva: `Get-Process YateGear | Stop-Process`.

**8. Probar y verificar todo**, con la API detenida, porque usan el mismo puerto:

```powershell
powershell -ExecutionPolicy Bypass -File .\probar.ps1       # la documentación de la API y los escenarios de los YAML: cada paso con ✓ o ✗
powershell -ExecutionPolicy Bypass -File .\verificar.ps1    # todo: generar, determinismo, trazabilidad, validador, código a mano y escenarios
```

**9. Abrirla en Visual Studio o Rider (opcional):** `salida/YateGear.sln`. Hace falta una versión que abra proyectos de .NET 10. El proyecto de inicio es `YateGear`; con F5 corre en el mismo puerto (perfil de `launchSettings.json`). El código a mano va en los `.cs`, nunca en los `.g.cs`, que el generador reescribe.

**Con el modelo de ejemplo** son los mismos pasos, con su modelo, su YAML y su carpeta:

```powershell
powershell -ExecutionPolicy Bypass -File .\generar.ps1 -Modelo ejemplo/Biblioteca.archimate -Specs ejemplo/specs/prestamos.yaml -Salida ejemplo/salida
powershell -ExecutionPolicy Bypass -File .\ejecutar.ps1 -Salida ejemplo/salida
```

Y en el navegador, después de prestar un libro (`ejemplo/salida/pruebas/Prestamos/pruebas.http`): http://localhost:5080/prestamos/consultas/consultar-el-prestamo/PRE-0001.

## Los comandos y sus parámetros

Desde la carpeta `generador`:

```powershell
powershell -ExecutionPolicy Bypass -File .\generar.ps1     # exporta, lee, valida, genera y compila
powershell -ExecutionPolicy Bypass -File .\ejecutar.ps1    # levanta la aplicación (Ctrl+C para detenerla)
powershell -ExecutionPolicy Bypass -File .\probar.ps1      # ejecuta los escenarios y marca cada paso con ✓ o ✗
powershell -ExecutionPolicy Bypass -File .\verificar.ps1   # todo lo anterior, más determinismo, trazabilidad y pruebas del validador
```

En Linux, lo mismo con `pwsh`:

```bash
pwsh ./generar.ps1
pwsh ./ejecutar.ps1
pwsh ./probar.ps1      # la salida de la aplicación queda en salida/intermedio/aplicacion*.log
pwsh ./verificar.ps1
```

Las herramientas de Python (`src/herramientas/`) se llaman con `.\.venv\Scripts\python.exe` en Windows y con `./.venv/bin/python` en Linux.

`generar.ps1` se detiene en el primer paso que falle y dice cuál. Sus parámetros, todos con valor por defecto, son `-Modelo` (por defecto, el único `.archimate` de `../modelo`), `-Specs` (por defecto, todos los `specs/*.yaml`; para generar solo algunos: `-Specs specs/uno.yaml,specs/otro.yaml`), `-Archi`, `-Salida` (la carpeta de lo generado, por defecto `salida`) y `-Puerto` (el puerto de la aplicación generada, por defecto 5080). Con `-SoloValidar` hace solo los pasos 1 a 4 (exportar, extraer y revisar los YAML) sin tocar la carpeta de salida: es el modo para quien está escribiendo un YAML o modelando. Ojo: `salida/` queda con exactamente los contextos que se generan, así que con `-Specs` se borran los archivos generados de los demás (nunca su código a mano); vuelven al generar todo.

`ejecutar.ps1` levanta la aplicación (el host, con todos los contextos) desde `salida/`, para que `dotnet` use el SDK que fija `salida/global.json`. Con la aplicación arriba, cada `salida/pruebas/<Proyecto>/pruebas.http` se puede ejecutar llamada por llamada con la extensión REST Client de VS Code o con Visual Studio.

`probar.ps1` compila, revisa una vez la documentación de la API con la aplicación levantada (`src/herramientas/revisar_api.py`: el documento OpenAPI tiene los endpoints de cada contexto, cada uno con su resumen y su etiqueta, y Swagger responde) y, para cada contexto (`salida/pruebas/<Proyecto>/escenarios.json`) y después para los escenarios entre contextos (`salida/pruebas/EntreContextos/escenarios.json`), levanta la aplicación, ejecuta sus escenarios y la detiene; termina con código 1 si algún paso falla. Con `-Contexto "<nombre del contexto o del proyecto>"` prueba solo ese, y con `-Contexto "entre contextos"`, solo los de punta a punta.

Los dos leen de `salida/contextos.json` qué proyecto levantar, en qué puerto y qué contextos hay, así que no tienen escrito ningún nombre del modelo. Los dos aceptan `-Salida`, para otra carpeta generada.

`verificar.ps1` revisa en un solo comando cuándo está terminado un contexto: genera y compila (una advertencia es un error), genera otra vez y compara la huella (determinismo), revisa la trazabilidad, corre las pruebas del validador (`pruebas-validador/casos.yaml`), revisa que ningún archivo manual conserve un valor provisional (`PENDIENTE`) y prueba la documentación de la API y los escenarios. Al final muestra una tabla con cada revisión y termina con código 1 si alguna falla. Acepta `-Modelo`, `-Specs`, `-Archi`, `-Salida` y `-Puerto`, y `-SinPruebasDelValidador` para otro modelo, como el de ejemplo:

```powershell
powershell -ExecutionPolicy Bypass -File .\verificar.ps1 -Modelo ejemplo/Biblioteca.archimate -Specs ejemplo/specs/prestamos.yaml -Salida ejemplo/salida -SinPruebasDelValidador
```

### Puerto

La aplicación usa el puerto **5080**. Si está ocupado:

- Para una sola vez: `.\ejecutar.ps1 -Puerto 5090` o `.\probar.ps1 -Puerto 5090`. Si usas un `pruebas.http`, cambia también su línea `@base`.
- Para cambiarlo siempre: genera con otro puerto, `.\generar.ps1 -Puerto 5090`. De ahí salen `salida/<Host>/Properties/launchSettings.json`, `salida/contextos.json` y los `pruebas.http`. No se editan a mano, porque el generador los reescribe. `verificar.ps1 -Puerto` no cambia lo generado: solo corre las pruebas en ese puerto.

## Cómo funciona

```
modelo/YateGear.archimate
   |  ACLI de Archi: --loadModel ... --xmlexchange.export ...
   v
salida/intermedio/<modelo>.xml          formato de intercambio (Open Exchange); no se versiona
   |  src/extraer.py (paquete lectura, con pyArchimate): lee, valida el modelo y toma todos sus contextos
   v
salida/intermedio/modelo-ddd.json  <--  specs/*.yaml (uno por contexto)
   |  src/specs.py (paquete validacion): revisa cada YAML contra el JSON
   |  src/generar.py (paquete generacion) + plantillas/*.j2 (Jinja2)
   v
salida/   solución C# (.NET 10): un proyecto por contexto con YAML, el host y el bus entre contextos;
          contextos.json, y pruebas/ y trazabilidad/ por contexto
   |  dotnet build
   v
ejecutar.ps1 / probar.ps1
```

Se lee el XML de intercambio y no el `.archimate` directo, porque los dos dan lo mismo. `src/herramientas/comparar_lectura.py` lo comprueba: compara el `.archimate` leído sin pyArchimate, el `.archimate` leído con pyArchimate y el XML leído con pyArchimate. Coinciden en totales, IDs, nombres, documentación, propiedades, tipos de acceso, origen y destino de cada relación, y cajas y líneas de cada vista. Antes de comparar se normaliza solo la forma de escribir: los nombres de tipo, las uniones y los códigos de acceso.

### Carpetas

De la carpeta `generador`:

| Carpeta o archivo | Qué es |
|---|---|
| `generar.ps1`, `ejecutar.ps1`, `probar.ps1`, `verificar.ps1` | Los comandos. Van en UTF-8 con BOM, porque Windows PowerShell 5.1 lee sin BOM como ANSI y rompería la "ó" de "Gestión". |
| `src/` | El generador en Python. Sus tres pasos son `extraer.py`, `specs.py` y `generar.py`; el código de cada uno está en un paquete (ver abajo). |
| `plantillas/` | Una plantilla Jinja2 por tipo de archivo generado. |
| `specs/` | Un YAML de especificaciones por contexto. Su comentario inicial explica cada sección. |
| `salida/` | Lo generado. Se versiona todo, salvo `bin/`, `obj/`, el XML exportado (`intermedio/*.xml`) y los registros de la aplicación (`intermedio/*.log`). |
| `pruebas-validador/` | `casos.yaml`: copias rotas a propósito de los YAML de `specs/` y el error que `specs.py` debe dar en cada una (ver "Validaciones"). |
| `ejemplo/` | Un modelo mínimo que no es YateGear (`Biblioteca.archimate`, Contexto Préstamos), su YAML (`specs/prestamos.yaml`) y lo generado (`salida/`, con su regla escrita a mano). Es el ejemplo de la guía de modelado y prueba que el generador no conoce YateGear. |
| `GUIA-DE-MODELADO.md` | Qué dibujar en Archi para que el generador lo lea, en qué orden trabajar y qué significa cada error del modelo. |
| `YATEGEAR.md` | Lo propio de YateGear: sus escenarios, las discrepancias de su modelo y los supuestos de sus YAML. |

De `src/`:

| Carpeta o archivo | Qué es |
|---|---|
| `extraer.py`, `specs.py`, `generar.py` | Los tres pasos, como los llama `generar.ps1`. Cada uno solo lee sus argumentos, llama a su paquete y escribe el resultado. |
| `lectura/` | `leer.py` lee el modelo con pyArchimate y lo deja como un grafo; `extractor.py` busca los contextos por tipo, relación y propiedad, y los valida. |
| `validacion/` | El revisor del YAML. `revisor.py` es la clase, y cada sección del YAML se revisa en su módulo: `revisor_raices.py`, `revisor_servicios_sa.py`, `revisor_comandos.py`, `revisor_eventos.py`, `revisor_consultas.py` y `revisor_escenarios.py`. Además, `entre_contextos.py` (escenarios de punta a punta), `contratos.py` (lo que un contexto recibe de otro), `carga.py` (lee el YAML) y `valores.py` (tipos, valores y formas del YAML que también usa la generación). |
| `generacion/` | El generador de C#. `contexto.py` es el generador de un contexto, y cada parte está en su módulo: `raices.py`, `servicios_sa.py`, `eventos.py`, `comandos.py`, `consultas.py`, `politicas.py` y `escenarios.py`. `solucion.py` junta los contextos, arma el host y escribe los archivos; `csharp.py` tiene los tipos y las expresiones de C#, y `constantes.py`, la versión de .NET, los paquetes y los nombres fijos. |
| `comun/` | `nombres.py` (nombres de C# y rutas a partir de los nombres del modelo) y `tipos.py` (los tipos de los campos). |
| `herramientas/` | Las pruebas del generador: `huella.py`, `revisar_trazabilidad.py`, `probar.py`, `revisar_api.py`, `probar_validador.py` y `comparar_lectura.py`. |

## Qué se lee del modelo

Todo se busca por tipo y por relación, nunca solo por nombre, porque hay nombres repetidos entre capas (por ejemplo, el objeto de negocio y el objeto de datos "Arriendo"). El único nombre que se usa para buscar es el del contexto. No se leen los anidamientos de las vistas: los objetos de valor se dibujan dentro de su raíz, pero lo que cuenta es su composición. La [guía de modelado](GUIA-DE-MODELADO.md) explica estas convenciones paso a paso, con un ejemplo y los errores de cada una.

| Concepto | Cómo se encuentra en el modelo |
|---|---|
| Contexto | Componente de aplicación "Contexto `<dominio>`". |
| Comandos | Asignación contexto --> proceso de aplicación con la propiedad `Código del servicio` (o `Servicio básico V4`, el nombre que usa el modelo de YateGear, de su vista V4). El valor es libre, pero único. |
| Consultas | Realización contexto --> servicio de aplicación con `Código del servicio` (o `Servicio básico V4`). |
| Servicios SA | Servicio SA --> servicio --> contexto, con la propiedad `Código del servicio anticorrupción` (o `Servicio anticorrupción V4`). Su interfaz es la que se le asigna. Su contraparte es el único elemento con el que esa interfaz intercambia flujos, y entre los dos hay una relación de servicio en cualquier sentido (en SA-08 el SA le sirve a la contraparte). |
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
| Modelo | La solución `<Modelo>.sln`, el host `<Modelo>/` (un solo programa que registra todos los contextos, con un solo puerto) y `contextos.json`, que dice a los scripts qué hay. Además, la página de inicio de la API (`<Modelo>/wwwroot/index.html`), con las rutas de cada contexto, y la documentación de la API (OpenAPI y Swagger); son infraestructura, como la bitácora. |
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

### Documentación de la API (OpenAPI y Swagger)

La aplicación generada publica el documento OpenAPI de toda la API en `GET /openapi/v1.json` y la página Swagger en `/swagger`. Sale de lo mismo que el código, sin escribir nada a mano:

- Cada endpoint lleva como etiqueta el nombre de su contexto (sin "Contexto "), así que Swagger los agrupa por contexto. Las rutas del host (`/contextos` y `/eventos-entre-contextos`) van en "Infraestructura".
- El resumen dice de qué elemento del modelo sale: "Comando SB-07: Confirmar la reserva", "Consulta SB-10: ...", "Evento ... de Contexto ...", "Mensaje ... que recibe SA-05 ...".
- La descripción de un comando o una consulta es su contrato: Entrada, Salida y Reglas, con el texto del modelo.
- El cuerpo y la respuesta salen de los records generados: la entrada del comando, la salida de la consulta, `RespuestaDeComando`. Los enums aparecen como texto, igual que viajan. Además se listan los códigos con que cada tipo de endpoint puede rechazar (404, 409 y 422; 202 en un evento que espera a otros).
- Un evento de otro contexto y un mensaje de un SA se reciben como JSON, para poder decir qué dato obligatorio falta; en el documento se muestran con la forma de su record.
- El nombre de cada esquema lleva su contexto (`GestionDelArriendo.ReservaCancelada`), porque dos contextos pueden tener clases con el mismo nombre.

En el código generado, cada contexto lo declara en su `Registro.g.cs` (el método `Documentar`), sin paquetes: solo el host referencia los dos paquetes NuGet. `probar.ps1` revisa que el documento y la página respondan.

## Reglas del generador

### Generalidad: el generador no conoce YateGear

El generador debe servir para cualquier modelo ArchiMate que siga las convenciones de diagramación de la tabla "Qué se lee del modelo", no solo para este. Por eso:

- El código del generador (`src/`, `plantillas/` y los `.ps1`) solo conoce las convenciones: tipos de elemento, relaciones y propiedades. Nunca nombres de contextos, raíces, campos ni datos de un modelo en particular.
- Lo que el modelo dice se lee del modelo. Lo que el modelo no dice o deja ambiguo (datos de entrada y salida, estados, transiciones, identidades, respuestas simuladas) se **declara** en el YAML del contexto, con `# supuesto` cuando no sale de la documentación.
- Si a un contexto le falta algo que el código no puede inferir ni declarar en el YAML, se amplía el formato del YAML (y `specs.py` lo revisa) y se documenta. No se escribe a mano en el generador.
- Si el modelo tiene un error o le falta un dato, se corrige el modelo en Archi, no el generador. Las de YateGear quedan en "Discrepancias encontradas" de [YATEGEAR.md](YATEGEAR.md#discrepancias-encontradas).

Los nombres del modelo que antes estaban escritos en los scripts (el proyecto, el contexto, el YAML y el XML del piloto) se quitaron en G1: hoy salen del modelo, de `specs/` o de `salida/contextos.json`. Desde G13, lo generado tampoco menciona YateGear (dice "la aplicación"), y el modelo de `ejemplo/` lo prueba: se genera, compila y pasa sus escenarios, y nada de lo que se genera para él nombra a YateGear ni a su dominio.

### Regla de los datos

Un dato pasa de un lugar a otro por su **nombre** y su **tipo**, que son los del lenguaje ubicuo. Si la entrada de un comando trae "inicio" y el objeto de valor "Fechas del arriendo" tiene el campo "inicio", es el mismo dato. Así no hace falta escribir correspondencias, y `specs.py` puede revisar cada dato. Si un nombre puede ir a más de un destino dentro de un comando, o puede venir de dos campos de la raíz, `specs.py` lo marca como error y dice cuáles son.

**Prioridad cuando un dato llega de varios orígenes:** gana el más reciente. Primero la respuesta del servicio SA (si hay varios, el último que se llamó), luego la entrada del comando y al final la raíz. Así, el valor nuevo que trae un comando reemplaza al que ya estaba guardado. `specs.py` lista estos casos; en el piloto son seis, todos en "Confirmar la reserva" y en "Obtener el nivel de riesgo del cliente".

### Nombres de C#

Los nombres del modelo pasan al código sin tildes: una clase o una propiedad en PascalCase y una variable en camelCase (`src/comun/nombres.py`). Dos casos se resuelven solos:

- Un dato cuyo nombre es una palabra reservada de C# ("base", "ref", "virtual") se escribe con `@` donde es un parámetro (`@base`). En JSON y en la ruta sigue llamándose igual.
- Una raíz, un servicio SA o un evento cuyo nombre coincide con una variable que el código generado ya usa ("Datos", "Eventos", "Resultado") lleva `_` al final como variable (`datos_`). Su clase no cambia.

Si dos elementos dan el mismo nombre de clase, o un nombre choca con uno que el generador necesita (una raíz llamada "Comando"), el generador se detiene y dice cuál: se cambia el nombre en el modelo o en el YAML.

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

Los `.csproj` tratan las advertencias como errores (`TreatWarningsAsErrors`): una advertencia en un archivo manual también detiene la compilación.

Si un manual queda sin su `.g.cs` (por ejemplo, porque se quitó un comando), el generador no lo borra: avisa al final y lo saca de la compilación en el `.csproj`, con un comentario que dice cuál es y por qué. Los `.g.cs` que ya no corresponden sí se borran.

### Bitácora

`GET /<contexto>/bitacora` (por ejemplo `/gestion-del-arriendo/bitacora`) muestra en orden los eventos publicados, los eventos recibidos de otros contextos, las llamadas a los servicios SA simulados y los errores de las políticas. Es **infraestructura del piloto y no sale del modelo**: sirve para ver el flujo y la usa `probar.ps1`. También son infraestructura el repositorio en memoria, el bus de eventos y la espera de eventos.

## Escenarios y pruebas

La sección `escenarios` del YAML define pruebas de punta a punta. Un paso es un comando, una consulta, un evento de otro contexto o un mensaje que recibe un SA. `con` fija valores de su entrada, y `espera` dice el resultado: un evento, un código HTTP (409, 422, 404 o 202), un rechazo con su motivo (`{código: 422, regla: REG-02}`; los campos que se pueden afirmar son `regla`, `requiere`, `identidad`, `operación` y `estado actual`, los de la respuesta de error) o, en una consulta, `{dato de la salida: valor, ...}` (en una lista, cuántos elementos tiene). Sin `espera`, el paso debe responder 2xx. Conviene afirmar el motivo de cada rechazo a propósito: dos rechazos distintos pueden tener el mismo código (en Calificaciones, los dos 409).

Cada paso tiene su identidad. Un comando que crea la raíz recibe la siguiente (el consecutivo, que una solicitud rechazada no gasta, o la que se forma con sus datos), y se revisa que la respuesta la traiga; los demás pasos la toman de `con` o, si no, de la última identidad con el mismo nombre de dato en el escenario (regla de los datos: el calendario de un yate tiene la identidad del yate). Un evento de otro contexto que llega con su propia identidad la toma de `con`. Los consecutivos siguen de un escenario al siguiente, en orden, porque todos corren contra la misma aplicación. Por eso **los escenarios dependen de su orden**: "Calificar dos veces" responde 409 porque "Calificaciones mutuas" corrió antes. Reordenarlos o correr uno solo puede cambiar sus resultados. El generador avisa (sin detenerse) cuando un paso crea una identidad que ya creó otro paso anterior sin esperar el 409, o usa una raíz que ningún paso anterior creó sin esperar el 404.

`specs.py` revisa que los escenarios estén bien escritos: que los nombres existan, que los valores de `con` sean válidos y que `espera` sea un evento que ese paso puede publicar, un código permitido o datos de la salida de la consulta con valores válidos (una lista, por cuántos elementos tiene). No simula los datos. De los escenarios salen `pruebas/<Proyecto>/pruebas.http` y `escenarios.json`, y `probar.ps1` los ejecuta.

`probar.ps1` prueba cada contexto, y después los escenarios entre contextos, con la aplicación recién levantada: con la integración (G12) un evento de un contexto llega a los demás, y así los escenarios de uno no cambian los de otro. Los eventos que un contexto publica en sus propios escenarios también llegan a los demás contextos; ahí pueden fallar (por ejemplo, porque el arriendo no existe en Gestión del arriendo), y ese error queda en el bus sin cambiar el resultado del paso. En los escenarios entre contextos, en cambio, un error en el bus hace fallar el paso (ver abajo).

Los escenarios de cada contexto de YateGear, con lo que prueba cada uno, están en [YATEGEAR.md](YATEGEAR.md#escenarios-de-cada-contexto).

### Escenarios entre contextos

`specs/entre-contextos.yaml` tiene escenarios de punta a punta (S4). Cada paso es un comando, una consulta o un mensaje de un SA del contexto que dice `en`; los eventos entre contextos no se envían a mano: llegan por el bus (G12). `con` fija datos de su entrada, y un dato que no está en `con` y se llama como una identidad ya creada en el escenario toma su valor (regla de los datos): así el yate YATE-0001 y el arriendo ARR-0001 pasan de un contexto a otro. `espera` es un evento o una lista de eventos de cualquier contexto, y de mensajes que envía un SA (G11), que deben ocurrir durante el paso (se buscan en `GET /eventos-entre-contextos` y en la bitácora del contexto que envía). Un paso falla también si durante él falla un suscriptor del bus (los `errores` de `GET /eventos-entre-contextos`), y `probar.py` dice al final cuántos hubo; o un código, o datos de una consulta. `specs.py` revisa el archivo contra los YAML de los contextos de la misma carpeta, y de él salen `pruebas/EntreContextos/pruebas.http` y `escenarios.json`.

Los cuatro escenarios entre contextos de YateGear están en [YATEGEAR.md](YATEGEAR.md#escenarios-entre-contextos).

## Reproducibilidad y trazabilidad

- El mismo modelo y el mismo YAML dan los mismos archivos. `verificar.ps1` lo comprueba solo (dos generaciones seguidas con la misma huella). A mano: `.\.venv\Scripts\python.exe src\herramientas\huella.py salida`, después de generar dos veces, o con dos carpetas para compararlas.
- Lo generado no depende del orden en que se dan los YAML. Todo se ordena por nombre o por ID. Hay dos excepciones, porque ahí el orden tiene significado: los campos van en el orden del modelo, y los pasos de las pruebas en el orden del YAML.
- Sin fechas ni horas en lo generado. Todo en UTF-8 sin BOM y con fin de línea LF. `.gitattributes` (`* text=auto eol=lf`) hace que git entregue LF en todas las máquinas.
- Cada archivo generado empieza con `// Generado desde ArchiMate: <tipo> "<nombre>" (<código>, <ID>).`. En `.csproj` y `.sln` va en la segunda y en la tercera línea, porque su formato lo exige. Los `.json` y el `.csv` no admiten comentarios.
- `salida/trazabilidad/<Proyecto>.csv` tiene una fila por cada elemento o relación del contexto. El proyecto `Integracion` (el bus entre contextos) no tiene filas, porque es infraestructura y no sale de ningún elemento del modelo, y tampoco `pruebas/EntreContextos/`, que sale de los escenarios; el host sí aparece, en la fila del contexto que registra. Las columnas son ID ArchiMate, tipo, nombre, archivo generado y clase. Para revisarlo: `.\.venv\Scripts\python.exe src\herramientas\revisar_trazabilidad.py salida\intermedio\modelo-ddd.json salida`.
- El código generado compila con cero advertencias, y una advertencia es un error de compilación.

## Validaciones

Si una falla, el generador se detiene y dice cuál, con el nombre y el ID del elemento.

| Dónde | Qué revisa |
|---|---|
| `extraer.py` (modelo) | La regla del agregado. Cada objeto de valor tiene exactamente una composición desde su raíz o entidad, con Cardinalidad. Cada `Campo:` tiene un tipo permitido. No hay nombres repetidos dentro del mismo tipo entre los elementos del contexto. Cada comando tiene exactamente un acceso a la raíz de su agregado; además puede leer otras raíces del contexto, y escribir otra raíz es error. Cada evento lo dispara al menos un comando del contexto. Cada comando, consulta y servicio SA tiene un solo contrato. |
| `specs.py` (YAML) | Cada comando, evento, consulta y servicio SA del contexto está en el YAML, y el YAML no nombra nada que no exista. Hay claves conocidas y no repetidas, tipos permitidos y estados de la lista cerrada. Los eventos de cada comando son exactamente los del modelo. Se cumple la regla de los datos. Las políticas, `junto_con` y `con` están completos. La identidad es un consecutivo o se forma con datos que el comando que crea tiene; los `valores` son válidos; cada evento de `requiere` está declarado y el comando tiene su identidad; las correspondencias de `guarda` tienen el mismo tipo; un evento sin `dispara` lo requiere algún comando; las consultas sobre todas filtran por datos de su entrada y sus agregaciones tienen el tipo correcto; una lista tiene nombre y sus datos son de la raíz. Con varios agregados, cada comando, evento y consulta se revisa contra la raíz de su agregado; `crea: si_no_existe` necesita una identidad recibida; las operaciones sobre listas tienen claves que son campos de la lista; un evento que dispara con otra identidad trae la de la raíz en sus datos. Un mensaje de un SA cubre la entrada del comando que dispara (y trae la identidad si el comando no crea); un SA que recibe tiene en el modelo un flujo que entra; un comando sobre todas no escribe y su temporizador cubre su entrada; `List<objeto de valor>` nombra un objeto de valor del contexto; `orden` usa datos de la raíz. Desde Cobros y depósito: la identidad de cada entidad es uno de sus campos; los `calculados` de un comando salen de datos que el comando tiene (antes o después de sus SA); en `usa`, `con`, `entrada` y `salida` nombran datos del SA, y un SA al que se llama tiene en el modelo un flujo que entra (uno que solo sale va con `envia`, G11); `agregar` con correspondencias nombra campos de la lista; `si` y `salvo` usan datos disponibles; `correspondencias` toman datos que llegan; los comandos de un mensaje o de un evento existen y usan la misma identidad; `politicas` nombra comandos con políticas en el modelo, y `junto_con` y `uno_de` todos sus eventos, sin repetir; `envia` sale con un evento del contexto que trae sus datos; una consulta por identidad que lee varias raíces dice con `de` cuál, y las demás tienen la misma identidad. Los escenarios están bien escritos, y los escenarios entre contextos, contra los YAML de sus contextos. **Contratos entre contextos (D2):** lo que un YAML declara recibir de otro contexto llega en el evento tal como lo publica el YAML de ese contexto: el dato con que llega, cada dato con el mismo tipo, y ningún dato obligatorio que se publique como opcional. Se revisa contra los YAML de la misma carpeta, en `specs.py` y en `generar.py` antes de escribir nada. |

Las validaciones tienen sus propias pruebas: `pruebas-validador/casos.yaml` tiene copias rotas a propósito de los YAML de `specs/` (al menos una por capacidad, de G1 a G12, y las de los contratos entre contextos), cada una con el error que debe dar, y `src/herramientas/probar_validador.py` comprueba que salga (lo corre `verificar.ps1`). Cada clave nueva del YAML trae su caso: si un caso deja de fallar, `specs.py` dejó de revisar algo.

## Supuestos

Son los supuestos del generador y de la aplicación que genera, para cualquier modelo. Los del modelo y de los YAML de YateGear (GEN-SUP-05 a 34, 37 a 47, 49 a 59 y 65 a 85) están en [YATEGEAR.md](YATEGEAR.md#supuestos). Los números no se reutilizan.

De la aplicación generada:

| ID | Supuesto | Por qué |
|---|---|---|
| GEN-SUP-02 | Los datos se guardan en memoria y se pierden al reiniciar. | El piloto prueba la estructura y el flujo, no la persistencia. |
| GEN-SUP-03 | Los sistemas externos están simulados y responden con valores fijos del YAML. | Así el flujo es repetible y no depende de sistemas que no controlamos. |
| GEN-SUP-04 | El bus de eventos es síncrono y en memoria. Si un suscriptor falla, el error queda en la bitácora y no deshace el comando que publicó el evento. | El evento ya ocurrió; deshacerlo cambiaría el hecho que registra. |

Del generador:

| ID | Supuesto | Por qué |
|---|---|---|
| GEN-SUP-35 | Los eventos de otros contextos que un comando requiere (`requiere`, D5) se guardan en memoria, por su nombre y su identidad, y se pierden al reiniciar; si llega otro igual, reemplaza al anterior. | Cada contexto guarda su propia copia de lo que recibe (V8-DEC-04), y el piloto no prueba la persistencia (GEN-SUP-02). |
| GEN-SUP-36 | Una identidad formada con datos une sus partes con `/`, en el orden del YAML; un enum va con su nombre de C# (por ejemplo `ARR-0001/Cliente`). | Es legible, es estable y no choca con los prefijos de los consecutivos. |
| GEN-SUP-48 | `crea: si_no_existe` crea la raíz con el primer estado de su lista, y solo la guarda si el comando termina bien. | Una solicitud rechazada no debe dejar rastro (como el consecutivo que no gasta número). |

De varios comandos, políticas e integración:

| ID | Supuesto | Por qué |
|---|---|---|
| GEN-SUP-60 | Un evento o un mensaje que dispara varios comandos los corre en orden; si uno falla, los siguientes no corren y la respuesta es la de ese error (los anteriores ya ocurrieron y publicaron sus eventos). | Es predecible y deja ver cuál falló. En el contrato firmado, si el depósito no se bloquea, no se cobra nada. |
| GEN-SUP-61 | Los eventos de una política con varios disparos (`junto_con`, `uno_de`) esperan en memoria, por identidad, y se pierden al reiniciar. | Como los de otros contextos (capa 3) y GEN-SUP-02. |
| GEN-SUP-62 | Cada contexto y los escenarios entre contextos se prueban con la aplicación recién levantada. | Con la integración, un evento de los escenarios de un contexto llega a los demás. |
| GEN-SUP-63 | Un evento se entrega primero a los demás contextos y después a las políticas del contexto que lo publica. | Así, con la inspección, Gestión del arriendo registra la devolución antes de que lleguen las cuentas cerradas, que la necesitan. |
| GEN-SUP-64 | Una llamada a un SA que no cumple su condición (`si`, `salvo`) no se hace, y su salida queda en null. | Un dato que falta se nota: si se usa sin la condición, responde 422 por el dato faltante. |

## Fuera de alcance

El generador construye una primera versión de referencia que demuestra el camino del modelo al código. Estas cosas quedan fuera a propósito:

- **De la aplicación generada:** autenticación (por eso no se revisa quién llama: GEN-SUP-46 y 79), base de datos (todo en memoria: GEN-SUP-02), microservicios (un solo programa: D1), paginación, errores en formato `ProblemDetails` (las respuestas de error tienen su propio contrato, el que afirman los escenarios) y la traducción del formato propio de cada sistema externo.
- **Del generador:** una versión del formato del YAML (el generador y los YAML cambian juntos, en el mismo repositorio), un archivo de configuración (el puerto se elige con `generar.ps1 -Puerto`, y los prefijos y las propiedades en español son la convención misma), empaquetarlo como una herramienta instalable, integración continua y un asistente que escriba el YAML a partir de la documentación.

## Limitaciones conocidas

- Una entidad solo puede estar compuesta por la raíz, y un objeto de valor compuesto por una entidad no se genera (`specs.py` lo dice).
- Las demás raíces de una consulta por identidad deben tener el mismo nombre de identidad que la raíz por la que se consulta.
- Los comandos que dispara un evento o un mensaje no forman una sola operación: si uno falla, los anteriores no se deshacen (GEN-SUP-60).
- Cada comando calcula sus valores con sus propias tarifas de prueba (archivos manuales); no hay una tabla de tarifas compartida.
- Un mensaje que recibe un SA llega con los nombres de los datos del arriendo: la traducción del formato propio del sistema externo (SA-05, SA-07) no se genera. La alerta de pérdida de señal sale por SA-05 cuando ocurre el evento "Pérdida de señal del yate" (`envia`); el comando no llama al SA.
- Una política interna entre raíces con distinta identidad todavía no se genera (`specs.py` lo dice).
- E2E-01 (no se cierra el arriendo antes de los ajustes de dinero) la cumple el flujo: el arriendo se cierra con "Cuenta del arriendo cerrada", que publica Cobros al cerrar las cuentas. Una llamada directa al endpoint de SB-09 con `nuevo estado: cerrado` no lo revisa, porque Gestión del arriendo no guarda el estado de la cuenta.
- Los servicios SA se llaman antes de `ValidarReglas`, porque las reglas usan sus respuestas (REG-01 necesita el estado del contrato). Por eso una solicitud rechazada por una regla ya consultó al CRM simulado.
- Los escenarios de cada contexto siguen enviando los eventos de otros contextos por sus endpoints de prueba; el recorrido completo por el bus se prueba en los escenarios entre contextos.
- Si se quita el YAML de un contexto, el generador borra sus archivos generados pero no su código a mano: avisa que esa carpeta quedó suelta.
- En el documento OpenAPI, el esquema de un evento muestra también `nombreEnElModelo` e `identidad`, dos propiedades calculadas del record que no hace falta enviar. Las respuestas de error (404, 409, 422) se listan sin su esquema.
- Un dato de la entrada de una consulta no puede llamarse "manejador", el parámetro con que su endpoint recibe el manejador.
- El temporizador de un comando sobre todas usa la hora local del equipo (`DateTime.Now`).
- Las pruebas del validador (`pruebas-validador/casos.yaml`) rompen los YAML de YateGear: no corren con otro modelo (`verificar.ps1 -SinPruebasDelValidador`).
- Los módulos de `validacion/` y `generacion/` se reparten una sola clase cada uno (`Revisor` y `Generador`), y el YAML se interpreta dos veces, al revisarlo y al generar. Las funciones más largas que quedan son `preparar_comando` (unas 200 líneas) y `preparar_escenarios` (unas 150).

## Códigos

Los códigos nombran las capacidades y las decisiones con que se construyó el generador. Aparecen en este documento, en los comentarios de `src/` y de las plantillas, y en los comentarios de lo generado.

Capacidades del generador:

| Código | Capacidad |
|---|---|
| G1 | Salida con varios contextos: una solución con un proyecto por contexto, y pruebas, escenarios y trazabilidad para cada uno. |
| G2 | Varios agregados en un contexto, y `crea: si_no_existe`. |
| G3 | Identidades que no son un consecutivo: recibida o formada con datos. |
| G4 | Objetos de valor con Cardinalidad Muchos en `guarda`: agregar, reemplazar o quitar. |
| G5 | Consultas sobre varias raíces o varios agregados: listas, filtros y agregaciones. |
| G6 | Un comando lee otra raíz del contexto. |
| G7 | Servicio SA de entrada: el sistema externo le envía mensajes a la aplicación (`recibe`). |
| G8 | Comando disparado por tiempo: `sobre: todas` con `temporizador`. |
| G9 | Entidades con identidad propia dentro de una raíz. |
| G10 | Políticas internas con varios disparos: `junto_con` y `uno_de`. |
| G11 | Servicio SA solo de salida: la aplicación envía mensajes (`envia`). |
| G12 | Integración entre contextos por el bus, con los nombres de los datos alineados. |
| G13 | Uso con otro modelo: la guía de modelado, el modelo de ejemplo y lo generado sin nombrar a YateGear. |

Decisiones:

| Código | Decisión |
|---|---|
| D1 | Los contextos corren en un solo programa y se comunican por un bus de eventos compartido. |
| D2 | En un evento entre contextos, quien recibe usa los nombres de los datos de quien publica. |
| D3 | Las discrepancias 1 y 2 de YateGear: una se cerró sin cambios y la otra se corrigió en el modelo. |
| D4 | La identidad del Yate es un consecutivo. |
| D5 | Un contexto guarda su copia de los eventos de otros contextos que sus comandos necesitan (`requiere`). |
| D6 | Los tiempos del temporizador van en el YAML, y su endpoint fuerza la revisión con una hora fija. |
| D7 | Las políticas con varios disparos se escriben en la sección `politicas`. |
| D8 | Las fuentes sin nombre de las agrupaciones de la V2 se arreglaron en Archi. |

Pasos del cierre que también se citan:

| Código | Qué fue |
|---|---|
| S4 | Los escenarios de punta a punta entre contextos (`specs/entre-contextos.yaml`). |
| S6 | Los contratos entre contextos: `specs.py` revisa que lo que un contexto recibe llegue como lo publica el otro. |

Otros identificadores vienen de la documentación del modelo de YateGear (README principal del repositorio): las vistas (V4, V6.1, ...), sus decisiones y supuestos (V6-DEC-17, V8-SUP-02, ...), los servicios (SB-07, SA-02), las reglas (REG-01) y los hallazgos de la entrevista (H-09).
