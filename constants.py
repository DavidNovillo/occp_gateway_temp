import json

# Se carga el ID único de cada raspberry
with open('/home/pi/ID.json') as identificador:
    datos_identificador = json.load(identificador)

ID_CARGADOR = str(datos_identificador['ID'])
NUM_CARGADOR = str(datos_identificador['Estacion'])
ID_WEBSOCKET = datos_identificador['id_websocket']

WS_URL = f'wss://app.tridenstechnology.com/ev-charge/gw-comm/condor-energy/{ID_WEBSOCKET}'

# Se cargan las tramas de comunicación con el cargador
TRAMA_INICIALIZAR = bytearray(
    b'\x23\x23\x00\x32\x40\x01\x10\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x83\x0D\x0A')
TRAMA_CARGAR = bytearray(
    b'\x23\x23\x00\x32\x40\x01\x10\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x84\x0D\x0A')
TRAMA_DETENER = bytearray(
    b'\x23\x23\x00\x32\x40\x01\x10\x00\x0B\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x8E\x0D\x0A')

# Trama de comunicación con el medidor
TRAMA_MEDIDOR_CONSUMO = bytearray.fromhex(
    datos_identificador['consumo_medidor'])
TRAMA_MEDIDOR_POTENCIA = bytearray.fromhex(
    datos_identificador['potencia_medidor'])
# TRAMA_MEDIDOR_CONSUMO = bytearray(b'\x01\x04\x01\x56\x00\x02\x90\x27')
# TRAMA_MEDIDOR_POTENCIA = bytearray(b'\x01\x04\x00\x34\x00\x02\x30\x05')

# Modelo y fabricante del cargador
CHARGE_POINT_MODEL = str(datos_identificador['Model'])
CHARGE_POINT_VENDOR = str(datos_identificador['Vendor'])
