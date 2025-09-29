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

