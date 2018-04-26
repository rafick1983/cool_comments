# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.apps import AppConfig
from django.db.models.signals import post_migrate

from signals import create_history_trigger


class CommentsConfig(AppConfig):
    name = 'comments'

    def ready(self):
        post_migrate.connect(create_history_trigger, self)
