# agcalc_min.py - Calculadora basada en agentes (MESA)
# Cada operacion (suma, resta, multiplicacion, division, potencia) es un agente independiente
# Los agentes se comunican entre si con mensajes (COMPUTE y RESULT)
# Incluye traza visible de los mensajes y del proceso de calculo

import re
from mesa import Model, Agent
from mesa.time import RandomActivation

# Aqui se activa la traza, si esta en True muestra todos los mensajes de los agentes
TRACE = True
def log(*args, **kwargs):
    if TRACE:
        print(*args, **kwargs)
print("[TRACE] ON")  # Se muestra para confirmar que la traza esta encendida


# Seccion del parser y tokens

# Aqui se definen los operadores y su precedencia
OPS = {"+": (1, "L"), "-": (1, "L"), "*": (2, "L"), "/": (2, "L"), "^": (3, "R"), "u-": (4, "R")}

# Esta funcion separa la expresion en partes (tokens)
def raw_tokens(expr: str):
    expr = expr.replace(" ", "")
    toks = re.findall(r"\d+\.\d+|\d+|[+\-*/^()]", expr)
    if not toks:
        raise ValueError("Expresion vacia o invalida")
    return toks

# Esta funcion detecta cuando el signo menos es unario (por ejemplo en -3)
def inject_unary_minus(tokens):
    out = []
    prev = None
    for t in tokens:
        if t == "-":
            if prev is None or prev in OPS or prev == "(":
                out.append("u-")
            else:
                out.append("-")
        else:
            out.append(t)
        prev = out[-1]
    return out

# Combina las dos funciones anteriores
def tokenize(expr: str):
    return inject_unary_minus(raw_tokens(expr))

# Algoritmo Shunting Yard para convertir la expresion infija a notacion polaca inversa (RPN)
def shunting_yard(tokens):
    out, stack = [], []
    for t in tokens:
        if re.fullmatch(r"\d+\.\d+|\d+", t):
            out.append(t)
        elif t in OPS:
            p, a = OPS[t]
            while stack and stack[-1] in OPS:
                p2, a2 = OPS[stack[-1]]
                if (a == "L" and p <= p2) or (a == "R" and p < p2):
                    out.append(stack.pop())
                else:
                    break
            stack.append(t)
        elif t == "(":
            stack.append(t)
        elif t == ")":
            while stack and stack[-1] != "(":
                out.append(stack.pop())
            if not stack:
                raise ValueError("Parentesis desbalanceados")
            stack.pop()
        else:
            raise ValueError(f"Token invalido: {t}")
    while stack:
        op = stack.pop()
        if op in ("(", ")"):
            raise ValueError("Parentesis desbalanceados")
        out.append(op)
    return out


# Seccion de mensajeria

# Aqui se crean los tipos de mensajes entre agentes

def msg_compute(sender, recipient, op, a, b, rid):
    return {"sender": sender, "recipient": recipient, "kind": "COMPUTE", "op": op, "a": a, "b": b, "rid": rid}

def msg_result(sender, recipient, value, rid):
    return {"sender": sender, "recipient": recipient, "kind": "RESULT", "value": value, "rid": rid}

def msg_error(sender, recipient, detail, rid=None):
    return {"sender": sender, "recipient": recipient, "kind": "ERROR", "detail": detail, "rid": rid}


# Agentes de operacion

# Cada uno realiza una operacion especifica segun su simbolo

class OpAgent(Agent):
    SYMBOL = None
    def __init__(self, uid, model):
        super().__init__(uid, model)
        self.inbox = []

    # Metodo que debe implementar cada agente
    def op(self, a, b):
        raise NotImplementedError

    def step(self):
        nxt = []
        for m in self.inbox:
            if m["kind"] == "COMPUTE" and m.get("op") == self.SYMBOL:
                a, b, rid = m["a"], m["b"], m["rid"]
                try:
                    val = self.op(a, b)
                    log(f"[{self.unique_id}] compute {self.SYMBOL}({a},{b}) = {val} (rid={rid})")
                    self.model.send(msg_result(self.unique_id, m["sender"], val, rid))
                except Exception as e:
                    log(f"[{self.unique_id}] ERROR {self.SYMBOL}({a},{b}) -> {e} (rid={rid})")
                    self.model.send(msg_error(self.unique_id, m["sender"], str(e), rid))
            else:
                nxt.append(m)
        self.inbox = nxt

# Agente de suma
class SumAgent(OpAgent):
    SYMBOL = "+"
    def op(self, a, b): return a + b

# Agente de resta
class SubAgent(OpAgent):
    SYMBOL = "-"
    def op(self, a, b): return a - b

# Agente de multiplicacion
class MulAgent(OpAgent):
    SYMBOL = "*"
    def op(self, a, b): return a * b

# Agente de division
class DivAgent(OpAgent):
    SYMBOL = "/"
    def op(self, a, b):
        if b == 0:
            raise ZeroDivisionError("Division por cero")
        return a / b

# Agente de potencia
class PowAgent(OpAgent):
    SYMBOL = "^"
    def op(self, a, b): return a ** b


# Agente principal (IOAgent)

