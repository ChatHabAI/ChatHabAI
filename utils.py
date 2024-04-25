import datetime
import random
import os

def replace_placeholders_in_text(text, object_data, object_name):
    for key in object_data.keys() if type(object_data) is dict else dir(object_data):
        value = str(object_data[key] if type(object_data) is dict else getattr(object_data, key))
        text = text.replace(f'{object_name}.{key}', value)

    return text

def get_item_by_index(array, index, default=None):
    try:
        return array[index]
    except IndexError:
        return default
        
def random_str(n):
    return ''.join(random.choices('abcdefghijklmnopqrstuvwxyz123456789', k=n))

def generate_unique_filename(ext, random_str_len=8):
    return f"{random_str(random_str_len)}_{datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S-%f')}.{ext}"

def generate_unique_filepath(dirname, ext):
    return f'{os.getcwd()}/{dirname}/{generate_unique_filename(ext)}'
