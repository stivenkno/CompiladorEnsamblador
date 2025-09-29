import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import re
from typing import Dict, Tuple, List

# Diccionario de registros RISC-V
regs: Dict[str, int] = {}
for i in range(32):
    regs[f"x{i}"] = i
regs.update({
    "zero": 0, "ra": 1, "sp": 2, "gp": 3, "tp": 4,
    "t0": 5, "t1": 6, "t2": 7, "s0": 8, "fp": 8, "s1": 9,
    "a0": 10, "a1": 11, "a2": 12, "a3": 13, "a4": 14, "a5": 15, "a6": 16, "a7": 17,
    "s2": 18, "s3": 19, "s4": 20, "s5": 21, "s6": 22, "s7": 23, "s8": 24, "s9": 25, "s10": 26, "s11": 27,
    "t3": 28, "t4": 29, "t5": 30, "t6": 31
})

# Opcodes y mapas de instrucciones
r_type = {
    "add": (0b000, 0b0000000), "sub": (0b000, 0b0100000),
    "sll": (0b001, 0b0000000), "slt": (0b010, 0b0000000),
    "sltu": (0b011, 0b0000000), "xor": (0b100, 0b0000000),
    "srl": (0b101, 0b0000000), "sra": (0b101, 0b0100000),
    "or": (0b110, 0b0000000), "and": (0b111, 0b0000000),
}
opcode_r = 0b0110011

i_arith_type = {
    "addi": 0b000, "slti": 0b010, "sltiu": 0b011,
    "xori": 0b100, "ori": 0b110, "andi": 0b111,
    "slli": 0b001, "srli": 0b101, "srai": 0b101,
}
opcode_i_arith = 0b0010011

load_type = {"lb": 0b000, "lh": 0b001, "lw": 0b010, "lbu": 0b100, "lhu": 0b101}
opcode_load = 0b0000011
opcode_jalr = 0b1100111

s_type = {"sb": 0b000, "sh": 0b001, "sw": 0b010}
opcode_s = 0b0100011

b_type = {"beq": 0b000, "bne": 0b001, "blt": 0b100, "bge": 0b101, "bltu": 0b110, "bgeu": 0b111}
opcode_b = 0b1100011

u_type = {"lui": 0b0110111, "auipc": 0b0010111}
uj_type = {"jal": 0b1101111}

pseudo = {
    "mv": "addi {}, {}, 0", "not": "xori {}, {}, -1", "neg": "sub {}, zero, {}",
    "seqz": "sltiu {}, {}, 1", "snez": "sltu {}, zero, {}", "sltz": "slt {}, {}, zero",
    "sgtz": "slt {}, zero, {}", "beqz": "beq {}, zero, {}", "bnez": "bne {}, zero, {}",
    "blez": "bge zero, {}, {}", "bgez": "bge {}, zero, {}", "bltz": "blt {}, zero, {}",
    "bgtz": "blt zero, {}, {}", "bgt": "blt {}, {}, {}", "ble": "bge {}, {}, {}",
    "bgtu": "bltu {}, {}, {}", "bleu": "bgeu {}, {}, {}", "j": "jal zero, {}",
    "jr": "jalr zero, {}, 0", "ret": "jalr zero, ra, 0", "call": "jal ra, {}",
    "nop": "addi zero, zero, 0", "li": "addi {}, zero, {}"
}

# Funciones auxiliares
def parse_imm(arg: str, symbol_table=None):
    if symbol_table and arg in symbol_table:
        return symbol_table[arg]
    if arg.startswith('%hi(') and arg.endswith(')'):
        label = arg[4:-1]
        if symbol_table and label in symbol_table:
            return (symbol_table[label] >> 12) & 0xFFFFF
        raise ValueError(f"Etiqueta no encontrada para %hi: {label}")
    if arg.startswith('%lo(') and arg.endswith(')'):
        label = arg[4:-1]
        if symbol_table and label in symbol_table:
            return symbol_table[label] & 0xFFF
        raise ValueError(f"Etiqueta no encontrada para %lo: {label}")
    if arg.startswith("0x"):
        return int(arg, 16)
    if arg.startswith("0b"):
        return int(arg, 2)
    return int(arg)

def get_reg(reg_str: str) -> int:
    reg = reg_str.lower()
    if reg in regs:
        return regs[reg]
    raise ValueError(f"Registro inválido: {reg_str}")

