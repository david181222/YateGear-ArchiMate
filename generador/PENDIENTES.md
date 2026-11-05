# Pendientes del generador

Estado al 5 de noviembre de 2026. Edwin terminó el piloto (Contexto Gestión del arriendo) y José lleva J1 a J7 (ver "Estado actual"). **Ahora sigue José con J8 (entrega) y después Santiago.** Aquí está lo que falta, lo que hay que decidir y quién hace cada cosa. Cada quien actualiza este archivo al terminar su parte: marca lo que cerró y escribe las decisiones tomadas.

Cómo funciona el generador y cómo se ejecuta: [README.md](README.md).

## 1. Qué está hecho (parte de Edwin)

Las cifras de esta sección son las de la entrega del piloto (3 de noviembre); las de hoy están en "Estado actual".

- El generador completo para un contexto: exporta el modelo con la ACLI de Archi, lo lee con pyArchimate, valida el modelo y el YAML, y genera el proyecto C# (.NET 8) con sus tres capas: estructura, transiciones de estado y eventos de otros contextos. Compila con cero advertencias.
- El piloto, "Contexto Gestión del arriendo": `probar.ps1` pasa los 19 pasos de sus 4 escenarios. REG-01 está escrita a mano en `salida/GestionDelArriendo/Comandos/ConfirmarLaReserva.cs`.
- Es determinista: el mismo modelo y el mismo YAML dan la misma huella. La trazabilidad está completa (161 filas), con 33 supuestos (GEN-SUP-02 a 34) y 3 discrepancias documentadas en el README. GEN-SUP-01 se retiró porque la tecnología es una decisión del equipo.

### Estado actual (5 de noviembre, después de J7)

| Qué | Hoy | Cómo se recalcula |
|---|---|---|
| Contextos generados | 4 de 5: Gestión del arriendo, Calificaciones, Disponibilidad de yates y Operación del arriendo (falta Cobros y depósito, de Santiago). | `generar.py` lista los generados y los que no tienen YAML. |
| Pasos de los escenarios | 63, todos en verde: 19, 10, 18 y 16. | `probar.ps1` |
| Trazabilidad | 400 filas: 163, 47, 86 y 104; todos los elementos de los cuatro contextos están. | `src/revisar_trazabilidad.py salida/intermedio/modelo-ddd.json salida` |
| Supuestos | 58: GEN-SUP-02 a 59 (GEN-SUP-01 se retiró). | Tablas "Supuestos" del README. |
| Discrepancias | 9: la 1 cerrada sin cambios, la 3 abierta (G12, D2) y las otras 7 corregidas en el modelo. | Tabla "Discrepancias encontradas" del README. |

Estas cifras cambian con cada contexto: al terminar uno, se actualiza esta tabla.

## 2. Lo que le falta al generador

Hoy el generador produce **1 de los 5 contextos**. Para los otros cuatro le faltan estas capacidades:

