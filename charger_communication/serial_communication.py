import time
import struct

from constants import TRAMA_INICIALIZAR

# FUNCION PARA OBTENER EL ESTADO DEL CARGADOR


def estados_cargador(dato):
    estado = f"Desconocido {dato}"
    if dato == "0x6":
        estado = "StandBy"
    if dato == "0x1":
        estado = "Start"
    if dato == "0x2":
        estado = "Cargando"
    if dato == "0x3":
        estado = "Carga Completa"
    if dato == "0x4":
        estado = "Cargador en Falla"
    if dato == "0x5":
        estado = "Pistola Conectada"
    if dato == "0xa":
        estado = "Sobrecalentamiento"
    if dato == "0xb":
        estado = "Falla de reinicio de contactor"
    if dato == "0xe":
        estado = "Sobrecarga de corriente"
    if dato == "0x1a":
        estado = "Pistola Conectada Fin de Carga"
    return estado


# ==== FUNCION PARA CREAR EL ESTADO DEL CARGADOR PARA EL SERVIDOR ====#


def estados_status_notification(dato):
    if dato == "StandBy":
        return ("Available", "NoError", "Estado del cargador: StandBy")
    elif dato == "Start":
        return ("Preparing", "NoError", "Estado del cargador: Start")
    elif dato == "Cargando":
        return ("Charging", "NoError", "Estado del cargador: Cargando")
    elif dato == "Carga Completa":
        return ("SuspendedEV", "NoError", "Estado del cargador: Carga Completa")
    elif dato == "Cargador en Falla":
        return ("Faulted", "InternalError", "Estado del cargador: Cargador en Falla")
    elif dato == "Pistola Conectada":
        return ("Preparing", "NoError", "Estado del cargador: Pistola Conectada")
    elif dato == "Sobrecalentamiento":
        return (
            "SuspendedEVSE",
            "HighTemperature",
            "Estado del cargador: Sobrecalentamiento",
        )
    elif dato == "Falla de reinicio de contactor":
        return (
            "SuspendedEVSE",
            "PowerSwitchFailure",
            "Estado: Falla de reinicio de contactor",
        )
    elif dato == "Sobrecarga de corriente":
        return (
            "SuspendedEVSE",
            "OverCurrentFailure",
            "Estado: Sobrecarga de corriente",
        )
    elif dato == "Pistola Conectada Fin de Carga":
        return ("Finishing", "NoError", "Estado: Pistola Conectada Fin de Carga")
    elif dato == "Trama Desconocida":
        return (
            "Unavailable",
            "InternalError",
            "Estado del cargador: Trama desconocida",
        )
    else:
        return (
            "Unavailable",
            "InternalError",
            "Estado: Desconocido - Sin respuesta del cargador",
        )


