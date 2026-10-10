import os
import webbrowser
from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = 'accounts'

    def ready(self):
        if os.environ.get('RUN_MAIN') == 'true':
            try:
                webbrowser.open('http://127.0.0.1:8000/admin-dashboard/')
            except webbrowser.Error:
                pass