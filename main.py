import re
import requests
import config
import dbworker
import telebot
from tabulate import tabulate
from bs4 import BeautifulSoup
from time import sleep
import pandas as pd
import pandasql as ps
from pandasql import sqldf
import datetime
import numpy as np
import matplotlib.pyplot as plt
import re
# настройка драйвера для работы на heroku
from selenium import webdriver as wb
from selenium.webdriver.chrome.options import Options
import os
chrome_options = wb.ChromeOptions()
chrome_options.binary_location = os.environ.get("GOOGLE_CHROME_BIN")
chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--no-sandbox")
driver = wb.Chrome(executable_path=str(os.environ.get("CHROMEDRIVER_PATH")),chrome_options = chrome_options)

driver.get("https://www.google.com")
#print(driver.page_source)

#Чтобы запускать парсинг в невидимом режиме
#ff = 'C:/Users/Nika/chromedriver.exe'
#chrome_option = wb.ChromeOptions()
#chrome_option.add_argument("headless")
#driver = wb.Chrome(executable_path=ff,chrome_options=chrome_option)


#bot = telebot.TeleBot(config.token)
load_dotenv()
TOKEN = environ.get('TOKEN')

bot = telebot.TeleBot(token=TOKEN)

pict = 'http://dvf-vavt.ru/images/Videogalereya/gettyimages-174831214-612x612.jpg'


# функция размножения строк для учета по разным категориям
def expand_col(df_src, col, sep='|'):
    di = {}
    idx = 0
    for i in df_src.iterrows():
        d = i[1]
        names = d[col].split(sep)
        for name in names:
            c = d.copy()
            c[col] = name.strip()
            di[idx] = c
            idx += 1
    df_new = pd.DataFrame(di).transpose()
    return df_new

# сам парсинг сайта
def FunTickets(data):
    # Определим введенная дата в нашем году или в будущем и передаем правильный год для поиска
    today = datetime.datetime.now()
    my_month = int(today.month)
    my_year = today.year
    next_year = my_year + 1
    p_month = int(data[3:5])
    if p_month >= my_month:
        year = my_year
        driver.get(
            'https://www.ticketland.ru/search/performance/?mnd=' + data + '.' + str(year) + '&mxd=' + data + '.' + str(
                year))
    else:
        year = next_year
        driver.get(
            'https://www.ticketland.ru/search/performance/?mnd=' + data + '.' + str(year) + '&mxd=' + data + '.' + str(
                year))
    res = []
    p = 0
    MyPage = BeautifulSoup(driver.page_source, 'lxml')
    sleep(0.5)
    # Находим число найденных мероприятий во фразе "Найдено N мероприятий"

    events = MyPage.find_all('span', {'class': 'text-bold sections-buttons__btn-count'})[0].text
    events = re.findall('\\d+', events)
    count_event = int(events[0])

    # Находим количество страниц
    if count_event <= 20:
        count_sheet = 1
    elif count_event // 20 == count_event / 20:
        count_sheet = count_event // 20
    else:
        count_sheet = count_event // 20 + 1

    # Проходимся по страницам
    for i in range(1, count_sheet + 1):
        if i > 1:
            driver.get('https://www.ticketland.ru/search/performance/?page=' + str(i) + '&mnd=' + data + '.' + str(
                year) + '&mxd=' + data + '.' + str(year))
            MyPage = BeautifulSoup(driver.page_source, 'lxml')
            sleep(1.5)

        # Проходим по страницам
        if i == 1:
            f_count_event = min(20, count_event)
        elif i == count_sheet and count_event % 20 != 0:
            f_count_event = count_event % 20
        else:
            f_count_event = 20
            p = 0  # Корректировка на случай, если в кл мероприятии не указана цена ('card-search__price' на 1 меньше на странице)

        # проходим по событиям на странице
        for ii in range(f_count_event):
            # Название мероприятия
            title = MyPage.find_all('a', {'class': 'card-search__name'})[ii].text
            title = title.strip()

            # Площадка
            teatre = MyPage.find_all('a', {'class': 'card-search__building text-anchor text-truncate'})[ii].text
            teatre = teatre.strip()

            # Строка с тэгами
            tags = MyPage.find_all('p', {'class': 'card-search__category d-none d-lg-block'})[ii].text
            if len(tags) == 0:  # Цирк Никулина почему-то с пустым тегом
                tags = teatre.split()[0]

            # разделяем строку вида: 2 ноя•пн•19:00•осталось более 100 билетов
            strr = MyPage.find_all('a', {'class': 'text-uppercase'})[ii].text
            strr_mas = strr.split('•')

            # Обрабатываем случай : не указан день, время и день недели (регулярные экскурсии)
            if len(strr_mas) == 4:

                ost = strr_mas[3].strip()
                ost = re.findall('([0-9]+)', ost)
                ostt = int(ost[0])

            elif len(strr_mas) == 1:

                ost = strr_mas[1].strip()
                ost = re.findall('([0-9]+)', ost)
                ostt = int(ost[0])

            # бывает, что сайт не показывает ни количество билетов, ни цену (глюк сайта)
            else:
                ostt = 0
                mminc = 0
                mmaxc = 0
                p += 1
            # Цена билетов
            # Если не указано кол-во билетов и цена, то классов 'card-search__price' на 1 меньше
            if len(strr_mas) == 4:
                # разделяем строку вида: 400 – 2 000 руб. или от 1 600 руб.
                price = MyPage.find_all('p', {'class': 'card-search__price'})[ii - p].text
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
    df_res = expand_col(df, 'tags', sep=',')
    df_res.to_csv('events.csv', index=False)

