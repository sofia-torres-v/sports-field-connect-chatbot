"""
Text Parser Function
Parsea el summary de Amazon Q para mostrarlo al agente
(Igual que en el workshop)
"""

import re


def handler(event, context):
    """
    Parsea texto con tags XML de Amazon Q
    
    Entrada:
    <SummaryItems>
        <Item>El cliente quiere reservar cancha</Item>
        <Item>DNI: 12345678</Item>
    </SummaryItems>
    
    Salida:
    - El cliente quiere reservar cancha.
    - DNI: 12345678.
    """
    print(f"Evento recibido: {event}")
    
    try:
        qic_summary_in = event['Details']['Parameters']['qicSummaryIn']
        qic_summary_out = parse_qic_summary(qic_summary_in)
        
        return {
            'qicSummaryOut': qic_summary_out
        }
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'qicSummaryOut': 'Error procesando summary'
        }


def parse_qic_summary(tagged_text):
    """
    Parsea tagged text y retorna texto limpio
    
    Args:
        tagged_text (str): Texto con tags XML
    
    Returns:
        str: Texto limpio con bullets
    """
    # Encontrar todos los items entre tags <Item>
    items = re.findall(r'<Item>(.*?)</Item>', tagged_text)
    
    # Formatear cada item con un bullet point
    formatted_items = [f"- {item}." for item in items]
    
    # Unir items con saltos de línea
    return "\n".join(formatted_items)