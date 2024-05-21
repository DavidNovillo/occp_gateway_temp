import websockets
import asyncio

from ocpp_communication.charge_point import MyChargePoint


def test_serial_cargador(accion):
    if accion == 'pistola conectada':
        (estado_cargador, porcentaje_carga,
         corriente, voltaje) = 'Pistola Conectada', 20, 0, 0
    elif accion == 'cargar':
        (estado_cargador, porcentaje_carga,
         corriente, voltaje) = 'Cargando', 20, 58, 380
    else:
        (estado_cargador, porcentaje_carga, corriente, voltaje) = 'Standby', 0, 0, 0
    return estado_cargador, porcentaje_carga, corriente, voltaje


def test_serial_medidor():
    return 18


async def prueba():
    # Establecimiento de la conexión WebSocket con el Central System
    async with websockets.connect('wss://app.tridenstechnology.com/ev-charge/gw-comm/condor-energy/prueba_loja', subprotocols=['ocpp1.6']) as ws:

        # Crear una instancia de la clase MyChargePoint
        charge_point = MyChargePoint('prueba_loja', ws)

        # Enviar un mensaje BootNotification
        boot_response = await charge_point.send_boot_notification()
        print(boot_response)

        if boot_response.status == 'Accepted':
            print('System accepted the boot notification')

        # heartbeat_response = await charge_point.send_heartbeat()
        # print(heartbeat_response)

asyncio.run(prueba())
