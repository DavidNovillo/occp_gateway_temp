def calculate_crc16(data):
    crc = 0xFFFF
    polynomial = 0xA001  # 0x8005 reversed

    for byte in data:
        crc ^= (0xFF & byte)
        for _ in range(8):
            if (crc & 0x0001):
                crc = (crc >> 1) ^ polynomial
            else:
                crc >>= 1
    crc = crc.to_bytes(2, byteorder='little')
    return crc


# Ejemplo de trama (en hexadecimal)
trama_hex = bytearray([0x01, 0x04, 0x01, 0x56, 0x00, 0x02])

# Calculamos el CRC-16/MODBUS
crc = calculate_crc16(trama_hex)

# Agregamos el CRC al final de la trama
trama_hex.extend(crc)

# Mostramos la trama completa en hexadecimal
trama_hex_str = ' '.join(format(byte, '02X') for byte in trama_hex)
print("Trama completa con CRC-16/MODBUS:", trama_hex_str)
