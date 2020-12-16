from enum import Enum

db_file = 'database.vdb'


class States(Enum):
    S_START = "0"
    S_ENTER_DAY = "1"
    S_ENTER_TAGS = "2"
    S_ENTER_PRICE = "3"
