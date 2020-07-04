#!/usr/bin/python3
# -*- coding: utf-8 -*-
import json
import re
import logging
import requests
from telegram import (ReplyKeyboardMarkup, ReplyKeyboardRemove,
                      InlineKeyboardButton, InlineKeyboardMarkup)
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters,
                          ConversationHandler, CallbackQueryHandler)

SERVICE_DOMAIN = '3wifi.stascorp.com'
SERVICE_URL = 'https://' + SERVICE_DOMAIN
USER_KEYS_DB_FILENAME = 'userkeys.json'

# Initializing settings
try:
    with open('config.json', 'r', encoding='utf-8') as file:
        config = json.load(file)
        TOKEN = config['bot_token']
        IP = config['webhook_ip']
        API_KEY = config['3wifi_apikey']
except FileNotFoundError:
    print('Please provide the following credentials')
    TOKEN = input('Telegram bot API token: ')
    IP = input('IP for webhook: ')
    API_KEY = input('3WiFi API read key: ')
    config = {
        'bot_token': TOKEN,
        'webhook_ip': IP,
        '3wifi_apikey': API_KEY
    }
    with open('config.json', 'w', encoding='utf-8') as outf:
        json.dump(config, outf, indent=4)

# Initializing user API keys database
try:
    with open(USER_KEYS_DB_FILENAME, 'r', encoding='utf-8') as file:
        USER_KEYS = json.load(file)
except FileNotFoundError:
    USER_KEYS = dict()
    with open(USER_KEYS_DB_FILENAME, 'w', encoding='utf-8') as outf:
        json.dump(USER_KEYS, outf, indent=4)

# Single BSSID pattern
bssid_pattern = re.compile(r"^(?:[0-9A-Fa-f]{2}[:-]){5}(?:[0-9A-Fa-f]{2})$")
# BSSID multi-line list pattern. Maximum 100 BSSID
bssid_list_pattern = re.compile(r"(?:[0-9A-Fa-f]{2}[:-]){5}(?:[0-9A-Fa-f]{2})(?:[\n](?:[0-9A-Fa-f]{2}[:-]){5}(?:[0-9A-Fa-f]{2})){0,99}")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)
logger = logging.getLogger(__name__)


class ConversationStates():
    LOGIN_PROMPT = 1
    PASSWORD_PROMPT = 2
    BSSID_PROMPT = 3
    ESSID_PROMPT = 4


def scoreformat(score):
    answer = ''
    score *= 100
    if score < 1:
        answer = "{0:.2f}".format(score)
    elif score < 10:
        answer = "{0:.1f}".format(score)
    else:
        answer = str(round(score))
    answer += '%'
    return answer


def getPersonalAPIkey(user_id):
    """Gets 3WiFi API key by Telegram user ID"""
    user_id = str(user_id)
    if user_id in USER_KEYS:
        return USER_KEYS[user_id]
    else:
        return API_KEY


def formatap(data):
    key_labels = {
        'essid': 'ESSID',
        'bssid': 'BSSID',
        'key': 'Password',
        'wps': 'WPS PIN',
        'time': 'Date'
    }
    order = ['essid', 'bssid', 'key', 'wps', 'time']    # Order of values in the answer
    copyable = ['essid', 'bssid', 'key', 'wps']   # Values that can be copied (monospaced font)
    answer = ''
    for element in order:
        if (element in data) and data[element]:   # Check if value is not empty
            key, value = element, data[element]
            if (key in copyable) and (value != '<empty>'):
                answer += f'{key_labels[key]}: `{value}`\n'
            else:
                answer += f'{key_labels[key]}: {value}\n'
    if 'lat' in data:
        answer += f"[Точка на карте]({SERVICE_URL}/map?lat={data['lat']}&lon={data['lon']})\n"
    else:
        answer += '- - - - -\n'
    return answer