# Función de ensamblado
def assemble(lines: List[str]) -> List[Tuple[str, str, str, str]]:
    label_dict: Dict[str, int] = {}
    data_dict: Dict[str, int] = {}
    result: List[Tuple[str, str, str, str]] = []

    current_addr = 0
    in_data = False
    in_text = False

    memory_address = 0x10000000  # Inicio de la sección .data

    # Primera pasada: identificar etiquetas en .data y .text
    text_lines = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if line == ".data":
            in_data = True
            in_text = False
            continue
        elif line == ".text":
            in_text = True
            in_data = False
            continue

        if in_data:
            match = re.match(r'(\w+):\s*.word\s+(-?\d+)', line)
            if match:
                label, value = match.groups()
                data_dict[label] = memory_address
                memory_address += 4
        elif in_text:
            if line.endswith(':'):
                label = line[:-1]
                label_dict[label] = current_addr
            else:
                text_lines.append(line)
                current_addr += 4
        if line.endswith(':'):
                label = line[:-1]
                label_dict[label] = current_addr
        else:
            text_lines.append(line)
            current_addr += 4

    # Fusionar etiquetas .data y .text
    symbol_table = {**label_dict, **data_dict}

    # Segunda pasada: ensamblar instrucciones
    current_addr = 0
    for original_line in text_lines:
        line = original_line.strip()
        if not line or line.startswith('#'):
            continue
        if '#' in line:
            line = line.split('#')[0].strip()

        parts = re.split(r'\s+', line, maxsplit=1)
        op = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        if op in pseudo:
            arg_list = re.split(r'\s*,\s*', args)
            line = pseudo[op].format(*arg_list)
            parts = re.split(r'\s+', line, maxsplit=1)
            op = parts[0].lower()
            args = parts[1] if len(parts) > 1 else ""

        arg_list = re.split(r'\s*,\s*', args)
        instr = 0

        if op in r_type:
            rd, rs1, rs2 = map(get_reg, arg_list)
            funct3, funct7 = r_type[op]
            instr = (funct7 << 25) | (rs2 << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | opcode_r
        elif op in i_arith_type:
            rd, rs1, imm = get_reg(arg_list[0]), get_reg(arg_list[1]), parse_imm(arg_list[2], symbol_table)
            funct3 = i_arith_type[op]
            if op in ["slli", "srli", "srai"]:
                funct7 = 0b0000000 if op != "srai" else 0b0100000
                instr = (funct7 << 25) | ((imm & 0x1F) << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | opcode_i_arith
            else:
                instr = ((imm & 0xFFF) << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | opcode_i_arith
        elif op in load_type:
            rd, mem = get_reg(arg_list[0]), arg_list[1]
            imm, rs1 = re.match(r'(-?\w+)\((\w+)\)', mem).groups()
            imm_val, rs1 = parse_imm(imm, symbol_table), get_reg(rs1)
            funct3 = load_type[op]
            instr = ((imm_val & 0xFFF) << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | opcode_load
        elif op in s_type:
            rs2, mem = get_reg(arg_list[0]), arg_list[1]
            imm, rs1 = re.match(r'(-?\w+)\((\w+)\)', mem).groups()
            imm_val, rs1 = parse_imm(imm, symbol_table), get_reg(rs1)
            funct3 = s_type[op]
            imm11_5 = (imm_val >> 5) & 0x7F
            imm4_0 = imm_val & 0x1F
            instr = (imm11_5 << 25) | (rs2 << 20) | (rs1 << 15) | (funct3 << 12) | (imm4_0 << 7) | opcode_s
        elif op in b_type:
            rs1, rs2, label = get_reg(arg_list[0]), get_reg(arg_list[1]), arg_list[2]
            offset = symbol_table[label] - current_addr
            funct3 = b_type[op]
            imm12 = (offset >> 12) & 1
            imm10_5 = (offset >> 5) & 0x3F
            imm4_1 = (offset >> 1) & 0xF
            imm11 = (offset >> 11) & 1
            instr = (imm12 << 31) | (imm11 << 7) | (imm10_5 << 25) | (rs2 << 20) | (rs1 << 15) | (funct3 << 12) | (imm4_1 << 8) | opcode_b
        elif op in u_type:
            rd, imm = get_reg(arg_list[0]), parse_imm(arg_list[1], symbol_table)
            opcode = u_type[op]
            instr = ((imm & 0xFFFFF000)) | (rd << 7) | opcode
        elif op in uj_type:
            rd, label = get_reg(arg_list[0]), arg_list[1]
            offset = symbol_table[label] - current_addr
            imm20 = (offset >> 20) & 1
            imm10_1 = (offset >> 1) & 0x3FF
            imm11 = (offset >> 11) & 1
            imm19_12 = (offset >> 12) & 0xFF
            instr = (imm20 << 31) | (imm19_12 << 12) | (imm11 << 20) | (imm10_1 << 21) | (rd << 7) | uj_type[op]
        else:
            raise ValueError(f"Instrucción no soportada: {op}")

        result.append((
            f"{current_addr:08x}",      # Dirección
            f"{instr:08x}",             # Hexadecimal
            f"{instr:032b}",            # Binario 32 bits
            original_line               # Instrucción original
        ))
        current_addr += 4

    return result

# GUI principal
def load_file():
    filepath = filedialog.askopenfilename(filetypes=[("Assembly files", "*.asm"), ("All files", "*.*")])
    if not filepath:
        return
    with open(filepath, "r") as f:
        lines = f.readlines()
    try:
        machine_code = assemble(lines)
        tree.delete(*tree.get_children())  # limpiar tabla antes de cargar
        for addr, hex_code, bin_code, src in machine_code:
            tree.insert("", "end", values=(addr, hex_code, bin_code, src.strip()))
    except Exception as e:
        messagebox.showerror("Error", str(e))

root = tk.Tk()
root.title("RISC-V Assembler")
root.geometry("1000x600")

tree = ttk.Treeview(
    root,
    columns=("Address", "Hex Code", "Binary Code", "Instruction"),
    show="headings"
)

tree.heading("Address", text="Address")
tree.heading("Hex Code", text="Hex Code")
tree.heading("Binary Code", text="Binary Code")
tree.heading("Instruction", text="Instruction")
tree.pack(expand=True, fill="both")

button = tk.Button(root, text="Cargar archivo .asm", command=load_file)
button.pack(pady=10)

root.mainloop()
