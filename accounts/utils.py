def normalize_phone(phone: str) -> str:
    digits = "".join(filter(str.isdigit, phone))

    if digits.startswith("8"):
        digits = "7" + digits[1:]

    if not digits.startswith("7"):
        digits = "7" + digits

    return f"+{digits}"
