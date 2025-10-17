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
    SYMBOL = "
