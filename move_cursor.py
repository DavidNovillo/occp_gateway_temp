import sys


def mover_cursor(x, y):
    sys.stdout.write(f"\033[{y};{x}H")
    sys.stdout.flush()


print("\nESTADO DEL CARGADOR")

mover_cursor(1, 6)
print("Estado del cargador: StandBy")

mover_cursor(1, 6)
print("Estado del cargador: Pistola Conectada")
