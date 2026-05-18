from .language import LANGUAGE_LABELS, SUPPORTED_LANGUAGES, get_request_language, get_ui_text


def language_context(request):
    language = get_request_language(request)
    return {
        "qf_language": language,
        "qf_language_label": LANGUAGE_LABELS[language],
        "qf_languages": [
            {"code": code, "label": LANGUAGE_LABELS[code]}
            for code in SUPPORTED_LANGUAGES
        ],
        "ui": get_ui_text(language),
    }
