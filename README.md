# Calculadora Basada en el Paradigma de Agentes - Johan Steven Galeano Gonzalez

## 1. Introduccion
Este proyecto implementa una **calculadora distribuida basada en agentes**, desarrollada en **Python** usando el framework **MESA**.  
Cada operacion aritmetica (suma, resta, multiplicacion, division y potencia) es manejada por un agente autonomo especializado, mientras que un agente coordinador se encarga de recibir la expresion, distribuir las operaciones y ensamblar el resultado final.

---

## 2. Diseño de la Solucion (Modelo Basado en Agentes)

### Agentes del sistema
- **Agente Suma**: realiza operaciones de suma.
- **Agente Resta**: realiza operaciones de resta.
- **Agente Multiplicacion**: realiza multiplicaciones.
- **Agente Division**: maneja divisiones y controla errores de division por cero.
- **Agente Potencia**: realiza operaciones de potenciacion.
- **Agente Entrada/Salida (IOAgent)**: recibe la expresion ingresada, aplica el algoritmo *Shunting Yard* para convertirla a notacion polaca inversa (RPN), distribuye las operaciones entre los demas agentes y muestra el resultado final.

### Entorno y scheduler
El entorno esta basado en la clase `CalcModel`, que contiene:
- Un **scheduler RandomActivation** para ejecutar a los agentes en cada paso.
- Un **bus de mensajes** que simula la comunicacion entre agentes.
- Un metodo `step()` que entrega los mensajes y ejecuta un ciclo de simulacion.

### Comunicacion entre agentes
Los agentes se comunican mediante **mensajes estructurados** con tres tipos principales:
- `COMPUTE`: enviado por el IOAgent para solicitar una operacion.
- `RESULT`: enviado por los agentes de operacion para devolver el resultado.
- `ERROR`: usado para manejar excepciones, como la division por cero.

Cada mensaje contiene:
```python
{
  "sender": "io",
  "recipient": "mul",
  "kind": "COMPUTE",
  "op": "*",
  "a": 3.0,
  "b": 4.0,
  "rid": "req1"
}
