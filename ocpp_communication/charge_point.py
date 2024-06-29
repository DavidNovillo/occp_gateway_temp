from ocpp.routing import on
from ocpp.v16 import ChargePoint as cp
from ocpp.v16.enums import Reason, ConfigurationStatus, TriggerMessageStatus, MessageTrigger, RemoteStartStopStatus, ClearChargingProfileStatus, ReadingContext, ValueFormat, Measurand, Location, UnitOfMeasure, Phase
from ocpp.v16 import call_result, call
import json

from constants import CHARGE_POINT_MODEL, CHARGE_POINT_VENDOR, ID_CARGADOR

# Función para almacenar los keys en un archivo JSON


def save_keys(key, value):
    # Load existing keys
    try:
        with open('/home/pi/keys.json', 'r') as keys_file:
            keys = json.load(keys_file)
    except FileNotFoundError:
        keys = {}
    # Update key value
    keys[key] = value
    # Write keys back to file
    with open('/home/pi/keys.json', 'w') as keys_file:
        json.dump(keys, keys_file, indent=4)


def load_keys(key, default_value):
    # Load existing keys
    try:
        with open('/home/pi/keys.json', 'r') as keys_file:
            keys = json.load(keys_file)
    except FileNotFoundError:
        keys = {}
    return keys.get(key, default_value)


