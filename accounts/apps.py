from django.apps import AppConfig

class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        """
        accounts 앱이 준비되는 시점에 signals.py를 로드합니다.
        이렇게 해야 유저 생성 시 가계부를 생성하는 Signal 로직이 정상적으로 등록 및 동작합니다.
        """
        import accounts.signals