| ID | Qué falta | Lo necesita | Qué pasa hoy | Quién |
|---|---|---|---|---|
| G1 | **Salida con varios contextos**: extraer todos los contextos, una solución con un proyecto por contexto, y pruebas, escenarios y trazabilidad para cada uno. Además, `ejecutar.ps1` y `probar.ps1` con `-Contexto`. Según D1: un host que referencia los contextos, ningún contexto referencia a otro, y el bus entrega los eventos por nombre y en JSON; si a un evento le falta un dato, el receptor lo rechaza con `DatoFaltante`. También salen del código los nombres del piloto que hoy están escritos a mano (sección "Generalidad" del README). | Todos | **Hecho (4 nov 2026, J3).** Un proyecto por contexto con YAML, el host con el nombre del modelo y el proyecto `Integracion` con el bus entre contextos. `extraer.py` toma todos los contextos del modelo por convención; los scripts leen `salida/contextos.json`. Probado también con dos contextos a la vez en el mismo host (19 de 19 cada uno). | José |
| G2 | **Varios agregados en un contexto.** Incluye escenarios con varias raíces (hoy suponen una sola raíz con consecutivo) y `crea: si_no_existe`, porque ningún comando del modelo crea el Calendario del yate. | Disponibilidad (2), Operación (3), Cobros (3) | **Hecho (J6, 4 nov 2026).** Cada comando, evento, consulta y paso de escenario usa la raíz de su agregado; un repositorio por raíz. Incluye `crea: si_no_existe` y escenarios con varias raíces (la identidad se lleva por el nombre del dato). | José |
| G3 | **Identidades que no son un consecutivo:** recibida (el número del arriendo o el del yate), compuesta (yate + hora; arriendo + quién califica) o consecutivo con otro prefijo. La identidad se declara en el YAML con los nombres de los datos, y el receptor de eventos de otros contextos la arma por nombre: hoy supone que la identidad del evento es la de la raíz local, y en SB-05 el evento trae el arriendo pero el Calendario se identifica por el yate. | Calificación, Calendario, Actas, Lectura, Depósito, Cuenta, Yate, Reclamo | **Hecho (J5 y J6, 4 nov 2026).** Identidad consecutiva con cualquier prefijo, compuesta o recibida (`identidad > de`); un evento de otro contexto declara con qué dato llega, y si dispara con otra identidad, la de la raíz sale de sus datos por su nombre (SB-05). | José |
| G4 | **Objetos de valor con Cardinalidad Muchos** en `guarda`: agregar, reemplazar o quitar, con una clave para saber cuál (SB-05 aparta, ocupa y suelta por arriendo), y `guarda` dentro de cada resultado. | Rango de fechas, Daño encontrado | **Hecho (J6, 4 nov 2026).** `{lista: agregar}`, `{lista: {reemplazar: [claves]}}` (404 si no hay) y `{lista: {quitar: [claves]}}`; `guarda` y `valores` también por resultado. Rango de fechas hecho; Daño encontrado va con J7. | José |
| G5 | **Consultas sobre varias instancias o varios agregados:** listas, filtros y promedios. | SB-04, SB-26 y SB-30 (José); SB-18 (Santiago) | **Casi hecho (J5 a J7):** `sobre: todas` con `filtro`, `filtro_manual`, agregaciones (SB-30) o una lista ordenada (`orden`; SB-04 y SB-26). Falta una consulta por identidad sobre varias raíces (SB-18, Santiago). | José y Santiago |
| G6 | **Leer otra raíz del contexto** (`lee_tambien`). | SB-24 lee el Acta de entrega | **Hecho (J7, 5 nov 2026).** Las otras raíces que el comando lee en el modelo se cargan por el dato con el nombre de su identidad (404 si no existen) y llegan en `datos` (SB-24). | José |
| G7 | **SA de entrada:** el sistema externo es el que llama a YateGear. | SA-05 (actas de la marina --> SB-22 y SB-23), SA-07 (lecturas del proveedor --> SB-25) | **Hecho (J7, 5 nov 2026).** `servicios_sa > recibe`: un receptor por SA y un endpoint por mensaje, que dispara el comando por nombre de dato y puede crear la raíz (SA-05 y SA-07). La traducción del formato propio del sistema externo no se genera. | José |
| G8 | **Comando disparado por tiempo.** | SB-27 Detectar la pérdida de señal | **Hecho (J7, 5 nov 2026).** Comando `sobre: todas` (el archivo manual elige las raíces y se publica un evento por cada una) con `temporizador` (`BackgroundService`); su endpoint fuerza la revisión con un "ahora" fijo. Probado corriendo cada minuto. | José |
| G9 | **Entidades** con identidad propia dentro de una raíz. | Cobro (Muchos), en Cuenta del arriendo | Se detiene con un mensaje. | Santiago |
| G10 | **Políticas internas con varios disparos:** "junto con" y "uno de". | SB-17: "Cargos del cierre cobrados" y, además, "Depósito liberado" o "Daños descontados del depósito" | `junto_con` existe solo para eventos de otros contextos. | Santiago |
| G11 | **SA solo de salida** (lenguaje publicado). | SA-08, envío de arriendos cerrados a Finanzas | Funciona como una llamada con respuesta; hay que revisarlo. | Santiago |
| G12 | **Integración entre contextos** según D1, con los nombres de los datos de los eventos alineados (D2). El host y el bus los construye José en G1; aquí se conectan las suscripciones entre contextos. | Los 11 eventos entre dominios de la V6 | Los eventos de otros contextos se simulan con endpoints de prueba. | Santiago |
| G13 | **Documentación para usar el generador con otro modelo:** las convenciones de diagramación que lee, y la referencia completa del formato del YAML (cada clave, para qué sirve y qué revisa `specs.py`). Cada capacidad nueva del YAML se documenta ahí al agregarla. | Cualquier modelo que siga las convenciones | **En parte (4 nov 2026):** el README tiene la sección "Formato del YAML" con todas las claves. Falta una guía de las convenciones de diagramación para quien modele en Archi desde cero. | José (y quien agregue claves) |

