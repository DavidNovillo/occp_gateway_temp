# charge_point.py
from datetime import datetime
import asyncio
from ocpp.routing import on
from ocpp.v16 import ChargePoint as cp
from ocpp.v16.enums import RemoteStartStopStatus
from ocpp.v16 import call_result, call

from constants import CHARGE_POINT_MODEL, CHARGE_POINT_VENDOR, ID_CARGADOR


class MyChargePoint(cp):
    # ENVÍO DE MENSAJES HACIA EL CENTRAL SYSTEM
    # Función que envía un mensaje de Boot Notification al Central System
    async def send_boot_notification(self):
        request = call.BootNotification(
            charge_point_model=CHARGE_POINT_MODEL,
            charge_point_vendor=CHARGE_POINT_VENDOR,
            charge_point_serial_number=ID_CARGADOR,
            charge_box_serial_number=ID_CARGADOR,
            firmware_version='3.00a',
            meter_type='Single/Three Phase',
            meter_serial_number='12345678901234567890',
        )
        response = await self.call(request)
        return response

    # Función que envía un mensaje de Heartbeat al Central System
    async def send_heartbeat(self):
        request = call.Heartbeat()
        response = await self.call(request)
        return response

    # Función que envía un mensaje de Authorize al Central System
    async def send_authorize(self, id_tag):
        request = call.AuthorizePayload(
            id_tag=id_tag
        )
        response = await self.call(request)
        return response

    # Función que envía un mensaje de DataTransfer al Central System
    async def send_data_transfer(self, vendor_id, message_id=None, data=None):
        request = call.DataTransferPayload(
            vendor_id=vendor_id,
            message_id=message_id,
            data=data
        )
        response = await self.call(request)
        return response

    # Función que envía un mensaje de MeterValues al Central System
    async def send_meter_values(self, meter_values):
        request = call.MeterValuesPayload(
            meter_value=meter_values
        )
        response = await self.call(request)
        return response

    # Función que envía un mensaje de StartTransaction al Central System
    async def send_start_transaction(self, connector_id, id_tag, timestamp, meter_start):
        request = call.StartTransactionPayload(
            connector_id=connector_id,
            id_tag=id_tag,
            timestamp=timestamp,
            meter_start=meter_start
        )
        response = await self.call(request)
        return response

    # Función que envía un mensaje de StopTransaction al Central System
    async def send_stop_transaction(self, meter_stop, timestamp, transaction_id, reason=None, id_tag=None):
        request = call.StopTransactionPayload(
            meter_stop=meter_stop,
            timestamp=timestamp,
            transaction_id=transaction_id,
            reason=reason,
            id_tag=id_tag
        )
        response = await self.call(request)
        return response

    # Función que envía un mensaje de StatusNotification al Central System
    async def send_status_notification(self, connector_id, status, error_code, timestamp=None, info=None, vendor_id=None, vendor_error_code=None):
        request = call.StatusNotificationPayload(
            connector_id=connector_id,
            status=status,
            error_code=error_code,
            timestamp=timestamp,
            info=info,
            vendor_id=vendor_id,
            vendor_error_code=vendor_error_code
        )
        response = await self.call(request)
        return response

    # RECEPCIÓN DE MENSAJES DESDE EL CENTRAL SYSTEM
    # Función para crear un cola de mensajes
    def __init__(self, *args, queue, **kwargs):
        super().__init__(*args, **kwargs)
        self.queue = queue

    async def _handle_call(self, call):
        # Imprimir el tipo de mensaje
        print(f'Received message: {call.action}')

        # Llamar al método original para procesar el mensaje
        await super()._handle_call(call)

    # Función que maneja la recepción de un mensaje Remote Start Transaction
    @on('RemoteStartTransaction')
    async def remote_start_transaction(self, id_tag, connector_id, **kwargs):
        print('Received RemoteStartTransaction request')
        print(f'id_tag: {id_tag}')
        print(f'connector_id: {connector_id}')
        print(f'Additional data: {kwargs}')
        # Almacenar los datos en la cola
        await self.queue.put((id_tag, connector_id, kwargs))
        # Aquí puedes manejar la solicitud RemoteStartTransaction
        # Por ejemplo, puedes iniciar una transacción y devolver un resultado

        # Iniciar la transacción
        # Puedes agregar tu lógica para iniciar la transacción aquí

        # Devolver un resultado
        return call_result.RemoteStartTransactionPayload(
            status=RemoteStartStopStatus.accepted
        )
