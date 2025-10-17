# Informe: Arquitectura del Sistema y Comunicación entre Agentes

## 1. Arquitectura General del Sistema

El sistema implementa una **calculadora distribuida** utilizando el paradigma de **agentes autónomos** con el framework **MESA** en Python.  
Cada agente representa una entidad independiente que tiene un propósito específico dentro del entorno, y todos se coordinan para resolver expresiones matemáticas.

### 1.1 Componentes principales

- **Agente de Entrada/Salida (IOAgent):**  
  Es el agente principal del sistema.  
  Recibe la expresión del usuario, la convierte a **notación polaca inversa (RPN)** mediante el algoritmo *Shunting Yard*, y gestiona el flujo de mensajes entre los demás agentes.  
  También se encarga de almacenar los resultados parciales en una pila y determinar cuándo la operación ha finalizado.

- **Agentes de Operación:**  
  Cada uno se especializa en una operación aritmética:
  - `SumAgent`: realiza sumas.
  - `SubAgent`: realiza restas.
  - `MulAgent`: realiza multiplicaciones.
  - `DivAgent`: realiza divisiones.
  - `PowAgent`: realiza potencias.  
  Estos agentes solo ejecutan operaciones cuando reciben un mensaje `COMPUTE` desde el IOAgent, y devuelven el resultado en un mensaje `RESULT`.

- **Modelo CalcModel (Entorno MESA):**  
  Representa el entorno donde los agentes existen y se comunican.  
  Utiliza un **scheduler (RandomActivation)** para ejecutar los pasos de cada agente en ciclos discretos, y un **bus de mensajes** interno que simula el intercambio de información entre ellos.

---

## 2. Flujo de Ejecución del Sistema

1. **Entrada del usuario:**  
   El IOAgent recibe la expresión, por ejemplo:  
2 + 5 * 4 - 3


2. **Conversión y apilamiento:**  
El IOAgent convierte la expresión a RPN y apila los valores detectados:
[IO] push 2 -> stack=[2.0]
[IO] push 5 -> stack=[2.0, 5.0]
[IO] push 4 -> stack=[2.0, 5.0, 4.0]


3. **Delegación de operaciones:**  
Según la precedencia de operadores, el IOAgent envía una solicitud `COMPUTE` al agente correspondiente:
[IO] op * with a=5.0, b=4.0 -> send to mul (rid=req1)
[BUS] io -> mul : COMPUTE {'op': '*', 'a': 5.0, 'b': 4.0, 'rid': 'req1'}



4. **Procesamiento por parte de los agentes:**
El agente de multiplicación realiza su operación:
[mul] compute *(5.0,4.0) = 20.0 (rid=req1)
[BUS] mul -> io : RESULT {'value': 20.0, 'rid': 'req1'}
[IO] recv RESULT rid=req1 value=20.0



5. **Operaciones sucesivas:**
Luego, el IOAgent continúa con las demás operaciones:
[IO] op + with a=2.0, b=20.0 -> send to sum (rid=req2)
[sum] compute +(2.0,20.0) = 22.0 (rid=req2)
[IO] recv RESULT rid=req2 value=22.0

[IO] op - with a=22.0, b=3.0 -> send to sub (rid=req3)
[sub] compute -(22.0,3.0) = 19.0 (rid=req3)
[IO] recv RESULT rid=req3 value=19.0
[IO] DONE => result=19.0



6. **Salida final:**
El IOAgent muestra el resultado final:
Resultado: 19.0



---

## 3. Mecanismos de Comunicación entre Agentes

### 3.1 Tipo de mensajes

El sistema implementa tres tipos de mensajes básicos que viajan a través del bus interno del modelo:

| Tipo de Mensaje | Emisor | Receptor | Contenido | Propósito |
|------------------|---------|-----------|------------|------------|
| `COMPUTE` | IOAgent | Agente de operación | `op`, `a`, `b`, `rid` | Solicitar el cálculo de una operación. |
| `RESULT` | Agente de operación | IOAgent | `value`, `rid` | Enviar el resultado de la operación solicitada. |
| `ERROR` | Agente de operación | IOAgent | `detail`, `rid` | Reportar errores, como divisiones por cero. |

### 3.2 Mecanismo de intercambio

- Todos los mensajes son almacenados temporalmente en un **bus de comunicación**, que actúa como un espacio intermedio.
- En cada ciclo de simulación (`step()`), el modelo:
1. Entrega los mensajes pendientes a los agentes correspondientes.
2. Ejecuta la lógica interna de cada agente.
3. Limpia el bus y avanza al siguiente paso.

Este proceso se repite hasta que el IOAgent marca la simulación como **terminada (`done = True`)**.

