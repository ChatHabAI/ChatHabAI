class Keyboard():
    count = 0

    def __init__(self, keyboard=list(), inline=True, one_time_keyboard=True, custom_type='', radio_button_param=''):
        Keyboard.count += 1
        self.id = Keyboard.count
        self.keyboard = keyboard
        self.inline = inline
        self.custom_type = custom_type
        self.radio_button_param = radio_button_param
        self.one_time_keyboard = one_time_keyboard # hide reply keyboard after answer

class Button():
    def __init__(self, text='', message_block_id=None, metadata='', url=''):
        self.text = text
        self.message_block_id = message_block_id
        print(metadata)
        self.metadata = str(metadata)
        self.url = url