from django.conf.urls import url, include
from push_notifications.api.rest_framework import APNSDeviceAuthorizedViewSet, GCMDeviceAuthorizedViewSet
from rest_framework.routers import DefaultRouter
import views

router = DefaultRouter()
router.register(r'comments', views.CommentViewSet)
router.register(r'history', views.HistoryViewSet)
router.register(r'device/apns', APNSDeviceAuthorizedViewSet)
router.register(r'device/gcm', GCMDeviceAuthorizedViewSet)

urlpatterns = [
    url(r'^', include(router.urls)),
    url(r'^child-comments/(?P<content_type_id>\d+)/(?P<object_id>\d+)/$', views.ChildCommentView.as_view(),
        name='child-comments'),
    url(r'^subscribe/(?P<content_type_id>\d+)/(?P<object_id>\d+)/$', views.ChildCommentView.as_view(),
        name='subscribe'),
    url(r'^result/(?P<id>[0-9a-fA-F-]+)/$', views.ExportResultView.as_view(), name='result'),
]
