import urllib.parse
import requests
import pandas as pd
from datetime import datetime, timedelta
import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from assets import config

def fetch_sales_data():
    query_string = f"(select 'POS_ITEMS_X_PEDIDO').{{'Fecha de Venta': text(POS_PEDIDOS.Fecha), 'Ultimo cobro': text(last(POS_PEDIDOS.POS_INGRESOS_X_PEDIDO order by Fecha).Fecha), Total: number('Valor Unidad' + IVA), 'Estado Ingresos': text(POS_PEDIDOS.EstadoIngresos), 'Categoria de Item': ITEMS.Categoria.Categoria}}"
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
            
            df['Fecha de Venta'] = pd.to_datetime(df['Fecha de Venta'], errors='coerce') + timedelta(hours=2)
            df['Ultimo cobro'] = pd.to_datetime(df['Ultimo cobro'], errors='coerce') + timedelta(hours=2)

            return df
        else:
            return pd.DataFrame()
    except requests.exceptions.RequestException as e:
        raise ConnectionError(f"Error al obtener los registros: {e}")

def process_sales_data(df_sales):
    if df_sales.empty:
        return {
            'pedidos_hoy': 0,
            'ingresos_hoy': 0,
            'pedidos_mes': 0,
            'ingresos_mes': 0,
        }

    df_sales = df_sales[df_sales['Estado Ingresos'].str.lower() == 'cobrado']

    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    first_day_of_month = today.replace(day=1)

    df_bicis = df_sales[df_sales['Categoria de Item'].str.lower() == 'bicicleta']
    df_otros = df_sales[df_sales['Categoria de Item'].str.lower() != 'bicicleta']

    ingresos_bicis_hoy = df_bicis[(df_bicis['Ultimo cobro'] >= today) & 
                                  (df_bicis['Ultimo cobro'] < today + timedelta(days=1))]['Total'].sum()
    ingresos_bicis_mes = df_bicis[df_bicis['Ultimo cobro'] >= first_day_of_month]['Total'].sum()

    ingresos_otros_hoy = df_otros[(df_otros['Fecha de Venta'] >= today) & 
                                  (df_otros['Fecha de Venta'] < today + timedelta(days=1))]['Total'].sum()
    ingresos_otros_mes = df_otros[df_otros['Fecha de Venta'] >= first_day_of_month]['Total'].sum()

    ingresos_hoy = ingresos_bicis_hoy + ingresos_otros_hoy
    ingresos_mes = ingresos_bicis_mes + ingresos_otros_mes

    pedidos_hoy = df_bicis[(df_bicis['Ultimo cobro'] >= today) & 
                           (df_bicis['Ultimo cobro'] < today + timedelta(days=1))]

    pedidos_mes = df_bicis[df_bicis['Ultimo cobro'] >= first_day_of_month]

    return {
        'pedidos_hoy': pedidos_hoy.shape[0],  # Cuenta de pedidos de bicicletas hoy
        'ingresos_hoy': round(ingresos_hoy, 2),  # Ingresos totales de hoy (bicicletas y otros items)
        'pedidos_mes': pedidos_mes.shape[0],  # Cuenta de pedidos de bicicletas este mes
        'ingresos_mes': round(ingresos_mes, 2),  # Ingresos totales de este mes (bicicletas y otros items)
    }
