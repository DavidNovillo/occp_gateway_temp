def test_serial_cargador(accion):
    if accion == 'pistola conectada':
        (estado_cargador, porcentaje_carga,
         corriente, voltaje) = 'Pistola Conectada', 20, 0, 0
    elif accion == 'cargar':
        (estado_cargador, porcentaje_carga,
         corriente, voltaje) = 'Cargando', 20, 58, 380
    else:
        (estado_cargador, porcentaje_carga, corriente, voltaje) = 'StandBy', 0, 0, 0
    return estado_cargador, porcentaje_carga, corriente, voltaje
