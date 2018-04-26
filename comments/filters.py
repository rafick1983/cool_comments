# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import django_filters

import models


class CommentFilter(django_filters.FilterSet):
    date_from = django_filters.DateTimeFilter(name="submit_date", lookup_expr='gte')
    date_to = django_filters.DateTimeFilter(name="submit_date", lookup_expr='lt')

    class Meta:
        model = models.Comment
        fields = ['content_type', 'object_pk', 'user', 'date_from', 'date_to']