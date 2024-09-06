import os
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
from fetch_data.fetch_sales import fetch_sales_data, process_sales_data
from fetch_data.fetch_subscriptions import fetch_subscriptions_data
import base64


# Definición de colores y rutas de archivos
KLETA_COLORS = {
    'primary_1': '#FFE461',
    'primary_2': '#01163A',
    'background': '#E8E8E8',
    'secondary_1': '#FF8700',
    'secondary_2': '#FFBA21',
    'secondary_3': '#FFF2BA',
    'secondary_4': '#033082'
}

SUBSCRIPTIONS_CSV = 'data/subscriptions.csv'
LAST_PROCESSED_CSV = 'data/last_processed.csv'
GOALS_CSV = 'data/monthly_goals.csv'
SOUND_PATH = 'assets/new_subscription.mp3'

def init_files():
    if not os.path.exists('data'):
        os.makedirs('data')

    if not os.path.exists(SUBSCRIPTIONS_CSV):
        pd.DataFrame(columns=['id', 'fecha_de_pago', 'tipo', 'descontar_nuevos', 'page']).to_csv(SUBSCRIPTIONS_CSV, index=False)

    if not os.path.exists(LAST_PROCESSED_CSV):
        pd.DataFrame(columns=['last_processed_id', 'last_processed_date']).to_csv(LAST_PROCESSED_CSV, index=False)

    init_goal_file()

def init_goal_file():
    current_month = datetime.now().strftime('%Y-%m')
    if not os.path.exists(GOALS_CSV):
        st.session_state['goals_entered'] = False
        prompt_for_goals(current_month)
    else:
        reset_goals_if_new_month(current_month)

def reset_goals_if_new_month(current_month):
    df = pd.read_csv(GOALS_CSV)
    if df.empty or 'month' not in df.columns or df['month'].iloc[0] != current_month:
        st.session_state['goals_entered'] = False
        prompt_for_goals(current_month)
    else:
        st.session_state['goals_entered'] = True

def prompt_for_goals(current_month):
    if 'goals_entered' not in st.session_state or not st.session_state['goals_entered']:
        st.info("Nuevo mes detectado. Por favor, ingrese los nuevos objetivos mensuales.")

        col1, col2, col3 = st.columns(3)
        with col1:
            goal_electrica = st.number_input("Objetivo para E-Kleta", min_value=0, key="goal_electrica")
        with col2:
            goal_mecanica = st.number_input("Objetivo para Kleta", min_value=0, key="goal_mecanica")
        with col3:
            goal_long_tail = st.number_input("Objetivo para Long Tail", min_value=0, key="goal_long_tail")

        col4, col5 = st.columns(2)
        with col4:
            goal_pedidos = st.number_input("Objetivo para Pedidos", min_value=0, key="goal_pedidos")
        with col5:
            goal_ingresos = st.number_input("Objetivo para Ingresos", min_value=0, key="goal_ingresos")

        if st.button("Guardar Objetivos"):
            goals_data = {
                'month': [current_month],
                'goal_electrica': [goal_electrica],
                'goal_mecanica': [goal_mecanica],
                'goal_long_tail': [goal_long_tail],
                'goal_pedidos': [goal_pedidos],
                'goal_ingresos': [goal_ingresos]
            }
            df = pd.DataFrame(goals_data)
            df.to_csv(GOALS_CSV, index=False)
            st.session_state['goals_entered'] = True
            st.success("Objetivos guardados correctamente.")
            st.rerun()

def get_goals():
    if os.path.exists(GOALS_CSV):
        df = pd.read_csv(GOALS_CSV)
        if not df.empty:
            return {
                'goal_electrica': int(df['goal_electrica'].iloc[0]),
                'goal_mecanica': int(df['goal_mecanica'].iloc[0]),
                'goal_long_tail': int(df['goal_long_tail'].iloc[0]),
                'goal_pedidos': int(df['goal_pedidos'].iloc[0]),
                'goal_ingresos': df['goal_ingresos'].iloc[0]
            }
    return None

