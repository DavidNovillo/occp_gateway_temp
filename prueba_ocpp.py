import websockets
import asyncio

from ocpp_communication.charge_point import MyChargePoint


async def handle_queue(queue):
    while True:
        if not queue.empty():
            data = await queue.get()
            print(f'Received data: {data}')
        await asyncio.sleep(1)  # Esperar un poco antes de verificar nuevamente


async def keep_hearbeat(charge_point, interval):
    while True:
        # Enviar un mensaje Heartbeat y esperar la respuesta
        heartbeat_response = await charge_point.send_heartbeat()
        print(heartbeat_response)
        await asyncio.sleep(interval)


async def main():
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

            while True:

                print('while True del main')

                await asyncio.sleep(20)
    except KeyboardInterrupt:
        await ws.close()
        print("Program interrupted by user. Exiting...")

if __name__ == '__main__':
    asyncio.run(main())
