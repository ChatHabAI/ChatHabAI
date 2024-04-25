import aiohttp
import json
from requests.auth import _basic_auth_str
from utils import generate_unique_filename

from config import YOUKASSA_SECRET_KEY, YOUKASSA_SHOP_ID, YOUKASSA_RETURN_URL

async def create_payment(tariff):
    try:
        headers = {
            "Authorization": _basic_auth_str(YOUKASSA_SHOP_ID, YOUKASSA_SECRET_KEY),
            "Idempotence-Key": generate_unique_filename(''),
            "Content-Type": "application/json",
        }

        url = "https://api.yookassa.ru/v3/payments"
        
        result = None
        price = f'{tariff["price"]}.00'

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url=url,
                headers=headers,
                json={
                    "amount": {
                      "value": price,
                      "currency": "RUB"
                    },
                    "capture": True,
                    "confirmation": {
                      "type": "redirect",
                      "return_url": YOUKASSA_RETURN_URL
                    },
                    "receipt": {
                        "customer": {
                            "email": "123456789@gmail.com"
                        },
                        "items": [
                            {
                                "description": tariff["button_text"],
                                "quantity": '1.00',
                                "amount": {
                                    "value": price,
                                    "currency": 'RUB'
                                },
                                "vat_code": 1,
                                "payment_subject": "service",
                                "payment_mode": "full_payment"
                            }
                        ]
                    },
                    "description": tariff["button_text"],
                },
            ) as response:
                result = await response.json()
                print(result)
                
                if response.status != 200:
                    return False

        return [result["confirmation"]["confirmation_url"], result["id"]]

    except Exception as ex:
        print('youkassa create')
        print(ex)
        return False


async def check_payment(payment_id):
    try:
        headers = {
            "Authorization": _basic_auth_str(YOUKASSA_SHOP_ID, YOUKASSA_SECRET_KEY),
            "Idempotence-Key": generate_unique_filename(''),
            "Content-Type": "application/json",
        }

        url = f"https://api.yookassa.ru/v3/payments/{payment_id}"
        
        result = None

        async with aiohttp.ClientSession() as session:
            async with session.get(
                url=url,
                headers=headers,
            ) as response:
                result = await response.json()
                print(result)
                
                if response.status != 200:
                    return False


        return result["status"] == "succeeded"

    except Exception as ex:
        print('youkassa check')
        print(ex)
        return False

