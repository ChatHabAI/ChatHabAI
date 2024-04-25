import datetime
import asyncio
import logging
import sys
import os

from copy import deepcopy

from aiobotocore.session import get_session

from aiogram.types import (
    CallbackQuery,
    BotCommand,
    Message,
)
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode

from aiogram.enums.chat_member_status import ChatMemberStatus

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from database import refresh_limits, database_init, get_user, get_or_create_user, save, update_statistics_file, get_message_blocks_with_filter, get_message_block, get_or_create_day_statistics
from project_utils import split_message_block_to_message_blocks, prepare_text, prepare_keyboard, prepare_file_paramater, is_keyboard_contains_link
from telegram_limits import MAX_MESSAGE_TEXT_LENGTH, MAX_MESSAGE_CAPTION_LENGTH
from custom_handlers import user_cache_by_id
from filter_callbacks import gpt_speech_to_text_filter
from config import AWS_KEY_ID, AWS_SECRET_KEY, S3_BUCKET_NAME, S3_BUCKET_REGION, MENU, DESCRIPTION_TEXT, SPEECH_DIR, UNSUPPORTED_CONTENT_TEXT, DISABLE_BOT, DISABLE_BOT_TEXT, BOT_ADMINS, PHOTOS_DIR, UPLOADS_DIR, PROTECT_CONTENT, BOT_TOKEN


bot = Bot(BOT_TOKEN)
dp = Dispatcher()

@dp.callback_query()
async def callback_query_handler(callback_query: CallbackQuery, bot: Bot):
    if DISABLE_BOT:
        await callback_query.message.answer(protect_content=PROTECT_CONTENT, text=DISABLE_BOT_TEXT, parse_mode=ParseMode.HTML)
        return False

    if callback_query.data.startswith('button:'):
        parts = callback_query.data.split(':')
        message_block_id = parts[1]
        message_block = await get_message_block(id=message_block_id)
        if message_block:
            user = await get_or_create_user(callback_query.from_user)

            metadata = None
            print(parts)
            if len(parts) > 2:
                metadata = parts[2]

            await send_message_block(bot, user, message_block, metadata=metadata)
            await callback_query.answer('')
        return True

    if callback_query.data.startswith('radio_button:'):
        message_block_id = callback_query.data.split(':')[1]
        value = callback_query.data.split(':')[2]

        message_block = await get_message_block(id=message_block_id)
        if message_block and message_block.keyboard:
            key = message_block.keyboard.radio_button_param
            user = await get_or_create_user(callback_query.from_user)

            if getattr(user, key, '') == value:
                await callback_query.answer('')
                return True

            setattr(user, key, value)
            user = await save(user)

            await bot.edit_message_reply_markup(
                chat_id=callback_query.message.chat.id,
                message_id=callback_query.message.message_id,
                reply_markup=prepare_keyboard(message_block, user)
            )
        
        return True

   # force inline button in telegram to stop flashing
   # await callback_query.answer('')

@dp.my_chat_member() # A bot member's status(start/restart or ban) was updated in a private chat
async def my_chat_member_handler(info):
    print('my_chat_member_handler')
    print(info) # info.old_chat_member info.new_chat_memeber info.chat info.from_user info.date
    # info.old_chat_member.status info.old_chat_member.user 'left' status for non members
    bot_was_banned = info.new_chat_member.status == ChatMemberStatus.KICKED

    if bot_was_banned:
        day_statistics = await get_or_create_day_statistics()
        day_statistics.subscribers -= 1
        day_statistics = await save(day_statistics)

        user = await get_or_create_user(info.from_user)
        user.is_subscribed = False
        user = await save(user)

