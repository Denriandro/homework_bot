class SendMessageError(Exception):
    """Ошибка отправки сообщения."""
    pass


class EmptyData(Exception):
    """Пусто."""
    pass


class NotForSending(Exception):
    """Не для пересылки в Телеграм."""
    pass
