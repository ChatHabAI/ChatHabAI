from aiogram.types import (
    KeyboardButton,
    ReplyKeyboardMarkup,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    FSInputFile,
    BufferedInputFile,
)

from utils import replace_placeholders_in_text, generate_unique_filepath
from telegram_limits import MAX_MESSAGE_TEXT_LENGTH
from config import BOT_TOKEN, PHOTOS_DIR, BOT_NAME

def get_ai_sign(ai_name):
    return f'\n\n@{BOT_NAME} - <b>{ai_name}</b>'

def init_message_block_content(message_block, text='', photo=None, voice=None, video=None, audio=None, animation=None, documents=list(), keyboard=None):
    message_block.text = text
    message_block.photo = photo # file_id or url
    message_block.voice = voice # file_id or url
    message_block.audio = audio # file_id or url
    message_block.video = video # file_id or url
    message_block.animation = animation # file_id or url
    message_block.documents = documents # file_id or url
    message_block.keyboard = keyboard

def get_largest_photo(message):
    return message.photo[-1]

async def get_image_from_message(bot, message):
    image = None

    if message.photo:
        image = await bot.get_file(get_largest_photo(message).file_id)
    elif message.document and 'image' in message.document.mime_type:
        image = await bot.get_file(message.document.file_id)

    return image

async def get_image_bytes_from_message(bot, message):
    image = await get_image_from_message(bot, message)
    image_bytes = None
    ext = ''

    if image:
        ext = image.file_path.split('.')[-1]
        image_bytes = await bot.download_file(image.file_path)

    return [image_bytes, ext]

async def get_image_filepath_from_message(bot, message):
    image = await get_image_from_message(bot, message)
    image_filepath = ''

    if image:
        ext = image.file_path.split('.')[-1]
        image_filepath = generate_unique_filepath(PHOTOS_DIR, ext)
        await bot.download_file(image.file_path)

    return image_filepath

async def get_image_url_from_message(bot, message):
    image = await get_image_from_message(bot, message)
    image_url = ''

    if image:
        image_url = f'https://api.telegram.org/file/bot{BOT_TOKEN}/{image.file_path}'

    return image_url

def split_message_block_to_message_blocks(message_block):
    message_blocks = []

    for i in range(0, len(message_block.text), MAX_MESSAGE_TEXT_LENGTH):
        m_b = deepcopy(message_block)
        m_b.link = None
        m_b.text = text[i:i + MAX_MESSAGE_TEXT_LENGTH]

        message_blocks.append(m_b)

    return message_blocks
    
def prepare_text(text, user):
    return replace_placeholders_in_text(text, user, 'user')

def is_keyboard_contains_link(keyboard):
    if keyboard and keyboard.one_time_keyboard:
        for row in keyboard.keyboard:
            for button in row:
                if button.message_block_id:
                    return True

    return False

def prepare_keyboard(message_block, user):
    keyboard = message_block.keyboard

    inline = keyboard.inline
    prepared_keyboard = []
    for row in keyboard.keyboard:
        prepared_row = []
        for button in row:
            text = prepare_text(button.text, user)

            if inline:
                callback_data = f'button:{button.message_block_id}'
                
                if message_block.keyboard.custom_type == 'radio_button':
                    callback_data = f'{keyboard.custom_type}:{message_block.id}:{text}'

                    if text == getattr(user, keyboard.radio_button_param, ''):
                        text = '✔' + text
                elif button.metadata:
                    callback_data += f':{button.metadata}'

                if button.url:
                    prepared_button = InlineKeyboardButton(text=text, url=button.url)
                else:
                    prepared_button = InlineKeyboardButton(text=text, callback_data=callback_data)
            else:
                prepared_button = KeyboardButton(text=text)
            
            prepared_row.append(prepared_button)

        prepared_keyboard.append(prepared_row)

    if inline:
        return InlineKeyboardMarkup(inline_keyboard=prepared_keyboard)

    return ReplyKeyboardMarkup(keyboard=prepared_keyboard, resize_keyboard=True, one_time_keyboard=keyboard.one_time_keyboard)


def prepare_file_paramater(file):
    if type(file) is list:
        data_type = file[1]
        
        if data_type == 'filepath':
            data, data_type = file
            data = FSInputFile(data)
        elif data_type == 'buffer':
            data, data_type, filename = file
            data = BufferedInputFile(data, filename)
    else: # file_id or URL
        data = file

    return data
