import os

DO_DATABASE_MIGRATIONS = True

PROTECT_CONTENT = False

BOT_TOKEN = ''

DATABASE_URI = f"sqlite+aiosqlite:///{os.path.join(os.getcwd(), 'database.db')}"

PHOTOS_DIR = "photos"
UPLOADS_DIR = "uploads"
SPEECH_DIR = "speech"

CONNECTION_TO_AI_ERROR_TEXT = 'The network is congested, try again later.'
CONNECTION_TO_GPT35FREE_ERROR_TEXT = 'Unfortunately, <b>ChatGPT 3.5</b> is not available right now, try repeating the request later or use other neural networks connected to the bot.'
CONNECTION_TO_AI_WAIT_TEXT = 'Request sent, please wait...'


DISABLE_BOT = False
DISABLE_BOT_TEXT = 'Bot is disabled'

CENSURE_TEXT = 'Your request was rejected by <b>OpenAI</b> because it violates company security policy, please try reformulating your request and resubmitting it.'
STABLE_DIFFUSION_CENSURE_TEXT = 'Your request was rejected by <b>Stable Diffusion</b> because it violates company security policy, please try reformulating your request and resubmitting it.'
UNSUPPORTED_CONTENT_TEXT = 'Your request was rejected by <b>OpenAI</b> because this data type is not supported by the system.'
LEIAPIX_UNSUPPORTED_CONTENT_TEXT = 'Your request was rejected by <b>LeiaPix</b> because this data type is not supported by the system.'
LEO_CENSURE_TEXT = 'Your request was rejected by <b>Leonardo AI</b> because it violates the companys security policy, please try reformulating your request and resubmitting it.'
GEMINI_CENSURE_TEXT = 'Your request was rejected by <b>Gemini</b> because it violates the companys security policy, please try rephrasing your request and resubmitting it.'


TEXT_PER_EACH_N_REQUEST_TO_AI = 'This message appears in every n request you make to the AI.'
N = 0

DEFAULT_PROMP_FOR_VISION = 'what is shown here?'

START_COMMAND = 'start'
HELP_COMMAND = 'help'
PREMIUM_COMMAND = 'premium'
CHATGPT_SETTINGS_COMMAND = 'chatgpt'
CHATGPT_TEXT_TO_SPEECH_COMMAND = 'gpt_tts'
DALLE_COMMAND = 'dalle3'
PRODIA_COMMAND = 'prodia'
STABLE_DIFFUSION_COMMAND = 'sdimg'
LEONARDO_COMMAND = 'leoimg'
LEIAPIX_COMMAND = 'leia'
GEMINI_COMMAND = 'gem'

HELP_TEXT = 'If you have any questions or suggestions for improving the performance of this bot, write to us ChatHabAI.'

PREMIUM_START_TEXT = '<b>Your data.\n</b>'
PREMIUM_STATUS_TEXT = 'Account status'
PREMIUM_REFRESH_TEXT = 'Limit update date'
PREMIUM_GPT_LIMITS_TEXT = 'Request limit in ChatGPT and Gemini'
PREMIUM_IMAGES_LIMITS_TEXT = 'Image generation limit'
PREMIUM_ANIMATIONS_LIMITS_TEXT = '3D animation generation limit (<b>LeiaPix</b>)'
PREMIUM_END_TEXT = '<b>Trial plan:</b> free limit is renewed on the first day of each month.\n<b>Premium plan:</b> purchased generations do not expire at the end of the month and are available for use at any time.\nIf you need a special one tariff plan, write to us @ChatHabAI.\n\n<b><u>Available for purchase:</u></b>\n<b>ChatGPT + Gemini (100)</b> - 100 requests to ChatGPT and Gemini.\n<b>Images (10)</b> - 10 generation of images by any neural network.\n<b>Images (100)</b> - 100 generation of images by any neural network.\n<b>3D- animations (10)</b> - 10 generations of 3D animation (<b>LeiaPix</b>).'

