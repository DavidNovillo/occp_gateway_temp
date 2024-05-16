# ================================================================#
# Código creado por @TekkuEc para BYD en Ecuador
# Versión: 3.XXy
# Desarrollador: David Novillo
# Colaboradores: Rafael Auqui, Christian Guerra
# Quito, Ecuador - Octubre 2019
# ===================== www.tekku.com.ec =========================#
import os
import subprocess
import time
import serial
# import RPi.GPIO as GPIO
import json
from termcolor import colored

from logger.logger_creator import custom_logger
from charger_communication.serial_communication import comunicacion_serial_cargador, comunicacion_serial_medidor
from constants import TRAMA_CARGAR, TRAMA_DETENER, TRAMA_INICIALIZAR, NUM_CARGADOR, ID_CARGADOR

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


# GPIO.setmode(GPIO.BOARD)
# GPIO.setup(luz_verde, GPIO.OUT)
# GPIO.setup(luz_naranja, GPIO.OUT)
# GPIO.setwarnings(False)

# # Declaración de funciones para encender y apagar las luces piloto
# def naranja_on():
#     return GPIO.output(luz_naranja, 0)


# def naranja_off():
#     return GPIO.output(luz_naranja, 1)


# def verde_on():
#     return GPIO.output(luz_verde, 1)


# def verde_off():
#     return GPIO.output(luz_verde, 0)


# naranja_off()
# verde_off()

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
