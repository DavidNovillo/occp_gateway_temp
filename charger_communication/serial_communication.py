import time
import struct

TRAMA_INICIALIZAR = bytearray(
    b'\x23\x23\x00\x32\x40\x01\x10\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x83\x0D\x0A')
TRAMA_CARGAR = bytearray(
    b'\x23\x23\x00\x32\x40\x01\x10\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x84\x0D\x0A')
TRAMA_DETENER = bytearray(
    b'\x23\x23\x00\x32\x40\x01\x10\x00\x0B\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x8E\x0D\x0A')
TRAMA_MEDIDOR = bytearray(b'\x01\x04\x01\x56\x00\x02\x90\x27')

# ===== FUNCION PARA OBTENER EL ESTADO DEL CARGADOR ====#


def estados_cargador(dato):
    estado = f'Desconocido {dato}'
    if (dato == '0x6'):
        estado = 'StandBy'
    if (dato == '0x1'):
        estado = 'Start'
    if (dato == '0x2'):
        estado = 'Cargando'
    if (dato == '0x3'):
        estado = 'Carga Completa'
    if (dato == '0x4'):
        estado = '0x4 Cargador en Falla'
    if (dato == '0x5'):
        estado = 'Pistola Conectada'
    if (dato == '0xa'):
        estado = '0xA Sobrecalentamiento'
    if (dato == '0xb'):
        estado = '0xB Falla de reinicio de contactor'
    if (dato == '0xe'):
        estado = '0xE Sobrecarga de corriente'
    if (dato == '0x1a'):
        estado = 'Pistola Conectada Fin de Carga'
    return (estado)
# *****************************************************#

# ==== FUNCION PARA CREAR EL ESTADO DEL CARGADOR PARA EL SERVIDOR ====#


def estados_cargador_servidor(dato):
    estado = {'estadoStandBy': False, 'estadoConexion': False,
              'estadoCarga': False, 'estadoCargaCompleta': False, 'errores': ''}
    if (dato == 'StandBy'):
        estado = {'estadoStandBy': True, 'estadoConexion': False,
                  'estadoCarga': False, 'estadoCargaCompleta': False, 'errores': ''}
    elif (dato == 'Start'):
        estado = {'estadoStandBy': False, 'estadoConexion': True,
                  'estadoCarga': False, 'estadoCargaCompleta': False, 'errores': ''}
    elif (dato == 'Cargando'):
        estado = {'estadoStandBy': False, 'estadoConexion': True,
                  'estadoCarga': True, 'estadoCargaCompleta': False, 'errores': ''}
    elif (dato == 'Carga Completa'):
        estado = {'estadoStandBy': False, 'estadoConexion': True,
                  'estadoCarga': False, 'estadoCargaCompleta': True, 'errores': ''}
    elif (dato == 'Cargador en Falla'):
        estado = {'estadoStandBy': False, 'estadoConexion': False, 'estadoCarga': False,
                  'estadoCargaCompleta': False, 'errores': 'Error Cargador en Falla'}
    elif (dato == 'Pistola Conectada'):
        estado = {'estadoStandBy': False, 'estadoConexion': True,
                  'estadoCarga': False, 'estadoCargaCompleta': False, 'errores': ''}
    elif (dato == 'Sobrecalentamiento'):
        estado = {'estadoStandBy': False, 'estadoConexion': False, 'estadoCarga': False,
                  'estadoCargaCompleta': False, 'errores': 'Error de sobrecalentamiento'}
    elif (dato == 'Falla de reinicio de contactor'):
        estado = {'estadoStandBy': False, 'estadoConexion': False, 'estadoCarga': False,
                  'estadoCargaCompleta': False, 'errores': 'Error en activacion del contactor'}
    elif (dato == 'Sobrecarga de corriente'):
        estado = {'estadoStandBy': False, 'estadoConexion': True, 'estadoCarga': False,
                  'estadoCargaCompleta': False, 'errores': 'Error de sobrecarga de corriente'}
    elif (dato == 'Pistola Conectada Fin de Carga'):
        estado = {'estadoStandBy': False, 'estadoConexion': True,
                  'estadoCarga': False, 'estadoCargaCompleta': False, 'errores': ''}
    else:
        return (estado)

    return (estado)


