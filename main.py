import requests
import threading
from datetime import datetime
import sqlite3
from config import t_api, w_api, commands
import schedule
import time

class BotHandler:

    def __init__(self, token):
        self.token = token
        self.api_url = "https://api.telegram.org/bot{}/".format(token)
        self.db = sqlite3.connect('mydb.db', check_same_thread=False)
        self.check_db()

    def check_db(self):
        cursor = self.db.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='notes'")
        if cursor.fetchall() == []:
            cursor.execute("CREATE TABLE notes ('id', 'city', 'date')")

    def send_notes(self):
        cursor = self.db.cursor()
        if cursor.execute("SELECT COUNT(*) FROM notes").fetchall()[0][0] > 0:
            cursor.execute("SELECT * FROM notes")
            users = cursor.fetchall()
            for user in users:
                self.send_weather_info(user[1], int(user[0]))

    def change_notes(self, id, city):
        cursor = self.db.cursor()
        cursor.execute("UPDATE albums SET city = '{}' WHERE id = '{}'".format(id, city))
        self.db.commit()

    def add_notes(self, id, city):
        cursor = self.db.cursor()
        cursor.execute("INSERT INTO notes VALUES ('{}','{}','{}')".format(id, city, datetime.now().strftime('%x')))
        self.db.commit()

    def rem_notes(self, id):
        cursor = self.db.cursor()
        cursor.execute("DELETE FROM notes WHERE id = '{}'".format(id))
        self.db.commit()

    def get_updates(self, offset=None, timeout=30):
        method = 'getUpdates'
        resp = requests.get(self.api_url + method, params={'timeout': timeout, 'offset': offset})
        result_json = resp.json()['result']
        return result_json

    def _send_message(self, chat_id, text):

        method = 'sendMessage'
        resp = requests.post(self.api_url + method, params={'chat_id': chat_id, 'text': text})
        return resp

    def get_last_update(self):
        get_result = self.get_updates()
        if len(get_result) > 0:
            last_update = get_result[-1]
        else:
            last_update = get_result[len(get_result)]
        return last_update

    def send_command_ans(self, text, city, id):
        if text == '/help':
            self._send_message(id, 'Если вы введете название какого-то либо города, '
                                   'бот выведет погоду в этом городе на сегодня.\n'
                                   'Команды:\n'
                                   '/add <название города> - добавить уведомление(каждый день в 6 утра по Ульяновскому '
                                   'времени  бот будет отсыласть уведомление о погоде в данном городе);\n'
                                   '/change <название города> - изменить название города для уведомлений\n'
                                   '/remove - отменить рассылку уведомлений')
        elif text == '/add' and Weather().check(city):
            self.add_notes(id, city)
            self._send_message(id, 'Каждое утро вам будет рассылаться уведомление о городе {}'.format(city))
        elif text == '/change' and Weather().check(city):
            self.change_notes(id, city)
            self._send_message(id, 'Город для рассылку уведомлений был изменен на {}'.format(city))
        elif text == '/remove' and text == city:
            self.rem_notes(id)
            self._send_message(id, 'Рассылка уведомлений была отключена')
        else:
            self._send_message(id, 'Что пошло не так. Для получения информации о боте напишите /help')

    def send_weather_info(self, text, id):
        weather = Weather().get_weather(text)
        if weather['cod'] == 400 or len(weather['list']) == 0:
            self._send_message(id, 'Мы не знаем такого города)')
        else:
            self._send_message(id, 'температура в городе {} варируется от  {} до {} '
                               .format(weather['list'][0]['name'], round(weather['list'][0]['main']['temp_max']),
                                       round(weather['list'][0]['main']['temp_min'])))


class Weather:

    def check(self, city):
        url = "http://api.openweathermap.org/data/2.5/find"
        api = w_api
        res = requests.get(url, params={'q': city, 'type': 'like',
                                        'units': 'metric', 'lang': 'ru', 'APPID': api})
        data = res.json()
        return not (data['cod'] == 400 or len(data['list']) == 0)

    def get_weather(self, city):
        url = "http://api.openweathermap.org/data/2.5/find"
        api = w_api
        res = requests.get(url, params={'q': city, 'type': 'like',
                                        'units': 'metric', 'lang': 'ru', 'APPID': api})
        data = res.json()
        return data


class Looper:

    def looper(self):
        schedule.every().day.at('08:00').do(weather_bot.send_notes, )

        while True:
            schedule.run_pending()
            time.sleep(1)


def main():
    new_offset = None

    while True:
        weather_bot.get_updates(new_offset)
        last_update = weather_bot.get_last_update()
        last_update_id = last_update['update_id']
        last_chat_id = last_update['message']['chat']['id']
        last_chat_text = last_update['message']['text']
        words_in_text = last_chat_text.split(' ', 1)
        if commands.count(words_in_text[0]) > 0:
            weather_bot.send_command_ans(words_in_text[0], words_in_text[-1], last_chat_id)
        else:
            weather_bot.send_weather_info(last_chat_text, last_chat_id)
        new_offset = last_update_id + 1


if __name__ == '__main__':
    weather_bot = BotHandler(t_api)
    x = threading.Thread(target=Looper().looper, daemon=True, )
    x.start()
    while True:
        try:
            main()
        finally:
            continue
