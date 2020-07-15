import requests
from datetime import datetime
import sqlite3
from config import t_api, w_api


class DataBase:    #надо довести до ума работу с бд
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

    def change_notes(self, id, pref_city, new_city):
        cursor = self.db.cursor()
        cursor.execute("UPDATE notes SET city = '{}' WHERE id = '{}' AND city = '{}'".format(new_city.capitalize, id,
                                                                                             pref_city.capitalize()))
        self.db.commit()
        cursor.close()

    def add_notes(self, id, city):
        cursor = self.db.cursor()
        cursor.execute("SELECT * FROM notes WHERE id = '{}' AND city = '{}'".format(id, city.capitalize()))
        if not cursor.fetchall():
            cursor.execute("INSERT INTO notes VALUES ('{}','{}','{}')".format(id, city.capitalize(),
                                                                              datetime.now().strftime('%x')))
            self.db.commit()
            cursor.close()
            return True
        cursor.close()
        return False

    def rem_notes(self, table, id, city=None):
        cursor = self.db.cursor()
        if city is None:
            cursor.execute("DELETE FROM notes WHERE id = '{}'".format(id))
        else:
            cursor.execute("DELETE FROM {} WHERE id = '{}' AND city = '{}'".format(table, id, city.capitalize()))
        self.db.commit()
        cursor.close()

    def check_note(self, id, city):
        cursor = self.db.cursor()
        cursor.execute("SELECT * FROM notes WHERE id = '{}' AND city = '{}'".format(id, city.capitalize()))
        res = len(cursor.fetchall()) != 0
        cursor.close()
        return res

    def get_info(self, ):
        cursor = self.db.cursor()
        cursor.execute("SELECT * FROM notes")
        res = cursor.fetchall()
        cursor.close()
        return res

    def get_chat_mode(self, id):
        cursor = self.db.cursor()
        cursor.execute("SELECT * FROM chats WHERE id = '{}'".format(id))
        if cursor.fetchall():
            res = cursor.execute("SELECT * FROM chats WHERE id = '{}'".format(id)).fetchall()[0][1]
        else:
            cursor.execute("INSERT INTO chats VALUES ('{}', '{}')".format(id, 'wheather'))
            self.db.commit()
            res = 'wheather'
        cursor.close()
        return res

    def change_mode(self, id, mode):
        cursor = self.db.cursor()
        cursor.execute("SELECT * FROM chats WHERE id = '{}'".format(id, mode))
        if not cursor.fetchall():
            cursor.execute("INSERT INTO chats VALUES ('{}', '{}')".format(id, mode))
            self.db.commit()
        else:
            cursor.execute("UPDATE chats SET mode = '{}' WHERE id = '{}'".format(mode, id))
            self.db.commit()
        cursor.close()


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
            self.send_message(id, 'Бот работает в нескольких режимах:\n'
                                  '/wheather- устанавливает режим погоды. Любое сообщение которое будет отправлено боту'
                                  '(не считая команд) будет считаться за название города и бот выведет погоду в '
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
            self.db.rem_notes('notes', id)
            self.send_message(id, 'Рассылка всех уведомлений была отключена')
        elif command == '/remove':
            if self.db.check_note(id, text):
                self.db.rem_notes('notes', id, text)
                self.send_message(id, 'Рассылка уведомлений о городе {} была отключена'.format(text.capitalize()))
            else:
                self.send_message(id, 'Мы не нашли {} в списке ваших уведомлений'.format(text.capitalize()))
        elif command == '/start' and text is None:
            self.send_message(id, 'Здравствуйте, это мой небольшой бот, который пока что умеет информировать о '
                                  'состоянии погоды в любом городе и рассылать ежедневные прогнозы. В разработке '
                                  'находится возможность перевода текста. Для получения '
                                  'большей информации напишите /help.')
        elif command == '/wheather' and text is None:
            self.db.change_mode(id, 'wheather')
            self.send_message(id, 'Установлен режим погоды')
        elif command == '/translate' and text is None:
            self.db.change_mode(id, 'translate')
            self.send_message(id, 'Установлен режим перевода')
        else:
            self.send_message(id, 'Что пошло не так. Для получения информации о боте напишите /help')

    def send_info(self, id, text):
        mode = self.db.get_chat_mode(id)
        if mode == 'wheather':
            self.send_info_wheather(id, text)
        elif mode == 'translate':
            self.send_info_translate(id, text)
        else:
            self.db.change_mode(id, 'wheather')
            self.send_message(id, 'Простите,у нас произошла какая-то ошибка и ваш режим будет автоматически изменен '
                                  'на режим погоды')

    def send_info_translate(self, id, text):
        self.send_message(id, 'К сожалению этот функционал пока что не реализован, потому что я не смог найти API '
                              'для переводчика(у Google- платный, а яндекс приостановил выдачу бесплатных). Этим я '
                              'хотел показать возможность смены режимов и ведения беседы с каждым человеком, '
                              'фиксируя данные о даилоге с каждым бользователем в базе данныхю')

    def send_info_wheather(self, id, text):
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
