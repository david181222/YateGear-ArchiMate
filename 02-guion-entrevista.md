# Guion de entrevista al experto del negocio
## Tema 5: Gestión del arrendamiento de yates de terceros

**Mensaje de arranque:**
> *Buenos días, Hideo. Somos el equipo de arquitectura que va a diseñar el software de gestión de arrendamientos que solicitó YateGear. Queremos entender bien el negocio antes de diseñar. ¿Podemos empezar?*

**Tipos de pregunta:** **[A]** abierta · **[P]** profundización · **[V]** validación.

**Alcance del Tema 5** (para trazar cada pregunta):
**A1** Inventario por marina y yates habilitados o bloqueados · **A2** Reserva y notificación al propietario y a la marina · **A3** Pagos (alquiler, depósito, seguro y combustible) · **A4** Seguimiento en tiempo real de ubicación y combustible · **A5** Cierre: devolución, inspección y ajustes de dinero · **A6** Calificaciones mutuas.

## 1. Contexto de la organización

- **CTX-01** [A] ¿Cómo funciona el negocio de YateGear? ¿Cómo gana la empresa y cómo gana el propietario?
- **CTX-02** [P] ¿Qué áreas tiene la empresa y qué hace cada una en un arriendo?
- **CTX-03** [V] Entendemos que YateGear no es dueña de los yates y que es intermediaria entre propietarios, marinas y clientes. ¿Es correcto?

## 2. Motivación del negocio

- **MOT-01** [A] ¿Por qué necesitan este software ahora y qué problemas tienen hoy? *(impulsores y evaluación)*
- **MOT-02** [P] ¿Quiénes se benefician del software y qué espera cada uno? *(interesados)*
- **MOT-03** [P] ¿Qué metas tienen y qué resultados medibles esperan lograr con el software? *(metas y resultados)*
- **MOT-04** [P] ¿Qué principios siguen al manejar yates que no son suyos y qué limitaciones debemos tener en cuenta? *(principios y restricciones)*
- **MOT-05** [V] Entendemos que el software debe cubrir los seis puntos del alcance:
• Inventario de yates disponibles por marina, para que el cliente consulte los de la marina más cercana. Los propietarios deciden si su yate está habilitado o bloqueado para arriendo.
• Reserva y notificación al propietario del yate y a la marina, para que realicen la preparación y la entrega.
• Pagos asociados al arriendo: valor del alquiler, depósito para daños, seguro y combustible consumido.
• Seguimiento en tiempo real de la ubicación y el nivel de combustible del yate, visible para la marina y para el cliente.
• Cierre del arriendo: devolución y recepción del yate, inspección y ajustes de dinero (cobro de combustible, devolución o retención del depósito).
• Sistema de calificaciones mutuas entre clientes y propietarios.

 ¿Falta o sobra alguno? *(requerimientos)*

## 3. Proceso de punta a punta (E2E)

- **E2E-01** [A] Cuéntenos un arriendo de principio a fin, desde que el cliente consulta hasta que se cierra el arriendo.
- **E2E-02** [P] **(A1)** ¿Cómo debería consultar el cliente los yates disponibles en la marina más cercana? ¿Cómo decide el propietario si su yate está habilitado o bloqueado?
- **E2E-03** [P] **(A2)** ¿Qué se revisa antes de confirmar una reserva? ¿Qué se le notifica al propietario y a la marina?
- **E2E-04** [P] **(A3)** ¿Cómo funcionan los pagos del arriendo y en qué momento se hace cada uno?
- **E2E-05** [P] **(A4)** ¿Para qué necesitan la marina y el cliente ver la ubicación y el combustible del yate en tiempo real?
- **E2E-06** [P] **(A5)** ¿Cómo es la devolución y la inspección, y cómo se hacen los ajustes de dinero?
- **E2E-07** [P] **(A6)** ¿Qué califica el cliente del propietario y el propietario del cliente? ¿Para qué se usa?
- **E2E-08** [V] Entendemos que el proceso inicia con la consulta de disponibilidad de la marina, continúa con la reserva y la evaluación de riesgo. Luego se realiza la formalización del contrato y los pagos, seguida de las notificaciones al propietario y a la marina. Posteriormente se lleva a cabo la entrega, el seguimiento durante el servicio y, al finalizar, la devolución e inspección. Finalmente, se realizan los ajustes económicos correspondientes y se registran las calificaciones de las partes. ¿Está bien?

## 4. Actores y reglas de negocio

- **ACT-01** [A] ¿Quiénes participan en un arriendo y de qué es responsable cada uno?
- **REG-01** [A] ¿Qué reglas nunca se pueden romper en un arriendo?
- **REG-02** [V] Entendemos que un yate no puede tener dos reservas en las mismas fechas y que el propietario no puede bloquear fechas ya reservadas. ¿Es correcto?

## 5. Excepciones

- **EXC-01** [A] ¿Qué problemas son los más comunes en un arriendo y cómo los resuelven?
- **EXC-02** [P] ¿Qué pasa si hay daños mayores al depósito o si se cancela una reserva?

## 6. Vocabulario, indicadores y normatividad

- **VOC-01** [P] ¿Hay palabras que signifiquen cosas distintas según quién las use? (por ejemplo "bloqueo", "disponible" o "entrega")
- **IND-01** [A] ¿Qué indicadores usan o quisieran usar para saber cómo va el arriendo de yates?
- **NOR-01** [A] ¿Qué normas deben cumplir en el arriendo? *(contrastar con fuentes oficiales)*

## 7. Interoperabilidad

- **INT-01** [A] ¿Con qué áreas, sistemas y empresas externas intercambia información el proceso de arriendo?
- **INT-02** [P] Para cada uno de la tabla: ¿qué información se intercambia, en qué dirección (enviamos, recibimos o ambas) y en qué momento del proceso?

| Código | Sistema o tercero (del enunciado) |
|---|---|
| INT-CRM | CRM para la gestión de clientes en los procesos comerciales |
| INT-CON | Gestión de contratos con propietarios y clientes |
| INT-ASE | Aseguradoras |
| INT-RIE | Empresas que evalúan el nivel de riesgo de cada arriendo |
| INT-MAR | Marinas |
| INT-PAG | Pasarelas de pago |
| INT-GPS | Fuente de datos de ubicación y combustible del yate |


## 8. Cierre

- **CIE-01** [A] ¿Qué es lo más importante que debe resolver el software y qué no esperan que haga?
- **CIE-02** [V] Le leemos un resumen de lo que entendimos. ¿Qué corregiría?



