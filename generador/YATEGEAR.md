# YateGear en el generador

Este documento reúne lo que es propio de YateGear al usar el [generador](README.md): sus escenarios, las discrepancias que el generador encontró en el modelo y los supuestos de sus YAML (`specs/*.yaml`) y de su código a mano (`salida/`). El manual del generador, que sirve para cualquier modelo, es el [README](README.md).

## Índice

- [Escenarios de cada contexto](#escenarios-de-cada-contexto)
- [Escenarios entre contextos](#escenarios-entre-contextos)
- [Discrepancias encontradas](#discrepancias-encontradas)
- [Supuestos](#supuestos)

## Escenarios de cada contexto

Cómo se escribe y cómo se juzga un escenario está en "Escenarios y pruebas" del [README](README.md#escenarios-y-pruebas).

Gestión del arriendo:

| Escenario | Arriendo | Qué prueba |
|---|---|---|
| Principal hasta el cierre | ARR-0001 | Llega "Yate registrado" (se recuerda la copia del yate); solicitud con esa copia, riesgo aceptable, el cliente cumple los requisitos (SB-11), los dos eventos de Cobros (`junto_con`: el primero responde 202), confirmación con REG-01 activa, aviso por la política, entrega, devolución y cierre. |
| Riesgo alto | ARR-0002 | El cliente de prueba `CLI-RIESGO-ALTO` termina en "no realizado por riesgo alto". |
| Cancelación | ARR-0003 | Cancelar, y luego registrar el avance de un arriendo cancelado: 409 a propósito. |
| Confirmar sin riesgo evaluado | ARR-0004 | Confirmar sin evaluar el riesgo: 422 por REG-01, escrita a mano. |
| Yate fuera del inventario | - | Una solicitud para un yate del que no llegó "Yate registrado": 409 a propósito (`requiere`), sin gastar consecutivo. |
| Licencia vencida | ARR-0005 | La licencia vence antes del fin del arriendo: SB-11 responde que no cumple, con el motivo (H-09, NOR-01). |

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

## Escenarios entre contextos

Están en `specs/entre-contextos.yaml`.

| Escenario | Qué prueba |
|---|---|
| Del inventario al envío a Finanzas | Se registra el yate (Gestión del arriendo recuerda su copia) y está disponible; la solicitud aparta las fechas; con el riesgo aceptable, SA-02 envía los datos para el contrato; el contrato firmado bloquea el depósito y cobra, Gestión del arriendo confirma, Disponibilidad ocupa las fechas y sale el aviso a la marina; la marina entrega el yate y Gestión inicia el arriendo; llega una lectura y el recorrido la muestra; una hora sin lecturas, Operación avisa la pérdida de señal y SA-05 envía la alerta a la marina; la inspección con daños dispara la devolución, las diferencias, los cargos del cierre, el descuento del depósito, el reclamo a la aseguradora, el cierre de las cuentas, el arriendo cerrado y el envío a Finanzas (SA-08); el arriendo queda cerrado y el cliente califica al propietario. |
| Cancelación con reembolso | Otro arriendo del mismo yate se paga y se cancela 9 días antes: Disponibilidad suelta las fechas y Cobros libera el depósito y devuelve el alquiler. |
| Riesgo alto | El cliente de prueba de riesgo alto: no se arrienda y las fechas se sueltan. |
| Cancelación antes del pago | Una solicitud se cancela antes del contrato firmado: Disponibilidad suelta las fechas, y en Cobros no aplica (`si_existe`), sin errores en el bus. |

Entre los cuatro pasan los 11 eventos entre dominios de la V6 (Reserva solicitada, confirmada y cancelada, Arriendo no realizado por riesgo alto, Riesgo aceptable obtenido, Alquiler y seguro cobrados, Depósito bloqueado, Yate entregado al cliente, Inspección de devolución registrada, Diferencias determinadas y Cuenta del arriendo cerrada), además de "Arriendo cerrado" hacia Calificaciones y "Yate registrado" hacia Gestión del arriendo. En la prueba no queda ningún error en el bus, y `probar.py` lo comprueba.

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

Los supuestos del generador y de la aplicación que genera (GEN-SUP-02 a 04, 35, 36, 48 y 60 a 64) están en el [README](README.md#supuestos).

GEN-SUP-01 se retiró: la tecnología (C# con API) es una decisión del equipo y no un supuesto (sección "Tecnología"). Su número no se reutiliza.

GEN-SUP-20 a 24 se retiraron en G12 (7 nov 2026): los datos de los eventos entre contextos ya no se suponen; se declaran con los nombres del contexto que los publica, con correspondencias donde hace falta (discrepancia 3, D2). GEN-SUP-19 se cumplió: los datos se revisaron al generar los cinco contextos. Sus números no se reutilizan.

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

Del generador, con Operación del arriendo:

| ID | Supuesto | Por qué |
|---|---|---|
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
| GEN-SUP-85 | `VerificarLosRequisitosDelCliente.cs` | La licencia de navegación está vigente si vence el día del fin del arriendo o después; no se compara con la fecha de hoy (como GEN-SUP-54, sin reloj). Sin terceros autorizados, el cliente no autorizó compartir sus datos (H-19). |
