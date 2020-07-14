import threading
from config import t_api, w_api
import schedule
import time
import models


def looper():
    db = models.DataBase('mydb.db')
    #schedule.every().day.at('06:00').do(models.BotHandler(t_api, db).send_notes, )#итоговое
    schedule.every(5).seconds.do(models.BotHandler(t_api, db).send_notes, )# для тестировок
    while True:
        schedule.run_pending()
        time.sleep(1)


def main():
    x = threading.Thread(target=looper, daemon=True, )
    x.start()
    commands = ['/help', '/add', '/change', '/remove', ]
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
                if words_in_message[0] in commands and len(words_in_message) == 2:
                    command = words_in_message[0]
                    attr = words_in_message[1]
                    weather_bot.commands(message_id, command, attr)
                elif words_in_message[0] in commands and len(words_in_message) == 1:
                    command = words_in_message[0]
                    weather_bot.commands(message_id, command)
                else:
                    weather_bot.send_info(message_id, message_text.capitalize())
        else:
            continue


if __name__ == '__main__':
    main()