## 3. Decisiones por tomar

**Ya decidido:** el proyecto generado es C# con una API web (ASP.NET Core, .NET 8). No es una decisión pendiente.

Cuando una de las siguientes se decida, se escribe la decisión en la columna "Decidido" y se agrega al README del generador.

| ID | Qué hay que decidir | Opciones | Recomendación | Quién la lleva | Antes de | Decidido |
|---|---|---|---|---|---|---|
| D1 | Cómo se comunican los contextos. | (a) Un solo programa con un bus de eventos compartido. (b) Una aplicación por contexto, que se llaman por HTTP. | (a): los 11 eventos entre dominios fluyen solos y el recorrido completo se prueba con un solo `probar.ps1`. | José la propone y el equipo decide | J3, porque cambia G1 | **(a) (4 nov 2026):** un solo programa, porque es la primera versión del proyecto en C#. Ningún contexto referencia a otro y el bus entrega por nombre y en JSON (ver G1 y G12). |
| D2 | Nombres de los datos de los eventos entre contextos. Hoy no coinciden: es la discrepancia 3 del README, con los supuestos GEN-SUP-19 a 24. | El que recibe usa los nombres del que publica, o se acuerda un nombre por dato. | El que recibe usa los nombres del YAML del que publica. Donde no calce con su modelo, se acuerda en equipo, porque son Partnership (V8-SUP-02). | Quien escriba cada YAML; Santiago revisa todo en G12 | Cada YAML | |
| D3 | Discrepancias 1 (SB-11) y 2 (SA-02) del README del generador. | Corregir el modelo y el README de entrega, o dejarlas documentadas. | Decidirlo en equipo. Si se corrige el modelo, se hace en Archi y se vuelve a generar. | José | J3 | **(4 nov 2026):** la 1 se cierra sin cambios (refinamiento entre la V4 y la V6); la 2 se corrigió en el modelo y en el README principal. Ver "Discrepancias encontradas" del README del generador, donde también están las nuevas 4 y 5, ya corregidas. |
| D4 | Identidad del Yate. | Consecutivo (por ejemplo `YATE-0001`), o la que dé Comercial al registrarlo. | Consecutivo, igual que el arriendo. | José | J6 | **Consecutivo `YATE-0001` (4 nov 2026).** |
| D5 | Cómo sabe Calificaciones que el arriendo está cerrado (SB-28 y SB-29 solo se permiten con el arriendo cerrado). | (a) Calificaciones guarda su copia de los "Arriendo cerrado" que recibe. (b) Queda como regla escrita a mano en `ValidarReglas`. | (a): la V8 dice que Calificaciones toma el arriendo cerrado tal como lo define Gestión del arriendo, y cada contexto guarda su propia copia (V8-DEC-04). Se marca como supuesto. | José | J5 | **(c) (4 nov 2026):** un comando declara en el YAML `requiere: [Arriendo cerrado]`; si ese evento no ha llegado para su identidad, responde 409. Reutiliza la memoria de `junto_con`. Va como supuesto desde GEN-SUP-35. |
| D6 | Pérdida de señal (SB-27): cada cuánto se revisa y desde cuántos minutos sin lecturas se avisa (V4-SUP-04). | Valores en el YAML. | Un parámetro en el YAML y un endpoint de prueba que fuerce la revisión, para que `probar.ps1` no tenga que esperar. | José | J7 | **(5 nov 2026):** cada 5 minutos, desde 30 minutos sin lecturas (supuestos GEN-SUP-54 y 55), y "ahora" en la entrada para que la prueba no espere.
| D7 | Cómo se escriben en el YAML las políticas con varios disparos (SB-17). | Extender `junto_con` a las políticas internas y agregar "uno de". | Esa misma. | Santiago | S2 | |
| D8 | Fuentes de las 6 agrupaciones de área de la V2 (opcional). | Arreglarlas en Archi o dejarlas. | Arreglarlas: así desaparecen los 6 errores que muestra la exportación. | José | Cuando pueda | **Arreglado (4 nov 2026):** las 6 agrupaciones de la V2 tienen fuente explícita (Sans 9, negrita). La exportación sale sin errores. |

