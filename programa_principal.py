# ================================================================#
# Código creado por @TekkuEc para Condor Energy en Ecuador
# Versión: 3.XXy
# Desarrollador: David Novillo
# Loja, Ecuador - Mayo 2024
# ===================== www.tekku.com.ec =========================#
import os
import subprocess
import time
import serial
from ocpp.routing import on
from ocpp.v16 import ChargePoint as cp
from ocpp.v16.enums import Action
from ocpp.v16 import call_result, call
import asyncio
import websockets
import RPi.GPIO as GPIO
import json
from termcolor import colored

from logger.logger_creator import custom_logger
from charger_communication.serial_communication import comunicacion_serial_cargador, comunicacion_serial_medidor
from constants import TRAMA_CARGAR, TRAMA_DETENER, TRAMA_INICIALIZAR, NUM_CARGADOR, ID_CARGADOR
from ocpp_communication.charge_point import MyChargePoint

# Importaciones de prueba
from tests.comunicacion_serial_test import test_serial_cargador, test_serial_medidor


async def main():
    version = f"3.00a    id:{ID_CARGADOR}"

    # Se crea el logger
    logger = custom_logger()
    logger.info(colored(f"\n\nIniciando programa...", attrs=[
                "bold", "blink"], color="light_green"))
    logger.info(colored(f"Versión del programa: {version}", attrs=[
                "bold"], color="light_green"))
    logger.info(colored(
        f"Estación de carga {Num_cargador} - ID: {ID_cargador}\n", attrs=["bold"], color="light_green"))

    # Asignación de pines GPIO para encender y apagar las luces piloto
    luz_verde = 8
    luz_naranja = 10

    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(luz_verde, GPIO.OUT)
    GPIO.setup(luz_naranja, GPIO.OUT)
    GPIO.setwarnings(False)

    # Declaración de funciones para encender y apagar las luces piloto
    def naranja_on():
        return GPIO.output(luz_naranja, 0)

    def naranja_off():
        return GPIO.output(luz_naranja, 1)

    def verde_on():
        return GPIO.output(luz_verde, 1)

    def verde_off():
        return GPIO.output(luz_verde, 0)

    naranja_off()
    verde_off()

    # Configuración de la comunicación serial con el cargador
    try:
        ser = serial.Serial("/dev/ttyUSB0", baudrate=9600,
                            parity=serial.PARITY_NONE, bytesize=serial.EIGHTBITS, timeout=0.5)
        ser.reset_output_buffer()
        ser.reset_input_buffer()
    except:
        logger.error("Revise el modulo USB - RS-485 del cargador")

    # Configuración de la comunicación serial con el medidor
    try:
        ser_medidor = serial.Serial("/dev/ttyUSB1", baudrate=9600, parity=serial.PARITY_NONE,
                                    stopbits=serial.STOPBITS_ONE, bytesize=serial.EIGHTBITS, timeout=0.3)
        ser_medidor.reset_output_buffer()
        ser_medidor.reset_input_buffer()

    except:
        logger.error("Revise el modulo USB - RS-485 del medidor")

    # Declaración e inicialización de variables
    estados = {
        "estadoStandBy": True,
        "estadoConexion": False,
        "estadoCarga": False,
        "estadoCargaCompleta": False,
        "errores": "",
    }
    estado_vehiculo = {
        "energiaEntregada": "0.0",
        "bateria": 0,
        "corriente": 0,
        "voltaje": 0,
    }

    band_cargar = False  # Bandera para enviar la trama de iniciar cargar una sola vez
    sin_conexion = False  # Bandera para saber si se perdió la conexión a internet
    fin_carga = False  # Indicador de finalizacion de carga normal
    estado_cargador = "Vacio"  # Indicador del estado del cargador
    porcentaje_carga = 0  # Variable con el valor del porcentaje de carga
    corriente = 0  # Variable con el valor de la corriente medida
    voltaje = 0  # Variable con el valor del voltaje medido
    energia_entregada_aux = 0.0  # Variable auxiliar para el cálculo de la energía
    energia_entregada = 0.0  # Variable con el valor final en kWh que se ha consumido
    # Variable con el valor en kWh del medidor al inicio de la carga
    energia_entregada_inicial = 0.0
    # Variable con el valor en kWh del medidor al terminar la carga
    energia_entregada_final = 0.0
    # Variable auxiliar del valor kWh cuando se reinicia el medidor
    energia_entregada_vieja = 0.0
    indicadorFinalizacion = ""  # Indicador de como se finalizo la carga
    band_init = 0  # Bandera para que se ejecute solo 1 vez el comienzo del initiateTransaction
    band_tiempo = 0
    band_recarga = 0
    hora_inicio = time.strftime("%H:%M")
    hora_fin = time.strftime("%H:%M")
    tiempo_1 = 0
    tiempo_2 = 0
    tiempo_kwh = 0

    diferencia_ts = 0
    band_abortar = 0
    sin_conexion_do = False

    # Función para limpiar la consola
    def clear():
        return os.system("clear")

    max_retries = 5
    retry_delay = 5  # delay in seconds

    for i in range(max_retries):
        try:
            # Establecimiento de la conexión WebSocket con el Central System
            async with websockets.connect('wss://sistema-de-manejo-central.com') as ws:

                # Crear una instancia de la clase MyChargePoint
                charge_point = MyChargePoint(ID_CARGADOR, ws)

                # Enviar un mensaje BootNotification
                boot_response = await charge_point.send_boot_notification()

                # Iniciar el bucle de eventos para escuchar los mensajes entrantes
                listen_task = asyncio.create_task(charge_point.start())

                # Mantener la comunicación serial con el equipo de carga
                while True:
                    # Time stamp
                    ts = int(time.time())
                    # Leer datos del cargador (TEST)
                    estado_cargador, porcentaje_carga, corriente, voltaje = comunicacion_serial_cargador(
                        ser, TRAMA_INICIALIZAR, logger)

                    # Aquí puedes agregar el código para procesar los datos recibidos y
                    # posiblemente enviar mensajes adicionales al Central System.
                break  # Si la conexión es exitosa, sal del bucle
        except websockets.exceptions.ConnectionClosed as e:
            logger.error(
                f"La conexión WebSocket se cerró inesperadamente: {e}")
        except websockets.exceptions.InvalidURI as e:
            logger.error(f"La URI proporcionada no es válida: {e}")
        except Exception as e:
            logger.error(f"Ocurrió un error al intentar conectar: {e}")

        logger.info(f"Reintentando conexión ({i+1}/{max_retries})...")
        await asyncio.sleep(retry_delay)  # Espera antes de reintentar

    if i == max_retries - 1:  # Si se alcanzó el número máximo de intentos
        logger.info(
            "Se alcanzó el número máximo de intentos de conexión. Reintentando...")

if __name__ == '__main__':
    asyncio.run(main())
