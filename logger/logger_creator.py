import logging
import logging.handlers
import json

# Se carga el ID único de cada raspberry
with open('/home/pi/ID.json') as identificador:
    datos_identificador = json.load(identificador)

ID_CARGADOR = str(datos_identificador['ID'])
NUM_CARGADOR = str(datos_identificador['Estacion'])

def custom_logger():
    # Create a custom logger
    logger = logging.getLogger(f'Electrolinera {NUM_CARGADOR}')
    logger.setLevel(logging.INFO)

    # Create handlers
    b_handler = logging.StreamHandler()
    c_handler = logging.handlers.RotatingFileHandler(
        f'infofile{NUM_CARGADOR}.log', maxBytes=5*1024*1024, backupCount=1)
    f_handler = logging.handlers.RotatingFileHandler(
        f'errorfile{NUM_CARGADOR}.log', maxBytes=3*1024*1024, backupCount=1)

    b_handler.setLevel(logging.INFO)
    c_handler.setLevel(logging.INFO)
    f_handler.setLevel(logging.ERROR)

    # Create formatters and add it to handlers
    b_format = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s', '%Y-%m-%d %H:%M:%S')
    c_format = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s', '%Y-%m-%d %H:%M:%S')
    f_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s', '%Y-%m-%d %H:%M:%S')

    b_handler.setFormatter(b_format)
    c_handler.setFormatter(c_format)
    f_handler.setFormatter(f_format)

    # Add handlers to the logger
    logger.addHandler(b_handler)
    logger.addHandler(c_handler)
    logger.addHandler(f_handler)

    return logger