def formatpin(data):
    key_labels = {
        'name': 'Name',
        'value': 'Pin',
        'score': 'Score'
    }
    order = ['name', 'value', 'score']    # Order of values in the answer
    copyable = ['value']   # Values that can be copied (monospaced font)
    answer = ''
    for element in order:
        if (element in data) and data[element]:   # Check if value is not empty
            key, value = element, data[element]
            if key == 'score':
                value = scoreformat(value)
            if key in copyable:
                answer += f'{key_labels[key]}: `{value}`\n'
            else:
                answer += f'{key_labels[key]}: {value}\n'
    answer += '- - - - -\n'
    return answer


def formataps(values):
    answer = ''
    for value in values:
        answer += formatap(value)
    return answer


def formatpins(values):
    answer = ''
    for value in values:
        answer += formatpin(value)
    return answer


def getApiErrorDesc(error, user_id):
    if error == 'cooldown':
        return 'Узбагойся и попробуй ещё раз через 10 сек 😜'
    elif error == 'loginfail':
        return 'Ошибка авторизации в 3WiFi. Если вы ранее авторизовывались через /login, попробуйте сделать это снова или выйдите с помощью /logout'
    elif error == 'lowlevel':
        if str(user_id) in USER_KEYS:
            return 'Недостаточно прав для выполнения команды. Возможно, ваш аккаунт 3WiFi заблокирован'
        else:
            return 'Недостаточно прав для выполнения команды. Вероятно, гостевой аккаунт заблокирован. Купить код приглашения можно тут: https://t.me/routerscan/15931'
    else:
        return 'Что-то пошло не так 😮 error: ' + error


