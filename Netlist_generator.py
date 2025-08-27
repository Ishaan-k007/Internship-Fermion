import os, json, re, pathlib, subprocess
from groq import Groq
from Main import expression

OUTDIR = pathlib.Path("out")
OUTDIR.mkdir(exist_ok=True)

# --- Prompt for Groq (simpler) ---
SYSTEM_MSG = """
You are a deterministic NAND-only compiler.

INPUT: an AST of a Boolean expression and the declared ports.
OUTPUT: ONLY SPICE instance lines, one per line. No prose, no code fences, no blank lines.

Hard constraints (must NEVER be violated):
- Use ONLY 2-input NAND gates named "nand2".
- Each line has EXACTLY 7 tokens:
  X<ID> <in1> <in2> <out> VDD VSS nand2
- IDs start at X1 and increase by 1 with no gaps.
- Allowed signal names:
  • Inputs: exactly the set given in ports where value == "in" (e.g., A, B, C...). Do not invent ports.
  • Output: Y (exactly Y), driven by the FINAL gate line only.
  • Internal wires: w1, w2, w3, ... Each w# may appear as an OUTPUT exactly once.
- Do NOT use names like not_A, t1, and1, tmp, etc.
- Do NOT emit comments or headers.

Deterministic compilation algorithm (follow EXACTLY; no simplification, no common-subexpression reuse):
- Post-order traversal (left → right → node).
- Leaf "A" (or any input): return the symbol as its net.
- NOT(X):  t1 = NAND(X, X)                                -> returns t1
- AND(A,B): t = NAND(A, B); o = NAND(t, t)                -> returns o
- OR(A,B):  a1 = NAND(A, A); b1 = NAND(B, B); o = NAND(a1, b1) -> returns o
- NOR(A,B): first OR(A,B) to get t; o = NAND(t, t)        -> returns o
- XOR(A,B):
    t  = NAND(A, B)
    t1 = NAND(A, t)
    t2 = NAND(B, t)
    o  = NAND(t1, t2)                                     -> returns o
- Single-variable expression (e.g., just "A"): output must be Y.
  Implement as a buffer: n = NAND(A, A); Y = NAND(n, n).
- For N-ary operators, reduce left-associatively into binaries of the same op.

Wire & emission rules:
- Allocate new wires sequentially w1, w2, w3, ... in the EXACT order gates are created by the algorithm.
- Emit each gate line immediately when created.
- The final CREATED gate must drive Y (not a w#).

Validity pattern for each line (must match exactly):
^X[1-9]\d* [A-Z]\w* [A-Z]\w* (?:w[1-9]\d*|Y) VDD VSS nand2$
"""

SYSTEM_MSG_FIXER = """
You are a validator/regenerator for NAND-only SPICE netlists.

INPUT:
- AST
- Candidate netlist lines (plain text, one per line)

OUTPUT:
- ONLY the corrected list of SPICE instance lines (no prose).

Validation you MUST enforce:
- Every line has exactly 7 tokens and ends with "nand2".
- IDs are X1..Xn strictly consecutive.
- Allowed names:
  • Inputs: exactly those declared as "in" in ports.
  • Output: Y (must appear exactly once as a gate OUTPUT, on the FINAL line only).
  • Internals: w1..wN; each w# appears once as an OUTPUT; may be used as inputs any number of times.
- No floating nets: any non-port input used must have been produced by an earlier line.
- Canonical decompositions only:
  NOT(X) = NAND(X,X)
  AND(A,B) = NAND(NAND(A,B), NAND(A,B))
  OR(A,B) = NAND(NAND(A,A), NAND(B,B))
  NOR(A,B) = OR(A,B) then NAND(result, result)
  XOR(A,B) = NAND(NAND(A, NAND(A,B)), NAND(B, NAND(A,B)))

Behavior:
- If the candidate strictly satisfies all rules AND matches the AST via the canonical construction, output it unchanged.
- Otherwise, REGENERATE from the AST using the deterministic post-order algorithm (same as the generator).

Output ONLY valid instance lines. No comments or blank lines.
"""


# --- Ask Groq for instances ---
def call_groq(ast_obj, prev_msg=None):
    client = Groq(api_key=os.environ["GROQ_API_KEY"])

    if prev_msg is None:
        model = "llama-3.3-70b-versatile"
        messages = [
            {"role": "system", "content": SYSTEM_MSG},
            {"role": "user", "content": json.dumps({
                "ast": ast_obj,
                "ports": {"A": "in", "B": "in", "C": "in", "Y": "out"}
            })}
        ]
    else:
        # Join previous gate lines into a string
        prev_netlist_str = "\n".join(prev_msg)

        model = "openai/gpt-oss-20b"
        messages = [
            {"role": "system", "content": SYSTEM_MSG_FIXER},
            {"role": "user", "content": f"AST: {ast_obj}"},
            {"role": "user", "content": f"Netlist:\n{prev_netlist_str}"}
        ]

    resp = client.chat.completions.create(
        model=model,
        temperature=0,
        messages=messages,
    )

    text = resp.choices[0].message.content.strip()
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    inst_lines = [ln for ln in lines if ln.lower().endswith("nand2") and len(ln.split()) == 7]

    return inst_lines


