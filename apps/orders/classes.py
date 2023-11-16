from woocommerce import API
import os

# Conect woocommerce api
class ApiStore():
    @staticmethod
    def conectApiStore():
        wcapi = API(
            url = str(os.getenv('url_site')),
            consumer_key = str(os.getenv('consumer_key')),
            consumer_secret = str(os.getenv('consumer_secret')),
            wp_api = True,
            version = 'wc/v3',
            timeout = 5000
        )
        return wcapi

class StatusSis():
    def st_sis_site():
        status_sis_site = {
            'AE': 'agd-envio',
            'AS': 'em-separacao',
            'AA': 'agd-ativacao',        
            'CC': 'cancelled',
            'ES': 'em-separacao',
            'MB': 'motoboy',
            'RS': 'reuso',
            'RT': 'retirada',
            'RE': 'reembolsar',
            'CN': 'completed',        
        }
        return status_sis_site