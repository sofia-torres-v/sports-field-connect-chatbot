"""
Router Function - Entry point
Lex invoca este archivo
"""

import json
from handlers.load_credits import handle_load_credits
from handlers.reserve_court import handle_reserve_court
from utils import close_intent


def handler(event, context):
    """
    Handler principal - Enruta a los sub-handlers
    Este es el único que Lex ve
    """
    print(f"Evento recibido: {json.dumps(event)}")
    
    try:
        intent_name = event['sessionState']['intent']['name']
        
        # Rutear según el intent
        if intent_name == 'LoadCreditsIntent':
            return handle_load_credits(event)
        elif intent_name == 'ReserveCourtIntent':
            return handle_reserve_court(event)
        else:
            return close_intent(
                event,
                'Failed',
                f'Intent desconocido: {intent_name}'
            )
    
    except Exception as e:
        print(f"Error en router: {str(e)}")
        return close_intent(
            event,
            'Failed',
            'Ocurrió un error procesando tu solicitud. Por favor intenta de nuevo.'
        )