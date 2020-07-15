import requests
from datetime import datetime
import sqlite3
from config import w_api


class DataBase:  # надо довести до ума работу с бд
    def __init__(self, name):
        self.db = sqlite3.connect(name, check_same_thread=False)
        self.check_db()

    def check_db(self):
        cursor = self.db.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='notes'")
        if not cursor.fetchall():
            cursor.execute("CREATE TABLE notes ('id', 'city', 'date')")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='chats'")
        if not cursor.fetchall():
            cursor.execute("CREATE TABLE chats ('id', 'mode')")
        cursor.close()

    def change_notes(self, send_id, pref_city, new_city):
        cursor = self.db.cursor()
        cursor.execute("UPDATE notes SET city = '{}' WHERE id = '{}' AND city = '{}'".format(new_city.capitalize,
                                                                                             send_id,
                                                                                             pref_city.capitalize()))
        self.db.commit()
        cursor.close()

    def add_notes(self, send_id, city):
        cursor = self.db.cursor()
        cursor.execute("SELECT * FROM notes WHERE id = '{}' AND city = '{}'".format(send_id, city.capitalize()))
        if not cursor.fetchall():
            cursor.execute("INSERT INTO notes VALUES ('{}','{}')".format(send_id, city.capitalize()))
            self.db.commit()
            cursor.close()
            return True
        cursor.close()
        return False

    def rem_notes(self, table, send_id, city=None):
        cursor = self.db.cursor()
        if city is None:
            cursor.execute("DELETE FROM notes WHERE id = '{}'".format(send_id))
        else:
            cursor.execute("DELETE FROM {} WHERE id = '{}' AND city = '{}'".format(table, send_id, city.capitalize()))
        self.db.commit()
        cursor.close()

    def check_note(self, send_id, city):
        cursor = self.db.cursor()
        cursor.execute("SELECT * FROM notes WHERE id = '{}' AND city = '{}'".format(send_id, city.capitalize()))
        res = len(cursor.fetchall()) != 0
        cursor.close()
        return res

    def get_info(self, ):
        cursor = self.db.cursor()
        cursor.execute("SELECT * FROM notes")
        res = cursor.fetchall()
        cursor.close()
        return res

    def get_chat_mode(self, send_id):
        cursor = self.db.cursor()
        cursor.execute("SELECT * FROM chats WHERE id = '{}'".format(send_id))
        if cursor.fetchall():
            res = cursor.execute("SELECT * FROM chats WHERE id = '{}'".format(send_id)).fetchall()[0][1]
        else:
            cursor.execute("INSERT INTO chats VALUES ('{}', '{}')".format(send_id, 'weather'))
            self.db.commit()
            res = 'weather'
        cursor.close()
        return res

    def change_mode(self, send_id, mode):
        cursor = self.db.cursor()
        cursor.execute("SELECT * FROM chats WHERE id = '{}'".format(send_id, mode))
        if not cursor.fetchall():
            cursor.execute("INSERT INTO chats VALUES ('{}', '{}')".format(send_id, mode))
            self.db.commit()
        else:
            cursor.execute("UPDATE chats SET mode = '{}' WHERE id = '{}'".format(mode, send_id))
            self.db.commit()
        cursor.close()


