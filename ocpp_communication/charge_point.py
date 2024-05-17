# charge_point.py
from datetime import datetime
from ocpp.routing import on
from ocpp.v16 import ChargePoint as cp
from ocpp.v16.enums import Action
from ocpp.v16 import call_result, call

from constants import CHARGE_POINT_MODEL, CHARGE_POINT_VENDOR


class MyChargePoint(cp):
    # ENVÍO DE MENSAJES HACIA EL CENTRAL SYSTEM
    # Función que envía un mensaje de Boot Notification al Central System
    async def send_boot_notification(self):
        request = call.BootNotificationPayload(
            charge_point_model=CHARGE_POINT_MODEL,
            charge_point_vendor=CHARGE_POINT_VENDOR
        )
        response = await self.call(request)
        return response

    # Función que envía un mensaje de Heartbeat al Central System
    async def send_heartbeat(self):
        request = call.HeartbeatPayload()
        response = await self.call(request)
        return response

    # RECEPCIÓN DE MENSAJES DESDE EL CENTRAL SYSTEM
    # Función que maneja un mensaje de RemoteStartTransaction desde el Central System
    @on(Action.RemoteStartTransaction)
    async def on_remote_start_transaction(self, **kwargs):
        # Aquí puedes agregar el código para manejar el mensaje de RemoteStartTransaction.
        # Por ejemplo, podrías iniciar una transacción de carga en respuesta a este mensaje.
        # Por ahora, simplemente vamos a responder con un status de 'Accepted'.
        return call_result.RemoteStartTransactionPayload(
            status=RemoteStartStopStatus.accepted
        )