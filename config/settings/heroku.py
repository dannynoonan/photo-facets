from .base import *


import dj_database_url
import psycopg2


# Database
# https://docs.djangoproject.com/en/3.0/ref/settings/#databases
DATABASES = {}
DATABASES['default'] = dj_database_url.config(conn_max_age=600, ssl_require=True)


# Postgresql 
# https://devcenter.heroku.com/articles/heroku-postgresql
HEROKU_POSTGRESQL_BRONZE_URL = os.environ['HEROKU_POSTGRESQL_BRONZE_URL']
conn = psycopg2.connect(HEROKU_POSTGRESQL_BRONZE_URL, sslmode='require')

