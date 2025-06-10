import http.client
import json
import time
import pytz
import base64
import hashlib
from datetime import datetime, timedelta
from urllib.parse import urlparse
from unittest import result
from django.conf import settings


class ApiTC:

    # Get tokem de acesso a API
    @staticmethod
    def get_token():
        time.sleep(0.5)

        payload_token = json.dumps({
            "username": settings.APITC_USERNAME,
            "password": settings.APITC_PASSWORD
        })
        
        headers_token = {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
        }
        conn = http.client.HTTPSConnection(settings.APITC_HTTPCONN)
        conn.request("POST", "/api/login", payload_token, headers_token)
        res_token = conn.getresponse()
        data_token = json.loads(res_token.read())
        token_api = data_token["AccessToken"]
        conn.close()
        return token_api


    # Set headers
    @staticmethod    
    def get_headers(token_api, cookie=None):
        headers = {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
            'X-Authorization': f'Bearer {token_api}'
        }
        if cookie is None:
            headers['Cookie'] = 'Encrypt_cookies=rd20o00000000000000000000ffff0af30e15o12021'
        return headers


    # Get EndPointID / Status
    @staticmethod
    def get_iccid(iccid, headers):
        payload_endpointId = ''
        conn = http.client.HTTPSConnection(settings.APITC_HTTPCONN)
        conn.request(
            "GET", f"/api/fetchSIM?iccid={iccid}", payload_endpointId, headers)
        res_endpointId = conn.getresponse()
        data_endpointId = json.loads(res_endpointId.read())
        simStatus = data_endpointId["Response"]["responseParam"]["rows"][0]['simStatus']
        endpointId = data_endpointId["Response"]["responseParam"]["rows"][0]['endPointId']
        conn.close()
        return endpointId, simStatus


    # Pl0an Change
    @staticmethod
    def planChange(endpointId,headers,dataDay,product):
        planList = {}
        if product == 'chip-internacional-america-do-sul' or product == 'chip-internacional-america-do-sul-premium':
            planList = {
                '500mb-dia': '607128',
                '1gb': '607131',
                '2gb': '607132',
            }
        else:
            planList = {
                '500mb-dia': '572960',
                '1gb': '572961',
                '2gb': '572963',
            }
        plan_list = json.loads(planList[dataDay])       
        payload = json.dumps({
            "Request": {
                "endPointId": endpointId,
                "requestParam": {
                    "planId": plan_list
                }
            }
        })
        
        conn = http.client.HTTPSConnection(settings.APITC_HTTPCONN)
        conn.request("POST", "/api/ChangePlan", payload, headers)
        res_plan = conn.getresponse()
        data_plan = res_plan.read()
        conn.close()
        return data_plan
    
    @staticmethod
    def mobileData(iccid):
        # Gerar token de acesso a API
        token_api = ApiTC.get_token()
        payload = ''
        headers = ApiTC.get_headers(token_api)
        london_tz = pytz.timezone("Europe/London")
        dateToday = datetime.now(london_tz).strftime("%Y%m%d")
        time.sleep(0.5)
        # Obter EndPointID
        endPointId = ApiTC.get_iccid(iccid, headers)
        
        time.sleep(0.5)
        # Obter dados de uso
        conn = http.client.HTTPSConnection(settings.APITC_HTTPCONN)    
        conn.request("GET", f"/api/GetStatistics?endPointId={endPointId[0]}&from_date={dateToday}&to_date={dateToday}", payload, headers)
        res = conn.getresponse()
        data_endpointId = json.loads(res.read())
        try:
            if data_endpointId["Response"]["responseParam"]["dataUsage"][0]['totalVolume'] is None:
                mobile_data = 0
            else:
                mobile_data = data_endpointId["Response"]["responseParam"]["dataUsage"][0]['totalVolume']
        except IndexError:
            # Caso não haja dados de uso, retornar 0
            mobile_data = 0
        except KeyError:
            # Caso a chave não exista, retornar 0
            mobile_data = 0
        
        conn.close()
        return mobile_data

