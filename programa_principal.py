# ================================================================#
# Código creado por @TekkuEc para Condor Energy en Ecuador
# Versión: 3.XXy
# Desarrollador: David Novillo
# Loja, Ecuador - Mayo 2024
# ===================== www.tekku.com.ec =========================#

import websockets
import asyncio
from datetime import datetime, timezone
import json
import serial
import os
import sys
import time
from termcolor import colored

from ocpp_communication.charge_point import MyChargePoint, load_keys
from logger.logger_creator import custom_logger
from charger_communication.serial_communication import comunicacion_serial_cargador, estados_status_notification
from constants import (
    TRAMA_CARGAR,
    TRAMA_DETENER,
    TRAMA_INICIALIZAR,
    WS_URL,
    NUM_CARGADOR,
    ID_WEBSOCKET,
)

# Variables globales
remote_start_transaction = False  # Variable para iniciar la transacción
stop_transaction = False  # Variable para detener la transacción
id_tag = None
connector_id = 0
transaction_id = None
send_meter_reading = False
logger = custom_logger()
indent = "                             "  # Indentación para el logger
send_heartbeat = False


async def handle_queue(queue):
    global \
        remote_start_transaction, \
        stop_transaction, \
        id_tag, \
        connector_id, \
        send_meter_reading, \
        transaction_id, \
        send_heartbeat
    data = None
    while True:
        if not queue.empty():
            data = await queue.get()
            logger.info(
                colored(f"Mensaje recibido: {data[0]}\n{indent}Datos recibidos: {data[1:]}", attrs=["bold"]))
            if data[0] == "RemoteStartTransaction":
                remote_start_transaction = True
                id_tag = data[1]
                connector_id = data[2]
            elif data[0] == "TriggerMessage":
                if data[1] == "MeterValues":
                    send_meter_reading = True
                    if data[2] is not None:
                        connector_id = data[2]
                elif data[1] == "Heartbeat":
                    send_heartbeat = True
            elif data[0] == "RemoteStopTransaction":
                transaction_id = data[1]
                stop_transaction = True
            else:
                send_meter_reading = False
                remote_start_transaction = False
                stop_transaction = False
        await asyncio.sleep(2)  # Esperar un poco antes de verificar nuevamente


def clear():  # Función para limpiar la consola
    return os.system("clear")


# Configuración inicial del puerto serial


def iniciar_serial(port):
    if port == "/dev/ttyUSB0":
        modulo = "cargador"
    else:
        modulo = "medidor"
    try:
        ser = serial.Serial(
            port,
            baudrate=9600,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            timeout=1,
        )
        return ser
    except serial.SerialException as e:
        logger.error(
            colored(f"Revise el modulo USB - RS-485 del {modulo}", color="red"))
        return None