def comunicacion_serial_cargador(ser, trama, logger):
    data_in = b''
    es_util = False
    es_inutil = False
    intentos = 4
    estado_cargador, porcentaje_carga, corriente, voltaje = 'Vacio', 0, 0, 0
    trama_a_enviar = trama

    # Se hace máximo 4 intentos de comunicación con el cargador
    while (es_util == False and intentos != 0):
        try:
            ser.write(trama_a_enviar)

        except ser.SerialTimeoutException as e:
            logger.error('Tiempo de espera al enviar la trama: %s', str(e))
        except Exception as e:
            logger.error('Problema inesperado al enviar la trama: %s', str(e))

        try:
            data_in = ser.read_until('\r\n')
        except ser.SerialTimeoutException as e:
            logger.error(
                'Tiempo de espera al leer la trama del cargador: %s', str(e))
        except Exception as e:
            logger.error(
                'Problema inesperado al leer la trama del cargador: %s', str(e))

        # Se verifica si la trama recibida es útil
        if len(data_in) > 0:
            try:
                indice = data_in.index(b'\x23')
                if indice != 0:
                    data_in = data_in[indice:]
                    logger.error(
                        f'Trama desfasada, longitud: {len(data_in)}, trama: {data_in}')
            except Exception as e:
                logger.error('No se encontró el x23 en la trama')
                logger.error(e)
                time.sleep(2)
        else:
            estado_cargador = 'Desconocido'
            logger.error('Sin respuesta del cargador')
            try:
                data_in = b''
                ser.reset_input_buffer()
                ser.reset_output_buffer()
            except Exception as e:
                logger.error(
                    'Problema en la comunicación serial (reset_input)')
                logger.error(e)
            time.sleep(2)

        if len(data_in) > 28 and hex(data_in[0]) == '0x23' and hex(data_in[1]) == '0x23':
            if hex(data_in[5]) == '0x1':
                es_inutil = True
                es_util = False
                trama_a_enviar = TRAMA_INICIALIZAR
                time.sleep(0.5)

            elif hex(data_in[5]) == '0x0':
                es_util = True
                es_inutil = False
                estado_cargador = estados_cargador(hex(data_in[13]))
                porcentaje_carga = int(data_in[28])
                aux = int(hex(data_in[24])+hex(data_in[25])[2:], 16)
                if aux >= 5000:
                    corriente = (0.1*aux)-500
                    voltaje = int(hex(data_in[26])+hex(data_in[27])[2:], 16)
                logger.info(f'Estado del cargador: {estado_cargador}')
        intentos = intentos-1

    if len(data_in) > 0 and es_util == False and es_inutil == False:
        logger.error(f'Trama Desconocida: {data_in}')
        estado_cargador = 'Trama Desconocida'
        logger.info(f'Estado del cargador: {estado_cargador}')
        time.sleep(3)
        try:
            data_in = b''
            ser.reset_input_buffer()
            ser.reset_output_buffer()
        except Exception as e:
            logger.error('Problema en la comunicación serial (reset_input)')
            logger.error(e)

    return estado_cargador, porcentaje_carga, corriente, voltaje
# **********************************************************************************************************************#


def comunicacion_serial_medidor(ser, logger):
    data_in = b''
    intentos = 2
    trama_correcta = False
    energia_entregada = 0.0

    # Se tiene 2 intentos de comunicación con el medidor
    while (trama_correcta == False and intentos != 0):
        try:
            ser.write(TRAMA_MEDIDOR)
        except Exception as e:
            logger.error('Problema al enviar la trama al medidor')
            logger.error(e)
            
        try:
            data_in = ser.read(9)
        except Exception as e:
            logger.error('Problema al leer la trama del medidor')
            logger.error(e)

        if len(data_in) > 0 and data_in[0] == 1:
            trama_correcta = True
            datos_utiles = data_in[3:7]
            valor = struct.unpack('>f', datos_utiles)
            energia_entregada = round(valor[0], 3)
            logger.info(
                f'Valor actual del medidor: {energia_entregada} Kwh')

        else:
            energia_entregada = 'vacio'
            logger.error('Sin respuesta del medidor')
            try:
                data_in = b''
                ser.reset_input_buffer()
                ser.reset_output_buffer()
            except Exception as e:
                logger.error(
                    'Problema en la comunicación serial (reset_input)')
                logger.error(e)

        intentos = intentos-1
        time.sleep(1)

    if len(data_in) > 0 and trama_correcta == False:
        logger.error(f'Trama Desconocida desde el medidor: {data_in}')
        energia_entregada = 'vacio'
        logger.error(f'Energía entregada: {energia_entregada}')
        try:
            data_in = b''
            ser.reset_input_buffer()
            ser.reset_output_buffer()
        except Exception as e:
            logger.error(
                'Problema en la comunicación serial con el medidor (reset_input)')
            logger.error(e)

    return energia_entregada