# Рисуем красивую табличку из датафрейма пандас и сохраняем в файле категорий или событий
def good_table(data, col_width=3.0, filename="tags.png", row_height=0.625, font_size=14,
              header_color='#30355e', row_colors=['#f1f1f2', 'w'], edge_color='w',
              bbox=[0, 0, 1, 1], header_columns=0,
              ax=None, **kwargs):
    if ax is None:
        size = (np.array(data.shape[::-1]) + np.array([0, 1])) * np.array([col_width, row_height])
        fig, ax = plt.subplots(figsize=size)
        ax.axis('off')
    mpl_table = ax.table(cellText=data.values, bbox=bbox, colLabels=data.columns, **kwargs)
    mpl_table.auto_set_font_size(False)
    mpl_table.set_fontsize(font_size)

    for k, cell in mpl_table._cells.items():
        cell.set_edgecolor(edge_color)
        if k[0] == 0 or k[1] < header_columns:
            cell.set_text_props(weight='bold', color='w', ha='left')
            cell.set_facecolor(header_color)
        else:
            cell.set_text_props(ha='left')
            cell.set_facecolor(row_colors[k[0] % len(row_colors)])

    ax.get_figure()
    fig.savefig(filename)
    return
@bot.message_handler(commands=["info"])
def cmd_info(message):
    bot.send_message(message.chat.id, "Информация о данном боте: \n"
                                      "Бот собирает информацию о мероприятиях на сайте ticketland.ru.\n"
                                      "Для получения информации введи желаемую дату мероприятия \n"
                                      "Вначале бот выводит таблицу с категориями событий и их количество \n"
                                      "Далее нужно ввести категорию и максимально возможную цену билета\n"
                                      "Бот укажет Название и место события, количество свободных билетов и цены\n"
                                      "При желании, цены можно повыбирать, указывая несколько раз\n"
                                      "В процессе диалога можно сменить категорию событий, выбрав команду /tags\n"
                                      "Введи /reset чтобы запустить новый диалог с ботом.")


