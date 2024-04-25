import asyncio
import os

from copy import deepcopy
from datetime import datetime

from config import AI_REQUEST_TIMEOUT, NOTIFICATION_RECEVIER, NOT_ENOUGH_CREDIT_BALANCE_NOTIFICATION_TEXT, GEMINI_DESCRIPTION_TEXT, PREMIUM_ANIMATIONS_LIMITS_TEXT, LEIAPIX_UNSUPPORTED_CONTENT_TEXT, LEIAPIX_DESCRIPTION_TEXT, PAYMENT_ERROR_TEXT, PAYMENT_NOT_PAID_TEXT, TARIFFS, BUY_TEXT, PREMIUM_START_TEXT, PREMIUM_STATUS_TEXT, PREMIUM_GPT_LIMITS_TEXT, PREMIUM_IMAGES_LIMITS_TEXT, PREMIUM_REFRESH_TEXT, PREMIUM_END_TEXT, LIMIT_ERROR, CHATGPT_SPEECH_TO_TEXT_SUPPORTED_EXTENSIONS, LEONARDO_DESCRIPTION_TEXT, CHATGPT_TEXT_TO_SPEECH_DESCRIPTION_TEXT, CHATGPT_SPEECH_TO_TEXT_WRONG_FORMAT_TEXT, DALLE_DESCRIPTION_TEXT, PRODIA_DESCRIPTION_TEXT, STABLE_DIFFUSION_DESCRIPTION_TEXT, BOT_TOKEN, SPEECH_DIR, UPLOADS_DIR, DEFAULT_PROMP_FOR_VISION, CONNECTION_TO_AI_ERROR_TEXT, CONNECTION_TO_AI_WAIT_TEXT, PROTECT_CONTENT, TEXT_PER_EACH_N_REQUEST_TO_AI, N
from integrations.gpt import ChatGPT
from integrations.youkassa import create_payment, check_payment
from utils import generate_unique_filepath
from project_utils import get_image_url_from_message, get_image_bytes_from_message, init_message_block_content, get_ai_sign
from keyboard_wrapper import Keyboard, Button

CHATGPT4_AI_NAME = "ChatGPT 4 Turbo"

user_cache_by_id = dict()

def add_request_key_to_cahce(user, user_text):
    user_cache_by_id[user.user_id] = user_cache_by_id.get(user.user_id) or []
    request_cache_key = str(datetime.now()) + user_text
    user_cache_by_id[user.user_id].append(request_cache_key)

    return request_cache_key


async def wait_your_turn(request_cache_key, user):
    while True:
        await asyncio.sleep(0.5)
        if user_cache_by_id[user.user_id].index(request_cache_key) == 0:
            break

async def add_N_message_if_needed(self, updated_copy_of_message_block, user):
    user.n = user.n + 1
    user = await updated_copy_of_message_block.db.save(user)

    if N and user.n % N == 0:
        n_request_message_block = deepcopy(self)
        n_request_message_block.text = TEXT_PER_EACH_N_REQUEST_TO_AI
        updated_copy_of_message_block.message_blocks = [deepcopy(updated_copy_of_message_block), n_request_message_block]
        init_message_block_content(updated_copy_of_message_block)

async def update_stat(updated_copy_of_message_block, user, field_name):
    user_day_statistics = await updated_copy_of_message_block.db.get_or_create_user_day_statistics(user.user_id)
    setattr(user_day_statistics, field_name, (getattr(user_day_statistics, field_name) or 0) + 1)

    user_day_statistics = await updated_copy_of_message_block.db.save(user_day_statistics)


async def send_balance_notifty(bot, provider, updated_copy_of_message_block):
    updated_copy_of_message_block.text = CONNECTION_TO_AI_ERROR_TEXT
    notification_recivier = await updated_copy_of_message_block.db.get_user_by_username(NOTIFICATION_RECEVIER)
    await bot.send_message(chat_id=notification_recivier.user_id, protect_content=PROTECT_CONTENT, text=f'{NOT_ENOUGH_CREDIT_BALANCE_NOTIFICATION_TEXT} {provider}')