def apiquery(user_id, bssid='*', essid=None, sensivity=False):
    """Implements querying single AP by its BSSID/ESSID"""
    api_key = getPersonalAPIkey(user_id)
    url = f'{SERVICE_URL}/api/apiquery?key={api_key}&bssid={bssid}'
    if essid is not None:
        url += f'&essid={essid}'
    if sensivity:
        url += '&sens=true'
    response = requests.get(url).json()

    reply_markup = None
    if not response['result']:
        return getApiErrorDesc(response['error'], user_id), reply_markup
    if len(response['data']) == 0:
        if bssid != '*':
            keyboard = [
                [
                    InlineKeyboardButton('Сгенерировать пин-коды WPS',
                                         callback_data=f'{user_id}/{bssid}')
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
        return 'Нет результатов :(', reply_markup
    return formataps(tuple(response['data'].values())[0]), reply_markup


def apiwps(user_id, bssid):
    """Implements generating PIN codes for single AP by its BSSID"""
    api_key = getPersonalAPIkey(user_id)
    response = requests.get(
        f'{SERVICE_URL}/api/apiwps?key={api_key}&bssid={bssid}'
    ).json()
    if not response['result']:
        return getApiErrorDesc(response['error'], user_id)
    if len(response['data']) == 0:
        return 'Нет результатов :('
    return formatpins(response['data'][bssid.upper()]['scores'])


def parseApDataArgs(args):
    """Parsing BSSID and ESSID from /pw command arguments"""
    if re.match(bssid_pattern, args[0]) is not None:
        bssid = args[0]
        if len(args) > 1:
            essid = ' '.join(args[1:])
        else:
            essid = None
    else:
        bssid = '*'
        essid = ' '.join(args)
    return bssid, essid


def unknown(update, context):
    """Handler for unknown commands"""
    update.message.reply_text(
        'Команда не найдена! Отправьте /help для получения информации по доступным командам'
        )


def help(update, context):
    """Hadler for /help command"""
    answer = '''{} бот!
/pw BSSID и/или ESSID — поиск по MAC-адресу или имени точки (пример: /pw FF:FF:FF:FF:FF:FF или /pw netgear или /pw FF:FF:FF:FF:FF:FF VILTEL)
/pws — то же самое, что /pw, но с учётом регистра (ESSID)
/wps BSSID — поиск WPS пин-кодов по MAC-адресу (пример: /wps FF:FF:FF:FF:FF:FF)'''.format(SERVICE_DOMAIN)
    private_commands = '''\n/login username:password — авторизоваться с личным аккаунтом 3WiFi для снятия ограничений гостевого аккаунта
/logout — выполнить выход из личного аккаунта 3WiFi'''
    if update.message.chat.type == 'private':
        answer += private_commands
    update.message.reply_text(answer)


def authorize(login, password, context, user_id):
    """3WiFi authorization interface"""
    r = requests.post(
        f'{SERVICE_URL}/api/apikeys',
        data={'login': login, 'password': password}
    ).json()
    if r['result']:
        if r['profile']['level'] > 0:
            user_id = str(user_id)
            nickname = r['profile']['nick']
            try:
                apikey = list(filter(lambda x: x['access'] == 'read', r['data']))[0]['key']
            except IndexError:
                answer = 'Ошибка: аккаунт *{}* не имеет API-ключа на чтение. Получите его на сайте, затем повторите попытку авторизации.'.format(nickname)
            else:
                USER_KEYS[user_id] = apikey
                with open(USER_KEYS_DB_FILENAME, 'w', encoding='utf-8') as outf:
                    json.dump(USER_KEYS, outf, indent=4)
                answer = 'Вы успешно авторизованы как *{}*. Чтобы выйти, отправьте /logout'.format(nickname)
                # Send security notification to users with the same token
                for telegram_id, api_key in USER_KEYS.items():
                    if (apikey == api_key) and (telegram_id != user_id) and (api_key != API_KEY):
                        context.bot.send_message(
                            chat_id=telegram_id,
                            text='*Уведомление безопасности*\n[Пользователь](tg://user?id={}) только что авторизовался в боте с вашим аккаунтом 3WiFi.'.format(user_id),
                            parse_mode='Markdown'
                            )
        else:
            answer = 'Ошибка: уровень доступа аккаунта ниже уровня *пользователь*'
    elif r['error'] == 'loginfail':
        answer = 'Ошибка — проверьте логин и пароль'
    elif r['error'] == 'lowlevel':
        answer = 'Ошибка: ваш аккаунт заблокирован'
    else:
        answer = 'Что-то пошло не так 😮 error: {}'.format(r['error'])
    return answer


def login(update, context):
    """Handler for /login command"""
    if update.message.chat.type != 'private':
        update.message.reply_text(
            'Команда работает только в личных сообщениях (ЛС)'
        )
        return ConversationHandler.END
    answer = 'Укажите логин:'
    if context.args:
        args = ' '.join(context.args)
        if ':' in args:
            login, password = args.split(':')[:2]
            answer = authorize(
                login, password, context, update.message.from_user.id
            )
            update.message.reply_text(answer, parse_mode='Markdown')
            return ConversationHandler.END
    update.message.reply_text(answer)
    return ConversationStates.LOGIN_PROMPT


def login_prompt(update, context):
    context.user_data['login'] = update.message.text
    update.message.reply_text('Укажите пароль:')
    return ConversationStates.PASSWORD_PROMPT


def password_prompt(update, context):
    password = update.message.text
    login = context.user_data['login']
    answer = authorize(login, password, context, update.message.from_user.id)
    update.message.reply_text(answer, parse_mode='Markdown')
    return ConversationHandler.END


def cancel_conversation(update, context):
    '''Generic conversation canceler'''
    update.message.reply_text(
        'Операция отменена.',
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


def logout(update, context):
    """Handler for /logout command"""
    if update.message.chat.type != 'private':
        update.message.reply_text(
            'Команда работает только в личных сообщениях (ЛС)'
        )
        return
    user_id = str(update.message.from_user.id)
    try:
        USER_KEYS.pop(user_id)
        with open(USER_KEYS_DB_FILENAME, 'w', encoding='utf-8') as outf:
            json.dump(USER_KEYS, outf, indent=4)
    except KeyError:
        answer = 'Ошибка: невозможно выйти из аккаунта 3WiFi, т.к. вы не вошли'
    else:
        answer = 'Выход выполнен, API-ключ вашего аккаунта 3WiFi удалён из базы данных бота. Чтобы авторизоваться снова, воспользуйтесь командой /login'
    update.message.reply_text(answer)


def pw(update, context):
    """Handler for /pw command"""
    answer = 'Ошибка: не передан BSSID или ESSID.\nПоиск по BSSID и/или ESSID выполняется так: /pw BSSID/ESSID (пример: /pw FF:FF:FF:FF:FF:FF VILTEL или /pw FF:FF:FF:FF:FF:FF или /pw netgear)'
    user_id = update.message.from_user.id
    args = context.args
    reply_markup = None
    if len(args) > 0:
        bssid, essid = parseApDataArgs(args)
        answer, reply_markup = apiquery(user_id, bssid, essid)
    elif update.message.chat.type == 'private':
        reply_keyboard = [['↪ Пропустить']]
        update.message.reply_text(
            'Укажите BSSID:',
            reply_markup=ReplyKeyboardMarkup(reply_keyboard,
                                             one_time_keyboard=True,
                                             resize_keyboard=True)
        )
        context.user_data['sensivity'] = False
        return ConversationStates.BSSID_PROMPT
    update.message.reply_text(
        answer, parse_mode='Markdown', reply_markup=reply_markup)
    return ConversationHandler.END


def bssid_prompt(update, context):
    t = update.message.text
    if re.match(bssid_pattern, t) is not None:
        reply_keyboard = [['↪ Пропустить']]
        context.user_data['bssid'] = t
        update.message.reply_text(
            'Укажите ESSID:',
            reply_markup=ReplyKeyboardMarkup(reply_keyboard,
                                             one_time_keyboard=True,
                                             resize_keyboard=True)
        )
        return ConversationStates.ESSID_PROMPT
    elif re.match(r'↪ ', t) is not None:
        # Skip the BSSID prompt
        context.user_data['bssid'] = '*'
        update.message.reply_text(
            'Укажите ESSID:', reply_markup=ReplyKeyboardRemove())
        return ConversationStates.ESSID_PROMPT
    else:
        update.message.reply_text(
            'Ошибка: неверный формат BSSID. Укажите BSSID:')
        return ConversationStates.BSSID_PROMPT


def essid_prompt(update, context):
    t = update.message.text
    if re.match(r'↪ ', t) is not None:
        # Skip the ESSID prompt
        essid = None
    else:
        essid = t
    bssid = context.user_data['bssid']
    sensivity = context.user_data['sensivity']
    answer, reply_markup = apiquery(
        update.message.from_user.id, bssid, essid, sensivity
    )
    update.message.reply_text(
        answer, parse_mode='Markdown', reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


def pws(update, context):
    """Handler for /pws command"""
    answer = 'Ошибка: не передан BSSID или ESSID.\nПоиск по BSSID и/или ESSID выполняется так: /pws BSSID/ESSID (пример: /pws FF:FF:FF:FF:FF:FF VILTEL или /pws FF:FF:FF:FF:FF:FF или /pws netgear)'
    user_id = update.message.from_user.id
    args = context.args
    if len(args) > 0:
        bssid, essid = parseApDataArgs(args)
        answer, reply_markup = apiquery(user_id, bssid, essid, sensivity=True)
    elif update.message.chat.type == 'private':
        update.message.reply_text('Укажите BSSID:')
        context.user_data['sensivity'] = True
        return ConversationStates.BSSID_PROMPT
    update.message.reply_text(
        answer, parse_mode='Markdown', reply_markup=reply_markup)
    return ConversationHandler.END


def wps(update, context):
    """Handler for /wps command"""
    answer = 'Поиск WPS пин-кодов выполняется так: /wps BSSID (пример: /wps FF:FF:FF:FF:FF:FF)'
    user_id = update.message.from_user.id
    args = context.args
    if (len(args) == 1) and (re.match(bssid_pattern, args[0]) is not None):
        answer = apiwps(user_id, args[0])
    if len(answer) > 3900:
        update.message.reply_text(
            f'{answer[:3900]}\nСписок слишком большой — смотрите полностью на {SERVICE_URL}/wpspin',
            parse_mode='Markdown'
        )
    else:
        update.message.reply_text(answer, parse_mode='Markdown')


def querybssidlist(update, context):
    """Handler for message containing BSSID"""
    user_id = update.message.from_user.id
    bssid_list = update.message.text.splitlines()
    # Filtering BSSID list with preversing order
    seen = set()
    bssid_list = [x.upper() for x in bssid_list if not (x in seen or seen.add(x))]
    del seen

    reply_markup = None
    if len(bssid_list) == 1:
        # Fetch 10 records for single BSSID
        answer, reply_markup = apiquery(user_id, bssid=bssid_list[0])
    else:
        # Fetch one record per BSSID
        response = requests.post(
            f'{SERVICE_URL}/api/apiquery',
            json={
                'key': getPersonalAPIkey(user_id),
                'bssid': bssid_list
            }
        ).json()
        if not response['result']:
            answer = getApiErrorDesc(response['error'], user_id)
        elif len(response['data']) == 0:
            answer = 'Нет результатов :('
        else:
            data = response['data']
            answer = ''
            for bssid in bssid_list:
                if bssid in data:
                    answer += formatap(data[bssid][0])
    update.message.reply_text(
        answer, parse_mode='Markdown', reply_markup=reply_markup)


def callbackbutton(update, context):
    """Handler for WPS PIN inline button"""
    query = update.callback_query
    initiator_id, bssid = query.data.split('/')
    user_id = str(query.from_user.id)
    if initiator_id != user_id:
        query.answer(text='Эта кнопка предназначена для инициатора запроса')
    else:
        query.answer()
        old_text = query.message.text
        query.edit_message_text(
            text=f'{old_text}\n\n*Пин-коды WPS:*\n_Ожидайте…_',
            parse_mode='Markdown'
        )
        answer = apiwps(initiator_id, bssid)
        query.edit_message_text(
            text=f'{old_text}\n\n*Пин-коды WPS:*\n{answer}',
            parse_mode='Markdown'
        )


def error(update, context):
    logger.warning('Update "%s" caused error "%s"', update, context.error)


updater = Updater(TOKEN, use_context=True)
dp = updater.dispatcher

auth_conversation = ConversationHandler(
    entry_points=[CommandHandler("login", login, pass_args=True)],
    states={
        ConversationStates.LOGIN_PROMPT: [
            MessageHandler(Filters.text & ~Filters.command, login_prompt)
        ],
        ConversationStates.PASSWORD_PROMPT: [
            MessageHandler(Filters.text & ~Filters.command, password_prompt)
        ]
    },
    fallbacks=[CommandHandler("cancel", cancel_conversation)]
)
ap_query_conversation = ConversationHandler(
    entry_points=[
        CommandHandler("pw", pw, pass_args=True),
        CommandHandler("pws", pws, pass_args=True)
    ],
    states={
        ConversationStates.BSSID_PROMPT: [
            MessageHandler(Filters.text & ~Filters.command, bssid_prompt)
        ],
        ConversationStates.ESSID_PROMPT: [
            MessageHandler(Filters.text & ~Filters.command, essid_prompt)
        ]
    },
    fallbacks=[CommandHandler("cancel", cancel_conversation)],
    conversation_timeout=600   # 10 minutes
)
dp.add_handler(auth_conversation)
dp.add_handler(ap_query_conversation)
dp.add_handler(CommandHandler("help", help))
dp.add_handler(CommandHandler("start", help))
dp.add_handler(CommandHandler("logout", logout))
dp.add_handler(CommandHandler("wps", wps, pass_args=True))
dp.add_handler(MessageHandler(Filters.regex(bssid_list_pattern) & ~Filters.command & Filters.private, querybssidlist))
dp.add_handler(MessageHandler((Filters.text | Filters.command) & Filters.private, unknown))
dp.add_handler(CallbackQueryHandler(callbackbutton))
dp.add_error_handler(error)

if IP == 'no':
    updater.start_polling(poll_interval=.5)
else:
    updater.start_webhook(
        listen='0.0.0.0',
        port=8443,
        url_path=TOKEN,
        key='private.key',
        cert='cert.pem',
        webhook_url=f'https://{IP}:8443/{TOKEN}'
    )