# --- Write SPICE ---
def write_spice(inst_lines, path: pathlib.Path):
    lines = []
    lines.append("* Beginner NAND-only SPICE netlist")
    lines.append(".model NMOS NMOS (LEVEL=1)")
    lines.append(".model PMOS PMOS (LEVEL=1)")
    lines.append(".subckt nand2 A B Y VDD VSS")
    lines.append("MP1 Y A VDD VDD PMOS")
    lines.append("MP2 Y B VDD VDD PMOS")
    lines.append("MN1 Y A n VSS NMOS")
    lines.append("MN2 n B VSS VSS NMOS")
    lines.append(".ends nand2")
    lines.append(".subckt boolean_circuit A B C Y VDD VSS")
    lines += inst_lines
    lines.append(".ends boolean_circuit")
    lines.append(".param VDD=1.8")
    lines.append("VDD VDD 0 {VDD}")
    lines.append("VSS VSS 0 0")
    lines.append("VA A 0 PULSE(0 {VDD} 0 100p 100p 5n 10n)")
    lines.append("VB B 0 PULSE(0 {VDD} 0 100p 100p 10n 20n)")
    lines.append("VC C 0 PULSE(0 {VDD} 0 100p 100p 20n 40n)")
    lines.append("XU A B C Y VDD VSS boolean_circuit")
    lines.append(".tran 0.1n 80n")
    lines.append(".control")
    lines.append("run")
    lines.append("plot v(A) v(B) v(C) v(Y)")
    lines.append(".endc")
    lines.append(".end")
    path.write_text("\n".join(lines))

# --- Write a very simple Xschem symbol ---
def write_sym(path: pathlib.Path):
    sym = [
        "v {xschem_version=2.9.9 file_version=1.2}",
        "G {}","K {}","V {}","S {}",
        "B 5 0 0 600 400 {name=body}",
        "T {boolean_circuit} 300 20 0 0 0.6 0.6 {}",
        "P 0 100 0 100 1 0 0 {name=A dir=left}",
        "P 0 200 0 200 1 0 0 {name=B dir=left}",
        "P 0 300 0 300 1 0 0 {name=C dir=left}",
        "P 600 200 600 200 1 0 0 {name=Y dir=right}",
        "P 300 0 300 0 1 0 0 {name=VDD dir=up}",
        "P 300 400 300 400 1 0 0 {name=VSS dir=down}",
        "E {}"
    ]
    path.write_text("\n".join(sym))

# --- Write a very simple Xschem schematic ---
def write_sch(path: pathlib.Path):
    sch = [
        "v {xschem_version=2.9.9 file_version=1.2}",
        "G {}","K {}","V {}","S {}",
        "C {boolean_circuit.sym} 480 0 0 0 {name=X1}",
        "C {devices/vsource.sym} 120 0 0 0 {name=VA value=PULSE(0 {VDD} 0 100p 100p 5n 10n)}",
        "C {devices/vsource.sym} 120 120 0 0 {name=VB value=PULSE(0 {VDD} 0 100p 100p 10n 20n)}",
        "C {devices/vsource.sym} 120 240 0 0 {name=VC value=PULSE(0 {VDD} 0 100p 100p 20n 40n)}",
        "C {devices/lab_wire.sym} 120 -60 0 0 {name=lab_A lab=A}",
        "C {devices/lab_wire.sym} 120 60 0 0 {name=lab_B lab=B}",
        "C {devices/lab_wire.sym} 120 180 0 0 {name=lab_C lab=C}",
        "C {devices/lab_wire.sym} 840 0 0 0 {name=lab_Y lab=Y}",
        "C {devices/code.sym} 0 -240 0 0 {name=SPICE value=\".param VDD=1.8\\n.tran 0.1n 80n\\n.control\\nrun\\nplot v(A) v(B) v(C) v(Y)\\n.endc\"}",
        "E {}"
    ]
    path.write_text("\n".join(sch))

# --- Main ---
def main():
    inst = call_groq(expression)
    inst_2 = call_groq(expression, prev_msg=inst)
    print("Got instances:\n"+"\n".join(inst_2))
    write_spice(inst, OUTDIR/"boolean_circuit.spice")
    #write_sym(OUTDIR/"boolean_circuit.sym")
    #write_sch(OUTDIR/"boolean_circuit.sch")
    #print("Files written in", OUTDIR)

if __name__=="__main__":
    main()


