import websockets
import asyncio
from datetime import datetime, timezone

from ocpp_communication.charge_point import MyChargePoint

data_store = None  # Inicializar data_store
start_transaction = False  # Variable para iniciar la transacción
stop_transaction = False  # Variable para detener la transacción
id_tag = None
connector_id = 0
transaction_id = None
send_meter_reading = False


async def handle_queue(queue):
    global data_store, start_transaction, stop_transaction, id_tag, connector_id, send_meter_reading, transaction_id
    while True:
        if not queue.empty():
            data = await queue.get()
            print(f'data: {data}')
            if data[0] == 'RemoteStartTransaction':
                start_transaction = True
                id_tag = data[1]
                connector_id = data[2]
            elif data[0] == 'TriggerMessage':
                if data[1] == 'MeterValues':
                    send_meter_reading = True
                    if data[2] is not None:
                        connector_id = data[2]
            elif data[0] == 'RemoteStopTransaction':
                transaction_id = data[1]
                stop_transaction = True
            else:
                send_meter_reading = False
                start_transaction = False
                stop_transaction = False
            data_store = data  # Almacenar los datos en una lista global
        await asyncio.sleep(1)  # Esperar un poco antes de verificar nuevamente


async def keep_hearbeat(charge_point, interval):
    while True:
        # Enviar un mensaje Heartbeat y esperar la respuesta
        heartbeat_response = await charge_point.send_heartbeat()
        print(heartbeat_response)
        await asyncio.sleep(interval)


async def main():
    time_interval = 30
    meter_reading = 210
    counter = time_interval + 1
    global data_store, start_transaction, stop_transaction, id_tag, connector_id, send_meter_reading, transaction_id
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
                current_time = datetime.now(timezone.utc).strftime(
                    '%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
                start_transaction_response = None
                if start_transaction == True:
                    # authorize_response = await charge_point.send_authorize(id_tag=id_tag)
                    # print(f'authorize_response: {authorize_response}')
                    # Enviar un mensaje StartTransaction
                    status_notification_response = await charge_point.send_status_notification(
                        connector_id=1,
                        status="Preparing",
                        error_code="NoError",
                    )
                    start_transaction_response = await charge_point.send_start_transaction(
                        connector_id=connector_id,
                        meter_start=meter_reading,
                        id_tag=id_tag,
                        timestamp=current_time,
                    )
                    print(
                        f'start_transaction_response: {start_transaction_response}')
                    start_transaction = False
                    if start_transaction_response.id_tag_info['status'] == 'Accepted':
                        counter = 0
                        transaction_id = start_transaction_response.transaction_id
                        status_notification_response = await charge_point.send_status_notification(
                            connector_id=1,
                            status="Charging",
                            error_code="NoError",
                        )

                if send_meter_reading == True or counter == time_interval:
                    # Enviar un mensaje MeterValues
                    meter_values_response = await charge_point.send_meter_values(
                        connector_id=0,
                        meter_value=meter_reading-210,
                        timestamp=current_time,
                        transaction_id=transaction_id,
                    )
                    counter = 0
                    meter_reading += 500
                    send_meter_reading = False
                    # print(f'meter_value: {meter_reading}')

                if counter < time_interval:
                    counter += 1
                if stop_transaction == True:
                    status_notification_response = await charge_point.send_status_notification(
                        connector_id=connector_id,
                        status="Finishing",
                        error_code="NoError",
                    )
                    # Enviar un mensaje StopTransaction
                    stop_transaction_response = await charge_point.send_stop_transaction(
                        meter_stop=meter_reading,
                        transaction_id=transaction_id,
                        timestamp=current_time,
                    )
                    print(
                        f'stop_transaction_response: {stop_transaction_response}')
                    print(f'meter_stop: {meter_reading}')
                    stop_transaction = False
                    counter = time_interval + 1

                    status_notification_response = await charge_point.send_status_notification(
                        connector_id=connector_id,
                        status="Available",
                        error_code="NoError",
                    )
                await asyncio.sleep(1)
    except KeyboardInterrupt:
        await ws.close()
        print("Program interrupted by user. Exiting...")

if __name__ == '__main__':
    asyncio.run(main())