async def process_text_result(self, updated_copy_of_message_block, user, result, stat_field_name='gpt_4_requests'):
    ai_name = CHATGPT4_AI_NAME if "4" in stat_field_name else "ChatGPT 3.5"
    if 'gemini' in stat_field_name:
        ai_name = 'Gemini'

    sign = get_ai_sign(ai_name)

    user = await updated_copy_of_message_block.db.get_user(user.user_id)
    if type(result) is str:
        updated_copy_of_message_block.text = result

        await update_limits(updated_copy_of_message_block, user)

        await add_N_message_if_needed(self, updated_copy_of_message_block, user)

        await update_stat(updated_copy_of_message_block, user, stat_field_name)
    else:
        updated_copy_of_message_block.text = result['error']

        if 'NOT_ENOUGH_CREDIT_BALANCE' in result['error']:
            await send_balance_notifty(bot, ai_name, updated_copy_of_message_block)

    updated_copy_of_message_block.text += sign

    return user

async def premium_handler(self, user, user_text, user_message, bot, metadata=None):
    updated_copy_of_message_block = deepcopy(self)

    current_date = datetime.now()
    if current_date.day == 1:
        refresh_date = current_date
    else:
        if current_date.month == 12:
            refresh_date = current_date.replace(day=1, month=1, year=current_date.year + 1)
        else:
            refresh_date = current_date.replace(day=1, month=current_date.month+1)

    status = 'Премиум' if user.is_premium else 'Пробный'
    refresh_date = 'Нет' if user.is_premium else refresh_date.strftime('%d.%m.%Y')

    updated_copy_of_message_block.text = f'{PREMIUM_START_TEXT}{PREMIUM_STATUS_TEXT}: <i>{status}</i>\n{PREMIUM_REFRESH_TEXT}: {refresh_date}\n{PREMIUM_GPT_LIMITS_TEXT}: {user.available_gpt_requests}\n{PREMIUM_IMAGES_LIMITS_TEXT}: {user.available_image_requests}\n{PREMIUM_ANIMATIONS_LIMITS_TEXT}: {user.available_animation_requests}\n\n{PREMIUM_END_TEXT}'
    keyboard = []
    for index, tariff in enumerate(TARIFFS):
        keyboard.append([Button(tariff["button_text"], 13, metadata=index)])

    updated_copy_of_message_block.keyboard = Keyboard(keyboard)
    
    return updated_copy_of_message_block

async def buy_handler(self, user, user_text, user_message, bot, metadata):
    updated_copy_of_message_block = deepcopy(self)

    tariff = TARIFFS[int(metadata)]
    updated_copy_of_message_block.text = tariff["description"]

    result = await create_payment(tariff)

    if result:
        keyboard = [
            [Button('Оплатить', url=result[0])],
            [Button('Проверить покупку', 14, metadata=f'{metadata};{result[1]}')]
        ]

        updated_copy_of_message_block.keyboard = Keyboard(keyboard)
    else:
        updated_copy_of_message_block.text = PAYMENT_ERROR_TEXT
    
    return updated_copy_of_message_block

async def check_handler(self, user, user_text, user_message, bot, metadata):
    updated_copy_of_message_block = deepcopy(self)
    updated_copy_of_message_block.text = BUY_TEXT

    tariff_index, payment_id = metadata.split(';')

    paid_payment = await updated_copy_of_message_block.db.get_payment(payment_id)

    if not paid_payment:
        result = await check_payment(payment_id)

        if result:
            tariff = TARIFFS[int(tariff_index)]

            if tariff["type"] == 'gpt':
                if user.is_premium:
                    user.available_gpt_requests += tariff["count"]
                else:
                    user.available_gpt_requests = tariff["count"]
            elif tariff["type"] == 'image':
                if user.is_premium:
                    user.available_image_requests += tariff["count"]
                else:
                    user.available_image_requests = tariff["count"]
            else:
                if user.is_premium:
                    user.available_animation_requests += tariff["count"]
                else:
                    user.available_animation_requests = tariff["count"]
            
            user.is_premium = True
            user = await updated_copy_of_message_block.db.save(user)
            await updated_copy_of_message_block.db.create_payment(payment_id)
        else:
            updated_copy_of_message_block.text = PAYMENT_NOT_PAID_TEXT

    return updated_copy_of_message_block

