from enum import Enum

token = '1487159881:AAH1DBXuQxJPQVVs0Mr4EOn1LZtDtRTnfgU'
db_file = 'database.vdb'


class States(Enum):
    S_START = "0"
    S_ENTER_DAY = "1"
    S_ENTER_TAGS = "2"
    S_ENTER_PRICE = "3"