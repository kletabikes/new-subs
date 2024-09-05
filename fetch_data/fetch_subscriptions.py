import urllib.parse
import requests
import pandas as pd
import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from assets import config

def fetch_subscriptions_data():
    query_string = f"(select 'SUBSCRIPTIONS').{{id: text(SubNinoxID), 'fecha_de_pago': text('Created on'), tipo:text(WIX_MODELOS.Tipo), 'descontar_nuevos': text('Descontar de Nuevos Usuarios'), page:text(Page)}}"
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
            return df
        else:
            return pd.DataFrame()
    except requests.exceptions.RequestException as e:
        raise ConnectionError(f"Error al obtener los registros: {e}")