class apiCM:
    
    @staticmethod    
    def generate_password_digest(app_secret):
        
        nonce = str(int(time.time() * 1000))
        created = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        digest = base64.b64encode(hashlib.sha256((nonce + created + app_secret).encode('utf-8')).digest()).decode('utf-8')
        return nonce, created, digest
    
    @staticmethod
    def get_token():

        # URL do endpoint
        url_api = f'{settings.APICM_URL}/aep/APP_getAccessToken_SBO/v1'
        parsed_url = urlparse(url_api)
        app_key = settings.APICM_KEY
        app_secret = settings.APICM_SECRET

        # Gerar PasswordDigest
        nonce, created, password_digest = apiCM.generate_password_digest(app_secret)

        # Corpo da requisição
        payload = json.dumps({
            "id": app_key,
            "type": "106",
        })

        # Cabeçalhos da requisição
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": 'WSSE realm="SDP", profile="UsernameToken", type="Appkey"',
            "X-WSSE": f'UsernameToken Username="{app_key}", PasswordDigest="{password_digest}", Nonce="{nonce}", Created="{created}"',
        }

        conn = http.client.HTTPSConnection(parsed_url.hostname, parsed_url.port, timeout=10)
        conn.request("POST", parsed_url.path, payload, headers)
        res = conn.getresponse()
        data = res.read()
                
        # Verificar status da requisição        
        if res.status != 200:
            result_token = 'error'
        else:
            try:
                if data:
                    data_dict = json.loads(data)
                    result_token = data_dict.get('accessToken')
                else:
                    result_token = 'error: resposta vazia'
            except json.JSONDecodeError:
                result_token = 'error: JSON malformado'

        conn.close()
            
        return result_token
    
    def mobileData(iccid):        
        # URL do endpoint
        print(f">>>>> Obtendo dados de uso para o ICCID: {iccid} <<<<<")
        url_api = f'{settings.APICM_URL}/aep/APP_getSubscriberAllQuota_SBO/v1'
        parsed_url = urlparse(url_api)
        app_key = settings.APICM_KEY
        app_secret = settings.APICM_SECRET
        api_token = apiCM.get_token()
        london_tz = pytz.timezone("Europe/London")
        date_today = datetime.now(london_tz)
        dateToday = date_today - timedelta(days=1).strftime("%Y%m%d")
        data_start = date_today - timedelta(days=4)
        dataStart = data_start.strftime("%Y%m%d")
        

        # Gerar PasswordDigest
        nonce, created, password_digest = apiCM.generate_password_digest(app_secret)
        print(f">>>>> Nonce: {nonce}, Created: {created}, Password Digest: {password_digest} <<<<<")

        # Cabeçalhos da requisição
        headers = {
            'Content-Type': 'application/json',
            "Accept": "application/json",
            "Authorization": 'WSSE realm="SDP", profile="UsernameToken", type="Appkey"',
            "X-WSSE": f'UsernameToken Username="{app_key}", PasswordDigest="{password_digest}", Nonce="{nonce}", Created="{created}"',
        }

        # Corpo da requisição
        payload = json.dumps({
            "accessToken": api_token,
            "iccid": iccid,
            "beginTime": dataStart,
            "endTime": dateToday,
        })
        
        # Fazer a requisição POST com tempo limite
        try:
            conn = http.client.HTTPSConnection(parsed_url.hostname, parsed_url.port, timeout=100)
            conn.request("POST", parsed_url.path, payload, headers)
            res = conn.getresponse()
            # Verificar o status da resposta
            data = res.read()
            print(f">>>>> Status da resposta: {res.status}")
        except TimeoutError as e:
            print(f">>>>> Erro ao conectar: {e}")
        except Exception as e:
            print(f">>>>> Erro ao conectar: {e}")
        finally:
            conn.close()
            
        # Verificar status da requisição        
        if res.status != 200:
            result_data = 0.0
        else:
            try:
                if data:
                    data_dict = json.loads(data)
                    print(f">>>>> Resposta da API Json: {data_dict}")                   
                    # Verifica se a chave 'historyQuota' existe e não é None
                    if isinstance(data_dict['historyQuota'], list) and len(data_dict['historyQuota']) > 0:
                        # Se for uma lista e não estiver vazia, pega o primeiro elemento
                        result_data = data_dict['historyQuota'][0]
                        print(f">>>>> Dados de uso obtidos: {result_data}")
                    else:
                        result_data = [0.0]
                        print(f">>>>> Dados de uso não encontrados ou inválidos: {result_data}")
                else:
                    result_data = [0.0]
            except json.JSONDecodeError:
                result_data = [0.0]
        
        return result_data
        