class BotHandler:

    def __init__(self, token, db):
        self.token = token
        self.api_url = "https://api.telegram.org/bot{}/".format(token)
        self.db = db

    def send_notes(self):
        users = self.db.get_info()
        for send_id, city in users:
            if WeatherHandler().check(city):
                weather = WeatherHandler().get_weather(city)
                self.send_message(send_id, 'В городе {} сегодня ожидается температура от {} до {}'
                                  .format(city, round(weather['list'][0]['main']['temp_min']),
                                          round(weather['list'][0]['main']['temp_max'])))

    def get_updates(self, offset=None, timeout=1):
        method = 'getUpdates'
        resp = requests.get(self.api_url + method, params={'timeout': timeout, 'offset': offset})
        result_json = resp.json()['result']
        return result_json

    def send_message(self, chat_id, text):
        method = 'sendMessage'
        resp = requests.post(self.api_url + method, params={'chat_id': chat_id, 'text': text})
        return resp

    def commands(self, send_id, command, text=None):
        cities = []
        if text is not None:
            cities = text.split('_')
        if command == '/help' and text is None:
            self.send_help(send_id)
        elif command == '/add' and WeatherHandler().check(text):
            self.add_notifications(send_id, text)
        elif command == '/change' and len(cities) == 2 and WeatherHandler.mas_check(cities):
            self.change_notifications(send_id, cities)
        elif command == '/remove':
            self.remove_notifications(send_id, text)
        elif command == '/start' and text is None:
            self.send_start(send_id)
        else:
            self.send_message(send_id, 'Что пошло не так. Для получения информации о боте напишите /help')

    def send_start(self, send_id):
        self.send_message(send_id, 'Здравствуйте, это мой небольшой бот, который пока что умеет информировать о '
                                   'состоянии погоды в любом городе и рассылать ежедневные прогнозы. В разработке '
                                   'находится возможность перевода текста. Для получения '
                                   'большей информации напишите /help.')

    def remove_notifications(self, send_id, text = None):
        if text is None:
            self.db.rem_notes('notes', send_id)
            self.send_message(send_id, 'Рассылка всех уведомлений была отключена')
        else:
            if self.db.check_note(send_id, text):
                self.db.rem_notes('notes', send_id, text)
                self.send_message(send_id, 'Рассылка уведомлений о городе {} была отключена'.format(text.capitalize()))
            else:
                self.send_message(send_id, 'Мы не нашли {} в списке ваших уведомлений'.format(text.capitalize()))

    def change_notifications(self, send_id, cities):
            self.db.change_notes(send_id, cities[0], cities[1])
            self.send_message(send_id, 'Город для рассылку уведомлений был изменен c {} на {}'
                              .format(cities[0].capitalize(), cities[1].capitalize()))

    def add_notifications(self, send_id, text):
            if self.db.add_notes(send_id, text):
                self.send_message(send_id, 'Каждое утро вам будет рассылаться уведомление о городе {}'.
                                  format(text.capitalize()))
            else:
                self.send_message(send_id, 'Город {} уже есть в списке ваших уведомлений'.format(text.capitalize()))

    def send_help(self, send_id):
        self.send_message(send_id, 'Бот работает в нескольких режимах:\n'
                                   '/weather- устанавливает режим погоды. Любое сообщение которое будет отправлено '
                                   'боту (не считая команд) будет считаться за название города и бот выведет погоду в '
                                   'этом городе на сегодня;\n'
                                   '/translate- устанавливает режим переводчика любое сообщение будет которое вы '
                                   'отправите боту будет переведено и отправленно вам\n.'
                                   'Команды:\n'
                                   '/add <название города> - добавить уведомление(каждый день в 6 утра по Ульяновскому '
                                   'времени  бот будет отсыласть уведомление о погоде в данном городе);\n'
                                   '/change <название города который вы хотите изменить>_<название нового города> - '
                                   'изменить название города для уведомлений\n'
                                   '/remove <название города>- отменить рассылку уведомлений, если не вводить город, '
                                   'удалятся все уведомления.\n')

    def send_info(self, send_id, text):
        mode = self.db.get_chat_mode(send_id)
        if mode == 'weather':
            self.send_info_weather(send_id, text)
        elif mode == 'translate':
            self.send_info_translate(send_id)
        else:
            self.db.change_mode(send_id, 'weather')
            self.send_message(send_id, 'Простите,у нас произошла какая-то ошибка и ваш режим будет автоматически '
                                       'изменен на режим погоды')

    def send_info_translate(self, send_id):
        self.send_message(send_id, 'К сожалению этот функционал пока что не реализован, потому что я не смог найти API '
                                   'для переводчика(у Google- платный, а яндекс приостановил выдачу бесплатных). Этим '
                                   'я хотел показать возможность смены режимов и ведения беседы с каждым человеком, '
                                   'фиксируя данные о даилоге с каждым бользователем в базе данных.')

    def send_info_weather(self, send_id, text):
        if WeatherHandler().check(text):
            weather = WeatherHandler().get_weather(text)
            self.send_message(send_id, 'В городе {} сегодня ожидается'
                                       ' температура от {} до {}'.format(text,
                                                                         round(weather['list'][0]['main']['temp_min']),
                                                                         round(weather['list'][0]['main']['temp_max'])))
        else:
            self.send_message(send_id, 'Что-то пошло не так, попробуйте еще раз.')

    def change_mode(self, send_id, command):
        if command == '/weather':
            self.db.change_mode(send_id, 'weather')
            self.send_message(send_id, 'Установлен режим погоды')
        elif command == '/translate':
            self.db.change_mode(send_id, 'translate')
            self.send_message(send_id, 'Установлен режим перевода')
        else:
            self.send_message(send_id, 'Произошла какая-то ошибка, попробуйте еще раз')


class WeatherHandler:
    urls = "http://api.openweathermap.org/data/2.5/find"
    api = w_api

    def mas_check(self, *args):
        for i in args:
            if not (self.check(i)):
                return False
        return True

    def check(self, city):
        count = 0
        data = self.get_weather(city)
        if 'count' in data:
            count = data['count']
        return count > 0

    def get_weather(self, city):
        res = requests.get(self.urls, params={'q': city, 'type': 'like',
                                              'units': 'metric', 'lang': 'ru', 'APPID': self.api})
        data = res.json()
        return data
