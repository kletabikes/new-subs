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

    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    first_day_of_month = today.replace(day=1)

    # 1. Filtrar las ventas donde 'Estado Ingresos' == "Cobrado"
    df_cobradas = df_sales[df_sales['Estado Ingresos'].str.lower() == 'cobrado']

    # 2. Filtrar las ventas de bicicletas
    df_bicis = df_cobradas[df_cobradas['Categoria de Item'].str.lower() == 'bicicleta']

    # 3. Lógica para filtrar ventas del fin de semana, y evitar duplicaciones
    if today.weekday() == 0:  # Si es lunes, incluir las ventas de sábado y domingo
        saturday = today - timedelta(days=2)
        sunday = today - timedelta(days=1)

        ventas_hoy_bicis = df_bicis[
            (df_bicis['Ultimo cobro'] >= saturday) & (df_bicis['Ultimo cobro'] < today + timedelta(days=1))
        ]
        ventas_hoy_total = df_cobradas[
            (df_cobradas['Ultimo cobro'] >= saturday) & (df_cobradas['Ultimo cobro'] < today + timedelta(days=1))
        ]
    else:
        # Si es cualquier otro día, solo contamos las ventas de hoy
        ventas_hoy_bicis = df_bicis[
            (df_bicis['Ultimo cobro'] >= today) & (df_bicis['Ultimo cobro'] < today + timedelta(days=1))
        ]
        ventas_hoy_total = df_cobradas[
            (df_cobradas['Ultimo cobro'] >= today) & (df_cobradas['Ultimo cobro'] < today + timedelta(days=1))
        ]

    # 4. Ventas del mes
    ventas_mes_bicis = df_bicis[df_bicis['Ultimo cobro'] >= first_day_of_month]
    ventas_mes_total = df_cobradas[df_cobradas['Ultimo cobro'] >= first_day_of_month]

    # 5. Calcular ingresos de todas las ventas (ingresos totales) y contar solo las bicicletas
    ingresos_hoy = ventas_hoy_total['Total'].sum()  # Ingresos de todas las ventas de hoy
    ingresos_mes = ventas_mes_total['Total'].sum()  # Ingresos de todas las ventas del mes

    # 6. Retornar los valores correctamente calculados
    return {
        'pedidos_hoy': ventas_hoy_bicis.shape[0],  # Número de pedidos de bicicletas hoy
        'ingresos_hoy': round(ingresos_hoy, 2),  # Ingresos totales de hoy (todas las ventas cobradas)
        'pedidos_mes': ventas_mes_bicis.shape[0],  # Número de pedidos de bicicletas este mes
        'ingresos_mes': round(ingresos_mes, 2),  # Ingresos totales de este mes (todas las ventas cobradas)
    }
