import tkinter as tk  # Importar tkinter para la interfaz gráfica
from tkinter import filedialog, ttk, messagebox  # Importar componentes específicos de tkinter para diálogos de archivos, tablas y mensajes
import re  # Importar re para expresiones regulares, útil para parsear texto
from typing import Dict, Tuple, List  # Importar tipos para anotaciones en el código

# Diccionario para nombres de registros a números
# Este diccionario mapea nombres de registros RISC-V a sus números binarios (0-31)
regs: Dict[str, int] = {}
for i in range(32):
    regs[f"x{i}"] = i  # Registros x0 a x31
regs.update({
    "zero": 0, "ra": 1, "sp": 2, "gp": 3, "tp": 4,  # Nombres ABI comunes
    "t0": 5, "t1": 6, "t2": 7, "s0": 8, "fp": 8, "s1": 9,
    "a0": 10, "a1": 11, "a2": 12, "a3": 13, "a4": 14, "a5": 15, "a6": 16, "a7": 17,
    "s2": 18, "s3": 19, "s4": 20, "s5": 21, "s6": 22, "s7": 23, "s8": 24, "s9": 25, "s10": 26, "s11": 27,
    "t3": 28, "t4": 29, "t5": 30, "t6": 31
})

# Codificaciones de instrucciones para diferentes tipos
# Tipo R: funct3, funct7 - Estas son instrucciones aritméticas/lógicas entre registros
r_type: Dict[str, Tuple[int, int]] = {
    "add": (0b000, 0b0000000),  # Suma
    "sub": (0b000, 0b0100000),  # Resta
    "sll": (0b001, 0b0000000),  # Desplazamiento lógico izquierdo
    "slt": (0b010, 0b0000000),  # Set less than
    "sltu": (0b011, 0b0000000),  # Set less than unsigned
    "xor": (0b100, 0b0000000),  # XOR
    "srl": (0b101, 0b0000000),  # Desplazamiento lógico derecho
    "sra": (0b101, 0b0100000),  # Desplazamiento aritmético derecho
    "or": (0b110, 0b0000000),   # OR
    "and": (0b111, 0b0000000),  # AND
}
opcode_r = 0b0110011  # Opcode para instrucciones tipo R

# Tipo I aritmético: funct3 - Instrucciones inmediatas aritméticas/lógicas
i_arith_type: Dict[str, int] = {
    "addi": 0b000,   # Suma inmediata
    "slti": 0b010,   # Set less than inmediata
    "sltiu": 0b011,  # Set less than unsigned inmediata
    "xori": 0b100,   # XOR inmediata
    "ori": 0b110,    # OR inmediata
    "andi": 0b111,   # AND inmediata
    "slli": 0b001,   # Desplazamiento lógico izquierdo inmediata
    "srli": 0b101,   # Desplazamiento lógico derecho inmediata
    "srai": 0b101,   # Desplazamiento aritmético derecho inmediata
}
opcode_i_arith = 0b0010011  # Opcode para tipo I aritmético

# Instrucciones de carga: funct3 - Para cargar datos de memoria
load_type: Dict[str, int] = {
    "lb": 0b000,   # Load byte
    "lh": 0b001,   # Load halfword
    "lw": 0b010,   # Load word
    "lbu": 0b100,  # Load byte unsigned
    "lhu": 0b101,  # Load halfword unsigned
}
opcode_load = 0b0000011  # Opcode para cargas

opcode_jalr = 0b1100111  # Opcode para JALR (salto con enlace relativo a registro)

# Tipo S para almacenes: funct3 - Para almacenar datos en memoria
s_type: Dict[str, int] = {
    "sb": 0b000,  # Store byte
    "sh": 0b001,  # Store halfword
    "sw": 0b010,  # Store word
}
opcode_s = 0b0100011  # Opcode para almacenes

