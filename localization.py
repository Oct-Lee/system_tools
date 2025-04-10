import gettext
import os
import locale

def setup_locale(lang_code=None):
    try:
        if lang_code is None:
            current_lang = locale.getdefaultlocale()[0]
        else:
            current_lang = lang_code
    except:
        current_lang = 'en_US'

    locale_path = os.path.join(os.path.dirname(__file__), 'locale')

    try:
        lang = gettext.translation('messages', localedir=locale_path, languages=[current_lang], fallback=True)
        lang.install()
        return lang.gettext
    except Exception as e:
        print(f"Error loading translations: {e}")
        return lambda x: x

_ = setup_locale()

