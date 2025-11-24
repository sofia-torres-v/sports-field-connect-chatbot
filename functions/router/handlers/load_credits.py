"""
Handler para LoadCreditsIntent
"""

import os
import boto3
import re
from utils import (
    get_slot_value, 
    close_intent, 
    get_current_timestamp_ba,
    elicit_slot,
    delegate
)

dynamodb = boto3.resource('dynamodb')
customers_table = dynamodb.Table(os.environ['CUSTOMERS_TABLE'])


def extract_amount(text):
    """
    Extrae el monto de créditos del mensaje del usuario
    
    Ejemplos:
    - "quiero cargar 100 créditos" -> 100
    - "cargar 50" -> 50
    - "necesito 200 créditos" -> 200
    - "quiero cargar créditos" -> None
    """
    if not text:
        return None
    
    text_lower = text.lower()
    
    # Buscar patrones como "100 créditos", "50", "cargar 200"
    patterns = [
        r'(\d+)\s*(?:créditos|creditos)',  # "100 créditos"
        r'cargar\s+(\d+)',                  # "cargar 100"
        r'recargar\s+(\d+)',                # "recargar 50"
        r'(?:necesito|quiero)\s+(\d+)',    # "quiero 200"
        r'\b(\d+)\b'                        # cualquier número
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text_lower)
        if match:
            amount = int(match.group(1))
            print(f"✅ Detectado monto: {amount} en '{text}'")
            return amount
    
    print(f"❌ No se detectó monto en: '{text}'")
    return None


def set_slot(slots, slot_name, value):
    """
    Establece un slot programáticamente
    """
    slots[slot_name] = {
        'shape': 'Scalar',
        'value': {
            'originalValue': str(value),
            'interpretedValue': str(value),
            'resolvedValues': [str(value)]
        }
    }


def handle_load_credits(event):
    """
    Maneja el intent de carga de créditos
    """
    invocation_source = event['invocationSource']
    slots = event['sessionState']['intent']['slots']
    session_attributes = event.get('sessionState', {}).get('sessionAttributes', {})
    
    # Extraer valores de los slots
    amount = get_slot_value(slots, 'sl_amount')
    customer_dni = get_slot_value(slots, 'sl_customer_dni')
    payment_method = get_slot_value(slots, 'slt_payment_methods')
    confirmation = get_slot_value(slots, 'sl_confirmation', '')
    
    print(f"🔍 invocationSource: {invocation_source}")
    print(f"📋 Session Attributes: {session_attributes}")
    print(f"📋 Slots - Monto: {amount}, DNI: {customer_dni}, Método: {payment_method}")
    
    # ==========================================
    # PASO 0: Pre-llenar monto si no existe
    # ==========================================
    if not amount:
        # Intentar extraer del mensaje original (viene de Connect)
        user_message = session_attributes.get('UserOriginalMessage', '')
        
        # También del transcript actual
        input_transcript = event.get('inputTranscript', '')
        
        # Buscar en ambos
        detected = extract_amount(user_message) or extract_amount(input_transcript)
        
        if detected:
            print(f"✅ Pre-llenando slot con monto: {detected}")
            set_slot(slots, 'sl_amount', detected)
            amount = str(detected)
    
    # ==========================================
    # PARTE 1: VALIDACIONES (DialogCodeHook)
    # ==========================================
    if invocation_source == 'DialogCodeHook':
        print("✅ Validando slots...")
        
        # Validación: Usuario canceló
        if confirmation and confirmation.lower().strip() in ['no', 'nop', 'negativo', 'cancelar', 'cancelo', 'nunca', 'no quiero']:
            print("❌ Usuario canceló")
            return close_intent(
                event,
                'Fulfilled',
                'Entendido, operación cancelada. ¿En qué más puedo ayudarte?'
            )
        
        # Todo OK, continuar
        return delegate(event)
    
    # ==========================================
    # PARTE 2: FULFILLMENT (cargar créditos)
    # ==========================================
    if invocation_source == 'FulfillmentCodeHook':
        print("✅ Cargando créditos...")
        
        try:
            amount = int(amount)
            
            # Buscar o crear cliente
            response = customers_table.get_item(Key={'customer_dni': customer_dni})
            
            if 'Item' in response:
                # Cliente existe - actualizar créditos
                current_credits = int(response['Item'].get('credits', 0))
                new_credits = current_credits + amount
                
                customers_table.update_item(
                    Key={'customer_dni': customer_dni},
                    UpdateExpression='SET credits = :credits, last_load = :timestamp',
                    ExpressionAttributeValues={
                        ':credits': new_credits,
                        ':timestamp': get_current_timestamp_ba()
                    }
                )
                
                message = (
                    f'✅ ¡Carga exitosa!\n\n'
                    f'💰 Créditos agregados: {amount}\n'
                    f'📊 Saldo anterior: {current_credits}\n'
                    f'📈 Nuevo saldo: {new_credits} créditos\n'
                    f'💳 Método de pago: {payment_method}'
                )
                
                # Agregar recordatorio si es efectivo
                if payment_method.lower() == 'efectivo':
                    message += '\n\n💡 Recuerda llevar efectivo.'
                
            else:
                # Cliente nuevo - crear registro
                customers_table.put_item(
                    Item={
                        'customer_dni': customer_dni,
                        'credits': amount,
                        'created_at': get_current_timestamp_ba(),
                        'last_load': get_current_timestamp_ba()
                    }
                )
                
                message = (
                    f'✅ ¡Cuenta creada y carga exitosa!\n\n'
                    f'🎉 Bienvenido al sistema\n'
                    f'💰 Créditos iniciales: {amount}\n'
                    f'💳 Método de pago: {payment_method}'
                )
            
            return close_intent(event, 'Fulfilled', message)
        
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            return close_intent(
                event,
                'Failed',
                'Error procesando la carga. Intenta de nuevo.'
            )