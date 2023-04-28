import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

import exceptions


load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверка доступности переменных окружения."""
    return all([TELEGRAM_TOKEN, PRACTICUM_TOKEN, TELEGRAM_CHAT_ID])


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug(f'Удачная отправка сообщения: "{message}"')
    except Exception as error:
        logging.error(f'При отправке сообщения произошла ошибка: "{error}"')
        raise exceptions.SendMessageError(
            f'Не удалось отправить сообщение {error}')


def get_api_answer(timestamp):
    """Делает запрос к API."""
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp}
        )
        if response.status_code != HTTPStatus.OK:
            raise ConnectionError(
                'Не удалось получить ответ API, '
                f'статус: {response.status_code}'
                f'причина: {response.reason}'
                f'текст: {response.text}'
                f'эндпоинт (url): {response.url}')
        return response.json()
    except requests.RequestException as error:
        logging.error(f'Беда с запросом {error}')


def check_response(response):
    """Проверяет ответ запроса к API."""
    if not isinstance(response, dict):
        raise TypeError('Ошибка в типе ответа API')
    if 'homeworks' not in response and 'current_date' not in response:
        logging.error('Отсутствие ожидаемых ключей в ответе API')
        raise KeyError('Пустой ответ от API')
    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        raise TypeError('Homeworks не является списком')
    return homeworks[0]


def parse_status(homework):
    """Извлекает из ответа API статус и имя домашки."""
    if not homework:
        raise exceptions.EmptyData('Никаких обновлений в статусе нет')
    if 'homework_name' not in homework:
        raise KeyError('В ответе отсутствует ключ homework_name')
    homework_name = homework['homework_name']
    verdict = homework['status']
    verdict = HOMEWORK_VERDICTS.get(verdict)
    if not verdict:
        logging.error('Неожиданный статус в ответе API')
        raise ValueError(f'Неизвестный статус работы: {verdict}')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_update(prev_value, new_value):
    """Проверка обновления переменной."""
    if new_value != prev_value:
        prev_value = new_value
    return prev_value


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical(
            'Отсутствует необходимое кол-во переменных окружения'
        )
        sys.exit('Отсутствуют переменные окружения')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    prev_status = None
    prev_message = None
    while True:
        try:
            response = get_api_answer(timestamp)
            homework = check_response(response)
            message = parse_status(homework)
            if check_update(prev_status, message):
                send_message(bot, message)
            else:
                logging.debug('Отсутствие в ответе новых статусов')
        except exceptions.NotForSending as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if check_update(prev_message, message):
                send_message(bot, message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s, %(levelname)s, %(message)s, %(name)s',
        handlers=[logging.FileHandler('log.txt', encoding='UTF-8'),
                  logging.StreamHandler(sys.stdout)]
    )
    main()
