# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from celery.result import AsyncResult
from django.db import connection
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import reverse
from rest_framework import viewsets, generics, exceptions, views, mixins
from rest_framework.decorators import action
from rest_framework.response import Response

from comments import tasks
from export import SUPPORTED_FORMATS
from filters import CommentFilter
import models
import serializers


SQL_GET_CHILDREN = r"""
WITH RECURSIVE r AS (
  SELECT c1.*, u1.first_name || u1.last_name AS user_name
  FROM comments_comment c1
  JOIN auth_user u1 ON u1.id = c1.user_id
  WHERE c1.object_pk = %s AND c1.content_type_id = %s AND c1.is_removed = false

  UNION

  SELECT c2.*, u2.first_name || u2.last_name AS user_name
  FROM comments_comment c2
  JOIN auth_user u2 ON u2.id = c2.user_id
  JOIN r ON c2.content_type_id = %s AND c2.object_pk::bigint = r.id AND c2.is_removed = false
)

SELECT * FROM r ORDER BY submit_date;
"""


def dictfetchall(cursor):
    "Returns all rows from a cursor as a dict"
    desc = [col[0] for col in cursor.description]
    return [dict(zip(desc, row)) for row in cursor.fetchall()]


def gen_export_response(task):
    return Response(status=202, headers={
        'Location': reverse('export:result', kwargs={'id': task.id})})


class CommentViewSet(viewsets.ModelViewSet):
    """
    post:
    Creates a comment.

    get:
    Returns a list of comments.

    You can filter the list using query params.
    To get all comments of a user, set the 'user' query param without 'content_type' and 'object_pk'
    """
    queryset = models.Comment.objects.filter(is_removed=False).select_related('user')
    serializer_class = serializers.CommentSerializer
    filter_class = CommentFilter

    def perform_destroy(self, instance):
        if instance.is_deletable():
            instance.is_removed = True
            instance.changed_by = self.request.user
            instance.save(update_fields=['is_removed', 'changed_by'])
        else:
            raise exceptions.PermissionDenied()

    @action(['POST'], False, 'export/?P<format>(%s)' % '|'.join(SUPPORTED_FORMATS))
    def export_to_xml(self, request, *args, **kwargs):
        task = tasks.export('xml', request.data)
        return gen_export_response(task)


class HistoryViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = models.History.objects.all()
    serializer_class = serializers.HistorySerializer
    filter_fields = ['user']


class ChildCommentView(generics.GenericAPIView):

    def get(self, request, *args, **kwargs):
        """
        Returns a list of child comments for specified entity
        """
        with connection.cursor() as cursor:
            params = (kwargs['object_id'], kwargs['content_type_id'],
                      ContentType.objects.get_for_model(models.Comment).id)
            cursor.execute(SQL_GET_CHILDREN, params)
            return Response(dictfetchall(cursor))


class SubscriptionViewSet(viewsets.ModelViewSet):
    queryset = models.Subscription.objects.all()

    def get_queryset(self):
        return super(SubscriptionViewSet, self).get_queryset().filter(subscriber=self.request.user)


class ExportResultView(views.APIView):

    def get(self, request, *args, **kwargs):
        res = AsyncResult(kwargs['id'])
        if res.state == 'SUCCESS':
            # res.result is a file id
            obj = models.File.objects.get(id=res.result)
            # a client gets a link to the file to download
            return Response(status=204, headers={'Location': obj.file.url})
        if res.state == 'FAILURE':
            # raise an error. A user gets 500, but we can see the traceback in the admin
            res.get()
        return Response(status=202)