async def update_limits(updated_copy_of_message_block, user, limits_type='gpt'):
    if limits_type == 'gpt':
        user.available_gpt_requests -= 1
    elif limits_type == 'image':
        user.available_image_requests -= 1
    else:
        user.available_animation_requests -= 1

    await updated_copy_of_message_block.db.save(user)    

async def gpt_text_to_speech_handler(self, user, user_text, user_message, bot, metadata=None):
    updated_copy_of_message_block = deepcopy(self)

    if not user.available_gpt_requests:
        updated_copy_of_message_block.text = LIMIT_ERROR
        return updated_copy_of_message_block

    parts = user_text.split(' ', 1)

    if len(parts) == 1:
        updated_copy_of_message_block.text = CHATGPT_TEXT_TO_SPEECH_DESCRIPTION_TEXT
        
        return updated_copy_of_message_block

    request_cache_key = add_request_key_to_cahce(user, user_text)

    await bot.send_message(chat_id=user.user_id, protect_content=PROTECT_CONTENT, text=CONNECTION_TO_AI_WAIT_TEXT)

    text = parts[1]

    result = False

    try:
        result = await asyncio.wait_for(ChatGPT.text_to_speech(text), timeout=AI_REQUEST_TIMEOUT)
    except asyncio.TimeoutError:
        pass

    await wait_your_turn(request_cache_key, user)

    user = await updated_copy_of_message_block.db.get_user(user.user_id)
    if type(result) is list:
        updated_copy_of_message_block.voice = result

        await update_limits(updated_copy_of_message_block, user)

        await add_N_message_if_needed(self, updated_copy_of_message_block, user)

        await update_stat(updated_copy_of_message_block, user, 'gpt_4_requests')
    else:
        updated_copy_of_message_block.text = result or CONNECTION_TO_AI_ERROR_TEXT

        if type(result) is str and 'NOT_ENOUGH_CREDIT_BALANCE' in result:
            await send_balance_notifty(bot, CHATGPT4_AI_NAME, updated_copy_of_message_block)

    updated_copy_of_message_block.text = (updated_copy_of_message_block.text or '') + get_ai_sign(CHATGPT4_AI_NAME)

    updated_copy_of_message_block.message_in_queue = True
    return updated_copy_of_message_block

async def gpt_speech_to_text_handler(self, user, user_text, user_message, bot, metadata=None):
    updated_copy_of_message_block = deepcopy(self)

    if not user.available_gpt_requests:
        updated_copy_of_message_block.text = LIMIT_ERROR
        return updated_copy_of_message_block

    result = ''
    audio = None
    filepath = ''

    if user_message.voice:
        audio = await bot.get_file(user_message.voice.file_id)
    elif user_message.audio:
        audio = await bot.get_file(user_message.audio.file_id)
    elif user_message.video:
        audio = await bot.get_file(user_message.video.file_id)
    elif user_message.document:
        audio = await bot.get_file(user_message.document.file_id)

    if audio:
        ext = audio.file_path.split('.')[-1]

        if ext in CHATGPT_SPEECH_TO_TEXT_SUPPORTED_EXTENSIONS:
            filepath = generate_unique_filepath(SPEECH_DIR, ext)
            await bot.download_file(audio.file_path, filepath)

    if not filepath:
        updated_copy_of_message_block.text = CHATGPT_SPEECH_TO_TEXT_WRONG_FORMAT_TEXT
        
        return updated_copy_of_message_block

    request_cache_key = add_request_key_to_cahce(user, user_text)

    await bot.send_message(chat_id=user.user_id, protect_content=PROTECT_CONTENT, text=CONNECTION_TO_AI_WAIT_TEXT)

    try:
        result = await asyncio.wait_for(ChatGPT.speech_to_text(filepath), timeout=AI_REQUEST_TIMEOUT)
    except asyncio.TimeoutError:
        result = { 'error': CONNECTION_TO_AI_ERROR_TEXT }

    os.remove(filepath)

    await wait_your_turn(request_cache_key, user)

    user = await process_text_result(self, updated_copy_of_message_block, user, result)

    updated_copy_of_message_block.message_in_queue = True
    return updated_copy_of_message_block

