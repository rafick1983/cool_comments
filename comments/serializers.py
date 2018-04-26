# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from rest_framework import serializers

import models


class CommentSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = models.Comment
        exclude = ['changed_by', 'is_removed']
        read_only_fields = ['user']

    def get_user_name(self, instance):
        return instance.user.get_full_name()

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super(CommentSerializer, self).create(validated_data)

    def update(self, instance, validated_data):
        validated_data['changed_by'] = self.context['request'].user
        return super(CommentSerializer, self).update(instance, validated_data)


class HistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.History
        fields = '__all__'


class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Subscription
        exclude = ('subscriber',)

    def create(self, validated_data):
        validated_data['subscriber'] = self.context['request'].user
        return super(SubscriptionSerializer, self).create(validated_data)


class ExportSerializer(serializers.Serializer):
    date_from = serializers.DateTimeField(required=False)
    date_to = serializers.DateTimeField(required=False)
