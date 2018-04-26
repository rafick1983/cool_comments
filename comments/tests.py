# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json

from django.utils import timezone

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import reverse
from django.core import serializers
from django.test import TestCase
from rest_framework.test import APITestCase
from push_notifications.models import GCMDevice
from mock import patch

from comments import tasks
from models import Article, Comment
import models


def format_response_message(response):
    return 'Operation: {} {}. Code: {}. Body: {}'.format(
        response.request['REQUEST_METHOD'], response.request['PATH_INFO'], response.status_code, response.content)


class ViewTests(APITestCase):
    app = 'comments'
    base_name = 'comment'

    @classmethod
    def setUpTestData(cls):
        user = get_user_model().objects.create_user('user', 'asdf1234')
        cls.user = user

    def setUp(self):
        self.client.force_authenticate(user=self.user)

    def test_add_comment(self):
        """
        Tests whether a comment gets added.
        """
        article = Article.objects.create(text='text')
        ct = ContentType.objects.get_for_model(Article)
        data = {
            'content_type': ct.pk,
            'object_pk': article.pk,
            'comment': 'Hi, everyone'
        }
        response = self.client.post(reverse('%s:%s-list' % (self.app, self.base_name)), data)
        self.assertEqual(response.status_code, 201, format_response_message(response))
        self.assertEqual(response.data['comment'], 'Hi, everyone')
        self.assertEqual(response.data['user'], self.user.pk)

    def test_list_comments_1st_level(self):
        """
        Tests whether only first level comments get returned
        """
        article_ct = ContentType.objects.get_for_model(Article)
        comment_ct = ContentType.objects.get_for_model(Comment)
        article = Article.objects.create(text='text')
        # add a comment to the article
        parent_comment = Comment.objects.create(
            content_type=article_ct,
            object_pk=article.pk,
            comment='Hi, everyone',
            user=self.user
        )
        # add a child comment
        Comment.objects.create(
            content_type=comment_ct,
            object_pk=parent_comment.pk,
            comment='Get out of here',
            user=self.user
        )
        # add a comment to the article
        parent_comment2 = Comment.objects.create(
            content_type=article_ct,
            object_pk=article.pk,
            comment='Hi, everyone 2',
            user=self.user
        )
        # add a child comment
        Comment.objects.create(
            content_type=comment_ct,
            object_pk=parent_comment2.pk,
            comment='Get out of here 2',
            user=self.user
        )
        # filter the queryset by model and pk
        data = {
            'content_type': article_ct.pk,
            'object_pk': article.pk
        }
        response = self.client.get(reverse('%s:%s-list' % (self.app, self.base_name)), data)
        self.assertEqual(response.status_code, 200, format_response_message(response))
        results = response.data['results']
        self.assertEqual(len(results), 2)
        self.assertEqual(len(filter(lambda item: item['comment'] == 'Hi, everyone', results)), 1)
        self.assertEqual(len(filter(lambda item: item['comment'] == 'Hi, everyone 2', results)), 1)

    def test_list_child_comments(self):
        """
        Tests
        """
        comment_ct = ContentType.objects.get_for_model(Comment)
        article_ct = ContentType.objects.get_for_model(Article)
        article = Article.objects.create(text='text')
        comment1 = models.Comment.objects.create(
            content_type=article_ct,
            object_pk=article.pk,
            comment='c1',
            user=self.user
        )
        comment2 = models.Comment.objects.create(
            content_type=comment_ct,
            object_pk=comment1.pk,
            comment='c2',
            user=self.user
        )
        comment31 = models.Comment.objects.create(
            content_type=comment_ct,
            object_pk=comment2.pk,
            comment='c3',
            user=self.user
        )
        comment32 = models.Comment.objects.create(
            content_type=comment_ct,
            object_pk=comment2.pk,
            comment='c3',
            user=self.user
        )

        models.Comment.objects.create(
            content_type=article_ct,
            object_pk=article.pk,
            comment='c0',
            user=self.user
        )

        # fetch all comments for the article
        response = self.client.get(reverse('%s:child-comments' % self.app,
                                           kwargs={'content_type_id': article_ct.pk, 'object_id': article.pk}))
        self.assertEqual(response.status_code, 200, format_response_message(response))
        # all article child comments must be in the response
        self.assertEqual(len(response.data), 5)

        # fetch all comments of the 'comment1' comment
        response = self.client.get(reverse('%s:child-comments' % self.app,
                                           kwargs={'content_type_id': comment_ct.pk, 'object_id': comment1.pk}))
        self.assertEqual(response.status_code, 200, format_response_message(response))
        # all comment1 child comments must be in the response
        self.assertEqual(len(response.data), 3)
        comment_ids = [item['id'] for item in response.data]
        self.assertIn(comment2.id, comment_ids)
        self.assertIn(comment31.id, comment_ids)
        self.assertIn(comment32.id, comment_ids)

    def test_list_user_comments(self):
        """
        Tests
        """
        article_ct = ContentType.objects.get_for_model(Article)
        article = Article.objects.create(text='text')
        c = models.Comment.objects.create(
            content_type=article_ct,
            object_pk=article.pk,
            comment='Hi, everyone',
            user=self.user
        )
        user2 = get_user_model().objects.create_user('user2', 'asdf1234')
        c2 = models.Comment.objects.create(
            content_type=article_ct,
            object_pk=article.pk,
            comment='Hello',
            user=user2
        )
        response = self.client.get(reverse('%s:%s-list' % (self.app, self.base_name)) + '?user=%s' % self.user.id)
        self.assertEqual(response.status_code, 200, format_response_message(response))
        results = response.data['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['comment'], 'Hi, everyone')

    def test_list_comments_by_date(self):
        article_ct = ContentType.objects.get_for_model(Article)
        article = Article.objects.create(text='text')
        c = models.Comment.objects.create(
            content_type=article_ct,
            object_pk=article.pk,
            comment='Hi, everyone',
            user=self.user
        )
        c.submit_date = '2017-01-01 00:00:00'
        c.save()

        user2 = get_user_model().objects.create_user('user2', 'asdf1234')
        c2 = models.Comment.objects.create(
            content_type=article_ct,
            object_pk=article.pk,
            comment='Hello',
            user=user2
        )
        c2.submit_date = '2017-02-01 00:00:00'
        c2.save()

        response = self.client.get(reverse('%s:%s-list' % (
            self.app, self.base_name)) + '?date_from=%s&date_to=%s' % ('2017-01-01 00:00:00', '2017-01-02 00:00:00'))
        self.assertEqual(response.status_code, 200, format_response_message(response))
        results = response.data['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['comment'], 'Hi, everyone')

    def test_update_comment(self):
        article_ct = ContentType.objects.get_for_model(Article)
        article = Article.objects.create(text='text')
        # add a comment to the article
        comment = Comment.objects.create(
            content_type=article_ct,
            object_pk=article.pk,
            comment='Hi, everyone',
            user=self.user
        )
        data = {'comment': 'hello'}
        response = self.client.patch(reverse('%s:%s-detail' % (self.app, self.base_name),
                                             kwargs={'pk': comment.pk}), data)
        self.assertEqual(response.status_code, 200, format_response_message(response))
        self.assertEqual(response.data['comment'], 'hello')

    def test_delete_childless_comment(self):
        article_ct = ContentType.objects.get_for_model(Article)
        article = Article.objects.create(text='text')
        comment = models.Comment.objects.create(
            content_type=article_ct,
            object_pk=article.pk,
            comment='c1',
            user=self.user
        )
        response = self.client.delete(reverse('%s:%s-detail' % (self.app, self.base_name),
                                              kwargs={'pk': comment.pk}))
        self.assertEqual(response.status_code, 204, format_response_message(response))
        self.assertEqual(models.Comment.objects.filter(is_removed=False, id=comment.id).exists(), False)

    def test_delete_comment_having_children(self):
        comment_ct = ContentType.objects.get_for_model(Comment)
        article_ct = ContentType.objects.get_for_model(Article)
        article = Article.objects.create(text='text')
        comment1 = models.Comment.objects.create(
            content_type=article_ct,
            object_pk=article.pk,
            comment='c1',
            user=self.user
        )
        models.Comment.objects.create(
            content_type=comment_ct,
            object_pk=comment1.pk,
            comment='c2',
            user=self.user
        )
        response = self.client.delete(reverse('%s:%s-detail' % (self.app, self.base_name),
                                              kwargs={'pk': comment1.pk}))
        self.assertEqual(response.status_code, 403, format_response_message(response))

    def test_history(self):
        article_ct = ContentType.objects.get_for_model(Article)
        article = Article.objects.create(text='text')
        # add a comment to the article
        comment = Comment.objects.create(
            content_type=article_ct,
            object_pk=article.pk,
            comment='Hi, everyone',
            user=self.user
        )

        # update
        data = {'comment': 'hello'}
        response = self.client.patch(reverse('%s:%s-detail' % (self.app, self.base_name),
                                             kwargs={'pk': comment.pk}), data)
        self.assertEqual(response.status_code, 200, format_response_message(response))

        # check
        response = self.client.get(reverse('%s:history-list' % self.app) + '?/user=%s' % self.user.id)
        self.assertEqual(response.status_code, 200, format_response_message(response))
        results = response.data['results']
        self.assertEqual(len(results), 1)

        # and delete
        response = self.client.delete(reverse('%s:%s-detail' % (self.app, self.base_name),
                                              kwargs={'pk': comment.pk}))
        self.assertEqual(response.status_code, 204, format_response_message(response))

        # check
        response = self.client.get(reverse('%s:history-list' % self.app) + '?/user=%s' % self.user.id)
        self.assertEqual(response.status_code, 200, format_response_message(response))
        results = response.data['results']
        self.assertEqual(len(results), 2)


class TaskTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        user = get_user_model().objects.create_user('user', 'asdf1234')
        cls.user = user

    def test_export(self):
        article_ct = ContentType.objects.get_for_model(Article)
        article = Article.objects.create(text='text')
        c = models.Comment.objects.create(
            content_type=article_ct,
            object_pk=article.pk,
            comment='Hi, everyone',
            user=self.user
        )
        with self.settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True):
            task = tasks.export.delay('xml', {})
            f = models.File.objects.get(id=task.result)
            objs = serializers.deserialize("xml", f.file.read())
            self.assertEqual(next(objs).object.pk, c.pk)

    @patch('push_notifications.models.GCMDeviceQuerySet.send_message')
    def test_push(self, send_message):
        # let's suppose the user got registered Google Cloud
        GCMDevice.objects.create(
            user=self.user,
            registration_id='1234567890'
        )

        article_ct = ContentType.objects.get_for_model(Article)
        article = Article.objects.create(text='text')

        # the user got subscribed
        models.Subscription.objects.create(
            content_type=article_ct,
            object_pk=article,
            subscriber=self.user
        )

        # someone has added a comment to the article
        user2 = get_user_model().objects.create_user('user2', 'asdf1234')
        with self.settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True):
            event_date = timezone.now()
            message = {
                'action': 'insert',
                'id': 1,
                'user': user2.id,
                'event_date': str(event_date),
                'content_type': article_ct.pk,
                'object_pk': article.pk,
                'comment': 'Hi'
            }
            task = tasks.notify.delay('insert', 1, article_ct.pk, article.pk, "Hi", user2.id, event_date)
            send_message.assert_called_with(json.dumps(message))
