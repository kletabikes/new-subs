import urllib.parse
import requests
import pandas as pd
import os, sys
from datetime import timedelta  # Importar timedelta para ajustar la hora
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from assets import config

def fetch_subscriptions_data():
    query_string = f"(select 'SUBSCRIPTIONS').{{id: text(SubNinoxID), 'fecha_de_pago': text('Created on'), tipo:text(WIX_MODELOS.Tipo), 'descontar_nuevos': text('Descontar de Nuevos Usuarios'), page:text(Page), status:text(Status)}}"
    encoded_query = urllib.parse.quote(query_string)
    query_url = f"{config.NINOX_API_ENDPOINT}teams/{config.NINOX_TEAM_ID}/databases/{config.NINOX_DATABASE_ID}/query?query={encoded_query}"
    headers = {
        'Authorization': f'Bearer {config.NINOX_API_KEY}',
        'Content-Type': 'application/json'
    }

    try:
        response = requests.get(query_url, headers=headers)
        response.raise_for_status()
        records = response.json()
        
        if records:
            df = pd.json_normalize(records)
            
            # Convertir 'fecha_de_pago' a datetime y agregar una hora
            df['fecha_de_pago'] = pd.to_datetime(df['fecha_de_pago'], errors='coerce') + timedelta(hours=2)
            
            # Filtrar los registros con status diferente de 'Not Happened'
            df_filtered = df[df['status'] != 'Not Happened']
            return df_filtered
        else:
            return pd.DataFrame()
    except requests.exceptions.RequestException as e:
        raise ConnectionError(f"Error al obtener los registros: {e}")