START_TEXT = f'Hello! This bot gives you access to several neural networks:\n\n-- <b>ChatGPT</b> (openai.com) text and voice responses, image descriptions.\n(To select a model and settings, use the command /{CHATGPT_SETTINGS_COMMAND} )\n\n-- <b>Gemini</b> (deepmind.google) text analysis, answers to text questions.\n(To get an answer from the neural network, use the command /{GEMINI_COMMAND})\n\n-- < b>Dalle3</b> (openai.com) generate images from text.\n(To create an image, start the request with the /{DALLE_COMMAND} command and then add a description)\n\n-- <b>Prodia</b > (prodia.com) generate images from text.\n(To create an image, start the request with the /{PRODIA_COMMAND} command and then add a description)\n\n-- <b>Stable Diffusion</b> (stability.ai ) generating images from text and pictures.\n(To create an image, start the request with the command /{STABLE_DIFFUSION_COMMAND} and then add a description)\n\n-- <b>Leonardo</b> (leonardo.ai) generating images from text.\n(To create an image, start the query with the command /{LEONARDO_COMMAND} and then add a description)\n\n-- <b>LeiaPix</b> (leiapix.com) turns a 2D image into a 3D animation. \n(To create a 3D animation, start the request with /{LEIAPIX_COMMAND} and then add a 2D image)'

SETTINGS_TEXT = f'Select one of the <b>ChatGPT models.</b>\n\n<b>ChatGPT 3.5</b> - can only respond to text requests.\n\n<b>ChatGPT 4 Turbo</b> - can answer text queries, decipher sounds, describe images. \n\n- For a text description of an image, you need to send the picture to the chat without additional commands. \n\n- To transcribe the sound, you need to send a voice message or recorded sound to the chat without additional commands. \n\n- To read the text, you need to start the request with the command /{CHATGPT_TEXT_TO_SPEECH_COMMAND} (example: /{CHATGPT_TEXT_TO_SPEECH_COMMAND} good morning).'

LIMIT_ERROR = f'The number of requests has been exhausted. To continue using the bot, please purchase additional generations in the /{PREMIUM_COMMAND} section or wait for the start of a new test period on the first day of each month.'

DALLE_DESCRIPTION_TEXT = f'<b>Dalle3.</b> Enter a description of the picture you want to generate. The better you describe the object, the more accurately it will be drawn (example: /{DALLE_COMMAND} plush cats).'
PRODIA_DESCRIPTION_TEXT = f'<b>Prodia.</b> Enter a description of the picture you want to generate. The better you describe the object, the more accurately it will be drawn (example: /{PRODIA_COMMAND} plush cats).'
STABLE_DIFFUSION_DESCRIPTION_TEXT = f'<b>Stable Diffusion.</b> Enter a description of the image you want to generate. The better you describe an object, the more accurately it will be drawn (example: /{STABLE_DIFFUSION_COMMAND} plush cats).\n\nTo derive one image from another:\n\n1. Attach any photo or drawing;\n\n2. Be sure to include /{STABLE_DIFFUSION_COMMAND};\n\n3 in the photo caption. Write an additional comment if necessary.'
LEONARDO_DESCRIPTION_TEXT = f'<b>Leonardo.</b> Enter a description of the picture you want to generate. The better you describe the object, the more accurately it will be drawn (example: /{LEONARDO_COMMAND} plush cats).'
LEIAPIX_DESCRIPTION_TEXT = f'<b>LeiaPix.</b> To create a 3D animation, start the request with the command /{LEIAPIX_COMMAND} and then add a 2D image.'
GEMINI_DESCRIPTION_TEXT = f'<b>Gemini.</b> Can answer text queries and analyze texts (example: /{GEMINI_COMMAND} how many zodiac signs?).'

CHATGPT_TEXT_TO_SPEECH_DESCRIPTION_TEXT = f'Enter the text you want to convert to speech (example: /{CHATGPT_TEXT_TO_SPEECH_COMMAND} Hello, how are you?)'

