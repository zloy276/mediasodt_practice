import threading
from config import t_api, w_api
import schedule
import time
import models


def looper():
    db = models.DataBase('mydb.db')
    schedule.every().day.at('06:00').do(models.BotHandler(t_api, db).send_notes, )#итоговое
    #schedule.every(5).seconds.do(models.BotHandler(t_api, db).send_notes, )# для тестировок
    while True:
        schedule.run_pending()
        time.sleep(1)


def main():
    x = threading.Thread(target=looper, daemon=True, )
    x.start()
    commands = ['/help', '/add', '/change', '/remove', '/start', ]
    modes = ['/weather', '/translate']
    new_offset = None
    db = models.DataBase('mydb.db')
    weather_bot = models.BotHandler(t_api, db)

    while True:
        messages = weather_bot.get_updates(new_offset)
        if len(messages) > 0:
            for message in messages:
                message_id = message['message']['chat']['id']
                new_offset = message['update_id'] + 1
                message_text = message['message']['text']
                words_in_message = message_text.split(' ', 1)
                command = words_in_message[0]
                com_attr = None
                if len(words_in_message)>1:
                    com_attr = words_in_message[1]
                if command in commands:
                    weather_bot.commands(message_id, command, com_attr)
                elif command in modes and com_attr is None:
                    weather_bot.change_mode(message_id, command)
                else:
                    weather_bot.send_info(message_id, message_text.capitalize())
        else:
            continue


if __name__ == '__main__':
    main()