def get_last_processed():
    if os.path.exists(LAST_PROCESSED_CSV):
        last_processed_df = pd.read_csv(LAST_PROCESSED_CSV)
        if not last_processed_df.empty:
            last_processed_id = last_processed_df['last_processed_id'].iloc[-1]
            last_processed_date = pd.to_datetime(last_processed_df['last_processed_date'].iloc[-1], errors='coerce')
            return last_processed_id, last_processed_date
    return None, None

def update_last_processed(last_id, last_date):
    pd.DataFrame({'last_processed_id': [last_id], 'last_processed_date': [last_date]}).to_csv(LAST_PROCESSED_CSV, index=False)

def store_new_subscriptions(new_subs):
    new_subs_df = pd.DataFrame(new_subs, columns=['id', 'fecha_de_pago', 'tipo', 'descontar_nuevos', 'page'])
    valid_subs_df = new_subs_df.dropna(subset=['tipo', 'page'])

    if not valid_subs_df.empty:
        valid_subs_df.to_csv(SUBSCRIPTIONS_CSV, mode='a', header=False, index=False)

def count_subscriptions_by_type():
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Si hoy es sábado (weekday() == 5), es el primer día de la semana
    # Calcular el primer día de la semana como el sábado anterior
    if today.weekday() >= 5:  # Sábado y domingo
        first_day_of_week = today - timedelta(days=today.weekday() - 5)
    else:  # De lunes a viernes
        first_day_of_week = today - timedelta(days=today.weekday() + 2)  # Obtener el sábado anterior

    # El último día de la semana sería el siguiente viernes (inclusive)
    last_day_of_week = first_day_of_week + timedelta(days=6)

    if os.path.exists(SUBSCRIPTIONS_CSV):
        subs_df = pd.read_csv(SUBSCRIPTIONS_CSV, on_bad_lines='skip')
        subs_df['fecha_de_pago'] = pd.to_datetime(subs_df['fecha_de_pago'], errors='coerce')

        if subs_df['fecha_de_pago'].isnull().sum() > 0:
            st.error("Existen fechas inválidas en el archivo de suscripciones.")
            return {
                'week': {'e_kleta': 0, 'm_kleta': 0, 'long_tail': 0},
                'today': {'e_kleta': 0, 'm_kleta': 0, 'long_tail': 0}
            }

        # Asegurarnos de que el sábado y domingo estén en el mismo mes que el lunes
        first_monday_of_week = first_day_of_week + timedelta(days=2)  # El lunes de la semana actual

        # Filtrar suscripciones desde el sábado (primero de la semana) hasta el viernes (último día de la semana)
        subs_this_week = subs_df[
            (subs_df['fecha_de_pago'] >= first_day_of_week) &
            (subs_df['fecha_de_pago'] <= last_day_of_week) &
            (subs_df['descontar_nuevos'] == 'No') &
            (subs_df['page'] == 'suscripcion')
        ]

        # Verificar si el sábado o domingo pertenecen al mes anterior, y excluirlos si es necesario
        subs_this_week = subs_this_week[
            (subs_this_week['fecha_de_pago'].dt.month == first_monday_of_week.month)
        ]

        # Filtrar suscripciones de hoy
        subs_today = subs_df[
            (subs_df['fecha_de_pago'] >= today) & 
            (subs_df['fecha_de_pago'] < today + timedelta(days=1)) &
            (subs_df['descontar_nuevos'] == 'No') & 
            (subs_df['page'] == 'suscripcion')
        ]

        # Contar suscripciones por tipo
        e_kleta_week = subs_this_week[subs_this_week['tipo'] == 'ELECTRICA'].shape[0]
        m_kleta_week = subs_this_week[subs_this_week['tipo'] == 'MECANICA'].shape[0]
        long_tail_week = subs_this_week[subs_this_week['tipo'] == 'LONG TAIL'].shape[0]

        e_kleta_today = subs_today[subs_today['tipo'] == 'ELECTRICA'].shape[0]
        m_kleta_today = subs_today[subs_today['tipo'] == 'MECANICA'].shape[0]
        long_tail_today = subs_today[subs_today['tipo'] == 'LONG TAIL'].shape[0]

        return {
            'week': {
                'e_kleta': e_kleta_week,
                'm_kleta': m_kleta_week,
                'long_tail': long_tail_week
            },
            'today': {
                'e_kleta': e_kleta_today,
                'm_kleta': m_kleta_today,
                'long_tail': long_tail_today
            }
        }
    else:
        st.warning("No se encontraron suscripciones en el CSV.")
        return {
            'week': {
                'e_kleta': 0,
                'm_kleta': 0,
                'long_tail': 0
            },
            'today': {
                'e_kleta': 0,
                'm_kleta': 0,
                'long_tail': 0
            }
        }

