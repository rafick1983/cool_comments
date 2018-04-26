# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import uuid

from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone

from comments import tasks


MAX_COMMENT_SIZE = 3000


class Article(models.Model):
    text = models.TextField()


class Comment(models.Model):
    content_type = models.ForeignKey(ContentType,
                                     verbose_name=_('content type'),
                                     related_name="content_type_set_for_%(class)s",
                                     on_delete=models.CASCADE)
    object_pk = models.TextField(_('object ID'))
    content_object = GenericForeignKey(ct_field="content_type", fk_field="object_pk")

    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('user added by'),
                             related_name="added_comments",
                             on_delete=models.CASCADE)
    # the field is used mainly to pass a user changed to the history table
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('user changed by'),
                             related_name="changed_comments", blank=True, null=True,
                             on_delete=models.SET_NULL)

    comment = models.TextField(_('comment'), max_length=MAX_COMMENT_SIZE)

    submit_date = models.DateTimeField(_('date/time submitted'), auto_now_add=True, db_index=True)
    is_removed = models.BooleanField(_('is removed'), default=False,
                                     help_text=_('Check this box if the comment is inappropriate. '
                                                 'A "This comment has been removed" message will '
                                                 'be displayed instead.'))

    class Meta:
        ordering = ('submit_date',)
        verbose_name = _('comment')
        verbose_name_plural = _('comments')

    def __unicode__(self):
        return self.comment[:50]

    def __init__(self, *args, **kwargs):
        super(Comment, self).__init__(*args, **kwargs)
        self._old_is_removed = self.is_removed
        self._old_comment = self.comment

    def clean(self):
        if self.pk is None and self.is_removed:
            raise ValidationError("You can't flag a new comment as removed.")

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        is_new = self.pk is None
        super(Comment, self).save(force_insert, force_update, using, update_fields)
        if self._old_is_removed != self.is_removed or self._old_comment != self.comment:
            if is_new:
                action = 'insert'
            elif self._old_is_removed != self.is_removed:
                action = 'delete' if self.is_removed else 'recover'
            else:
                action = 'update'
            tasks.notify.delay(action, self.id, self.content_type.pk, self.object_pk, self.comment, self.user_id,
                               timezone.now())

    def is_deletable(self):
        return not Comment.objects.filter(
            object_pk=self.id, content_type=ContentType.objects.get_for_model(Comment)).exists()


class History(models.Model):
    comment = models.ForeignKey(Comment, models.CASCADE, 'history')
    event_date = models.DateTimeField(_('date/time happened'), db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('user'),
                             related_name="comment_history", blank=True, null=True,
                             on_delete=models.CASCADE)
    old_comment = models.TextField(_('old comment'), max_length=MAX_COMMENT_SIZE, blank=True)
    new_comment = models.TextField(_('comment'), max_length=MAX_COMMENT_SIZE, blank=True)
    old_is_removed = models.BooleanField(db_index=True)
    new_is_removed = models.BooleanField(db_index=True)

    class Meta:
        ordering = ('event_date',)
        verbose_name = _('history')
        verbose_name_plural = _('history')


class Subscription(models.Model):
    content_type = models.ForeignKey(ContentType,
                                     verbose_name=_('content type'),
                                     related_name="content_type_set_for_%(class)s",
                                     on_delete=models.CASCADE)
    object_pk = models.TextField(_('object ID'))
    content_object = GenericForeignKey(ct_field="content_type", fk_field="object_pk")

    subscriber = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('subscriber'),
                                   related_name="comment_subscriptions",
                                   on_delete=models.CASCADE)

    class Meta:
        verbose_name = _('subscription')
        verbose_name_plural = _('subscriptions')


class File(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.FileField(null=True, blank=True)
    # The field is to collect and remove old files by celery task, for example
    add_date = models.DateTimeField(_('date/time added'), auto_now_add=True, db_index=True)
