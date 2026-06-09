import re


def validate_name(text: str) -> bool:
    """
    Проверяет ФИО:
    - Минимум два слова.
    - Разрешены кириллица, латиница, дефис, пробел.
    - Длина каждого слова от 2 символов.
    """
    pattern = r"^[a-zA-Zа-яА-ЯёЁ\-]{2,}(?: [a-zA-Zа-яА-ЯёЁ\-]{2,})+$"
    return bool(re.match(pattern, text.strip()))


def validate_email(text: str) -> bool:
    """
    Проверяет email:
    - name@domain.tld
    - без пробелов
    - доменная зона от 2 символов
    """
    pattern = r"^[^\s@]+@[^\s@]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, text.strip()))


def validate_and_clean_phone(text: str) -> str | None:
    """
    Очищает телефон от скобок, дефисов и пробелов.
    Проверяет, что телефон начинается с +7, 7 или 8 и имеет длину 11 цифр.
    Возвращает очищенный номер (в формате 7XXXXXXXXXX) или None.
    """
    # Удаляем все нецифровые символы и плюсы для проверки
    clean_digits = re.sub(r"[\s\-\(\)\+]", "", text)

    if len(clean_digits) == 11 and clean_digits[0] in ("7", "8"):
        # Приводим к единому стандарту
        return "7" + clean_digits[1:]

    return None
