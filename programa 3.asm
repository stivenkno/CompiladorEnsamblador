# Recursive Fibonacci function in RISC-V
# Arguments:
#   a0 = n (the Fibonacci index)
# Returns:
#   a0 = fib(n)

fib:
    addi sp, sp, -16      # Reserva espacio en la pila
    sw ra, 12(sp)         # Guarda la dirección de retorno
    sw s0, 8(sp)          # Guarda s0
    sw a0, 4(sp)          # Guarda argumento n

    # Base case: if n == 0 -> return 0
    beq a0, zero, fib_base0  

    # Base case: if n == 1 -> return 1
    addi t0, zero, 1
    beq a0, t0, fib_base1  

    # Recursive case: fib(n) = fib(n-1) + fib(n-2)
    addi a0, a0, -1       # a0 = n-1
    jal ra, fib           # Llamada recursiva fib(n-1)
    mv s0, a0             # Guarda resultado fib(n-1) en s0

    lw a0, 4(sp)          # Recupera n original
    addi a0, a0, -2       # a0 = n-2
    jal ra, fib           # Llamada recursiva fib(n-2)

    add a0, a0, s0        # a0 = fib(n-1) + fib(n-2)
    j fib_return

fib_base0:
    addi a0, zero, 0
    j fib_return

fib_base1:
    addi a0, zero, 1
    j fib_return

fib_return:
    lw ra, 12(sp)         # Restaura ra
    lw s0, 8(sp)          # Restaura s0
    addi sp, sp, 16       # Libera pila
    jr ra                 # Retorno


# MAIN PROGRAM
_start:
    addi a0, zero, 10     # Queremos fib(10)
    jal ra, fib           # Llamar fib(10)

    # Exit program
    li a7, 93             # syscall: exit
    ecall
