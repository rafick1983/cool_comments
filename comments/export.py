# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from import_export import resources
import models


SUPPORTED_FORMATS = ('xml', 'csv')


class CommentResource(resources.ModelResource):
    class Meta:
        model = models.Comment