async def gpt_vision_handler(self, user, user_text, user_message, bot, metadata=None):
    updated_copy_of_message_block = deepcopy(self)

    if not user.available_gpt_requests:
        updated_copy_of_message_block.text = LIMIT_ERROR
        return updated_copy_of_message_block

    result = ''
    image_url = await get_image_url_from_message(bot, user_message)

    request_cache_key = add_request_key_to_cahce(user, user_text)

    await bot.send_message(chat_id=user.user_id, protect_content=PROTECT_CONTENT, text=CONNECTION_TO_AI_WAIT_TEXT)

    try:
        result = await asyncio.wait_for(ChatGPT.talk_process_v4_vision(user_text or DEFAULT_PROMP_FOR_VISION, image_url), timeout=AI_REQUEST_TIMEOUT)
    except asyncio.TimeoutError:
        result = { 'error': CONNECTION_TO_AI_ERROR_TEXT }
    

    await wait_your_turn(request_cache_key, user)

    user = await process_text_result(self, updated_copy_of_message_block, user, result)

    updated_copy_of_message_block.message_in_queue = True
    return updated_copy_of_message_block

async def generate_image_handler(self, user, user_text, user_message, bot, provider):
    updated_copy_of_message_block = deepcopy(self)

    parts = user_text.split(' ', 1)

    image_bytes = None
    image_url = None
    ext = ''

    is_dalle = provider == 'dalle3'
    is_prodia = provider == 'prodia'
    is_sd = provider == 'stable_diffusion'
    is_leonardo = provider == 'leonardo'
    is_leiapix = provider == 'leiapix'

    if not user.available_image_requests and not is_leiapix or is_leiapix and not user.available_animation_requests:
        updated_copy_of_message_block.text = LIMIT_ERROR
        return updated_copy_of_message_block

    if is_sd:
        image_bytes, ext = await get_image_bytes_from_message(bot, user_message)
    elif is_leiapix:
        image_url = await get_image_url_from_message(bot, user_message)

    if is_leiapix:
        if not image_url and (len(parts) > 1 or user_message.document or user_message.video or user_message.audio or user_message.voice or user_message.sticker):
            updated_copy_of_message_block.text = LEIAPIX_UNSUPPORTED_CONTENT_TEXT

            return updated_copy_of_message_block

    if len(parts) == 1 and not image_bytes and not image_url:
        if is_sd:
            updated_copy_of_message_block.text = STABLE_DIFFUSION_DESCRIPTION_TEXT
        elif is_dalle:
            updated_copy_of_message_block.text = DALLE_DESCRIPTION_TEXT
        elif is_prodia:
            updated_copy_of_message_block.text = PRODIA_DESCRIPTION_TEXT
        elif is_leonardo:
            updated_copy_of_message_block.text = LEONARDO_DESCRIPTION_TEXT
        elif is_leiapix:
            updated_copy_of_message_block.text = LEIAPIX_DESCRIPTION_TEXT

        return updated_copy_of_message_block



    request_cache_key = add_request_key_to_cahce(user, user_text)

    await bot.send_message(chat_id=user.user_id, protect_content=PROTECT_CONTENT, text=CONNECTION_TO_AI_WAIT_TEXT)

    prompt = parts[1] if len(parts) > 1 else ''

    result = False

    try:
        if is_dalle:
            sign = get_ai_sign('Dalle3')
            result = await asyncio.wait_for(ChatGPT.image_process_dalle3(prompt), timeout=AI_REQUEST_TIMEOUT)
        elif is_prodia:
            sign = get_ai_sign('Prodia')
            result = await asyncio.wait_for(ChatGPT.image_process(prompt), timeout=AI_REQUEST_TIMEOUT)
        elif is_leonardo:
            sign = get_ai_sign('Leonardo')
            result = await asyncio.wait_for(ChatGPT.image_process_leonardo(prompt), timeout=AI_REQUEST_TIMEOUT)
        elif is_leiapix:
            sign = get_ai_sign('LeiaPix')
            result = await asyncio.wait_for(ChatGPT.image_process_leiapix(image_url), timeout=AI_REQUEST_TIMEOUT)
        else:
            sign = get_ai_sign('Stable Diffusion')
            result = await asyncio.wait_for(ChatGPT.image_process_stable_diffusion(prompt, image_bytes, ext), timeout=AI_REQUEST_TIMEOUT)
    except asyncio.TimeoutError:
        pass

    await wait_your_turn(request_cache_key, user)

    user = await updated_copy_of_message_block.db.get_user(user.user_id)
    if type(result) is list or (type(result) is str and 'http' in result):
        if is_leiapix:
            updated_copy_of_message_block.video = result
        else:
            updated_copy_of_message_block.photo = result

        await update_limits(updated_copy_of_message_block, user, limits_type='animation' if is_leiapix else 'image')

        await add_N_message_if_needed(self, updated_copy_of_message_block, user)

        await update_stat(updated_copy_of_message_block, user, f'{provider}_requests')
    else:
        updated_copy_of_message_block.text = result or CONNECTION_TO_AI_ERROR_TEXT

        if type(result) is str and 'NOT_ENOUGH_CREDIT_BALANCE' in result:
            await send_balance_notifty(bot, provider, updated_copy_of_message_block)

    updated_copy_of_message_block.text = (updated_copy_of_message_block.text or '') + sign

    updated_copy_of_message_block.message_in_queue = True
    return updated_copy_of_message_block

