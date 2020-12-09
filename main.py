import re
import requests
import config
import dbworker
import telebot
from tabulate import tabulate
from bs4 import BeautifulSoup
from selenium import webdriver as wb
#Чтобы запускать парсинг в невидимом режиме
ff = 'C:/Users/Nika/chromedriver.exe'
chrome_option = wb.ChromeOptions()
chrome_option.add_argument("headless")
driver = wb.Chrome(executable_path=ff,chrome_options=chrome_option)
from time import sleep
import pandas as pd
import pandasql as ps
from pandasql import sqldf

bot = telebot.TeleBot(config.token)

pict = 'http://dvf-vavt.ru/images/Videogalereya/gettyimages-174831214-612x612.jpg'


def FunTickets(data):
    # TO DO if от месяца - чтобы выбирать еще 2021 год
    driver.get('https://www.ticketland.ru/search/performance/?mnd=' + data + '.2020&mxd=' + data + '.2020')
    res = []
    MyPage = BeautifulSoup(driver.page_source, 'lxml')
    sleep(1.5)
    # Находим число найденных мероприятий во фразе "Найдено N мероприятий"
    events = MyPage.find_all('p', {'class': 'mt-2'})[0].text
    events = re.findall('\\d+', events)
    count_event = int(events[0])

    f_count_event = min(20, count_event)

    for ii in range(f_count_event):
        # Название мероприятия
        title = MyPage.find_all('a', {'class': 'card-search__name'})[ii].text
        title = title.strip()

        # Площадка
        teatre = MyPage.find_all('a', {'class': 'card-search__building text-anchor text-truncate'})[ii].text
        teatre = teatre.strip()

        # Строка с тэгами
        tags = MyPage.find_all('p', {'class': 'card-search__category d-none d-lg-block'})[ii].text

        # разделяем строку вида: 2 ноя•пн•19:00•осталось более 100 билетов
        strr = MyPage.find_all('a', {'class': 'text-uppercase'})[ii].text
        strr_mas = strr.split('•')

        if len(strr_mas) == 4:

            ost = strr_mas[3].strip()
            ost = re.findall('([0-9]+)', ost)
            ostt = int(ost[0])
        else:
        #Обрабатываем случай : не указан день, время и день недели
            ost = strr_mas[1].strip()
            ost = re.findall('([0-9]+)', ost)
            ostt = int(ost[0])

        # разделяем строку вида: 400 – 2 000 руб. или от 1 600 руб.
        price = MyPage.find_all('p', {'class': 'card-search__price'})[ii].text
        price_mas = price.split('–')
        minc = re.findall('\\d+', price_mas[0].strip())
        mminc = float(''.join(minc))

        if price.find('–') > -1:  # если указан диапазон 400 – 2 000 руб.
            maxc = re.findall('\\d+', price_mas[1].strip())
            mmaxc = float(''.join(maxc))
        else:  # если указано от от 1 600 руб.
            mmaxc = 0

        res.append({'title': title,
                    'tags': tags,
                    'teatre': teatre,
                    'ost': ostt,
                    'min_price': mminc,
                    'max_price': mmaxc})
    df = pd.DataFrame(res)
    #TO DO сделать дубли записей, разделив tags, в которых несколько категорий через запятую
    #TO DO сделать проход по всем страницам сайта
    #TO DO записать датафрейм в файл и в диалоге далее использовать данные из файла
    return df


@bot.message_handler(commands=["info"])
def cmd_info(message):
    bot.send_message(message.chat.id, "Информация о данном боте: \n"
                                      "Бот собирает информацию о мероприятиях на сайте ticketland.ru.\n"
                                      "Для получения информации введи желаемую дату мероприятия \n"
                                      "Вначале бот выводит таблицу с категориями событий и их количество \n"
                                      "Далее нужно ввести категорию, по которой бот выведет список событий\n"
                                      "Бот укажет Название и место события, количество свободных билетов и цену\n"
                                      "При желании, категории можно указывать несколько раз\n"
                                      "Введи /reset чтобы запустить новый диалог с ботом.")


