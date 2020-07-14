import requests
import threading
from datetime import datetime
import sqlite3
from config import t_api, w_api
import schedule
import time


class DataBase:
    def __init__(self, name):
        self.db = sqlite3.connect(name, check_same_thread=False)
        self.check_db()

    def check_db(self):
        cursor = self.db.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='notes'")
        if cursor.fetchall() == []:
            cursor.execute("CREATE TABLE notes ('id', 'city', 'date')")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='chats'")
        if cursor.fetchall() == []:
            cursor.execute("CREATE TABLE chats ('id', 'mode')")
        cursor.close()

    def change_notes(self, id, pref_city, new_city):
        cursor = self.db.cursor()
        cursor.execute("UPDATE notes SET city = '{}' WHERE id = '{}' AND city = '{}'".format(new_city.capitalize, id,
                                                                                             pref_city.capitalize()))
        self.db.commit()
        cursor.close()

    def add_notes(self, id, city):
        cursor = self.db.cursor()
        cursor.execute("SELECT * FROM notes WHERE id = '{}' AND city = '{}'".format(id, city.capitalize()))
        if cursor.fetchall() == []:
            cursor.execute("INSERT INTO notes VALUES ('{}','{}','{}')".format(id, city.capitalize(),
                                                                              datetime.now().strftime('%x')))
            self.db.commit()
            cursor.close()
            return True
        cursor.close()
        return False

    def rem_notes(self, id, city):
        cursor = self.db.cursor()
        cursor.execute("DELETE FROM notes WHERE id = '{}' AND city = '{}'".format(id, city.capitalize()))
        self.db.commit()
        cursor.close()

    def check_note(self, id, city):
        cursor = self.db.cursor()
        cursor.execute("SELECT * FROM notes WHERE id = '{}' AND city = '{}'".format(id, city.capitalize()))
        res = len(cursor.fetchall()) != 0
        cursor.close()
        return res

    def rem_all_notes(self, id):
        cursor = self.db.cursor()
        cursor.execute("DELETE FROM notes WHERE id = '{}'".format(id))
        self.db.commit()
        cursor.close()

    def get_info(self, ):
        cursor = self.db.cursor()
        cursor.execute("SELECT * FROM notes")
        res = cursor.fetchall()
        cursor.close()
        return res


class BotHandler:

    def __init__(self, token, db):
        self.token = token
        self.api_url = "https://api.telegram.org/bot{}/".format(token)
        self.db = db

    def send_notes(self):
        users = self.db.get_info()
        for id, city, date in users:
            self.send_info(id, city)

    def get_updates(self, offset=None, timeout=1):
        method = 'getUpdates'
        resp = requests.get(self.api_url + method, params={'timeout': timeout, 'offset': offset})
        result_json = resp.json()['result']
        return result_json

    def send_message(self, chat_id, text):
        method = 'sendMessage'
        resp = requests.post(self.api_url + method, params={'chat_id': chat_id, 'text': text})
        return resp

    def commands(self, id, command, text=None):
        cities = []
        if text is not None:
            cities = text.split('_')
        if command == '/help' and text is None:
            self.send_message(id, 'Если вы введете название какого-то либо города, '
                                  'бот выведет погоду в этом городе на сегодня.\n'
                                  'Команды:\n'
                                  '/add <название города> - добавить уведомление(каждый день в 6 утра по Ульяновскому '
                                  'времени  бот будет отсыласть уведомление о погоде в данном городе);\n'
                                  '/change <название города который вы хотите изменить>_<название нового города> - '
                                  'изменить название города для уведомлений\n'
                                  '/remove <название города>- отменить рассылку уведомлений, если не вводить город, '
                                  'удалятся все уведомления')
        elif command == '/add' and WeatherHandler().check(text):
            if self.db.add_notes(id, text):
                self.send_message(id, 'Каждое утро вам будет рассылаться уведомление о городе {}'.
                                  format(text.capitalize()))
            else:
                self.send_message(id, 'Город {} уже есть в списке ваших уведомлений'.format(text.capitalize()))
        elif command == '/change' and len(cities) == 2 and WeatherHandler.mas_check(cities):
            self.db.change_notes(id, cities[0], cities[1])
            self.send_message(id, 'Город для рассылку уведомлений был изменен c {} на {}'
                              .format(cities[0].capitalize(), cities[1].capitalize()))
        elif command == '/remove' and text is None:
            self.db.rem_all_notes(id)
            self.send_message(id, 'Рассылка всех уведомлений была отключена')
        elif text == '/remove' and WeatherHandler().check(text):
            if self.db.check_note(id, text):
                self.db.rem_notes(id, text)
                self.send_message(id, 'Рассылка уведомлений о городе {} была отключена'.format(text.capitalize()))
            else:
                self.send_message(id, 'Мы не нашли {} в списке ваших уведомлений'.format(text.capitalize()))
        else:
            self.send_message(id, 'Что пошло не так. Для получения информации о боте напишите /help')

    def send_info(self, id, text):
        if WeatherHandler().check(text):
            weather = WeatherHandler().get_weather(text)
            self.send_message(id, 'В городе {} сегодня ожидается'
                                  ' температура от {} до {}'.format(text,
                                                                    round(weather['list'][0]['main']['temp_min']),
                                                                    round(weather['list'][0]['main']['temp_max'])))
        else:
            self.send_message(id, 'Что-то пошло не так, попробуйте еще раз.')


class WeatherHandler:
    urls = "http://api.openweathermap.org/data/2.5/find"
    api = w_api

    def mas_check(self, *args):
        for i in args:
            if not (self.check(i)):
                return False
        return True

    def check(self, city):
        data = self.get_weather(city)
        return data['cod'] != '400' and 'list' in data

    def get_weather(self, city):
        res = requests.get(self.urls, params={'q': city, 'type': 'like',
                                              'units': 'metric', 'lang': 'ru', 'APPID': self.api})
        data = res.json()
        return data
