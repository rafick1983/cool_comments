# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

import models


class HistoryInline(admin.TabularInline):
    model = models.History
    extra = 0

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(models.Comment)
class CommentAdmin(admin.ModelAdmin):
    inlines = [HistoryInline]