## 4. Reparto del trabajo

### José (sigue ahora)

| Paso | Qué hacer | Listo cuando |
|---|---|---|
| J1 | Clonar el repositorio en otra carpeta y correr `generar.ps1` y `probar.ps1` desde cero, como indica el README. | **Hecho en Linux (4 nov 2026):** 19 de 19, 0 advertencias, `salida/` idéntica a la versionada. Para eso los `.ps1` quedaron multiplataforma (sección 6). **Confirmado en Windows** por el equipo: también funciona. |
| J2 | Llevar D1 y D3 al equipo. | **Hecho (4 nov 2026):** D1 y D3 decididas; además se corrigieron en el modelo las discrepancias 2, 4 y 5. |
| J3 | G1: salida con varios contextos. | **Hecho (4 nov 2026):** el piloto da 19 de 19, 0 advertencias, trazabilidad completa y huella estable en dos generaciones seguidas. |
| J4 | G2 y G3: varios agregados e identidades nuevas. **Se reparte:** cada G se construye con el primer contexto que lo usa, porque G2 no se puede probar con el piloto (tiene un solo agregado). G3 y G5 (promedio) van con J5; G2 y G4 van con J6. | El piloto sigue en verde en cada paso. **Estado (4 nov 2026):** G3 en parte con J5 (falta disparar con otra identidad); G2 sin empezar. J4 se cierra con J6. **Hecho con J6 (4 nov 2026).** |
| J5 | Contexto Calificaciones: YAML con escenarios. Necesita G3 (identidad compuesta), G5 (promedio) y D5. | **Hecho (4 nov 2026):** 10 de 10 (con dos 409 a propósito), el piloto sigue en 19 de 19 en el mismo programa, 0 advertencias, trazabilidad completa y huella estable. Supuestos GEN-SUP-35 a 40. |
| J6 | Contexto Disponibilidad de yates. Necesita G2, G4 (Rango de fechas), G5 (yates disponibles) y D4. Los eventos de Gestión del arriendo (Reserva solicitada, confirmada, cancelada y no realizado por riesgo alto) disparan SB-05, y `con` fija la acción: apartar, ocupar o soltar. | **Hecho (4 nov 2026):** 18 de 18 (cinco rechazos a propósito: 422 por REG-01, REG-02, INT-CON y NOR-01, y 404), con los otros dos contextos en verde en el mismo programa, 0 advertencias, trazabilidad completa y huella estable. Reglas escritas a mano en los archivos manuales. Discrepancias 6 a 8 corregidas en el modelo; supuestos GEN-SUP-41 a 48. |
| J7 | Contexto Operación del arriendo. Necesita G2, G3, G4 (Daño encontrado), G5 (recorrido), G6, G7, G8 y D6. | **Hecho (5 nov 2026):** 16 de 16 (seis rechazos a propósito con su motivo), con los otros tres contextos en verde en el mismo programa, 0 advertencias, trazabilidad completa y huella estable. Reglas y cálculos escritos a mano; discrepancia 9 corregida en el modelo; supuestos GEN-SUP-49 a 59. |
| J8 | Entregar a Santiago. | Los 4 contextos en verde, el README y este archivo actualizados, y commit hecho. |

### Santiago (cuando José termine)

