"""
Handler para ReserveCourtIntent
"""

import os
import boto3
import uuid
from utils import (
    get_slot_value, 
    close_intent, 
    get_current_timestamp_ba,
    validate_reservation_time,
    format_date,
    get_current_time_ba
)

dynamodb = boto3.resource('dynamodb')
customers_table = dynamodb.Table(os.environ['CUSTOMERS_TABLE'])
reservations_table = dynamodb.Table(os.environ['RESERVATIONS_TABLE'])

# Costos de canchas (en créditos)
COURT_COSTS = {
    'fútbol': 50,
    'futbol': 50,
    'fútbol 5': 50,
    'fútbol 7': 50,
    'tenis': 30,
    'básquet': 40,
    'basquet': 40,
    'basketball': 40,
    'paddle': 35,
    'padel': 35
}

def handle_reserve_court(event):
    """
    Maneja el intent de reserva de cancha
    """
    from utils import elicit_slot, delegate
    
    invocation_source = event['invocationSource']
    slots = event['sessionState']['intent']['slots']
    
    # Extraer valores de los slots
    customer_dni = get_slot_value(slots, 'sl_customer_dni')
    court_type = get_slot_value(slots, 'slt_court_types')
    date = get_slot_value(slots, 'sl_date')
    time = get_slot_value(slots, 'sl_time')
    confirmation = get_slot_value(slots, 'sl_confirmation', '')
    
    # NUEVO: Intentar extraer tipo de cancha del mensaje original
    session_attributes = event.get('sessionState', {}).get('sessionAttributes', {})
    input_transcript = session_attributes.get('UserOriginalMessage', event.get('inputTranscript', '')).lower()
    
    # Si NO tiene tipo de cancha, intentar extraerlo del mensaje
    if not court_type and input_transcript:
        print(f"🔍 Buscando tipo de cancha en: '{input_transcript}'")
        
        if 'tenis' in input_transcript or 'tennis' in input_transcript:
            court_type = 'tenis'
            slots['slt_court_types'] = {
                'shape': 'Scalar',
                'value': {
                    'originalValue': 'tenis',
                    'interpretedValue': 'tenis',
                    'resolvedValues': ['tenis']
                }
            }
            print("✅ Detectado: tenis")
        elif 'futbol' in input_transcript or 'fútbol' in input_transcript:
            court_type = 'futbol'
            slots['slt_court_types'] = {
                'shape': 'Scalar',
                'value': {
                    'originalValue': 'futbol',
                    'interpretedValue': 'futbol',
                    'resolvedValues': ['futbol']
                }
            }
            print("✅ Detectado: futbol")
        elif 'basquet' in input_transcript or 'básquet' in input_transcript or 'basketball' in input_transcript:
            court_type = 'basquet'
            slots['slt_court_types'] = {
                'shape': 'Scalar',
                'value': {
                    'originalValue': 'basquet',
                    'interpretedValue': 'basquet',
                    'resolvedValues': ['basquet']
                }
            }
            print("✅ Detectado: basquet")
        elif 'padel' in input_transcript or 'pádel' in input_transcript or 'paddle' in input_transcript:
            court_type = 'padel'
            slots['slt_court_types'] = {
                'shape': 'Scalar',
                'value': {
                    'originalValue': 'padel',
                    'interpretedValue': 'padel',
                    'resolvedValues': ['padel']
                }
            }
            print("✅ Detectado: padel")

    print(f"🔍 invocationSource: {invocation_source}")
    print(f"📋 Valores - DNI: {customer_dni}, Cancha: {court_type}, Fecha: {date}, Hora: {time}, Confirmación: {confirmation}")

    # ==========================================
    # PARTE 1: VALIDACIONES (mientras Lex pide slots)
    # ==========================================
    if invocation_source == 'DialogCodeHook':
        print("✅ Estamos en DialogCodeHook (validando mientras pedimos slots)")
        
        # --- VALIDACIÓN 1: Usuario dijo NO → Volver a Amazon Q ---
        if confirmation:
            confirmation_lower = confirmation.lower().strip()
            print(f"🔍 Verificando confirmación: '{confirmation_lower}'")
            
            if confirmation_lower in ['no', 'nop', 'negativo', 'cancelar', 'cancelo', 'nunca', 'no quiero']:
                print("❌ Usuario dijo NO - Volviendo a Amazon Q")
                
                return close_intent(
                    event,
                    'Fulfilled',
                    'Entendido, reserva cancelada. ¿En qué más puedo ayudarte?'
                )
        
        # --- VALIDACIÓN 2: Fecha/hora en el pasado → Volver a pedir ---
        if date and time:
            print(f"🔍 Validando fecha {date} y hora {time}")
            
            if not validate_reservation_time(date, time):
                print("❌ Fecha/hora en el pasado - Volviendo a pedir")
                
                now_ba = get_current_time_ba()
                
                # Limpiar fecha y hora para volver a pedirlos
                slots['sl_date'] = None
                slots['sl_time'] = None
                
                return elicit_slot(
                    event,
                    'sl_date',
                    f'❌ Lo siento, ese horario ({format_date(date)} a las {time}) ya pasó.\n'
                    f'Hora actual en Buenos Aires: {now_ba.strftime("%d/%m/%Y %H:%M")}\n\n'
                    f'Por favor elige una fecha futura. ¿Para qué fecha? Ejemplo: 30/10/2025'
                )
        
        # Si todo OK, dejar que Lex continúe
        print("✅ Validaciones OK - Delegando a Lex")
        return delegate(event)
    
    # ==========================================
    # PARTE 2: FULFILLMENT (crear la reserva)
    # ==========================================
    if invocation_source == 'FulfillmentCodeHook':
        print("✅ Estamos en FulfillmentCodeHook (todos los slots llenos, usuario dijo SÍ)")
        
        if court_type:
            court_type = court_type.lower()
        
        try:
            # 1. Verificar que el cliente existe
            response = customers_table.get_item(Key={'customer_dni': customer_dni})
            
            if 'Item' not in response:
                return close_intent(
                    event,
                    'Fulfilled',
                    f'❌ No encontramos una cuenta con DNI {customer_dni}.\n'
                    f'Primero debes cargar créditos diciendo "quiero cargar créditos".'
                )
            
            customer = response['Item']
            current_credits = int(customer.get('credits', 0))
            
            # 2. Calcular costo
            cost = COURT_COSTS.get(court_type, 50)
            
            # 3. Verificar créditos suficientes
            if current_credits < cost:
                return close_intent(
                    event,
                    'Fulfilled',
                    f'❌ Créditos insuficientes.\n'
                    f'Necesitas: {cost} créditos\n'
                    f'Tienes: {current_credits} créditos\n'
                    f'Faltan: {cost - current_credits} créditos\n\n'
                    f'Puedes cargar más créditos diciendo "quiero cargar créditos".'
                )
            
            # 4. Crear la reserva
            reservation_id = f"RES-{uuid.uuid4().hex[:8].upper()}"
            reservation_datetime = f"{date} {time}"
            
            reservations_table.put_item(
                Item={
                    'reservation_id': reservation_id,
                    'customer_dni': customer_dni,
                    'court_type': court_type,
                    'reservation_date': date,
                    'reservation_time': time,
                    'reservation_datetime': reservation_datetime,
                    'cost': cost,
                    'status': 'confirmed',
                    'created_at': get_current_timestamp_ba()
                }
            )
            
            # 5. Descontar créditos
            new_credits = current_credits - cost
            customers_table.update_item(
                Key={'customer_dni': customer_dni},
                UpdateExpression='SET credits = :credits',
                ExpressionAttributeValues={
                    ':credits': new_credits
                }
            )
            
            # 6. Retornar confirmación
            message = (
                f'✅ ¡Reserva confirmada!\n\n'
                f'📋 Código: {reservation_id}\n'
                f'🏟️ Cancha: {court_type.capitalize()}\n'
                f'📅 Fecha: {format_date(date)}\n'
                f'🕐 Hora: {time}\n'
                f'💰 Costo: {cost} créditos\n\n'
                f'Tu nuevo saldo: {new_credits} créditos\n\n'
                f'Recuerda llegar 10 minutos antes. ¡Que disfrutes tu partido!'
            )
            
            return close_intent(event, 'Fulfilled', message)
        
        except Exception as e:
            print(f"❌ Error creando reserva: {str(e)}")
            return close_intent(
                event,
                'Fulfilled',
                'Ocurrió un error procesando la reserva. Por favor intenta de nuevo.'
            )