class MyChargePoint(cp):
    # Función para obtener recibir información desde el otro archivo
    def set_info(self, info):
        self.info = info

    # Método para verificar el estado de la conexión
    def is_connected(self):
        return self._connection.open

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
        request = call.Authorize(
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
    async def send_meter_values(self, connector_id, energy_value, power_value, battery_value, timestamp, transaction_id):
        sampled_value = [
            {
                "value": str(energy_value),
                "context": ReadingContext.sample_periodic.value,
                "format": ValueFormat.raw.value,
                "measurand": Measurand.energy_active_import_register.value,
                "unit": UnitOfMeasure.kwh.value
            },
            {
                "value": str(power_value),
                "context": ReadingContext.sample_periodic.value,
                "format": ValueFormat.raw.value,
                "measurand": Measurand.power_active_import.value,
                "unit": UnitOfMeasure.w.value
            },
            {
                "value": str(battery_value),
                "context": ReadingContext.sample_periodic.value,
                "format": ValueFormat.raw.value,
                "measurand": Measurand.soc.value,
                "unit": UnitOfMeasure.percent.value
            }
        ]
        request = call.MeterValues(
            connector_id=connector_id,
            transaction_id=transaction_id,
            meter_value=[
                {
                    "timestamp": timestamp,
                    "sampled_value": sampled_value
                }
            ],
        )
        response = await self.call(request)
        return response

    # Función que envía un mensaje de StartTransaction al Central System
    async def send_start_transaction(self, connector_id, id_tag, timestamp, meter_start):
        request = call.StartTransaction(
            connector_id=connector_id,
            id_tag=id_tag,
            timestamp=timestamp,
            meter_start=int(meter_start*1000)
        )
        response = await self.call(request)
        return response

    # Función que envía un mensaje de StopTransaction al Central System
    async def send_stop_transaction(self, meter_stop, timestamp, transaction_id, reason=None, id_tag=None, transaction_data=None):
        request = call.StopTransaction(
            meter_stop=int(meter_stop*1000),
            timestamp=timestamp,
            transaction_id=transaction_id,
            reason=Reason.remote,
            id_tag=id_tag,
            transaction_data=transaction_data
        )
        response = await self.call(request)
        return response

    # Función que envía un mensaje de StatusNotification al Central System
    async def send_status_notification(self, connector_id, status, error_code, timestamp=None, info=None, vendor_id=None, vendor_error_code=None):
        request = call.StatusNotification(
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

    # async def _handle_call(self, call):
    #     # Imprimir el tipo de mensaje
    #     print(f'Mensaje recibido: {call.action}')
    #     # Llamar al método original para procesar el mensaje
    #     await super()._handle_call(call)

    # Función que maneja la recepción de un mensaje Clear Charging Profile
    @on('ClearChargingProfile')
    async def on_clear_charging_profile(self, **kwargs):
        # Almacenar los datos en la cola
        await self.queue.put(('ClearChargingProfile', kwargs))
        # Devolver un resultado
        return call_result.ClearChargingProfile(
            status=ClearChargingProfileStatus.accepted
        )

    # Función que maneja la recepción de un mensaje Remote Start Transaction
    @on('RemoteStartTransaction')
    async def remote_start_transaction(self, id_tag, connector_id, **kwargs):
        # Almacenar los datos en la cola
        await self.queue.put(('RemoteStartTransaction', id_tag, connector_id, kwargs))
        # Devolver un resultado
        if self.info == 'StandBy' or self.info == 'Pistola Conectada':
            print('Status: Accepted')
            return call_result.RemoteStartTransaction(status=RemoteStartStopStatus.accepted)

        else:
            print('Status: Rejected')
            return call_result.RemoteStartTransaction(status=RemoteStartStopStatus.rejected)

    # Función que maneja la recepción de un mensaje Trigger Message

    @on('TriggerMessage')
    async def on_trigger_message(self, requested_message: MessageTrigger, connector_id: int = None):
        # Almacenar los datos en la cola
        await self.queue.put(('TriggerMessage', requested_message, connector_id))
        # Devolver un resultado
        return call_result.TriggerMessage(status=TriggerMessageStatus.accepted)

    # Función que maneja la recepción de un mensaje RemoteStopTransaction
    @on('RemoteStopTransaction')
    async def on_remote_stop_transaction(self, transaction_id):
        # Almacenar los datos en la cola
        await self.queue.put(('RemoteStopTransaction', transaction_id))
        # Devolver un resultado
        return call_result.RemoteStopTransaction(
            status=RemoteStartStopStatus.accepted
        )

    # Función que maneja la recepción de un mensaje ChangeConfiguration
    @on('ChangeConfiguration')
    async def on_change_configuration(self, key, value, **kwargs):
        print(f'Received ChangeConfiguration key: {key} with value: {value}')
        # Almacenar los keys en el archivo keys.json
        save_keys(key, value)
        # Almacenar los datos en la cola
        await self.queue.put(('ChangeConfiguration', key, value))
        # Return a result
        return call_result.ChangeConfiguration(
            status=ConfigurationStatus.accepted
        )

    # Función que maneja la recepción de un mensaje GetConfiguration
    @on('GetConfiguration')
    async def on_get_configuration(self, key=None, **kwargs):
        print(f'Received GetConfiguration with keys: {key}')

        # Preparar las listas de configuraciones encontradas y desconocidas
        found_configurations = []
        unknown_configuration = []

        if key:
            # Si se proporcionaron claves específicas, buscar cada una
            for k in key:
                # Usar la función load_keys para buscar el valor de cada clave
                # Asumiendo que 'None' es el valor predeterminado si la clave no se encuentra
                value = load_keys(k, None)
                if value is not None:
                    found_configurations.append({
                        'key': k,
                        'readonly': False,  # O determinar si es de solo lectura
                        'value': str(value)
                    })
                else:
                    unknown_configuration.append(k)
        else:
            # Si no se proporcionaron claves, cargar todas las configuraciones disponibles
            # Esto asume que tienes una forma de listar todas las claves disponibles,
            # posiblemente modificando load_keys para devolver todo si 'key' es None
            # Modifica esta línea según tu implementación
            all_keys = load_keys(None, {})
            for k, v in all_keys.items():
                found_configurations.append({
                    'key': k,
                    'readonly': False,  # Ajustar según sea necesario
                    'value': v
                })

        # Devolver el resultado
        return call_result.GetConfiguration(
            configuration_key=found_configurations,
            unknown_key=unknown_configuration
        )