def comunicacion_serial_cargador(ser, trama, logger):
    data_in = b""
    es_util = False
    es_inutil = False
    intentos = 4
    estado_cargador, porcentaje_carga, corriente, voltaje = "Vacio", 0, 0, 0
    trama_a_enviar = trama

    # Se hace máximo 4 intentos de comunicación con el cargador
    while es_util == False and intentos > 0:
        try:
            ser.write(trama_a_enviar)
        except ser.SerialTimeoutException as e:
            logger.error("Tiempo de espera al enviar la trama: %s", str(e))
        except Exception as e:
            logger.error("Problema inesperado al enviar la trama: %s", str(e))

        try:
            data_in = ser.read_until("\r\n")
        except ser.SerialTimeoutException as e:
            logger.error(
                "Tiempo de espera al leer la trama del cargador: %s", str(e))
        except Exception as e:
            logger.error(
                "Problema inesperado al leer la trama del cargador: %s", str(e)
            )

        # Se verifica si la trama recibida es útil
        if len(data_in) > 0:
            try:
                indice = data_in.index(b"\x23")
                if indice != 0:
                    data_in = data_in[indice:]
                    logger.error(
                        f"Trama desfasada, longitud: {len(data_in)}, trama: {data_in}")
            except Exception as e:
                logger.error("No se encontró el x23 en la trama")
                logger.error(e)
        else:
            estado_cargador = "Desconocido"
            intentos = intentos - 1
            logger.error("Sin respuesta del cargador")
            try:
                data_in = b""
                ser.reset_input_buffer()
                ser.reset_output_buffer()
            except Exception as e:
                logger.error(
                    "Problema en la comunicación serial (reset_input)")
                logger.error(e)

        if (
            len(data_in) > 28
            and hex(data_in[0]) == "0x23"
            and hex(data_in[1]) == "0x23"
        ):
            if hex(data_in[5]) == "0x1":
                es_inutil = True
                es_util = False
                trama_a_enviar = TRAMA_INICIALIZAR

            elif hex(data_in[5]) == "0x0":
                es_util = True
                es_inutil = False
                estado_cargador = estados_cargador(hex(data_in[13]))
                porcentaje_carga = int(data_in[28])
                aux = int(hex(data_in[24]) + hex(data_in[25])[2:], 16)
                if aux >= 5000:
                    corriente = (0.1 * aux) - 500
                    voltaje = int(hex(data_in[26]) + hex(data_in[27])[2:], 16)
                logger.info(f"Estado del cargador: {estado_cargador}")
        intentos = intentos - 1
        time.sleep(0.5)

    if len(data_in) > 0 and es_util == False and es_inutil == False:
        logger.error(f"Trama Desconocida: {data_in}")
        estado_cargador = "Trama Desconocida"
        logger.info(f"Estado del cargador: {estado_cargador}")
        try:
            data_in = b""
            ser.reset_input_buffer()
            ser.reset_output_buffer()
        except Exception as e:
            logger.error("Problema en la comunicación serial (reset_input)")
            logger.error(e)

    return estado_cargador, porcentaje_carga, corriente, voltaje


# **********************************************************************************************************************#


def comunicacion_serial_medidor(ser, logger, trama):
    data_in = b""
    intentos = 1
    trama_correcta = False
    energia_entregada = 0.0

    # Se tiene 2 intentos de comunicación con el medidor
    while trama_correcta == False and intentos >= 0:
        try:
            ser.write(trama)
        except Exception as e:
            logger.error("Problema al enviar la trama al medidor")
            logger.error(e)

        try:
            data_in = ser.read(9)
        except Exception as e:
            logger.error("Problema al leer la trama del medidor")
            logger.error(e)

        if len(data_in) > 0 and data_in[0] == 1:
            trama_correcta = True
            datos_utiles = data_in[3:7]
            valor = struct.unpack(">f", datos_utiles)
            energia_entregada = round(valor[0], 2)
            if trama[2] == 0x01:
                logger.info(f"Energía: {energia_entregada} kWh")
            elif trama[2] == 0x00:
                logger.info(f"Potencia: {energia_entregada/1000} kW")
            else:
                logger.error(f"Respuesta del medidor: {energia_entregada}")

        else:
            energia_entregada = 0
            logger.error("Sin respuesta del medidor")
            try:
                data_in = b""
                ser.reset_input_buffer()
                ser.reset_output_buffer()
            except Exception as e:
                logger.error(
                    "Problema en la comunicación serial (reset_input)")
                logger.error(e)

        intentos = intentos - 1
        time.sleep(0.5)

    if len(data_in) > 0 and trama_correcta == False:
        logger.error(f"Trama Desconocida desde el medidor: {data_in}")
        energia_entregada = 0
        logger.error(f"Respuesta del medidor: {energia_entregada}")
        try:
            data_in = b""
            ser.reset_input_buffer()
            ser.reset_output_buffer()
        except Exception as e:
            logger.error(
                "Problema en la comunicación serial con el medidor (reset_input)"
            )
            logger.error(e)

    return energia_entregada