---

## 4. Ejemplo de Interacción 
Inicialización y apilamiento de operandos

[IO] push 2 -> stack=[2.0]
[IO] push 5 -> stack=[2.0, 5.0]
[IO] push 4 -> stack=[2.0, 5.0, 4.0]

<img width="921" height="545" alt="image" src="https://github.com/user-attachments/assets/21576321-2840-487b-b3a5-0ab716061517" />


El IOAgent comienza leyendo los valores de la expresión y los apila internamente en su estructura de datos (pila).
Hasta este punto no se ha enviado ningún cálculo.

### Primera comunicación: Multiplicación

[IO] op * with a=5.0, b=4.0 -> send to mul (rid=req1)
[BUS] io -> mul : COMPUTE {'op': '*', 'a': 5.0, 'b': 4.0, 'rid': 'req1'}
[mul] compute *(5.0,4.0) = 20.0 (rid=req1)
[BUS] mul -> io : RESULT {'value': 20.0, 'rid': 'req1'}
[IO] recv RESULT rid=req1 value=20.0


El IOAgent detecta que debe realizar la multiplicación (*) antes que las demás operaciones.

Envía un mensaje COMPUTE al agente mul con los valores a=5.0 y b=4.0.

El agente mul procesa la operación y responde con un mensaje RESULT conteniendo el valor 20.0.

El IOAgent recibe este resultado y lo vuelve a apilar para continuar el cálculo.

### Segunda comunicación: Suma

[IO] op + with a=2.0, b=20.0 -> send to sum (rid=req2)
[BUS] io -> sum : COMPUTE {'op': '+', 'a': 2.0, 'b': 20.0, 'rid': 'req2'}
[sum] compute +(2.0,20.0) = 22.0 (rid=req2)
[BUS] sum -> io : RESULT {'value': 22.0, 'rid': 'req2'}
[IO] recv RESULT rid=req2 value=22.0


Una vez completada la multiplicación, el IOAgent envía una nueva orden de cálculo al agente sum.

El agente sum realiza la suma (2.0 + 20.0) y devuelve 22.0.

El resultado se registra y vuelve a la pila.

### Tercera comunicación: Resta

[IO] push 3 -> stack=[22.0, 3.0]
[IO] op - with a=22.0, b=3.0 -> send to sub (rid=req3)
[BUS] io -> sub : COMPUTE {'op': '-', 'a': 22.0, 'b': 3.0, 'rid': 'req3'}
[sub] compute -(22.0,3.0) = 19.0 (rid=req3)
[BUS] sub -> io : RESULT {'value': 19.0, 'rid': 'req3'}
[IO] recv RESULT rid=req3 value=19.0
[IO] DONE => result=19.0


Finalmente, el IOAgent procesa la última operación pendiente: la resta (-).

Envía la solicitud al agente sub, que calcula el resultado 19.0.

Al recibir el último RESULT, el IOAgent marca la simulación como completada con DONE.

### Mas capturas de analisis 

<img width="921" height="441" alt="image" src="https://github.com/user-attachments/assets/f5a1d8ab-20f2-4348-b72f-efe858a552ac" />

<img width="921" height="432" alt="image" src="https://github.com/user-attachments/assets/4eed019c-43c8-498f-9b98-7a2834d7e6eb" />



---

## 5. Análisis de la Arquitectura y Comportamiento

- **Modularidad:** Cada agente tiene una responsabilidad específica y puede operar de manera independiente.
- **Desacoplamiento:** Los agentes no conocen la estructura completa de la expresión, solo la operación que les corresponde.
- **Escalabilidad:** Se pueden agregar nuevos agentes (por ejemplo, logaritmo, raíz cuadrada, seno) sin modificar la lógica base.
- **Trazabilidad:** Cada operación es identificada por un código de solicitud (`rid=reqX`), lo que permite seguir el flujo de mensajes fácilmente.
- **Sincronización:** El IOAgent actúa como coordinador central, asegurando que las operaciones se ejecuten en orden correcto.

---

## 6. Conclusión

El sistema demuestra de forma práctica cómo el **paradigma de agentes** puede aplicarse a una tarea tradicionalmente secuencial como el cálculo matemático.  
Mediante comunicación basada en mensajes y ejecución distribuida, cada operación es procesada por un agente especializado, lo que refleja los principios fundamentales de los **Modelos Basados en Agentes (MBA)**:
- Autonomía  
- Comunicación  
- Colaboración  
- Sincronización  

El resultado final es una arquitectura **robusta, extensible y fácilmente observable**, que simula correctamente la interacción de entidades inteligentes para resolver un problema común de forma distribuida.

---
