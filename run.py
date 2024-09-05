import os
import streamlit as st
from git import Repo
from scripts.kpis import main
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime
import time

# Cargar las variables de entorno desde un archivo .env si estamos localmente
load_dotenv()

# Configurar las credenciales dependiendo si estamos en local o en Streamlit Cloud
if "GITHUB_TOKEN" in os.environ:
    GITHUB_USERNAME = os.getenv("GITHUB_USERNAME")
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    VALID_EMAIL = os.getenv("VALID_EMAIL")
    VALID_PASSWORD = os.getenv("VALID_PASSWORD")
else:
    GITHUB_USERNAME = st.secrets["GITHUB_USERNAME"]
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
    VALID_EMAIL = st.secrets["VALID_EMAIL"]
    VALID_PASSWORD = st.secrets["VALID_PASSWORD"]

BRANCH_NAME = "main"  # Trabajamos solo con la rama main

def check_goals_exist():
    GOALS_CSV = 'data/monthly_goals.csv'
    current_month = datetime.now().strftime('%Y-%m')
    
    if os.path.exists(GOALS_CSV):
        df = pd.read_csv(GOALS_CSV)
        if 'month' in df.columns and df['month'].iloc[0] == current_month:
            return True
    return False

def login():
    st.title("Iniciar sesión")

    email = st.text_input("Correo electrónico")
    password = st.text_input("Contraseña", type="password")

    if st.button("Iniciar sesión"):
        if email == VALID_EMAIL and password == VALID_PASSWORD:
            st.session_state['logged_in'] = True
            st.rerun()  # Recargar la página después de iniciar sesión
        else:
            st.error("Correo electrónico o contraseña incorrectos.")

def commit_and_push():
    try:
        repo = Repo(os.getcwd())

        # Asegurarse de que tenemos la última versión de main
        origin = repo.remote(name='origin')

        # Configurar la URL remota con el token de GitHub para autenticación
        repo.git.remote('set-url', 'origin', f'https://{GITHUB_USERNAME}:{GITHUB_TOKEN}@github.com/{GITHUB_USERNAME}/your-repo.git')

        # Hacer pull de la última versión del repositorio
        origin.pull(BRANCH_NAME)

        # Añadir cambios y hacer commit
        repo.git.add('data/*')  # Añadir solo archivos relevantes
        repo.index.commit("Auto commit for data updates")

        # Hacer push usando el token
        origin.push(refspec=f"{BRANCH_NAME}:{BRANCH_NAME}")

        st.success("Datos guardados y push realizado correctamente.")
        st.rerun()  # Refrescar la página después del push

    except Exception as e:
        st.error(f"Error al hacer commit/push en GitHub: {e}")

def run_main_loop():
    if check_goals_exist():
        main()

        if st.button("Guardar Datos"):
            commit_and_push()

        refresh_time = 180  # Refrescar cada 180 segundos

        time.sleep(refresh_time)

        st.rerun()

    else:
        main()

if __name__ == "__main__":
    st.set_page_config(layout="wide", initial_sidebar_state="expanded")

    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    if not st.session_state['logged_in']:
        login()
    else:
        run_main_loop()