| Paso | Qué hacer | Listo cuando |
|---|---|---|
| S1 | Clonar el repositorio y correr todo desde cero. | Los 4 contextos de José dan todos sus pasos en verde. |
| S2 | Contexto Cobros y depósito: 3 agregados, 8 comandos y 4 SA. Necesita G9 (Cobro), G10 (SB-17), G11 (SA-08), G5 (SB-18 lee la Cuenta y el Depósito) y D7. | Cumple la sección 5. |
| S3 | G12, la integración: aplicar D1 y alinear los nombres de los datos de los eventos en los 5 YAML (D2). Los endpoints de eventos de otros contextos pueden quedar para las pruebas. | Un evento publicado en un contexto dispara el comando del otro sin pasos a mano. |
| S4 | Un escenario de punta a punta entre contextos: desde "Consultar yates disponibles" hasta el envío a Finanzas (SA-08), pasando por los 11 eventos entre dominios. | `probar.ps1` lo da en verde. |
| S5 | Cierre: el README del generador (tablas, supuestos, discrepancias y limitaciones), una mención del generador en el README principal ("Contenido del repositorio" y "Tabla de aportes") y la verificación final. | Huella estable, trazabilidad completa, cero advertencias, todos los escenarios en verde y commit hecho. |

## 5. Cuándo está terminado un contexto

- [ ] `specs/<contexto>.yaml` lleva `# supuesto` en cada dato que no salga del README. Sus escenarios incluyen al menos un rechazo a propósito (409 o 422).
- [ ] `specs.py` no da errores.
- [ ] `generar.ps1` compila con 0 advertencias.
- [ ] `probar.ps1` da todos los pasos en ✓.
- [ ] `src/huella.py` da la misma huella en dos generaciones seguidas.
- [ ] `src/revisar_trazabilidad.py` no encuentra faltantes.
- [ ] Las reglas de contrato que necesitan los escenarios están escritas a mano en los archivos manuales (`.cs`, nunca en los `.g.cs`).
- [ ] El README del generador está al día: supuestos nuevos desde GEN-SUP-35, sin repetir números; discrepancias nuevas; y la tabla "qué genera" si hay elementos nuevos.
- [ ] Este archivo está al día: los G y los D que se cerraron.

## 6. Cosas que conviene saber

- La aplicación se corre desde `salida/`, para que `dotnet` use el SDK 8 de `global.json`. `ejecutar.ps1` y `probar.ps1` ya lo hacen.
- Los `.ps1` van en UTF-8 con BOM. Sin BOM, Windows PowerShell 5.1 rompe las tildes.
- Los `.g.cs` no se editan, porque el generador los reescribe. El código a mano va en los `.cs` manuales, que el generador crea una sola vez y nunca sobrescribe.
- `dotnet run` puede dejar vivo el proceso del host (en `salida/<Modelo>/bin/`). Si la compilación falla porque el ejecutable "está siendo usado por otro proceso", hay que detenerlo. `probar.ps1` lo detiene solo al terminar.
- La ACLI exporta lo que está **guardado** en disco, y funciona aunque Archi esté abierto. Los 6 errores `IllegalArgumentException` de la V2 ya no salen (D8). Si vuelve a salir uno, alguna caja quedó con una fuente sin nombre.
- Antes de editar en Archi, revisa que el modelo abierto sea `modelo/YateGear.archimate` del repositorio (Archi recuerda los modelos abiertos antes, y puede haber copias viejas en otras carpetas).
- En el modelo, todo se busca por tipo y por relación, nunca solo por nombre. Las agrupaciones del canvas de la V11 también agregan comandos y eventos: solo cuentan las "Agregado ...".
- El puerto (5080) se cambia en `PUERTO`, en `src/generar.py`. Para una sola vez: `-Puerto`. Es uno solo para todos los contextos, porque corren en el mismo programa.
- Para agregar un contexto basta con escribir su `specs/<contexto>.yaml`: `generar.ps1` genera todos los que tienen YAML, y `probar.ps1 -Contexto "<nombre>"` prueba solo uno.
- Un cambio en el modelo se hace en Archi y se guarda en `modelo/YateGear.archimate`; después se vuelve a correr `generar.ps1`.
- Si una revisión nueva pasa a la primera, conviene romper a propósito una copia del YAML para comprobar que de verdad detecta el error.
- Los `.ps1` corren en Windows y en Linux (`pwsh`). Las rutas van con `/`, que sirve en los dos. Para detener la aplicación, `probar.ps1` la busca por la ruta de su ejecutable y no por el nombre, porque en Linux el nombre del proceso se corta a 15 caracteres.
- En Linux, el venv se crea con la ruta real de Python 3.13. Si se crea desde un enlace (como el `python3.13` que `uv` deja en `~/.local/bin`), el venv no encuentra la biblioteca estándar y `ensurepip` falla con "No module named 'encodings'".
