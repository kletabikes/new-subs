from dotenv import load_dotenv
import os

load_dotenv()

# Variables de Ninox
NINOX_API_KEY = os.getenv('NINOX_API_KEY')
NINOX_API_ENDPOINT = os.getenv('NINOX_API_ENDPOINT')
NINOX_TEAM_ID = os.getenv('NINOX_TEAM_ID')
NINOX_DATABASE_ID = os.getenv('NINOX_DATABASE_ID')
TABLE_NAME = 'SUBSCRIPTIONS'

# Variables de GitHub
GITHUB_USERNAME = os.getenv('GITHUB_USERNAME')
GITHUB_EMAIL = os.getenv('GITHUB_EMAIL')
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
REPO_NAME = os.getenv('REPO_NAME')