# Tipo B para branches: funct3 - Instrucciones de salto condicional
b_type: Dict[str, int] = {
    "beq": 0b000,   # Branch equal
    "bne": 0b001,   # Branch not equal
    "blt": 0b100,   # Branch less than
    "bge": 0b101,   # Branch greater or equal
    "bltu": 0b110,  # Branch less than unsigned
    "bgeu": 0b111,  # Branch greater or equal unsigned
}
opcode_b = 0b1100011  # Opcode para branches

# Tipo U: opcode - Instrucciones con inmediato superior
u_type: Dict[str, int] = {
    "lui": 0b0110111,    # Load upper immediate
    "auipc": 0b0010111,  # Add upper immediate to PC
}

# Tipo UJ: opcode - Instrucciones de salto incondicional
uj_type: Dict[str, int] = {
    "jal": 0b1101111,  # Jump and link
}

# Pseudo-instrucciones mapeadas a instrucciones base
# Estas son abreviaturas que se expanden a instrucciones reales
pseudo: Dict[str, str] = {
    "mv": "addi {}, {}, 0",              # Mover (copia)
    "not": "xori {}, {}, -1",            # NOT lógico
    "neg": "sub {}, zero, {}",           # Negar (resta de zero)
    "seqz": "sltiu {}, {}, 1",           # Set if equal to zero
    "snez": "sltu {}, zero, {}",         # Set if not equal to zero
    "sltz": "slt {}, {}, zero",          # Set if less than zero
    "sgtz": "slt {}, zero, {}",          # Set if greater than zero
    "beqz": "beq {}, zero, {}",          # Branch if equal to zero
    "bnez": "bne {}, zero, {}",          # Branch if not equal to zero
    "blez": "bge zero, {}, {}",          # Branch if less or equal to zero
    "bgez": "bge {}, zero, {}",          # Branch if greater or equal to zero
    "bltz": "blt {}, zero, {}",          # Branch if less than zero
    "bgtz": "blt zero, {}, {}",          # Branch if greater than zero
    "bgt": "blt {}, {}, {}",             # Branch if greater than
    "ble": "bge {}, {}, {}",             # Branch if less or equal
    "bgtu": "bltu {}, {}, {}",           # Branch if greater than unsigned
    "bleu": "bgeu {}, {}, {}",           # Branch if less or equal unsigned
    "j": "jal zero, {}",                 # Jump (sin enlace)
    "jr": "jalr zero, {}, 0",            # Jump register
    "ret": "jalr zero, ra, 0",           # Return
    "call": "jal ra, {}",                # Call (jal con ra)
    "nop": "addi zero, zero, 0",         # No operation
    "li": "addi {}, zero, {}",           # Load immediate (simple, asume imm cabe en 12 bits; para grandes usa lui manual)
}

# Función para parsear valores inmediatos (soporta decimal, hex 0x, binario 0b)
# Esta función convierte una cadena que representa un inmediato a un entero
def parse_imm(arg: str) -> int:
    try:
        if arg.startswith('0x'):  # Si es hexadecimal
            return int(arg, 16)
        elif arg.startswith('0b'):  # Si es binario
            return int(arg, 2)
        else:  # Decimal por defecto
            return int(arg)
    except ValueError:
        raise ValueError(f"Inmediato inválido: {arg}")  # Error si no se puede convertir

# Función para obtener el número de registro
# Convierte un nombre de registro a su número binario
def get_reg(reg_str: str) -> int:
    reg_lower = reg_str.lower()  # Convertir a minúsculas para case-insensitive
    if reg_lower in regs:
        return regs[reg_lower]  # Retornar el número si existe
    raise ValueError(f"Registro inválido: {reg_str}")  # Error si no existe

