# -*- coding: utf-8 -*-
import telebot
import requests
import sys
import re

token_bot = input('telegram token: ')
API_key = ''
bssid_pattern = re.compile(r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$")

bot = telebot.TeleBot(token_bot)

@bot.message_handler(content_types=["text"])
def handler(message):
    try:
        tmp = message.text.split()
        if tmp[0] == '/help': bot.send_message(message.chat.id, "3wifi.stascorp.com бот!\n/pw bssid/essid - поиск пароля и wps пина по мак адресу или имени точки (пример: /pw FF:FF:FF:FF:FF:FF или /pw netgear)\nwps /bssid - поиск wps пина по мак адресу (пример: /wps FF:FF:FF:FF:FF:FF)")
        elif len(tmp) == 2:
            if tmp[0] == '/pw' and re.match(bssid_pattern, tmp[1]) != None:
                r = requests.get('http://3wifi.stascorp.com/api/apiquery?key={}&bssid={}'.format(API_key, tmp[1]))
                result = r.json()
                if len(result['data']) > 0:
                    result = result['data'][tmp[1].upper()]
                    for value in result:
                        bot.send_message(message.chat.id, 'ESSID: ' + value['essid'])
                        bot.send_message(message.chat.id, value['key'])
                        if value['wps'] != '': bot.send_message(message.chat.id, 'wps pin: ' + value['wps'])
                        else: bot.send_message(message.chat.id, '<нет WPS пина>')
                else: bot.send_message(message.chat.id, 'Нет результатов :(')
            elif re.match(bssid_pattern, tmp[1]) == None:
                r = requests.get('http://3wifi.stascorp.com/api/apiquery?key={}&bssid=*&essid={}'.format(API_key, tmp[1]))
                result = r.json()
                if len(result['data']) > 0:
                    result = result['data']['*|{}'.format(tmp[1])]
                    for value in result:
                        bot.send_message(message.chat.id, 'essid: ' + value['essid'])
                        if value['bssid'] != '': bot.send_message(message.chat.id, 'bssid: ' + value['bssid'])
                        else: bot.send_message(message.chat.id, 'bssid: <нет bssid>')
                        bot.send_message(message.chat.id, 'key:')
                        bot.send_message(message.chat.id, value['key'])
                        if value['wps'] != '': bot.send_message(message.chat.id, 'wps pin: ' + value['wps'])
                        else: bot.send_message(message.chat.id, '<нет WPS пина>')
                else: bot.send_message(message.chat.id, 'Нет результатов :(')
            elif tmp[0] == '/wps':
                r = requests.get('http://3wifi.stascorp.com/api/apiwps?key={}&bssid={}'.format(API_key, tmp[1]))
                result = r.json()
                if len(result['data']) > 0:
                    result = result['data'][tmp[1].upper()]['scores']
                    for value in result:
                        bot.send_message(message.chat.id, 'Name: ' + value['name'])
                        bot.send_message(message.chat.id, value['value'])
                        bot.send_message(message.chat.id, 'Score: ' + str(value['score']))
                else: bot.send_message(message.chat.id, 'Нет результатов :(')
        else: bot.send_message(message.chat.id, 'Команда не найдена :( Отправь "help" для получения списка команд')
    except: bot.send_message(message.chat.id, 'Произошла ошибка :( Жди, когда 3wifi заработает. Если же он работает - отпиши автору о баге')


while API_key == '':
    try:
        r = requests.post('http://3wifi.stascorp.com/api/apikeys', data = {'login':'antichat', 'password':'antichat'})
        result = r.json()
        if result['result']: API_key = result['data'][0]['key']
    except: print('Problem with 3wifi')
print("API key is " + API_key)

bot.polling(none_stop=True)