CHATGPT_SPEECH_TO_TEXT_SUPPORTED_EXTENSIONS = ['mp3', 'mp4', 'mpeg', 'mpga', 'm4a', 'wav', 'webm', 'oga', 'ogg', 'flac']
CHATGPT_SPEECH_TO_TEXT_WRONG_FORMAT_TEXT = f'Submit audio in one of the following formats: {", ".join(CHATGPT_SPEECH_TO_TEXT_SUPPORTED_EXTENSIONS)}'

MENU = [
    [START_COMMAND, 'Запуск бота'],
    [CHATGPT_SETTINGS_COMMAND, 'ChatGPT'],
    [GEMINI_COMMAND, 'Gemini'],
    [DALLE_COMMAND, 'DALLE3'],
    [PRODIA_COMMAND, 'Prodia'],
    [STABLE_DIFFUSION_COMMAND, 'Stable Diffusion'],
    [LEONARDO_COMMAND, 'Leonardo'],
    [LEIAPIX_COMMAND, 'LeiaPix'],
    [PREMIUM_COMMAND, 'Premium'],
    [HELP_COMMAND, 'Help'],
]

TARIFFS = [
    { 'type': 'gpt', 'count': 100, 'price': 200, 'button_text': 'ChatGPT + Gemini (100) - 200 rub.', 'description': 'You buy 100 requests to <b >ChatGPT</b> any version and <b>Gemini</b> for 200 RUB. Click "Pay" to go to the payment system website.\n\n❗️After payment, click the "Check Purchase" button' },
 { 'type': 'image', 'count': 10, 'price': 80, 'button_text': 'Images (10) - 80 rub.', 'description': 'You buy 10 image generation by any neural network for 80 RUB Click "Pay" to go to the payment system website.\n\n❗️After payment, click the "Check Purchase" button' },
 { 'type': 'image', 'count': 100, 'price': 800, 'button_text': 'Images (100) - 800 rub.', 'description': 'You buy 100 image generation by any neural network for 800 RUB Click "Pay" to go to the payment system website.\n\n❗️After payment, click the "Check Purchase" button' },
 { 'type': 'animation', 'count': 10, 'price': 160, 'button_text': '3D animations (10) - 160 rub.', 'description': 'You buy 10 generations of 3D animations neural network <b>LeiaPix</b> for 160 RUB. Click "Pay" to go to the payment system website.\n\n❗️After payment, click the "Check Purchase" button' },
]

BUY_TEXT = 'Thank you for your purchase! Limits have been added to your account'

DESCRIPTION_TEXT = 'This bot can work with several neural networks:\n-- ChatGPT - openai.com\n-- Gemini - deepmind.google\n-- Dalle3 - openai.com\n-- Prodia - prodia.com\n-- Stable Diffusion - stability.ai\n-- Leonardo - leonardo.ai\n-- LeiaPix - leiapix.com\n\nContacts:\n-- Website - ChatHabAI.com\n-- Channel - @ChatHab_AI\n-- Help - @ChatHabAI'

OPENAI_API_KEY = ''
STABLE_DIFFUSION_API_KEY = ''
LEONARDO_AI_API_KEY = ''
LEONARDO_AI_MODEL_ID = ''
LEIA_CLIENT_ID = ''
LEIA_CLIENT_SECRET = ''
GOOGLE_AI_STUDIO_API_KEY = ''

AWS_KEY_ID = ''
AWS_SECRET_KEY = ''
S3_BUCKET_NAME = ''
S3_BUCKET_REGION = ''

BOT_NAME = ''

YOUKASSA_SECRET_KEY = ''
YOUKASSA_SHOP_ID= ''
YOUKASSA_RETURN_URL = f'https://t.me/{BOT_NAME}'

PAYMENT_ERROR_TEXT = 'Something went wrong while creating the payment'
PAYMENT_NOT_PAID_TEXT = 'Payment has not been received. If you have any difficulties with payment, write to us ChatHabAI.'

NOT_ENOUGH_CREDIT_BALANCE_NOTIFICATION_TEXT = 'Insufficient funds on balance:'
NOTIFICATION_RECEVIER = 'ChatHabAI'

AI_REQUEST_TIMEOUT = 180

BOT_ADMINS = [""]