async def send_message_block(bot, user, message_block, user_text=None, user_message=None, metadata=None):
    if message_block.required_admin_role and not user.is_admin and not user.username in BOT_ADMINS:
        return False

    if message_block.prev:
        prev_block = await get_message_block(id=message_block.prev)

        if prev_block:
            await send_message_block(bot, user, prev_block, user_text=user_text, user_message=user_message, metadata=metadata)

    if message_block.handler:
        message_block = await message_block.handler(user, user_text, user_message, bot, metadata)
        message_blocks = getattr(message_block, 'message_blocks', None)

        if message_block.text and len(message_block.text) > MAX_MESSAGE_TEXT_LENGTH:
            message_blocks = message_blocks or []
            message_blocks.extend(split_message_block_to_message_blocks(message_block))
            message_block.text = ''
        
        if message_blocks:
            prepared_message_blocks = []

            for m_b in message_blocks:
                if m_b.text and len(m_b.text) > MAX_MESSAGE_TEXT_LENGTH:
                    prepared_message_blocks.extend(split_message_block_to_message_blocks(m_b))
                else:
                    prepared_message_blocks.append(m_b)

            for m_b in prepared_message_blocks:
                m_b.handler = None
                await send_message_block(bot, user, m_b)
                await asyncio.sleep(1)

    kwargs = {
        "chat_id": user.user_id,
        "protect_content": PROTECT_CONTENT,
        "parse_mode": ParseMode.HTML
    }

    if message_block.keyboard:
        kwargs["reply_markup"] = prepare_keyboard(message_block, user)

    prepared_text = prepare_text(message_block.text, user)
    if message_block.photo or len(message_block.documents) or message_block.voice or message_block.audio or message_block.video or message_block.animation:
        kwargs["caption"] = f'{prepared_text[0:MAX_MESSAGE_CAPTION_LENGTH - 3]}...' if len(prepared_text) > MAX_MESSAGE_CAPTION_LENGTH else prepared_text
    else:
        kwargs["text"] = prepared_text

    if message_block.photo:
        kwargs["photo"] = prepare_file_paramater(message_block.photo)
        await bot.send_photo(**kwargs)

        if type(message_block.photo) is list and message_block.photo[1] == 'filepath':
            os.remove(message_block.photo[0])
    elif message_block.voice:
        kwargs["voice"] = prepare_file_paramater(message_block.voice)
        await bot.send_voice(**kwargs)

        if type(message_block.voice) is list:
            os.remove(message_block.voice[0])
    elif message_block.video:
        kwargs["video"] = prepare_file_paramater(message_block.video)
        await bot.send_video(**kwargs)

        if message_block.video is str and 's3.amazonaws.com' in message_block.video:
            session = get_session()
            async with session.create_client('s3', region_name=S3_BUCKET_REGION, aws_secret_access_key=AWS_SECRET_KEY, aws_access_key_id=AWS_KEY_ID) as s3:
                key = message_block.video.split('/')[-1].split('?')[0]
    elif message_block.audio:
        kwargs["audio"] = prepare_file_paramater(message_block.audio)
        await bot.send_audio(**kwargs)
    elif message_block.animation:
        kwargs["animation"] = prepare_file_paramater(message_block.animation)
        await bot.send_animation(**kwargs)
    elif len(message_block.documents):
        kwargs["document"] = prepare_file_paramater(message_block.documents[0])
        await bot.send_document(**kwargs)

        for document in message_block.documents[1:]:
            kwargs["document"] = prepare_file_paramater(document)
            kwargs["caption"] = ''
            await bot.send_document(**kwargs)
    elif prepared_text:
        await bot.send_message(**kwargs)
    
    user.last_message_block = message_block.id
    user = await save(user)

    if message_block.link and not message_block.wait_answer:
        next_block = await get_message_block(id=message_block.link)

        if next_block:
            if message_block.delay:
                await asyncio.sleep(message_block.delay)
            
            await send_message_block(bot, user, next_block, user_text=user_text, user_message=user_message, metadata=metadata)

    if getattr(message_block, 'message_in_queue', False) and user_cache_by_id.get(user.user_id):
        user_cache_by_id[user.user_id] = user_cache_by_id[user.user_id][1:]