# Función principal de ensamblado: ensamblador de dos pasadas
# Primera pasada: recolecta etiquetas (labels)
# Segunda pasada: ensambla instrucciones, maneja pseudo, genera binario y hex
def assemble(lines: List[str]) -> List[Tuple[str, str, str]]:
    # Primera pasada: recolectar etiquetas y sus direcciones
    label_dict: Dict[str, int] = {}  # Diccionario para etiquetas -> direcciones
    current_addr = 0  # Dirección actual inicia en 0
    for line in lines:  # Iterar sobre cada línea
        line = line.strip()  # Eliminar espacios en blanco
        if not line or line.startswith('#'):  # Ignorar líneas vacías o comentarios
            continue
        if '#' in line:  # Eliminar comentarios inline
            line = line.split('#')[0].strip()
        if line.endswith(':'):  # Si es una etiqueta
            label = line[:-1].strip()  # Obtener nombre de etiqueta
            if label in label_dict:  # Verificar duplicados
                raise ValueError(f"Etiqueta duplicada: {label}")
            label_dict[label] = current_addr  # Asignar dirección actual
            continue  # No incrementa dirección para etiquetas
        current_addr += 4  # Cada instrucción ocupa 4 bytes

    # Segunda pasada: ensamblar
    result: List[Tuple[str, str, str]] = []  # Lista para resultados (instrucción, bin, hex)
    current_addr = 0  # Reiniciar dirección
    for original_line in lines:  # Iterar nuevamente sobre líneas originales
        line = original_line.strip()  # Limpiar línea
        if not line or line.startswith('#') or line.endswith(':'):  # Ignorar no-instrucciones
            continue
        if '#' in line:  # Eliminar comentarios
            line = line.split('#')[0].strip()

        # Parsear operación y argumentos
        parts = re.split(r'\s+', line, maxsplit=1)  # Dividir en op y args
        op = parts[0].lower()  # Operación en minúsculas
        args = parts[1] if len(parts) > 1 else ""  # Argumentos si existen

        # Manejar pseudo-instrucciones expandiéndolas a base
        if op in pseudo:  # Si es pseudo
            arg_list = re.split(r'\s*,\s*', args)  # Dividir args
            new_line = pseudo[op].format(*arg_list)  # Formatear a instrucción base
            parts = re.split(r'\s+', new_line, maxsplit=1)  # Reparsear
            op = parts[0].lower()
            args = parts[1] if len(parts) > 1 else ""

        # Parsear lista de argumentos
        arg_list = re.split(r'\s*,\s*', args)  # Dividir por comas

        # Ensamblar basado en tipo de instrucción
        instr = 0  # Inicializar instrucción binaria en 0
        if op in r_type:  # Tipo R
            rd = get_reg(arg_list[0])  # Registro destino
            rs1 = get_reg(arg_list[1])  # Registro fuente 1
            rs2 = get_reg(arg_list[2])  # Registro fuente 2
            funct3 = r_type[op][0]  # funct3 de la op
            funct7 = r_type[op][1]  # funct7 de la op
            # Construir binario: funct7 | rs2 | rs1 | funct3 | rd | opcode
            instr = (funct7 << 25) | (rs2 << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | opcode_r
        elif op in i_arith_type:  # Tipo I aritmético
            rd = get_reg(arg_list[0])  # Destino
            rs1 = get_reg(arg_list[1])  # Fuente
            imm_str = arg_list[2]  # Inmediato como string
            imm = parse_imm(imm_str)  # Parsear inmediato
            funct3 = i_arith_type[op]  # funct3
            if op in ['slli', 'srli', 'srai']:  # Para shifts (shamt 5 bits)
                imm = imm & 0x1f  # Máscara para 5 bits
                if op == 'srai':  # Ajuste para srai
                    imm |= (0b0100000 << 5)
            else:  # Inmediato normal 12 bits
                imm = imm & 0xfff
            # Construir: imm | rs1 | funct3 | rd | opcode
            instr = (imm << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | opcode_i_arith
        elif op in load_type:  # Cargas (tipo I)
            rd = get_reg(arg_list[0])  # Destino
            offset_base = arg_list[1]  # offset(base)
            match = re.match(r'(-?[\w]+)\((\w+)\)', offset_base)  # Parsear con regex
            if not match:
                raise ValueError(f"Formato de carga inválido: {offset_base}")
            imm_str, base = match.groups()  # Obtener imm y base
            imm = parse_imm(imm_str)  # Parsear imm
            rs1 = get_reg(base)  # Base como registro
            funct3 = load_type[op]  # funct3
            imm = imm & 0xfff  # 12 bits
            # Construir similar a I aritmético
            instr = (imm << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | opcode_load
        elif op == 'jalr':  # JALR (tipo I especial)
            rd = get_reg(arg_list[0])
            offset_base = arg_list[1]
            match = re.match(r'(-?[\w]+)\((\w+)\)', offset_base)
            if not match:
                raise ValueError(f"Formato de jalr inválido: {offset_base}")
            imm_str, base = match.groups()
            imm = parse_imm(imm_str)
            rs1 = get_reg(base)
            funct3 = 0b000  # funct3 fijo para jalr
            imm = imm & 0xfff
            instr = (imm << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | opcode_jalr
        elif op in s_type:  # Tipo S (almacenes)
            rs2 = get_reg(arg_list[0])  # Fuente a almacenar
            offset_base = arg_list[1]
            match = re.match(r'(-?[\w]+)\((\w+)\)', offset_base)
            if not match:
                raise ValueError(f"Formato de store inválido: {offset_base}")
            imm_str, base = match.groups()
            imm = parse_imm(imm_str)
            rs1 = get_reg(base)
            funct3 = s_type[op]
            imm = imm & 0xfff
            imm11_5 = (imm >> 5) & 0x7f  # Bits altos de imm
            imm4_0 = imm & 0x1f  # Bits bajos
            # Construir: imm11_5 | rs2 | rs1 | funct3 | imm4_0 | opcode
            instr = (imm11_5 << 25) | (rs2 << 20) | (rs1 << 15) | (funct3 << 12) | (imm4_0 << 7) | opcode_s
        elif op in b_type:  # Tipo B (branches)
            rs1 = get_reg(arg_list[0])
            rs2 = get_reg(arg_list[1])
            imm_str = arg_list[2]
            if imm_str in label_dict:  # Si es etiqueta, calcular offset
                imm = label_dict[imm_str] - current_addr
            else:
                imm = parse_imm(imm_str)
            if imm % 2 != 0:  # Offset debe ser par
                raise ValueError("Offset de branch debe ser par")
            imm = imm & 0x1ffe  # 13 bits
            funct3 = b_type[op]
            # Descomponer imm en bits específicos para formato B
            imm12 = (imm >> 12) & 0x01
            imm10_5 = (imm >> 5) & 0x3f
            imm4_1 = (imm >> 1) & 0x0f
            imm11 = (imm >> 11) & 0x01
            # Construir: imm12 | imm10_5 | rs2 | rs1 | funct3 | imm4_1 | imm11 | opcode
            instr = (imm12 << 31) | (imm10_5 << 25) | (rs2 << 20) | (rs1 << 15) | (funct3 << 12) | (imm4_1 << 8) | (imm11 << 7) | opcode_b
        elif op in u_type:  # Tipo U
            rd = get_reg(arg_list[0])
            imm_str = arg_list[1]
            imm = parse_imm(imm_str) & 0xfffff000  # 20 bits superiores
            opcode = u_type[op]
            # Construir: imm | rd | opcode
            instr = imm | (rd << 7) | opcode
        elif op in uj_type:  # Tipo UJ (jal)
            rd = get_reg(arg_list[0])
            imm_str = arg_list[1]
            if imm_str in label_dict:  # Calcular offset si etiqueta
                imm = label_dict[imm_str] - current_addr
            else:
                imm = parse_imm(imm_str)
            if imm % 2 != 0:
                raise ValueError("Offset de JAL debe ser par")
            imm = imm & 0x1ffffe  # 21 bits
            # Descomponer imm para formato UJ
            imm20 = (imm >> 20) & 0x1
            imm19_12 = (imm >> 12) & 0xff
            imm11 = (imm >> 11) & 0x1
            imm10_1 = (imm >> 1) & 0x3ff
            # Construir: imm20 | imm10_1 | imm11 | imm19_12 | rd | opcode
            instr = (imm20 << 31) | (imm19_12 << 12) | (imm11 << 20) | (imm10_1 << 21) | (rd << 7) | uj_type[op]
        elif op == 'ecall':  # Soporte para ecall (instrucción especial para syscalls)
            # Encoding fijo para ecall: opcode 0b1110011, imm=0, rd=0, rs1=0, funct3=0
            instr = 0b00000000000000000000000001110011
        else:
            raise ValueError(f"Instrucción desconocida: {op}")  # Error si op no reconocida

        # Convertir a strings binario y hex
        bin_str = bin(instr)[2:].zfill(32)  # Binario de 32 bits con ceros a la izquierda
        hex_str = hex(instr)  # Hexadecimal

        result.append((original_line.strip(), bin_str, hex_str))  # Agregar a resultados
        current_addr += 4  # Avanzar dirección

    return result  # Retornar lista de resultados

# Configuración de la GUI
def main():
    root = tk.Tk()  # Crear ventana principal
    root.title("Ensamblador RISC-V")  # Título de la ventana

    # Botón para cargar archivo TXT
    def load_file():
        file_path = filedialog.askopenfilename(filetypes=[("Archivos de texto", "*.txt")])  # Diálogo para seleccionar archivo
        if file_path:  # Si se selecciona un archivo
            with open(file_path, 'r') as f:  # Abrir y leer
                content = f.read()
            input_text.delete(1.0, tk.END)  # Limpiar área de texto
            input_text.insert(tk.END, content)  # Insertar contenido

    load_button = tk.Button(root, text="Cargar Archivo TXT", command=load_file)  # Crear botón
    load_button.pack(pady=10)  # Colocar con padding

    # Área de texto para código assembly de entrada
    input_text = tk.Text(root, height=10, width=60)  # Crear área de texto
    input_text.pack(pady=10)  # Colocar

    # Botón para ensamblar
    def assemble_action():
        lines = input_text.get(1.0, tk.END).splitlines()  # Obtener líneas del texto
        try:
            assembled = assemble(lines)  # Llamar a función assemble
            # Limpiar tabla
            for item in tree.get_children():
                tree.delete(item)
            # Poblar tabla con resultados
            for instr, bin_str, hex_str in assembled:
                tree.insert('', tk.END, values=(instr, bin_str, hex_str))
        except Exception as e:  # Manejar errores
            messagebox.showerror("Error", str(e))  # Mostrar mensaje de error

    assemble_button = tk.Button(root, text="Ensamblar", command=assemble_action)  # Crear botón
    assemble_button.pack(pady=10)  # Colocar

    # Tabla para mostrar resultados
    columns = ("Instrucción", "Binario", "Hexadecimal")  # Columnas
    tree = ttk.Treeview(root, columns=columns, show="headings", height=10)  # Crear Treeview
    tree.heading("Instrucción", text="Instrucción")  # Configurar encabezados
    tree.heading("Binario", text="Binario")
    tree.heading("Hexadecimal", text="Hexadecimal")
    tree.column("Instrucción", width=200)  # Configurar anchos
    tree.column("Binario", width=300)
    tree.column("Hexadecimal", width=100)
    tree.pack(fill=tk.BOTH, expand=True, pady=10)  # Colocar y expandir

    root.mainloop()  # Iniciar loop de la GUI

if __name__ == "__main__":  # Si se ejecuta directamente
    main()  # Llamar a main