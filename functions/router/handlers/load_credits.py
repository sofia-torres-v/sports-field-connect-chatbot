"""
Handler para LoadCreditsIntent
"""

import os
import boto3
from utils import get_slot_value, close_intent, get_current_timestamp_ba

dynamodb = boto3.resource('dynamodb')
customers_table = dynamodb.Table(os.environ['CUSTOMERS_TABLE'])


def handle_load_credits(event):
    """
    Maneja el intent de carga de créditos
    """
    from utils import elicit_slot, delegate, close_intent
    
    invocation_source = event['invocationSource']
    slots = event['sessionState']['intent']['slots']
    
    # Extraer valores
    customer_dni = get_slot_value(slots, 'sl_customer_dni')
    amount = get_slot_value(slots, 'sl_amount')
    payment_method = get_slot_value(slots, 'slt_payment_methods')
    confirmation = get_slot_value(slots, 'sl_confirmation', '')
    
    print(f"🔍 invocationSource: {invocation_source}")
    print(f"📋 Valores - DNI: {customer_dni}, Monto: {amount}, Método: {payment_method}, Confirmación: {confirmation}")
    
    # ==========================================
    # PARTE 1: VALIDACIONES (mientras Lex pide slots)
    # ==========================================
    if invocation_source == 'DialogCodeHook':
        print("✅ Estamos en DialogCodeHook (validando mientras pedimos slots)")
        
        # --- VALIDACIÓN: Usuario dijo NO → Volver a Amazon Q ---
        if confirmation:
            confirmation_lower = confirmation.lower().strip()
            print(f"🔍 Verificando confirmación: '{confirmation_lower}'")
            
            if confirmation_lower in ['no', 'nop', 'negativo', 'cancelar', 'cancelo', 'nunca', 'no quiero']:
                print("❌ Usuario dijo NO - Volviendo a Amazon Q")
                
                return close_intent(
                    event,
                    'Fulfilled',
                    'Entendido, operación cancelada. ¿En qué más puedo ayudarte?'
                )
        
        # Si todo OK, dejar que Lex continúe
        print("✅ Validaciones OK - Delegando a Lex")
        return delegate(event)
    
    # ==========================================
    # PARTE 2: FULFILLMENT (cargar créditos)
    # ==========================================
    if invocation_source == 'FulfillmentCodeHook':
        print("✅ Estamos en FulfillmentCodeHook (todos los slots llenos, usuario dijo SÍ)")
        
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
                    f'✅ Carga exitosa!\n'
                    f'Se agregaron {amount} créditos a tu cuenta.\n'
                    f'Créditos anteriores: {current_credits}\n'
                    f'Nuevo saldo: {new_credits} créditos\n'
                    f'Método de pago: {payment_method}'
                )
                
                # Agregar recordatorio solo si es efectivo
                if payment_method.lower() == 'efectivo':
                    message += '\n💡 Recuerda llevar efectivo.'
                
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
                    f'✅ Cuenta creada y carga exitosa!\n'
                    f'Bienvenido! Se creó tu cuenta con {amount} créditos.\n'
                    f'Método de pago: {payment_method}\n'
                    f'(Para demo, el cliente fue registrado automáticamente)'
                )
            
            return close_intent(event, 'Fulfilled', message)
        
        except Exception as e:
            print(f"❌ Error cargando créditos: {str(e)}")
            return close_intent(
                event,
                'Fulfilled',
                'Ocurrió un error procesando la carga. Por favor intenta de nuevo.'
            )