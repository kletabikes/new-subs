import os
import pandas as pd
from datetime import datetime, timedelta
from fetch_data.fetch_sales import fetch_sales_data, process_sales_data_last_week
from fetch_data.fetch_subscriptions import fetch_subscriptions_data
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def get_goals():
    GOALS_CSV = 'data/monthly_goals.csv'
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

def count_subscriptions_by_type_last_week(subs_df):
    # Implementación de get_last_week_start_end()
    def get_last_week_start_end():
        today = datetime.now()
        current_week_start = today - timedelta(days=today.weekday())
        current_week_start = current_week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        last_week_end = current_week_start - timedelta(seconds=1)
        last_week_start = last_week_end - timedelta(days=6)
        last_week_start = last_week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        last_week_end = last_week_end.replace(hour=23, minute=59, second=59, microsecond=999999)
        return last_week_start, last_week_end

    last_week_start, last_week_end = get_last_week_start_end()

    subs_df['fecha_de_pago'] = pd.to_datetime(subs_df['fecha_de_pago'], errors='coerce')

    subs_last_week = subs_df[
        (subs_df['fecha_de_pago'] >= last_week_start) &
        (subs_df['fecha_de_pago'] <= last_week_end) &
        (subs_df['descontar_nuevos'] == 'No') &
        (subs_df['page'] == 'suscripcion')
    ]

    e_kleta_last_week = subs_last_week[subs_last_week['tipo'] == 'ELECTRICA'].shape[0]
    m_kleta_last_week = subs_last_week[subs_last_week['tipo'] == 'MECANICA'].shape[0]
    long_tail_last_week = subs_last_week[subs_last_week['tipo'] == 'LONG TAIL'].shape[0]

    return {
        'week': {
            'e_kleta': e_kleta_last_week,
            'm_kleta': m_kleta_last_week,
            'long_tail': long_tail_last_week
        }
    }

def send_last_week_summary(subscriptions_count_last_week, sales_data_last_week, goals):
    sender_email = os.environ.get('SENDER_EMAIL')
    receiver_email = os.environ.get('RECEIVER_EMAIL')
    password = os.environ.get('EMAIL_PASSWORD')

    if not sender_email or not receiver_email or not password:
        print("Las credenciales de correo electrónico no están configuradas. Por favor, configúrelas en las variables de entorno.")
        return

    # Crear el mensaje de correo electrónico
    message = MIMEMultipart("alternative")
    message["Subject"] = f"Resumen de la última semana de Suscripciones y Ventas - {datetime.now().strftime('%Y-%m-%d')}"
    message["From"] = sender_email
    message["To"] = receiver_email

    # Contenido HTML del correo electrónico con tablas
    html = f"""
    <html>
    <body>
        <h2 style="color: #4B0082;">Resumen de la última semana de Suscripciones y Ventas</h2>

        <h3 style="color: #4B0082;">Suscripciones de la semana pasada</h3>
        <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; width: 100%;">
            <tr style="background-color: #f2f2f2;">
                <th>Tipo</th>
                <th>Objetivo</th>
                <th>Acumulado</th>
            </tr>
            <tr>
                <td style="text-align: center;">E-Kleta</td>
                <td style="text-align: center;">{int(goals['goal_electrica'] / 4)}</td>
                <td style="text-align: center;">{subscriptions_count_last_week['week']['e_kleta']}</td>
            </tr>
            <tr>
                <td style="text-align: center;">Kleta</td>
                <td style="text-align: center;">{int(goals['goal_mecanica'] / 4)}</td>
                <td style="text-align: center;">{subscriptions_count_last_week['week']['m_kleta']}</td>
            </tr>
            <tr>
                <td style="text-align: center;">Long Tail</td>
                <td style="text-align: center;">{int(goals['goal_long_tail'] / 4)}</td>
                <td style="text-align: center;">{subscriptions_count_last_week['week']['long_tail']}</td>
            </tr>
        </table>

        <h3 style="color: #4B0082;">Ventas de la semana pasada</h3>
        <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; width: 100%;">
            <tr style="background-color: #f2f2f2;">
                <th>Tipo</th>
                <th>Objetivo</th>
                <th>Acumulado</th>
            </tr>
            <tr>
                <td style="text-align: center;">Pedidos</td>
                <td style="text-align: center;">{int(goals['goal_pedidos'] / 4)}</td>
                <td style="text-align: center;">{sales_data_last_week.get('pedidos_semana_pasada', 0)}</td>
            </tr>
            <tr>
                <td style="text-align: center;">Ingresos</td>
                <td style="text-align: center;">€{goals['goal_ingresos'] / 4:.2f}</td>
                <td style="text-align: center;">€{sales_data_last_week.get('ingresos_semana_pasada', 0)}</td>
            </tr>
        </table>
    </body>
    </html>
    """

    # Convertir el contenido HTML a un objeto MIMEText
    part = MIMEText(html, "html")
    message.attach(part)

    # Enviar el correo electrónico
    try:
        # Si estás utilizando Gmail, debes configurar una contraseña de aplicación
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, message.as_string())
            print("Resumen de la última semana enviado con éxito")
    except Exception as e:
        print(f"Error al enviar el correo: {e}")
        print(e)  # Imprime el error en la consola para depuración

def main():
    goals = get_goals()
    if goals is None:
        print("No se encontraron objetivos mensuales. Por favor, ingrese los objetivos.")
        return

    df_subscriptions = fetch_subscriptions_data()
    df_sales = fetch_sales_data()

    subscriptions_count_last_week = count_subscriptions_by_type_last_week(df_subscriptions)
    sales_data_last_week = process_sales_data_last_week(df_sales)

    send_last_week_summary(subscriptions_count_last_week, sales_data_last_week, goals)

if __name__ == "__main__":
    main()