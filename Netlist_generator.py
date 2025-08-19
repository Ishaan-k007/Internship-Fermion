# pip install groq
import os, json
from groq import Groq
from Main import expression
import subprocess

client = Groq(api_key=os.environ["GROQ_API_KEY"])

ast = expression

system_msg = """
You are a digital logic synthesis assistant.
Convert this Boolean expression in AST form into a NAND-only gate-level netlist.
Use signal names like w1, w2, w3 for wires.
Use this format:
NAND2 <name> ( .A(<input1>), .B(<input2>), .Y(<output>) );
Only use NAND2 gates. Final output net must be named Y.
"""

user_msg = {
    "ast": ast,
    "ports": {"A":"in","B":"in","C":"in","Y":"out"},
    "power": {"vdd":"VDD","gnd":"VSS"}
}

resp = client.chat.completions.create(
    model="llama-3.3-70b-versatile",   # pick the Groq Llama model you want
    temperature=0,
    messages=[
        {"role": "system", "content": system_msg},
        {"role": "user", "content": json.dumps(user_msg)}
    ]
)

def write_spice_file(netlist_text, filename="generated_nand.spice"):
    with open(filename, "w") as f:
        f.write("* AI-generated NAND-only logic netlist\n")
        f.write(".subckt NAND2 A B Y\n.ends\n\n")

        f.write("* Logic circuit\n")
        f.write(netlist_text + "\n\n")

        f.write("* Inputs\n")
        f.write("VDD VDD 0 DC 1.8\n")
        f.write("VA A 0 PULSE(0 1.8 0n 1n 1n 10n 20n)\n")
        f.write("VB B 0 PULSE(0 1.8 0n 1n 1n 20n 40n)\n")
        f.write("VC C 0 PULSE(0 1.8 0n 1n 1n 40n 80n)\n")

        f.write("\n.tran 0.1n 100n\n")
        f.write(".control\nrun\nplot V(A) V(B) V(C) V(Y)\n.endc\n\n")
        f.write(".end\n")
    print(f" Wrote SPICE file: {filename}")



def run_ngspice(filename="generated_nand.spice"):
    print(f"🔧 Running simulation on {filename} ...\n")
    subprocess.run(["ngspice", "-b", filename])  # -b: batch mode

netlist = resp.choices[0].message.content
print(netlist)


write_spice_file(netlist)  # <--- YES, this takes the LLM output
run_ngspice()
