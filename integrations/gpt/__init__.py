import base64
import requests
import aiohttp
import asyncio
import openai
import json
import uuid
import time
import re
import os

from aiobotocore.session import get_session

from translate import Translator

from freeGPT import AsyncClient
from PIL import Image
from io import BytesIO

from openai import AsyncOpenAI
from utils import generate_unique_filename, generate_unique_filepath
from config import GEMINI_CENSURE_TEXT, GOOGLE_AI_STUDIO_API_KEY, LEIA_CLIENT_ID, LEIA_CLIENT_SECRET, AWS_KEY_ID, AWS_SECRET_KEY, S3_BUCKET_NAME, S3_BUCKET_REGION, LEO_CENSURE_TEXT, LEONARDO_AI_API_KEY, LEONARDO_AI_MODEL_ID, OPENAI_API_KEY, STABLE_DIFFUSION_API_KEY, PHOTOS_DIR, SPEECH_DIR, STABLE_DIFFUSION_CENSURE_TEXT, CENSURE_TEXT, CONNECTION_TO_GPT35FREE_ERROR_TEXT, CONNECTION_TO_AI_ERROR_TEXT


client = AsyncOpenAI(
        api_key = OPENAI_API_KEY,
    )


def translate_ru_promt_if_needed(prompt):
    if prompt and re.search(r'[а-яА-я]', prompt):
        translator = Translator(from_lang="ru", to_lang="en")
        prompt = translator.translate(prompt)

    return prompt

