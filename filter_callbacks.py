def image_filter(message, user):
    return message.photo or (message.document and 'image' in message.document.mime_type)

def audio_video_filter(message, user):
    return message.voice or message.audio or message.video or (message.document and ('audio' in message.document.mime_type or 'video' in message.document.mime_type))

def gpt_4_selected_filter(message, user):
    return '4' in user.gpt_version

def gpt_vision_filter(message, user):
    return image_filter(message, user) and gpt_4_selected_filter(message, user)
    
def gpt_speech_to_text_filter(message, user):
    return audio_video_filter(message, user) and gpt_4_selected_filter(message, user)