async def main():
    # Declaración de variables globales
    global remote_start_transaction, \
        stop_transaction, \
        id_tag, \
        connector_id, \
        send_meter_reading, \
        transaction_id, \
        logger, \
        indent, \
        send_heartbeat
    version = "3.00m"  # versión del programa

    clear()  # Limpiar la consola

    # Se crea el logger
    logger.info(colored(
        f"Iniciando programa...\n{indent}Version: {version}\n{indent}Punto de carga: {NUM_CARGADOR}\n{indent}ID WS: {ID_WEBSOCKET}", attrs=["bold"], color="light_green"))

    # Configuración de la comunicación serial con el cargador
    ser = iniciar_serial("/dev/ttyUSB0")

    cp_status, battery_status, corriente, voltaje = None, None, None, None

    # Función para verificar el estado del cargador en segundo plano
    async def check_charger_status(should_pause, charge_point=None):
        nonlocal cp_status, battery_status, corriente, voltaje, ser
        contador_sin_comunicacion = 0
        while True:
            if not should_pause[0]:
                logger.info(
                    colored("Comunicación constante activa", attrs=["bold"]))
                cp_status, battery_status, corriente, voltaje = comunicacion_serial_cargador(
                    ser, TRAMA_INICIALIZAR, logger)

                # Enviar el estado del cargador a la instancia de ChargePoint
                charge_point.set_info(cp_status)

            if cp_status == "Desconocido":
                contador_sin_comunicacion += 1
            else:
                contador_sin_comunicacion = 0

            if contador_sin_comunicacion == 2:
                ser.close()
                await asyncio.sleep(3)
                ser = iniciar_serial("/dev/ttyUSB0")

            # if contador_sin_comunicacion >= 3:
            #     logger.error(colored(
            #         "Error en la comunicación con el cargador, reiniciando Raspberry...", color="red"))
            #     os.system("sudo reboot")
            await asyncio.sleep(300)

    # Función para manejar la excepción en la tarea del charge_point
    async def run_task_with_exception_handling(task_coro, charge_point=None):
        nonlocal cp_status, battery_status, corriente, voltaje
        try:
            # Intenta ejecutar la tarea original
            await task_coro
        except Exception as e:
            logger.error(
                colored(f"Error en la tarea {task_coro.__name__}: \n{e}", color="red"))
            if not charge_point.is_connected():
                logger.error(colored("Se perdió la conexión...", color="red"))

    # Función para calcular el consumo en kWh
    def energy(time, voltaje, corriente):
        return (time * voltaje * corriente * 1.73205081) / 3600000

    # Cargar valores de intervalos de tiempo desde el archivo keys.json
    meter_values_interval = load_keys("MeterValuesInterval", 30)
    heartbeat_interval = load_keys("HeartbeatInterval", 14400)
    logger.info(
        f"Intervalo de MeterValues: {meter_values_interval} s\n{indent}Intervalo de Heartbeat: {heartbeat_interval} s")

    # Inicialización de variables
    cp_status, battery_status, corriente, voltaje = comunicacion_serial_cargador(
        ser, TRAMA_INICIALIZAR, logger)

    energy_consumption = 0
    power = 0
    retry_delay = 30  # delay in seconds
    counter = meter_values_interval + 1
    save_time = True
    cuenta_consumo = 0

    while True:
        try:
            # Crear una cola
            queue = asyncio.Queue()
            should_pause = [False]

            # Establecimiento de la conexión WebSocket con el Central System
            try:
                async with websockets.connect(
                    WS_URL, subprotocols=["ocpp1.6"], ping_interval=30, ping_timeout=30
                ) as ws:
                    # Crear una instancia de la clase MyChargePoint
                    charge_point = MyChargePoint(ID_WEBSOCKET, ws, queue=queue)

                    # Iniciar charge_point.start() y handle_queue() en segundo plano
                    asyncio.create_task(run_task_with_exception_handling(
                        charge_point.start(), charge_point))
                    task_queue = asyncio.create_task(
                        run_task_with_exception_handling(handle_queue(queue), charge_point))
                    # Se inicia la comunicación serial constante con el cargador en segundo plano
                    task_serial = asyncio.create_task(
                        check_charger_status(should_pause, charge_point))

                    # Enviar un mensaje BootNotification y esperar la respuesta
                    boot_response = await charge_point.send_boot_notification()
                    logger.info(
                        colored(f"Boot Notification enviado\n{indent}Respuesta: {boot_response}", color="yellow"))

                    # Enviar el estado del cargador a la instancia de ChargePoint
                    charge_point.set_info(cp_status)

                    # Función que retorna los status del Status Notification según el estado del cargador
                    status = estados_status_notification(cp_status)

                    # Enviar un mensaje StatusNotification
                    await charge_point.send_status_notification(
                        connector_id=1,
                        status=status[0],
                        error_code=status[1],
                        info=status[2],
                    )
                    logger.info(
                        colored(f"Status Notification enviado: {status}", color="green"))

                    contador_standby = 0
                    last_cp_status = cp_status

                    while True:
                        if charge_point.is_connected() == False:
                            await asyncio.sleep(5)
                            task_queue.cancel()
                            task_serial.cancel()
                            break

                        current_time = (datetime.now(timezone.utc).strftime(
                            "%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z")

                        if last_cp_status != cp_status:
                            status = estados_status_notification(cp_status)

                            # Enviar un mensaje StatusNotification
                            await charge_point.send_status_notification(
                                connector_id=1,
                                status=status[0],
                                error_code=status[1],
                                info=status[2],
                            )
                            logger.info(
                                colored(f"Status Notification enviado por cambio de estado:\n{indent}{status}\n{indent}Estado anterior: {last_cp_status}", color="green"))
                            last_cp_status = cp_status

                        # Bucle para enviar el HeartBeat
                        if save_time == True:
                            hora_intervalo = time.time() + heartbeat_interval
                            save_time = False

                        if time.time() >= hora_intervalo or send_heartbeat == True:
                            heartbeat_response = await charge_point.send_heartbeat()
                            logger.info(
                                colored(f"Heartbeat enviado\n{indent}Respuesta: {heartbeat_response}", color="light_yellow"))
                            save_time = True
                            send_heartbeat = False

                        # Iniciar la transacción remota
                        if remote_start_transaction == True:
                            # Pausar la comunicación constante con el cargador:
                            should_pause[0] = True

                            # Leer el estado del cargador y del medidor
                            cp_status, battery_status, corriente, voltaje = (
                                comunicacion_serial_cargador(ser, TRAMA_INICIALIZAR, logger))

                            status = estados_status_notification(cp_status)

                            # Enviar un mensaje StatusNotification
                            await charge_point.send_status_notification(
                                connector_id=connector_id,
                                status=status[0],
                                error_code=status[1],
                                info=status[2],
                            )
                            logger.info(
                                f"Status Notification enviado: {status}\n{indent}Connector_id: {connector_id}")

                            # Enviar un mensaje StartTransaction
                            start_transaction_response = (
                                await charge_point.send_start_transaction(
                                    connector_id=connector_id,
                                    meter_start=energy_consumption,
                                    id_tag=id_tag,
                                    timestamp=current_time,
                                )
                            )
                            logger.info(
                                colored(f"Start Transaction enviado\n{indent}Respuesta: {start_transaction_response}", color="light_blue"))

                            energy_consumption_start = energy_consumption

                            if start_transaction_response.id_tag_info["status"] == "Accepted":
                                counter = 0
                                transaction_id = start_transaction_response.transaction_id

                            remote_start_transaction = False

                            # Comprobar si la pistola está conectada para enviar la trama de carga
                            if cp_status == "Pistola Conectada":
                                cp_status, battery_status, corriente, voltaje = (
                                    comunicacion_serial_cargador(ser, TRAMA_CARGAR, logger))

                        if send_meter_reading == True or counter == meter_values_interval:
                            # Comprobar si la pistola está conectada para enviar la trama de carga
                            if cp_status == "Pistola Conectada":
                                cp_status, battery_status, corriente, voltaje = (
                                    comunicacion_serial_cargador(ser, TRAMA_CARGAR, logger))

                                status = estados_status_notification(cp_status)
                                # Enviar un mensaje StatusNotification
                                await charge_point.send_status_notification(
                                    connector_id=connector_id,
                                    status=status[0],
                                    error_code=status[1],
                                    info=status[2],
                                )
                                logger.info(
                                    f"Status Notification enviado: {status}\n{indent}Connector_id: {connector_id}")

                            else:
                                cp_status, battery_status, corriente, voltaje = (
                                    comunicacion_serial_cargador(ser, TRAMA_INICIALIZAR, logger))

                            if cp_status == "StandBy":
                                contador_standby += 1

                            elif cp_status == "Cargando":
                                contador_standby = 0

                            if cuenta_consumo >= 1:
                                energy_consumption = energy_consumption + \
                                    energy(63, voltaje, corriente)
                            else:
                                cuenta_consumo += 1

                            power = corriente * voltaje * 1.73205081

                            if contador_standby >= 6:
                                logger.info(
                                    colored("Timeout del estado StandBy durante la carga. Terminando la transacción...", color="light_red"))

                            # Enviar un mensaje MeterValues
                            await charge_point.send_meter_values(
                                connector_id=0,
                                energy_value=energy_consumption,
                                power_value=power,
                                battery_value=battery_status,
                                timestamp=current_time,
                                transaction_id=transaction_id,
                            )
                            logger.info(
                                colored(f"Meter Values enviado\n{indent}Energy: {energy_consumption} kWh\n{indent}Power: {power} W\n{indent}Battery: {battery_status}%", color="light_cyan"))
                            counter = 0
                            send_meter_reading = False

                        if counter < meter_values_interval:
                            counter += 1
                        if (stop_transaction == True or cp_status == "Carga Completa" or battery_status == 100 or contador_standby >= 6):
                            # Detener la carga
                            cp_status, battery_status, corriente, voltaje = (
                                comunicacion_serial_cargador(ser, TRAMA_DETENER, logger))

                            status = estados_status_notification(cp_status)
                            # Enviar un mensaje StatusNotification
                            await charge_point.send_status_notification(
                                connector_id=connector_id,
                                status=status[0],
                                error_code=status[1],
                                info=status[2],
                            )
                            logger.info(
                                f"Status Notification enviado: {status}\n{indent}Connector_id: {connector_id}")

                            # Enviar un mensaje StopTransaction
                            stop_transaction_response = (
                                await charge_point.send_stop_transaction(
                                    meter_stop=energy_consumption,
                                    transaction_id=transaction_id,
                                    timestamp=current_time,
                                )
                            )
                            logger.info(
                                colored(f"Stop Transaction enviado\n{indent}Meter stop:{energy_consumption}\n{indent}Respuesta: {stop_transaction_response}", color="light_magenta"))

                            stop_transaction = False

                            # Esperar un poco antes de enviar el StatusNotification
                            await asyncio.sleep(10)
                            cp_status, battery_status, corriente, voltaje = (
                                comunicacion_serial_cargador(ser, TRAMA_INICIALIZAR, logger))

                            # Comprobar si aún no se ha detenido la carga
                            if cp_status == "Cargando":
                                cp_status, battery_status, corriente, voltaje = (
                                    comunicacion_serial_cargador(ser, TRAMA_DETENER, logger))

                            while cp_status == "Pistola Conectada Fin de Carga" or cp_status == "Carga Completa":
                                await asyncio.sleep(10)
                                cp_status, battery_status, corriente, voltaje = (
                                    comunicacion_serial_cargador(ser, TRAMA_INICIALIZAR, logger))

                            status = estados_status_notification(cp_status)
                            # Enviar un mensaje StatusNotification
                            await charge_point.send_status_notification(
                                connector_id=connector_id,
                                status=status[0],
                                error_code=status[1],
                                info=status[2],
                            )
                            logger.info(
                                f"Status Notification enviado: {status}\n{indent}Connector_id: {connector_id}")

                            # Se regresan las variables a su valor inicial
                            counter = meter_values_interval + 1
                            send_once = True
                            should_pause[0] = False
                            contador_standby = 0
                            last_cp_status = cp_status
                            cuenta_consumo = 0
                            # Limpiar la consola
                            clear()
                        await asyncio.sleep(2)

            except websockets.exceptions.ConnectionClosed as e:
                logger.error(
                    colored(f"La conexión WebSocket se cerró inesperadamente: \n{e}", color="red"))
            except websockets.exceptions.InvalidURI as e:
                logger.error(
                    colored(f"La URI proporcionada no es válida: {e}", color="red"))
            except Exception as e:
                logger.error(colored(f"Ocurrió un error: \n{e}", color="red"))

        except Exception as e:
            logger.error(
                colored(f"Ocurrió un error al intentar conectar: \n{e}", color="red"))
        except KeyboardInterrupt:
            await ws.close()
            print("Program interrupted by user. Exiting...")

        logger.info(colored(f"Reintentando conexión...", color="light_red"))
        await asyncio.sleep(retry_delay)  # Espera antes de reintentar


if __name__ == "__main__":
    asyncio.run(main())
