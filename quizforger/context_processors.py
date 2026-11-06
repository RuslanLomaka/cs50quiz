from .language import LANGUAGE_LABELS, SUPPORTED_LANGUAGES, get_request_language, get_ui_text

# One Impressum covers all of the owner's sites, so its address lives in one place only.
IMPRINT_URL = "https://edv.ruslanlomaka.org/impressum/"


def language_context(request):
    language = get_request_language(request)
    return {
        "qf_language": language,
        "qf_language_label": LANGUAGE_LABELS[language],
        "qf_languages": [
            {"code": code, "label": LANGUAGE_LABELS[code]} for code in SUPPORTED_LANGUAGES
        ],
        "ui": get_ui_text(language),
        "qf_imprint_url": IMPRINT_URL,
    }