# Este agente coordina la comunicacion entre todos los demas
# Recibe la expresion, la convierte a RPN y delega los calculos
class IOAgent(Agent):
    def __init__(self, uid, model):
        super().__init__(uid, model)
        self.inbox = []
        self.rpn = []
        self.stack = []
        self.pending = {}
        self.next_rid = 0
        self.done = False
        self.final = None

    def load_expression(self, expr: str):
        tokens = tokenize(expr)
        self.rpn = shunting_yard(tokens)
        self.stack.clear()
        self.pending.clear()
        self.next_rid = 0
        self.done = False
        self.final = None

    def _rid(self):
        self.next_rid += 1
        return f"req{self.next_rid}"

    # Aqui se procesa cada paso del modelo
    def step(self):
        rest = []
        # Primero se procesan los mensajes que llegaron
        for m in self.inbox:
            if m["kind"] == "RESULT":
                rid = m["rid"]
                if rid in self.pending:
                    log(f"[IO] recv RESULT rid={rid} value={m['value']}")
                    self.stack.append(float(m["value"]))
                    del self.pending[rid]
            elif m["kind"] == "ERROR":
                raise RuntimeError(f"Error de agente: {m['detail']}")
            else:
                rest.append(m)
        self.inbox = rest

        # Si hay operaciones pendientes se espera
        if self.pending:
            return

        # Si no hay mas tokens y solo queda un valor en la pila, se termina
        if not self.rpn and len(self.stack) == 1 and not self.done:
            self.final = self.stack.pop()
            self.done = True
            log(f"[IO] DONE -> result={self.final}")
            return

        # Si aun hay tokens en la RPN
        if self.rpn:
            t = self.rpn.pop(0)

            # Si el token es un numero, se apila
            if re.fullmatch(r"\d+\.\d+|\d+", t):
                self.stack.append(float(t))
                log(f"[IO] push {t} -> stack={self.stack}")
                return

            # Si es un signo unario, se envia al agente de resta
            if t == "u-":
                if len(self.stack) < 1:
                    raise ValueError("RPN invalida (unario -)")
                x = self.stack.pop()
                a, b = 0.0, x
                dest = "sub"
                rid = self._rid()
                self.pending[rid] = t
                log(f"[IO] op u- with x={x} -> send to {dest} (rid={rid})")
                self.model.send(msg_compute(self.unique_id, dest, "-", a, b, rid))
                return

            # Si es un operador binario normal, se envia al agente correspondiente
            if t in {"+", "-", "*", "/", "^"}:
                if len(self.stack) < 2:
                    raise ValueError("RPN invalida (faltan operandos)")
                b = self.stack.pop()
                a = self.stack.pop()
                dest = {"+": "sum", "-": "sub", "*": "mul", "/": "div", "^": "pow"}[t]
                rid = self._rid()
                self.pending[rid] = t
                log(f"[IO] op {t} with a={a}, b={b} -> send to {dest} (rid={rid})")
                self.model.send(msg_compute(self.unique_id, dest, t, a, b, rid))
                return

            raise ValueError(f"Token inesperado en RPN: {t}")


# Modelo principal

# Este modelo contiene los agentes y el sistema de mensajes
class CalcModel(Model):
    def __init__(self):
        super().__init__()
        self.schedule = RandomActivation(self)
        self._bus = []

        # Aqui se crean todos los agentes
        self.io = IOAgent("io", self); self._add(self.io)
        self.sum = SumAgent("sum", self); self._add(self.sum)
        self.sub = SubAgent("sub", self); self._add(self.sub)
        self.mul = MulAgent("mul", self); self._add(self.mul)
        self.div = DivAgent("div", self); self._add(self.div)
        self.pow = PowAgent("pow", self); self._add(self.pow)

    def _add(self, a): self.schedule.add(a)

    # Busca un agente por su identificador
    def _by_id(self, uid):
        for a in self.schedule.agents:
            if a.unique_id == uid:
                return a
        return None

    # Funcion para enviar mensajes entre agentes
    def send(self, message: dict):
        self._bus.append(message)
        k = {k: message.get(k) for k in ["op", "a", "b", "value", "rid", "detail"] if k in message}
        log(f"[BUS] {message['sender']} -> {message['recipient']} : {message['kind']} {k}")

    # Entrega los mensajes a sus destinatarios
    def _deliver(self):
        for m in self._bus:
            dst = self._by_id(m["recipient"])
            if dst is None:
                raise RuntimeError(f"Agente destino no existe: {m['recipient']}")
            dst.inbox.append(m)
        self._bus.clear()

    # Un paso del modelo (entrega + ejecucion)
    def step(self):
        self._deliver()
        self.schedule.step()


# Interfaz por consola

# Aqui se ejecuta la calculadora con entrada del usuario
def run_cli_once():
    expr = input("Escribe la expresion: ").strip()
    model = CalcModel()
    model.io.load_expression(expr)
    steps = 0
    MAX_STEPS = 4000
    while not model.io.done and steps < MAX_STEPS:
        model.step()
        steps += 1
    if not model.io.done:
        raise RuntimeError("No convergio, revisa la expresion o division por cero")
    print("Resultado:", model.io.final)

# Inicio del programa
if __name__ == "__main__":
    print("Calculadora por agentes (MESA). Ctrl+C para salir.")
    while True:
        run_cli_once()
