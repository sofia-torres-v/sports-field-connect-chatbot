"""
Check Balance Function
Consulta el balance de créditos de un cliente
Se invoca directamente desde Amazon Connect (no desde Lex)
"""

import json
import os
import boto3

dynamodb = boto3.resource('dynamodb')
customers_table = dynamodb.Table(os.environ['CUSTOMERS_TABLE'])


def handler(event, context):
    """
    Handler para consultar balance
    
    Evento esperado desde Connect:
    {
        "Details": {
            "Parameters": {
                "customer_dni": "12345678"
            }
        }
    }
    """
    print(f"Evento recibido: {json.dumps(event)}")
    
    try:
        # Extraer DNI del evento de Connect
        customer_dni = event['Details']['Parameters']['customer_dni']
        
        print(f"Consultando saldo para DNI: {customer_dni}")
        
        # Buscar cliente en DynamoDB
        response = customers_table.get_item(
            Key={'customer_dni': customer_dni}
        )
        
        print(f"Respuesta de DynamoDB: {json.dumps(response, default=str)}")
        
        if 'Item' in response:
            credits = int(response['Item'].get('credits', 0))
            
            result = {
                'balance': str(credits),
                'found': 'true',
                'message': f'Tienes {credits} créditos disponibles.'
            }
            
            print(f"Resultado exitoso: {json.dumps(result)}")
            return result
        else:
            result = {
                'balance': '0',
                'found': 'false',
                'message': f'No encontramos una cuenta con DNI {customer_dni}. Primero debes cargar créditos.'
            }
            
            print(f"Cliente no encontrado: {json.dumps(result)}")
            return result
    
    except KeyError as e:
        error_result = {
            'error': 'DNI no proporcionado',
            'message': 'Por favor proporciona tu DNI.',
            'found': 'false'
        }
        print(f"Error - Falta DNI: {json.dumps(error_result)}")
        return error_result
    
    except Exception as e:
        error_result = {
            'error': str(e),
            'message': 'Ocurrió un error consultando tu balance.',
            'found': 'false'
        }
        print(f"Error general: {json.dumps(error_result)}")
        return error_result