class ChatGPT:
    @staticmethod
    async def talk_process_gemini(prompt):
        try:
            headers = {
                "Content-Type": "application/json",
                "x-goog-api-key": GOOGLE_AI_STUDIO_API_KEY,
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url='https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent',
                    headers=headers,
                    json={
                        "contents":[
                            {
                                "role": "user",
                                "parts":[{"text": prompt}]
                            }
                        ]
                    },
                ) as response:
                    result = await response.json()

                    if response.status != 200:
                        print(result)
                        return {'error': CONNECTION_TO_AI_ERROR_TEXT}

                    promptFeedback = result.get("promptFeedback", {})
                    if promptFeedback.get("blockReason", '') == 'SAFETY':
                        return {'error': GEMINI_CENSURE_TEXT}

            return result["candidates"][0]["content"]["parts"][0]["text"]

        except Exception as ex:
            print('GOOGLE TEXT TO TEXT')
            print(ex)
            print(result)
            return {'error': CONNECTION_TO_AI_ERROR_TEXT}

    @staticmethod
    async def image_process_leiapix(image_url=None):
        try:
            session = get_session()
            async with session.create_client('s3', region_name=S3_BUCKET_REGION, aws_secret_access_key=AWS_SECRET_KEY, aws_access_key_id=AWS_KEY_ID) as s3:
                async def get_presigned_url(key, method):
                    return await s3.generate_presigned_url(ClientMethod=method, Params={'Bucket': S3_BUCKET_NAME, 'Key': key}, ExpiresIn=3 * 60)

                access_token = None

                url = 'https://api.leiapix.com/api/v1'

                headers = {
                    "content-Type": "application/json",
                    "accept": "application/json",
                }

                result = None

                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        url='https://auth.leialoft.com/auth/realms/leialoft/protocol/openid-connect/token',
                        data={
                            'client_id': LEIA_CLIENT_ID,
                            'client_secret': LEIA_CLIENT_SECRET,
                            'grant_type': 'client_credentials'
                        },
                    ) as response:
                        result = await response.json()

                        if response.status != 200:
                            print(result)
                            return False

                        access_token = result['access_token']

                    ext = image_url.split('.')[-1]
                    disparity_file_name = generate_unique_filename(ext)

                    headers["Authorization"] = f'Bearer {access_token}'

                    async with session.post(
                        url= f'{url}/disparity',
                        headers=headers,
                        json={
                            'correlationId': str(uuid.uuid4()),
                            'inputImageUrl': image_url,
                            'resultPresignedUrl': await get_presigned_url(disparity_file_name, 'put_object')
                        },
                    ) as response:
                        result = await response.json()

                        if response.status == 402 or result.get('errorCode', '') == 'NOT_ENOUGH_CREDIT_BALANCE':
                            return "NOT_ENOUGH_CREDIT_BALANCE"

                        if response.status != 200 and response.status != 201:
                            print(result)
                            return False

                    animation_file_name = generate_unique_filename('mp4')

                    async with session.post(
                        url= f'{url}/animation',
                        headers=headers,
                        json={
                            'correlationId': str(uuid.uuid4()),
                            'inputImageUrl': image_url,
                            'inputDisparityUrl': await get_presigned_url(disparity_file_name, 'get_object'),
                            'resultPresignedUrl': await get_presigned_url(animation_file_name, 'put_object'),
                            'animationLength': 5
                        },
                    ) as response:
                        result = await response.json()

                        if response.status == 402 or result.get('errorCode', '') == 'NOT_ENOUGH_CREDIT_BALANCE':
                            return "NOT_ENOUGH_CREDIT_BALANCE"

                        if response.status != 200 and response.status != 201:
                            print(result)
                            return False

                    await s3.delete_object(Bucket=S3_BUCKET_NAME, Key=disparity_file_name)

                return await get_presigned_url(animation_file_name, 'get_object')

        except Exception as ex:
            print('LEIAPIX')
            print(ex)
            return False

    @staticmethod
    async def image_process_leonardo(prompt=None):
        try:
            prompt = translate_ru_promt_if_needed(prompt)

            headers = {
                "authorization": f'Bearer {LEONARDO_AI_API_KEY}',
                "content-Type": "application/json",
                "accept": "application/json",
            }

            url = "https://cloud.leonardo.ai/api/rest/v1/generations"
            
            result = None
            generationId = None
            generated_images = []

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url=url,
                    headers=headers,
                    json={
                        "height": 1024,
                        "width": 1024,
                        "modelId": LEONARDO_AI_MODEL_ID,
                        "prompt": prompt,
                        "num_images": 1,
                    },
                ) as response:
                    result = await response.json()

                    if 'not enough api tokens' in result.get('error', ''):
                        return "NOT_ENOUGH_CREDIT_BALANCE"

                    if 'content moderation filter' in result.get("error", ''):
                        return LEO_CENSURE_TEXT

                    generationId = result["sdGenerationJob"]["generationId"]

                    if response.status != 200:
                        return False

                while True:
                    await asyncio.sleep(6)

                    async with session.get(
                        url=f'{url}/{generationId}',
                        headers=headers,
                    ) as response:
                        result = await response.json()

                        if 'not enough api tokens' in result.get('error', ''):
                            return "NOT_ENOUGH_CREDIT_BALANCE"

                        if response.status != 200:
                            return False

                        if result["generations_by_pk"]:
                            generated_images = result["generations_by_pk"]["generated_images"]
                            if len(generated_images):
                                break
            
            return generated_images[0]["url"]

        except Exception as ex:
            print('LEO')
            print(ex)
            return False

    @staticmethod
    async def image_process_stable_diffusion(prompt=None, image_bytes=None, ext=None):
        try:
            prompt = translate_ru_promt_if_needed(prompt)

            headers = {
                "Accept": "application/json",
                "Authorization": f"Bearer {STABLE_DIFFUSION_API_KEY}"
            }

            engine_id = 'stable-diffusion-xl-1024-v1-0' if image_bytes else 'stable-diffusion-v1-6'
            url = f"https://api.stability.ai/v1/generation/{engine_id}/{'image' if image_bytes else 'text'}-to-image"
            
            result = None

            async with aiohttp.ClientSession() as session:
                if image_bytes:
                    with Image.open(image_bytes) as image:
                        data = {
                            "image_strength": 0.20,
                            "init_image_mode": "IMAGE_STRENGTH",
                            "text_prompts[0][text]": prompt or '.',
                            "text_prompts[0][weight]": 1 if prompt else 0,
                            "cfg_scale": 35,
                            "samples": 1,
                            "steps": 30,
                        }

                        form = aiohttp.FormData()

                        supported_dimensions = [
                            [1024, 1024],
                            [1152, 896],
                            [1216, 832],
                            [1344, 768],
                            [1536, 640],
                            [640, 1536],
                            [768, 1344],
                            [832, 1216],
                            [896, 1152],
                        ]

                        size_is_supported = False

                        for dimensions in supported_dimensions:
                            if image.size[0] == dimensions[0] and image.size[1] == dimensions[1]:
                                size_is_supported = True

                        if not size_is_supported:
                            resized_image = image.resize(supported_dimensions[0])

                            resized_image_bytes = BytesIO()
                            resized_image.save(resized_image_bytes, format=image.format)
                            image_bytes = resized_image_bytes

                        part = form.add_field('init_image', image_bytes.getvalue())
                        for key, value in data.items():
                            form.add_field(key, str(value))

                        async with session.post(
                            url=url,
                            headers=headers,
                            data=form
                        ) as response:
                            result = await response.json()

                            if response.status != 200:
                                if result["name"] == 'invalid_prompts':
                                    return STABLE_DIFFUSION_CENSURE_TEXT
                                print(result)
                                return False
                            
                else:
                    headers["Content-Type"] = "application/json"

                    async with session.post(
                        url=url,
                        headers=headers,
                        json={
                            "text_prompts": [
                                {
                                    "text": prompt
                                }
                            ],
                            "cfg_scale": 7,
                            "height": 1024,
                            "width": 1024,
                            "samples": 1,
                            "steps": 30,
                        },
                    ) as response:
                        result = await response.json()

                        if response.status != 200:
                            if result["name"] == 'invalid_prompts':
                                return STABLE_DIFFUSION_CENSURE_TEXT
                            elif result["name"] == 'insufficient_balance':
                                return "NOT_ENOUGH_CREDIT_BALANCE"
                                
                            print(result)
                            return False
            
            return [BytesIO(base64.b64decode(result["artifacts"][0]["base64"])).getvalue(), 'buffer', generate_unique_filename(ext)]

        except Exception as ex:
            print('SD')
            print(ex)
            print(result)
            return False


    @staticmethod
    async def speech_to_text(filepath):
        try:
            try:
                transcript = None

                with open(filepath, 'rb') as audio_file:
                    transcript = await client.audio.transcriptions.create(
                      model="whisper-1", 
                      file=audio_file
                    )
                
                return transcript.text
            except openai.APIError as ex:
                if 'quota' in ex.message:
                    return {'error': "NOT_ENOUGH_CREDIT_BALANCE"}
                else:
                    raise ex

        except Exception as ex:
            print('speech_to_text')
            print(ex)
            if 'content_policy_violation' in str(ex):
                return {'error': CENSURE_TEXT}

            return {'error': CONNECTION_TO_AI_ERROR_TEXT}

    @staticmethod
    async def text_to_speech(text):
        try:
            try:
                filepath = generate_unique_filepath(SPEECH_DIR, 'ogg')
                response = await client.audio.speech.create(
                    model="tts-1",
                    voice="alloy",
                    input=text,
                    response_format="opus",
                )

                response.stream_to_file(filepath)

                return [filepath, 'filepath']
            except openai.APIError as ex:
                if 'quota' in ex.message:
                    return "NOT_ENOUGH_CREDIT_BALANCE"
                else:
                    raise ex

        except Exception as ex:
            print('text_to_speech')
            print(ex)
            if 'content_policy_violation' in str(ex):
                return CENSURE_TEXT

            return CONNECTION_TO_AI_ERROR_TEXT

    @staticmethod
    async def talk_process_v4_vision(prompt, image_url):
        try:
            try:
                completion = await client.chat.completions.create(
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                  "type": "image_url",
                                  "image_url": {
                                    "url": image_url,
                                  },
                                },
                            ],
                        }
                    ],
                    model="gpt-4-vision-preview",
                    max_tokens=600
                )
                return completion.choices[0].message.content
            except openai.APIError as ex:
                if 'quota' in ex.message:
                    return {'error': "NOT_ENOUGH_CREDIT_BALANCE"}
                else:
                    raise ex

        except Exception as ex:
            print('v4 vision')
            print(ex)
            if 'content_policy_violation' in str(ex):
                return {'error': CENSURE_TEXT}

            return {'error': CONNECTION_TO_AI_ERROR_TEXT}

    @staticmethod
    async def talk_process_v4(prompt):
        try:
            try:
                completion = await client.chat.completions.create(
                    messages=[
                        {
                            "role": "user",
                            "content": prompt,
                        }
                    ],
                    model="gpt-4-1106-preview",
                )
                
                return completion.choices[0].message.content
            except openai.APIError as ex:
                if 'quota' in ex.message:
                    return {'error': "NOT_ENOUGH_CREDIT_BALANCE"}
                else:
                    raise ex

        except Exception as ex:
            print('v4')
            print(ex)
            if 'content_policy_violation' in str(ex):
                return {'error': CENSURE_TEXT}

            return {'error': CONNECTION_TO_AI_ERROR_TEXT}

    @staticmethod
    async def talk_process(prompt):
        try:
            resp = await AsyncClient.create_completion("gpt3", prompt)
            if 'Gateway Time-out' in resp or 'https://chat18.aichatos.xyz' in resp:
                return {'error': CONNECTION_TO_GPT35FREE_ERROR_TEXT}

            return resp
        except Exception as ex:
            print('v3.5')
            print(ex)
            return {'error': CONNECTION_TO_AI_ERROR_TEXT}

    @staticmethod
    async def image_process_dalle3(prompt):
        try:
            try:
                response = await client.images.generate(
                    model="dall-e-3",
                    prompt=prompt,
                    size="1024x1024",
                    quality="standard",
                    n=1,
                )

                return response.data[0].url
            except openai.APIError as ex:
                if 'quota' in ex.message:
                    return "NOT_ENOUGH_CREDIT_BALANCE"
                else:
                    raise ex


        except Exception as ex:
            print('dalle')
            print(ex)
            if 'content_policy_violation' in str(ex):
                return CENSURE_TEXT

            return False

    @staticmethod
    async def image_process(prompt):
        try:
            prompt = translate_ru_promt_if_needed(prompt)

            resp = await AsyncClient.create_generation("prodia", prompt)
            
            return [BytesIO(resp).getvalue(), 'buffer', generate_unique_filename('jpg')]

        except Exception as ex:
            print('prodia')
            print(ex)
            return False