def color_for_goal(percentage):
    if percentage >= 0.9:
        return 'green'
    elif 0.4 <= percentage < 0.9:
        return 'orange'
    else:
        return 'red'

def reproducir_sonido():
    file_path = "assets/new_subscription.mp3"
    with open(file_path, "rb") as f:
        data = f.read()
        b64 = base64.b64encode(data).decode()
        
        # Código HTML para reproducir el sonido
        audio_html = f"""
            <audio autoplay>
            <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
            Tu navegador no soporta el elemento de audio.
            </audio>
        """
        st.markdown(audio_html, unsafe_allow_html=True)

# Función para verificar y reproducir el sonido si hay un aumento
def verificar_y_reproducir_sonido(subs_count_actual):
    if 'last_subs_count' not in st.session_state:
        st.session_state['last_subs_count'] = subs_count_actual
    else:
        last_count = st.session_state['last_subs_count']
        if subs_count_actual > last_count:
            reproducir_sonido()  # Reproduce sonido si hay aumento
        st.session_state['last_subs_count'] = subs_count_actual

def show_scorecards(subscriptions_count, sales_data, goals):
    today_count = sum(subscriptions_count['today'].values())

    st.markdown("<h1 style='text-align: center; color:{};'>Suscripciones y pedidos (Hoy)</h1>".format(KLETA_COLORS['primary_2']), unsafe_allow_html=True)

    col1, col2, col3, col_divider, col4, col5 = st.columns([1, 1, 1, 0.05, 1, 1])

    col1.markdown(f"""
        <div style="text-align: center; padding: 20px; border: 2px solid {KLETA_COLORS['primary_2']}; border-radius: 10px; background-color: {KLETA_COLORS['secondary_3']};">
            <h2 style="text-align:center; margin-bottom: 5px; color: {KLETA_COLORS['secondary_4']}; font-size: 60px">E-Kleta</h2>
            <p style="font-size: 55px;">{subscriptions_count['today']['e_kleta']}</p>
        </div>
    """, unsafe_allow_html=True)

    col2.markdown(f"""
        <div style="text-align: center; padding: 20px; border: 2px solid {KLETA_COLORS['primary_2']}; border-radius: 10px; background-color: {KLETA_COLORS['secondary_3']};">
            <h2 style="text-align:center; margin-bottom: 5px; color: {KLETA_COLORS['secondary_4']}; font-size: 60px">Kleta</h2>
            <p style="font-size: 55px;">{subscriptions_count['today']['m_kleta']}</p>
        </div>
    """, unsafe_allow_html=True)

    col3.markdown(f"""
        <div style="text-align: center; padding: 20px; border: 2px solid {KLETA_COLORS['primary_2']}; border-radius: 10px; background-color: {KLETA_COLORS['secondary_3']};">
            <h2 style="text-align:center; margin-bottom: 5px; color: {KLETA_COLORS['secondary_4']}; font-size: 60px">Long Tail</h2>
            <p style="font-size: 55px;">{subscriptions_count['today']['long_tail']}</p>
        </div>
    """, unsafe_allow_html=True)

    col_divider.markdown("""
        <div style='border-left: 2px solid #ccc; height: 100%; margin-left: auto; margin-right: auto;'></div>
    """, unsafe_allow_html=True)

    col4.markdown(f"""
        <div style="text-align: center; padding: 20px; border: 2px solid {KLETA_COLORS['primary_2']}; border-radius: 10px; background-color: {KLETA_COLORS['secondary_3']};">
            <h2 style="text-align:center; margin-bottom: 5px; color: {KLETA_COLORS['secondary_4']}; font-size: 60px">Pedidos</h2>
            <p style="font-size: 55px;">{sales_data['pedidos_hoy']}</p>
        </div>
    """, unsafe_allow_html=True)

    col5.markdown(f"""
        <div style="text-align: center; padding: 20px; border: 2px solid {KLETA_COLORS['primary_2']}; border-radius: 10px; background-color: {KLETA_COLORS['secondary_3']};">
            <h2 style="text-align:center; margin-bottom: 5px; color: {KLETA_COLORS['secondary_4']}; font-size: 60px">Ingresos</h2>
            <p style="font-size: 55px;">€{sales_data['ingresos_hoy']}</p>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    st.markdown("<h1 style='text-align: center; color:{};'>Acumulado de la semana</h1>".format(KLETA_COLORS['primary_2']), unsafe_allow_html=True)

    col1, col2, col3, col_divider, col4, col5 = st.columns([1, 1, 1, 0.05, 1, 1])

    if goals:
        weeks_in_month = 4  # Asumimos que cada mes tiene 4 semanas
        weekly_goal_electrica = goals['goal_electrica'] / weeks_in_month
        weekly_goal_mecanica = goals['goal_mecanica'] / weeks_in_month
        weekly_goal_long_tail = goals['goal_long_tail'] / weeks_in_month
        weekly_goal_pedidos = goals['goal_pedidos'] / weeks_in_month
        weekly_goal_ingresos = goals['goal_ingresos'] / weeks_in_month

        e_kleta_percentage = subscriptions_count['week']['e_kleta'] / weekly_goal_electrica
        m_kleta_percentage = subscriptions_count['week']['m_kleta'] / weekly_goal_mecanica
        long_tail_percentage = subscriptions_count['week']['long_tail'] / weekly_goal_long_tail

        e_kleta_color = color_for_goal(e_kleta_percentage)
        m_kleta_color = color_for_goal(m_kleta_percentage)
        long_tail_color = color_for_goal(long_tail_percentage)

        col1.markdown(f"""
            <div style="text-align: center; padding: 20px; border: 2px solid {KLETA_COLORS['primary_2']}; border-radius: 10px; background-color: {KLETA_COLORS['secondary_3']};">
                <h2 style="text-align:center; margin-bottom: 5px; color: {KLETA_COLORS['secondary_4']}; font-size: 60px">E-Kleta</h2>
                <p style="font-size: 55px;">{subscriptions_count['week']['e_kleta']}</p>
                <p style="color: {e_kleta_color}; font-size: 40px;">Objetivo: {int(weekly_goal_electrica)}</p>
            </div>
        """, unsafe_allow_html=True)

        col2.markdown(f"""
            <div style="text-align: center; padding: 20px; border: 2px solid {KLETA_COLORS['primary_2']}; border-radius: 10px; background-color: {KLETA_COLORS['secondary_3']};">
                <h2 style="text-align:center; margin-bottom: 5px; color: {KLETA_COLORS['secondary_4']}; font-size: 60px">Kleta</h2>
                <p style="font-size: 55px;">{subscriptions_count['week']['m_kleta']}</p>
                <p style="color: {m_kleta_color}; font-size: 40px;">Objetivo: {int(weekly_goal_mecanica)}</p>
            </div>
        """, unsafe_allow_html=True)

        col3.markdown(f"""
            <div style="text-align: center; padding: 20px; border: 2px solid {KLETA_COLORS['primary_2']}; border-radius: 10px; background-color: {KLETA_COLORS['secondary_3']};">
                <h2 style="text-align:center; margin-bottom: 5px; color: {KLETA_COLORS['secondary_4']}; font-size: 60px">Long Tail</h2>
                <p style="font-size: 55px;">{subscriptions_count['week']['long_tail']}</p>
                <p style="color: {long_tail_color}; font-size: 40px;">Objetivo: {int(weekly_goal_long_tail)}</p>
            </div>
        """, unsafe_allow_html=True)

        pedidos_percentage = sales_data['pedidos_mes'] / weekly_goal_pedidos
        ingresos_percentage = sales_data['ingresos_mes'] / weekly_goal_ingresos

        pedidos_color = color_for_goal(pedidos_percentage)
        ingresos_color = color_for_goal(ingresos_percentage)

        col4.markdown(f"""
            <div style="text-align: center; padding: 20px; border: 2px solid {KLETA_COLORS['primary_2']}; border-radius: 10px; background-color: {KLETA_COLORS['secondary_3']};">
                <h2 style="text-align:center; margin-bottom: 5px; color: {KLETA_COLORS['secondary_4']}; font-size: 60px">Pedidos</h2>
                <p style="font-size: 55px;">{sales_data['pedidos_mes']}</p>
                <p style="color: {pedidos_color}; font-size: 40px;">Objetivo: {int(weekly_goal_pedidos)}</p>
            </div>
        """, unsafe_allow_html=True)

        col5.markdown(f"""
            <div style="text-align: center; padding: 20px; border: 2px solid {KLETA_COLORS['primary_2']}; border-radius: 10px; background-color: {KLETA_COLORS['secondary_3']};">
                <h2 style="text-align:center; margin-bottom: 5px; color: {KLETA_COLORS['secondary_4']}; font-size: 60px">Ingresos</h2>
                <p style="font-size: 55px;">€{sales_data['ingresos_mes']}</p>
                <p style="color: {ingresos_color}; font-size: 40px;">Objetivo: €{weekly_goal_ingresos:.2f}</p>
            </div>
        """, unsafe_allow_html=True)
    
    # Verificar y reproducir sonido si hay un aumento en las suscripciones
    verificar_y_reproducir_sonido(today_count)

def main():
    init_files()

    last_processed_id, last_processed_date = get_last_processed()

    df_subscriptions = fetch_subscriptions_data()
    df_sales = fetch_sales_data()

    if not df_subscriptions.empty:
        df_subscriptions['fecha_de_pago'] = pd.to_datetime(df_subscriptions['fecha_de_pago'], errors='coerce')

        # Procesar solo suscripciones que llegaron después de la última fecha procesada
        if last_processed_date is not None:
            new_subs = df_subscriptions[df_subscriptions['fecha_de_pago'] > last_processed_date]
        else:
            new_subs = df_subscriptions

        if not new_subs.empty:
            new_subs_list = new_subs[['id', 'fecha_de_pago', 'tipo', 'descontar_nuevos', 'page']].values.tolist()
            store_new_subscriptions(new_subs_list)
            update_last_processed(new_subs['id'].max(), new_subs['fecha_de_pago'].max())

    if 'goals_entered' not in st.session_state or not st.session_state['goals_entered']:
        st.stop()

    goals = get_goals()
    if goals:
        subscriptions_count = count_subscriptions_by_type()
        sales_data = process_sales_data(df_sales)

        show_scorecards(subscriptions_count, sales_data, goals)
    else:
        st.warning("No se encontraron objetivos mensuales. Por favor, ingrese los objetivos.")

if __name__ == "__main__":
    main()
