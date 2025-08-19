from datetime import datetime
import http.client
import base64
import hashlib
import json
import time
from urllib.parse import urlparse
from django.conf import settings
import pytz


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
        elif product == 'chip-internacional-israel-premium':
            planList = {
                '500mb-dia': '640425',
                '1gb': '640426',
                '2gb': '640427',
            }
        elif product == 'chip-internacional-tunisia-premium':
            planList = {
                '500mb-dia': '640418',
                '1gb': '640420',
                '2gb': '640424',
            }
        elif product == 'chip-internacional-marrocos-premium':
            planList = {
                '500mb-dia': '640430',
                '1gb': '640431',
                '2gb': '640432',
            }
        elif product == 'chip-internacional-egito-premium':
            planList = {
                '500mb-dia': '640438',
                '1gb': '640440',
                '2gb': '640442',
            }
        elif product == 'chip-internacional-indonesia-premium':
            planList = {
                '500mb-dia': '640433',
                '1gb': '640434',
                '2gb': '640437',
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

class ApiTI:

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
                '500mb-dia': '866503',
                '1gb': '866507',
                '2gb': '866509',
            }
        elif product == 'chip-internacional-israel-premium':
            planList = {
                '500mb-dia': '640425',
                '1gb': '640426',
                '2gb': '640427',
            }
        elif product == 'chip-internacional-tunisia-premium':
            planList = {
                '500mb-dia': '640418',
                '1gb': '640420',
                '2gb': '640424',
            }
        elif product == 'chip-internacional-marrocos-premium':
            planList = {
                '500mb-dia': '640430',
                '1gb': '640431',
                '2gb': '640432',
            }
        elif product == 'chip-internacional-egito-premium':
            planList = {
                '500mb-dia': '640438',
                '1gb': '640440',
                '2gb': '640442',
            }
        elif product == 'chip-internacional-indonesia-premium':
            planList = {
                '500mb-dia': '640433',
                '1gb': '640434',
                '2gb': '640437',
            }
        else:
            planList = {
                '500mb-dia': '865961',
                '1gb': '864628',
                '2gb': '865963',
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
        token_api = ApiTI.get_token()
        payload = ''
        headers = ApiTI.get_headers(token_api)
        london_tz = pytz.timezone("Europe/London")
        dateToday = datetime.now(london_tz).strftime("%Y%m%d")
        time.sleep(0.5)
        # Obter EndPointID
        endPointId = ApiTI.get_iccid(iccid, headers)
        
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
    
    @staticmethod
    def mobileData(iccid):
        url_api = f'{settings.APICM_URL}/aep/APP_getSubscriberAllQuota_SBO/v1'
        parsed_url = urlparse(url_api)
        app_key = settings.APICM_KEY
        app_secret = settings.APICM_SECRET
        api_token = apiCM.get_token()
        
        # Gerar data atual
        london_tz = pytz.timezone("Europe/London")
        date_today = datetime.now(london_tz).strftime("%Y%m%d")

        # Gerar PasswordDigest
        nonce, created, password_digest = apiCM.generate_password_digest(app_secret)

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
            "himsi":"",
            "iccid": iccid,
            "beginTime": date_today,
            "endTime": date_today,
            "childOrderId":"",
            "thirdOrderId":"",
            "ext":""
        })

        # Fazer a requisição POST com tempo limite
        try:
            conn = http.client.HTTPSConnection(parsed_url.hostname, parsed_url.port, timeout=100)
            conn.request("POST", parsed_url.path, payload, headers)
            res = conn.getresponse()

            # Verificar o status da resposta
            if res.status == 200:
                data = res.read()
                try:
                    data_dict = json.loads(data)
                    # Extrair dados de uso se existirem
                    mobile_data = data_dict
                    print(f">>>>>>>>>>>>>>>>>>>> mobile_data: {mobile_data}")                    
                    return mobile_data
                except json.JSONDecodeError:
                    print(f"Erro ao decodificar JSON: {data}")
                    return 0
            else:
                print(f"Erro na API: Status {res.status}")
                return 0
                
        except Exception as e:
            print(f"Erro ao conectar com API CM: {e}")
            return 0
        finally:
            if 'conn' in locals():
                conn.close()
        
        # # Resultado
        # print(f">>>>>>>>>>>>>>>>>>> Status da resposta: {data}")
        # return data
        

