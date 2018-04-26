# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime
import json

import celery
from django.core.files import File as DjangoFile
from django.core.serializers.xml_serializer import Serializer
from push_notifications.models import GCMDevice

import models


def json_encoder(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, datetime):
        return str(obj)
    raise TypeError("Type %s not serializable" % type(obj))


@celery.task()
def notify(action, comment_id, content_type, object_pk, text, user_id, event_date):
    from models import Subscription
    devices = GCMDevice.objects.filter(
        user_id__in=Subscription.objects.filter(content_type=content_type, object_pk=object_pk).values_list(
            'subscriber', flat=True))
    message = {
        'action': action,
        'id': comment_id,
        'user': user_id,
        'event_date': event_date,
        'content_type': content_type,
        'object_pk': object_pk,
        'comment': text
    }
    devices.send_message(json.dumps(message, default=json_encoder))


@celery.task()
def export(export_format, data):
    from models import File
    from filters import CommentFilter
    qs = models.Comment.objects.filter(is_removed=False)
    f = CommentFilter(data, qs)
    serializer = Serializer()
    serializer.serialize(f.qs)
    myfile = DjangoFile(serializer.stream, 'comments.' + export_format)
    obj = File.objects.create(file=myfile)
    return obj.id.hex