@bot.message_handler(commands=["commands"])
def cmd_commands(message):
    bot.send_message(message.chat.id, "/reset - перезапуск бота.\n"
                                      "/start - создать новый диалог.\n"
                                      "/info - получить информацию о работе бота\n")


# По команде /reset будем сбрасывать состояния, возвращаясь к началу диалога
@bot.message_handler(commands=["reset"])
def cmd_reset(message):
    bot.send_message(message.chat.id, "Начнем заново.\n"
                                      "Введи дату, на которую хочешь получить мероприятия Формат ввода: dd.mm.\n"
                                      "Введи /info или /commands чтобы получить информацию о боте.")
    bot.send_photo(message.chat.id, pict)
    dbworker.set_state(message.chat.id, config.States.S_ENTER_DAY.value)
    dbworker.del_state(str(message.chat.id) + 'day')
    dbworker.del_state(str(message.chat.id) + 'tags')


@bot.message_handler(commands=["start"])
def cmd_start(message):
    dbworker.del_state(str(message.chat.id) + 'day')
    dbworker.del_state(str(message.chat.id) + 'tags')
    dbworker.set_state(message.chat.id, config.States.S_START.value)
    state = dbworker.get_current_state(message.chat.id)
    # Под "остальным" понимаем состояние "0" - начало диалога
    bot.send_photo(message.chat.id, pict)
    bot.send_message(message.chat.id, "Привет! Я Nikabot :) \n"
                                      "Введи дату в формате ДД.ММ, чтобы найти билеты на мероприятия.\n"
                                      "Введи /info для получения справочной информации.\n"
                                      "Введи /commands чтобы получить список команд.\n"
                                      "Введи /reset чтобы сбросить сеанс и запустить поиск заново.")

    dbworker.set_state(message.chat.id, config.States.S_ENTER_DAY.value)


@bot.message_handler(func=lambda message: dbworker.get_current_state(message.chat.id) == config.States.S_ENTER_DAY.value
                     and message.text.strip().lower() not in ('/reset', '/info', '/start', '/commands',
                                                              '/listtags'))
def get_day(message):
    day = dbworker.del_state(str(message.chat.id)+'day') # Удалить день
    dbworker.set_state(message.chat.id, config.States.S_ENTER_LISTTAGS.value)
    date = message.text
    dbworker.set_state(str(message.chat.id) + 'day', date)  # Записать день

    bot.send_message(message.chat.id, "Выбери и введи категорию.\n"
                                      "Ниже - количество найденных событий по категориям")
    x = FunTickets(date)
    query = """
    select tags "Категория", count(1) "Событий", sum(ost) "Билетов", min(min_price) "Мин цена"
    from x
    group by tags
    """
    for_sending  = ps.sqldf(query, locals())
    bot.send_message(message.chat.id, tabulate(for_sending, headers=for_sending.columns, tablefmt="pipe"))


@bot.message_handler(func=lambda message: dbworker.get_current_state(message.chat.id) == config.States.S_ENTER_LISTTAGS.value
                     and message.text.strip().lower() not in ('/reset', '/info', '/start', '/commands'))
def listtags(message):
    dbworker.del_state(str(message.chat.id) + 'tags') # Перезапись категории
    bot.send_message(message.chat.id, 'Выбираю мероприятия...')
    day = dbworker.get_current_state(str(message.chat.id) + 'day').strip()
    #dbworker.set_state(message.chat.id, config.States.S_START.value)
    tag = message.text
    x = FunTickets(day)
    for_sending = x[(x.tags == tag)].head(5)
    bot.send_message(message.chat.id, tabulate(for_sending, headers=for_sending.columns, tablefmt="pipe"))

@bot.message_handler(func=lambda message: message.text not in ('/reset', '/info', '/start', '/commands'))
def cmd_sample_message(message):
    bot.send_message(message.chat.id, "Слушай, я Nikabot!\n"
                                      "Я тебя не понимаю :(\n"
                                      "Введи /start чтобы начать диалог заново. \n"
                                      "Введи /info чтобы получить информацию обо мне.\n"
                                      "Введи /commands чтобы получить список комманд.")
    bot.send_photo(message.chat.id, pict)


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    bot.infinity_polling()


# See PyCharm help at https://www.jetbrains.com/help/pycharm/