async def stable_diffusion_handler(self, user, user_text, user_message, bot, metadata=None):
    return await generate_image_handler(self, user, user_text, user_message, bot, 'stable_diffusion')

async def dalle3_handler(self, user, user_text, user_message, bot, metadata=None):
    return await generate_image_handler(self, user, user_text, user_message, bot, 'dalle3')

async def prodia_handler(self, user, user_text, user_message, bot, metadata=None):
    return await generate_image_handler(self, user, user_text, user_message, bot, 'prodia')

async def leonardo_handler(self, user, user_text, user_message, bot, metadata=None):
    return await generate_image_handler(self, user, user_text, user_message, bot, 'leonardo')

async def leiapix_handler(self, user, user_text, user_message, bot, metadata=None):
    return await generate_image_handler(self, user, user_text, user_message, bot, 'leiapix')

async def gemini_handler(self, user, user_text, user_message, bot, metadata=None):
    return await text_to_text_handler(self, user, user_text, user_message, bot, metadata, 'gemini')

async def text_to_text_handler(self, user, user_text, user_message, bot, metadata=None, provider=''):
    updated_copy_of_message_block = deepcopy(self)

    if not user.available_gpt_requests:
        updated_copy_of_message_block.text = LIMIT_ERROR
        return updated_copy_of_message_block

    is_gemini = provider == 'gemini'

    parts = user_text.split(' ', 1)

    if is_gemini and len(parts) == 1:
        updated_copy_of_message_block.text = GEMINI_DESCRIPTION_TEXT

        return updated_copy_of_message_block

        prompt = parts[1]

    request_cache_key = add_request_key_to_cahce(user, user_text)

    await bot.send_message(chat_id=user.user_id, protect_content=PROTECT_CONTENT, text=CONNECTION_TO_AI_WAIT_TEXT)

    result = ''
    is_user_select_gpt_4 = '4' in user.gpt_version

    try:
        if is_gemini:
            prompt = parts[1]

            result = await asyncio.wait_for(ChatGPT.talk_process_gemini(prompt), timeout=AI_REQUEST_TIMEOUT)
        elif is_user_select_gpt_4:
            result = await asyncio.wait_for(ChatGPT.talk_process_v4(user_text), timeout=AI_REQUEST_TIMEOUT)
        else:
            result = await asyncio.wait_for(ChatGPT.talk_process(user_text), timeout=AI_REQUEST_TIMEOUT)

    except asyncio.TimeoutError:
        result = { 'error': CONNECTION_TO_AI_ERROR_TEXT }

    await wait_your_turn(request_cache_key, user)

    if provider:
        provider += '_requests'

    user = await process_text_result(self, updated_copy_of_message_block, user, result, provider or ('gpt_4_requests' if is_user_select_gpt_4 else 'gpt_35_requests'))

    updated_copy_of_message_block.message_in_queue = True
    return updated_copy_of_message_block
