"""
Utilidades compartidas entre handlers
"""

from datetime import datetime
import pytz

# Zona horaria de Buenos Aires
BUENOS_AIRES_TZ = pytz.timezone('America/Argentina/Buenos_Aires')


def get_current_time_ba():
    """Retorna la hora actual en Buenos Aires"""
    return datetime.now(BUENOS_AIRES_TZ)


def get_current_timestamp_ba():
    """Retorna timestamp actual en formato ISO"""
    return get_current_time_ba().isoformat()


def validate_reservation_time(date_str, time_str):
    """
    Valida que la reserva NO sea en el pasado (hora de Buenos Aires)
    
    Args:
        date_str: Fecha en formato YYYY-MM-DD
        time_str: Hora en formato HH:MM
    
    Returns:
        bool: True si es válida (futuro), False si es pasado
    """
    try:
        # Hora actual en Buenos Aires
        now_ba = get_current_time_ba()
        
        # Parsear la fecha/hora de la reserva
        reservation_datetime_str = f"{date_str} {time_str}"
        reservation_datetime = datetime.strptime(
            reservation_datetime_str,
            '%Y-%m-%d %H:%M'
        )
        
        # Localizar en Buenos Aires
        reservation_datetime_ba = BUENOS_AIRES_TZ.localize(reservation_datetime)
        
        # Comparar
        return reservation_datetime_ba > now_ba
    
    except Exception as e:
        print(f"Error validando tiempo: {str(e)}")
        return False


def format_date(date_str):
    """Formatea fecha de YYYY-MM-DD a DD/MM/YYYY"""
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        return date_obj.strftime('%d/%m/%Y')
    except:
        return date_str


def get_slot_value(slots, slot_name, default=None):
    """
    Extrae el valor de un slot de manera segura
    """
    slot = slots.get(slot_name, {})
    if slot and 'value' in slot:
        return slot['value'].get('interpretedValue', default)
    return default

def close_intent(event, fulfillment_state, message):
    """
    Cierra el intent con un mensaje
    
    Args:
        event: Evento de Lex
        fulfillment_state: 'Fulfilled' o 'Failed'
        message: Mensaje para el usuario
    """
    return {
        'sessionState': {
            'dialogAction': {
                'type': 'Close'
            },
            'intent': {
                'name': event['sessionState']['intent']['name'],
                'state': fulfillment_state
            }
        },
        'messages': [
            {
                'contentType': 'PlainText',
                'content': message
            }
        ]
    }

def elicit_slot(event, slot_to_elicit, message):
    """
    Vuelve a pedir un slot específico (NO termina el flujo)
    """
    return {
        'sessionState': {
            'dialogAction': {
                'type': 'ElicitSlot',
                'slotToElicit': slot_to_elicit
            },
            'intent': {
                'name': event['sessionState']['intent']['name'],
                'slots': event['sessionState']['intent']['slots'],
                'state': 'InProgress'
            }
        },
        'messages': [
            {
                'contentType': 'PlainText',
                'content': message
            }
        ]
    }


def delegate(event):
    """
    Le dice a Lex: "continúa tú, pide el siguiente slot"
    """
    return {
        'sessionState': {
            'dialogAction': {
                'type': 'Delegate'
            },
            'intent': event['sessionState']['intent']
        }
    }