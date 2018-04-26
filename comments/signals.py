import os
import sys

from django.core.management.color import color_style
from django.core.management.base import OutputWrapper
from django.db import connection


def create_history_trigger(sender, **kwargs):
    from models import Comment
    stdout = OutputWrapper(sys.stdout)
    style = color_style()

    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'history.sql')) as f:
        sql = f.read()
    sql = sql.format(table_name=Comment._meta.db_table)
    stdout.write("  Creating the Comment History trigger...", ending=' ')
    cursor = connection.cursor()
    cursor.execute(sql)
    stdout.write(style.SUCCESS("OK"))