@bot.message_handler(commands=["commands"])
def cmd_commands(message):
    bot.send_message(message.chat.id, "/reset - перезапуск бота.\n"
                                      "/start - создать новый диалог.\n"
                                      "/info - получить информацию о работе бота\n"
                                      "/tags - сменить категорию событий\n")


# По команде /reset сброс состояния
@bot.message_handler(commands=["reset"])
def cmd_reset(message):
    bot.send_message(message.chat.id, "Начнем заново.\n"
                                      "Введи дату, на которую хочешь получить мероприятия Формат ввода: ДД.ММ\n"
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

@bot.message_handler(commands=["tags"])
def listtags(message):
    dbworker.del_state(str(message.chat.id) + 'tags') # Удалить категорию
    day = dbworker.get_current_state(str(message.chat.id) + 'day').strip()
    if day == '0':
        bot.send_message(message.chat.id, "Данную команду можно выбрать только после ввода желаемой даты!")
    else:
        dbworker.set_state(message.chat.id, config.States.S_ENTER_TAGS.value)
        bot.send_message(message.chat.id, "Ты выбрал дату: {} \n" 
                                     "В файле - найденные мероприятия по категориям".format(day))
        df = pd.read_csv('events.csv')
        query = """
                select tags "Категория", count(1) "Событий", sum(ost) "Билетов", min(min_price) "Мин цена"
                from df
                group by tags
                """
        df = ps.sqldf(query, locals())
        good_table(df, header_columns=0, col_width=2.0, )
        with open("tags.png", "rb") as fp:
            bot.send_document(message.chat.id, fp)
        x = ['1 - Детям', '2 - Цирк', '3 - Концерты', '4 - Мюзиклы', '5 - Шоу', '7 - Спектакли', '8 - Экскурсии'
            , '9 - Классика', '10 - Фестивали', '11 - Спорт']
        bot.send_message(message.chat.id, "Возможные категории: ")
        bot.send_message(message.chat.id, "\n".join(x))
        bot.send_message(message.chat.id, "Введи цифру нужной категории")

@bot.message_handler(func=lambda message: dbworker.get_current_state(message.chat.id) == config.States.S_ENTER_DAY.value
                     and message.text.strip().lower() not in ('/reset', '/info', '/start', '/commands'))
def get_day(message):
    date = message.text
    date_match = re.match("\d{1,2}['.']\d{1,2}", date)# формат ввода проверка
    if date_match:
        mass = date.split('.')
        if not (int(mass[0]) < 1 or int(mass[0]) > 31 or int(mass[1]) < 1 or int(mass[1]) > 12):
            bot.send_message(message.chat.id, "Получаю данные... Жди...\n")
            x = FunTickets(date)
            df = pd.read_csv('events.csv')
            query = """
                    select tags "Категория", count(1) "Событий", sum(ost) "Билетов", min(min_price) "Мин цена"
                    from df
                    group by tags
                    """
            df = ps.sqldf(query, locals())
            good_table(df, header_columns=0, col_width=2.0, )
            with open("tags.png", "rb") as fp:
                bot.send_message(message.chat.id, "В файлике - количество найденных событий по категориям")
                bot.send_document(message.chat.id, fp)

            x = ['1 - Детям', '2 - Цирк','3 - Концерты', '4 - Мюзиклы', '5 - Шоу', '7 - Спектакли', '8 - Экскурсии'
                 , '9 - Классика','10 - Фестивали', '11 - Спорт']
            bot.send_message(message.chat.id, "Возможные категории: ")
            bot.send_message(message.chat.id,"\n".join(x))
            bot.send_message(message.chat.id, "Введи цифру нужной категории")
            day = dbworker.del_state(str(message.chat.id) + 'day')  # Удалить день
            dbworker.set_state(message.chat.id, config.States.S_ENTER_TAGS.value)
            dbworker.set_state(str(message.chat.id) + 'day', date)  # Записать день
        else:# проверка на несуществующую дату
            bot.send_message(message.chat.id, 'Некорректная дата. Напомню, формат ДД.ММ, например, 31.01')
    else:# проверка формата ввода
        bot.send_message(message.chat.id, 'Не похоже, чтобы ты ввел дату. Напомню, формат ДД.ММ, например, 31.01')


@bot.message_handler(func=lambda message: dbworker.get_current_state(message.chat.id) == config.States.S_ENTER_TAGS.value
                     and message.text.strip().lower() not in ('/reset', '/info', '/start', '/commands'))
def get_tag(message):
    tag = message.text
    if tag not in ('1','2','3','4','5','6','7','8','9','10','11'):
        bot.send_message(message.chat.id, 'Ты ввел что-то не то. Напомню, нужно ввести цифру категории')
        x = ['1 - Детям', '2 - Цирк', '3 - Концерты', '4 - Мюзиклы', '5 - Шоу', '7 - Спектакли', '8 - Экскурсии',
         '9 - Классика', '10 - Фестивали', '11 - Спорт']
        bot.send_message(message.chat.id, "Возможные категории: ")
        bot.send_message(message.chat.id, "\n".join(x))
    else:
        dbworker.del_state(str(message.chat.id) + 'tags') # Удалить категорию
        dbworker.set_state(message.chat.id, config.States.S_ENTER_PRICE.value)
        dbworker.set_state(str(message.chat.id) + 'tags', tag)  # Записать категорию
        bot.send_message(message.chat.id, 'Введи бюджет на 1 билет')


@bot.message_handler(func=lambda message: dbworker.get_current_state(message.chat.id) == config.States.S_ENTER_PRICE.value
                     and message.text.strip().lower() not in ('/reset', '/info', '/start', '/commands'))
def price(message):
    price = message.text
    price_match = re.match("\d+",price) # формат ввода проверка
    if price_match:
        price_int = int(price)
        dbworker.del_state(str(message.chat.id) + 'price') # Перезапись категории
        day = dbworker.get_current_state(str(message.chat.id) + 'day').strip()
        tag = dbworker.get_current_state(str(message.chat.id) + 'tags').strip()
        bot.send_message(message.chat.id, 'Вывожу подходящие мероприятия: дата {}, категория {}'.format(day, tag))
        df = pd.read_csv('events.csv')
        x = [('1', 'Детям'), ('2','Цирк'), ('3','Концерты'), ('4','Мюзиклы'), ('5','Шоу')
            ,('7','Спектакли'), ('8','Экскурсии'),('9','Классика'), ('10','Фестивали'), ('11','Спорт')]
        for d in x: tag = tag.replace(d[0], d[1])
        df = df[(df.tags == tag) & (df.min_price <= price_int)][['title', 'teatre', 'ost', 'min_price','max_price']]
        if not df.empty:
            query = """
                select 'Событие "'||title||'", место "'||teatre||'", доступно билетов '||ost||', цены '||min_price||'-'||max_price
                as "Список событий"
                from df
                """
            df = ps.sqldf(query, locals())
            good_table(df, header_columns=0, col_width=23.0, filename="events.png")
            with open("events.png", "rb") as fp:
                bot.send_document(message.chat.id, fp)
        else:
            bot.send_message(message.chat.id, "Для данной категории не найдено событий... \n")
        bot.send_message(message.chat.id, "Измени сумму бюджета\n"
                                          "или Введи /tags чтобы выбрать другую категорию за ту же дату\n"
                                          "или Введи /start чтобы выбрать другую дату")
    else:# проверка формата ввода
        bot.send_message(message.chat.id, "Это не число... \n"
                                          "Введи сумму бюджета 1 билет\n"
                                          "или Введи /tags чтобы сменить желаемую категорию\n"
                                          "или Введи /start чтобы выбрать другую дату")

@bot.message_handler(func=lambda message: message.text not in ('/reset', '/info', '/start', '/commands','/tags'))
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

