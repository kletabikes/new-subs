import urllib.parse
import requests
import pandas as pd
from datetime import datetime, timedelta
import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from assets import config

# Función para obtener datos de ventas de la API de Ninox
def fetch_sales_data():
    query_string = f"(select 'POS_ITEMS_X_PEDIDO').{{cafe = POS_PEDIDOS.Cafe, 'Fecha de Venta': text('Fecha de Venta'), Total: number('Valor Unidad' + IVA), 'Estado Ingresos': text(POS_PEDIDOS.EstadoIngresos), 'Categoria de Item': ITEMS.Categoria.Categoria}}"
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
            return df
        else:
            print("No se encontraron registros.")
            return pd.DataFrame()
    except requests.exceptions.RequestException as e:
        raise ConnectionError(f"Error al obtener los registros: {e}")


# Función para procesar datos de ventas actuales
def process_sales_data(df_sales):
    if df_sales.empty:
        return {
            'pedidos_hoy': 0,
            'ingresos_hoy': 0,
            'pedidos_semana': 0,
            'ingresos_semana': 0,
        }

    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    first_day_of_week = today - timedelta(days=today.weekday())  # Lunes de la semana actual

    df_sales['Total'] = pd.to_numeric(df_sales['Total'], errors='coerce').fillna(0)
    df_cobradas = df_sales[df_sales['Estado Ingresos'].str.lower() == 'cobrado']
    df_bicis = df_cobradas[df_cobradas['Categoria de Item'].str.lower() == 'bicicleta']

    # Ventas de hoy
    ventas_hoy_bicis = df_bicis[(df_bicis['Fecha de Venta'] >= today) & (df_bicis['Fecha de Venta'] < today + timedelta(days=1))]
    ventas_hoy_total = df_cobradas[(df_cobradas['Fecha de Venta'] >= today) & (df_cobradas['Fecha de Venta'] < today + timedelta(days=1))]

    # Ventas de la semana
    ventas_semana_bicis = df_bicis[(df_bicis['Fecha de Venta'] >= first_day_of_week) & (df_bicis['Fecha de Venta'] < today + timedelta(days=1))]
    ventas_semana_total = df_cobradas[(df_cobradas['Fecha de Venta'] >= first_day_of_week) & (df_cobradas['Fecha de Venta'] < today + timedelta(days=1))]

    ingresos_hoy_bicis = ventas_hoy_bicis['Total'].sum()
    ingresos_hoy_total = ventas_hoy_total['Total'].sum()
    ingresos_semana_bicis = ventas_semana_bicis['Total'].sum()
    ingresos_semana_total = ventas_semana_total['Total'].sum()

    return {
        'pedidos_hoy': ventas_hoy_bicis.shape[0],
        'ingresos_hoy': round(ingresos_hoy_total, 2),
        'pedidos_semana': ventas_semana_bicis.shape[0],
        'ingresos_semana': round(ingresos_semana_total, 2),
    }

# Función para procesar los datos de ventas de la semana pasada
def process_sales_data_last_week(df_sales):
    today = (datetime.now() + timedelta(hours=2)).replace(hour=0, minute=0, second=0, microsecond=0)
    current_week_monday = today - timedelta(days=today.weekday())  # Lunes de esta semana
    last_week_sunday = current_week_monday - timedelta(seconds=1)  # Domingo 23:59:59 de la semana pasada
    last_week_monday = last_week_sunday - timedelta(days=6)  # Lunes 00:00:00 de la semana pasada

    last_week_monday = last_week_monday.replace(hour=0, minute=0, second=0, microsecond=0)
    last_week_sunday = last_week_sunday.replace(hour=23, minute=59, second=59, microsecond=999999)

    print(f"Rango de fechas para la semana pasada: {last_week_monday} - {last_week_sunday}")

    if df_sales.empty:
        return {
            'pedidos_semana_pasada': 0,
            'ingresos_semana_bicis': 0,
            'ingresos_semana_cafe': 0,
            'ingresos_semana_pasada': 0,
        }

    # Convertir 'Total' a numérico y llenar NaN
    df_sales['Total'] = pd.to_numeric(df_sales['Total'], errors='coerce').fillna(0)
    df_sales['Categoria de Item'] = df_sales['Categoria de Item'].fillna('')

    # Filtrar ventas cobradas
    df_cobradas = df_sales[df_sales['Estado Ingresos'].str.lower() == 'cobrado']

    # Filtrar las ventas de bicicletas y otros productos
    df_bicis = df_cobradas[
        (df_cobradas['cafe'] == False) &  # No es café
        (df_cobradas['Categoria de Item'].str.contains('bicicleta'))  # Es bicicleta
    ]

    df_otros = df_cobradas[
        (df_cobradas['cafe'] == False) &  # No es café
        (~df_cobradas['Categoria de Item'].str.contains('bicicleta'))  # No es bicicleta
    ]

    # Filtrar las ventas de café
    df_cafe = df_cobradas[df_cobradas['cafe'] == True]

    # Filtrar los productos por rango de fechas
    ventas_semana_bicis = df_bicis[
        (df_bicis['Fecha de Venta'] >= last_week_monday) & 
        (df_bicis['Fecha de Venta'] <= last_week_sunday)
    ]
    
    ventas_semana_otros = df_otros[
        (df_otros['Fecha de Venta'] >= last_week_monday) & 
        (df_otros['Fecha de Venta'] <= last_week_sunday)
    ]

    ventas_semana_cafe = df_cafe[
        (df_cafe['Fecha de Venta'] >= last_week_monday) & 
        (df_cafe['Fecha de Venta'] <= last_week_sunday)
    ]

    # Ventas totales
    ventas_semana_total = pd.concat([ventas_semana_bicis, ventas_semana_otros, ventas_semana_cafe])

    # Sumar ingresos
    ingresos_semana_bicis = ventas_semana_bicis['Total'].sum() if not ventas_semana_bicis.empty else 0
    ingresos_semana_cafe = ventas_semana_cafe['Total'].sum() if not ventas_semana_cafe.empty else 0
    ingresos_semana_total = ventas_semana_total['Total'].sum() if not ventas_semana_total.empty else 0

    print("\nVentas de la semana pasada (Bicicletas):")

    print("Ventas de la semana pasada (Café):")

    print("Ventas de la semana pasada (Total):")

    print(f"Pedidos semana pasada (Bicicletas): {ventas_semana_bicis.shape[0]}, Ingresos semana pasada (Total): {ingresos_semana_total}")

    return {
        'pedidos_semana_pasada': ventas_semana_total.shape[0],
        'ingresos_semana_bicis': round(ingresos_semana_bicis, 2),
        'ingresos_semana_cafe': round(ingresos_semana_cafe, 2),
        'ingresos_semana_pasada': round(ingresos_semana_total, 2),
    }

if __name__ == "__main__":
    df_sales = fetch_sales_data()

    result = process_sales_data_last_week(df_sales)

    # Imprimir el resultado final
    print("\nRESULTADO FINAL:")
    print(f"Pedidos de la semana pasada: {result['pedidos_semana_pasada']}")
    print(f"Ingresos de la semana pasada (Bicicletas): {result['ingresos_semana_bicis']}")
    print(f"Ingresos de la semana pasada (Café): {result['ingresos_semana_cafe']}")
    print(f"Ingresos de la semana pasada (Total): {result['ingresos_semana_pasada']}")
