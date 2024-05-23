import websockets
import asyncio
from datetime import datetime

from ocpp_communication.charge_point import MyChargePoint

data_store = None  # Inicializar data_store
start_transaction = False  # Variable para iniciar la transacción
id_tag = None
connector_id = None


async def handle_queue(queue):
    global data_store, start_transaction, id_tag, connector_id
    while True:
        if not queue.empty():
            data = await queue.get()
            print(f'data: {data}')
            if 'RemoteStartTransaction' == data[0]:
                start_transaction = True
                id_tag = data[1]
                connector_id = data[2]
            else:
                start_transaction = False
                data_store = data  # Almacenar los datos en una lista global
        await asyncio.sleep(1)  # Esperar un poco antes de verificar nuevamente


async def keep_hearbeat(charge_point, interval):
    while True:
        # Enviar un mensaje Heartbeat y esperar la respuesta
        heartbeat_response = await charge_point.send_heartbeat()
        print(heartbeat_response)
        await asyncio.sleep(interval)


async def main():
    global data_store, start_transaction, id_tag, connector_id
    try:
        # Crear una cola
        queue = asyncio.Queue()

        # Establecimiento de la conexión WebSocket con el Central System
        async with websockets.connect('wss://app.tridenstechnology.com/ev-charge/gw-comm/condor-energy/prueba_loja', subprotocols=['ocpp1.6']) as ws:

            # Crear una instancia de la clase MyChargePoint
            charge_point = MyChargePoint('prueba_loja', ws, queue=queue)

            # Iniciar charge_point.start() y handle_queue() en segundo plano
            start_task = asyncio.create_task(charge_point.start())
            queue_task = asyncio.create_task(handle_queue(queue))

            # Enviar un mensaje BootNotification y esperar la respuesta
            boot_response = await charge_point.send_boot_notification()
            print(f'interval: {boot_response.interval}')

            heartbeat_task = asyncio.create_task(
                keep_hearbeat(charge_point, boot_response.interval))

            # Enviar un mensaje StatusNotification
            status_notification_response = await charge_point.send_status_notification(
                connector_id=1,
                status="Available",
                error_code="NoError",
            )
            print(f'status response: {status_notification_response}')

            while True:
                if start_transaction == True:
                    # Enviar un mensaje StartTransaction
                    start_transaction_response = await charge_point.send_start_transaction(
                        connector_id=connector_id,
                        meter_start=10,
                        id_tag=id_tag,
                        timestamp=datetime.now().isoformat(),
                    )
                    print(start_transaction_response)
                    start_transaction = False

                await asyncio.sleep(1)
    except KeyboardInterrupt:
        await ws.close()
        print("Program interrupted by user. Exiting...")

if __name__ == '__main__':
    asyncio.run(main())
