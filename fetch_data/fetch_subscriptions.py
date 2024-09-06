import urllib.parse
import requests
import pandas as pd
import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from assets import config


def fetch_subscriptions_data():
<<<<<<< HEAD
    query_string = f"(select 'SUBSCRIPTIONS').{{id: text(SubNinoxID), 'fecha_de_pago': text('Created on'), tipo:text(WIX_MODELOS.Tipo), 'descontar_nuevos': text('Descontar de Nuevos Usuarios'), page:text(Page), status:text(Status)}}"
=======
    query_string = f"(select {config.TABLE_NAME}).{{id: text(SubNinoxID), 'fecha_de_inicio': text('Fecha Inicio'), tipo:text(WIX_MODELOS.Tipo), page:text(Page), plan: text(WIX_PLANES.Plan), status:text(Status), ciudad:text(USERS.WIX_CIUDAD.Ciudad)}}"
>>>>>>> 9db4931 (primer commit)
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
<<<<<<< HEAD
            
            df_filtered = df[df['status'] != 'Not Happened']
            return df_filtered
=======

            df['ciudad'] = df['ciudad'].apply(lambda x: 'Barcelona' if x.lower() == 'barcelona' 
                                              else 'Valencia' if x.lower() == 'valencia' 
                                              else 'otros')

            df = df[df['page'] == 'suscripcion']
            df = df[df['status'] != 'Not Happened']

            df['fecha_de_inicio'] = pd.to_datetime(df['fecha_de_inicio'], errors='coerce')
            df[['fecha_de_inicio', 'tipo']] = df[['fecha_de_inicio', 'tipo']].replace('', pd.NA)

            # Eliminar filas con NaN en 'fecha_de_inicio' o 'tipo'
            df = df.dropna(subset=['fecha_de_inicio', 'tipo'])

            return df
>>>>>>> 9db4931 (primer commit)
        else:
            return pd.DataFrame()
    except requests.exceptions.RequestException as e:
        raise ConnectionError(f"Error al obtener los registros: {e}")