async def my_message_handler(message: Message, bot: Bot, without_filters=False):
    print('message_handler')
    print(Message)

    user = await get_user(message.from_user.id)
    is_new_user = False

    if not user:
        is_new_user = True

    user = await get_or_create_user(message.from_user)
    day_statistics = await get_or_create_day_statistics()

    if not user.last_message_date or user.last_message_date != day_statistics.date:
        day_statistics.unique_users += 1
        day_statistics = await save(day_statistics)

        user.last_message_date = day_statistics.date
        user = await save(user)

    if DISABLE_BOT:
        await bot.send_message(chat_id=user.user_id, protect_content=PROTECT_CONTENT, text=DISABLE_BOT_TEXT, parse_mode=ParseMode.HTML)
        return False

    message_block = None

    text = message.text.strip() if message.text else ''
    if message.caption and not text:
        text = message.caption.strip()

    is_command = text.startswith('/')

    if is_command:
        parts = text.split(' ', 1)
        command = parts[0].replace('/', '')
        parameter = parts[1] if len(parts) > 1 else None # deeplink or parameter
        message_block = await get_message_block(command=command)

        bot_was_started_or_restared = is_new_user or not user.is_subscribed

        if bot_was_started_or_restared:
            day_statistics.subscribers += 1
            day_statistics = await save(day_statistics)

            user.is_subscribed = True
            user = await save(user)

    elif user.last_message_block:
        last_message_block = await get_message_block(id=user.last_message_block)

        if last_message_block and (last_message_block.wait_answer or is_keyboard_contains_link(last_message_block.keyboard)):
            keyboard = last_message_block.keyboard
            id = None
            
            if keyboard and not keyboard.inline and keyboard.one_time_keyboard:
                for row in keyboard.keyboard:
                    for button in row:
                        if button.message_block_id and prepare_text(button.text, user) == text:
                            id = button.message_block_id

            if last_message_block.wait_answer and text:
                setattr(user, last_message_block.wait_answer, text)
                user = await save(user)

                if last_message_block.link:
                    id = last_message_block.link

            if id:
                message_block = await get_message_block(id=id)

    if not message_block and not without_filters:
        message_blocks_with_filter = await get_message_blocks_with_filter()

        for m_b in message_blocks_with_filter:
            if m_b.filter(message, user):
                if gpt_speech_to_text_filter(message, user) and text:
                    await my_message_handler(message, bot, without_filters=True) # first answer only to text

                message_block = m_b
                break


    if not message_block:
        message_block = await get_message_block(tag=text)

    if not message_block and text:
        message_block = await get_message_block(default=True)

    if not message_block:
        await message.answer(protect_content=PROTECT_CONTENT, text=UNSUPPORTED_CONTENT_TEXT, parse_mode=ParseMode.HTML)

    if message_block:
        await send_message_block(bot, user, message_block, user_text=text, user_message=message)


@dp.message()
async def message_handler(message: Message, bot: Bot):
    return await my_message_handler(message, bot)
   

#https://core.telegram.org/bots/api#update
allowed_updates=['message', 'callback_query', 'my_chat_member']

menu = []

for item in MENU:
    menu.append(BotCommand(command=item[0], description=item[1]))

async def set_my_info():
    await bot.set_my_commands(menu)
    await bot.set_my_description(DESCRIPTION_TEXT)

async def polling_main() -> None:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(update_statistics_file, 'cron', hour=21)
    scheduler.add_job(refresh_limits, 'cron', day=1)
    scheduler.start()
    await update_statistics_file()

    # delete webhook if needed
    webhookInfo = await bot.get_webhook_info()
    if webhookInfo.url:
        await bot.delete_webhook(drop_pending_updates=True)

    await set_my_info()

    await dp.start_polling(bot, allowed_updates=allowed_updates)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    database_init()
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    os.makedirs(PHOTOS_DIR, exist_ok=True)
    os.makedirs(SPEECH_DIR, exist_ok=True)

    try:
        asyncio.run(polling_main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped!")
