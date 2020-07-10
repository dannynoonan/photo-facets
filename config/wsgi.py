"""
WSGI config for photo-facets project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.0/howto/deployment/wsgi/
"""

import os
from django.core.wsgi import get_wsgi_application
from dj_static import Cling

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.heroku')

# application = get_wsgi_application()
# https://stackoverflow.com/questions/22007428/error-r10-boot-timeout-django-app-on-heroku
application = Cling(get_wsgi_application())
