from .base import *


import dj_database_url
import psycopg2


# Database
# https://docs.djangoproject.com/en/3.0/ref/settings/#databases
DATABASES['default'] = dj_database_url.config(conn_max_age=600, ssl_require=True)


# Postgresql 
# https://devcenter.heroku.com/articles/heroku-postgresql
DATABASE_URL = os.environ['DATABASE_URL']
conn = psycopg2.connect(DATABASE_URL, sslmode='require')

