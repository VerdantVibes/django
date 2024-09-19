from django.urls import path, include
from rest_framework.routers import DefaultRouter

from core import views as core_views
from core import views_donate
from core import views_feedback
from core import views_editor

router = DefaultRouter()
router.register(r'portfolios', core_views.PortfolioViewSet, basename='portfolio')
router.register(r'report_base_templates', core_views.ReportBaseTemplateViewSet, basename='reportBaseTemplate')
router.register(r'story-rooms', core_views.StoryRoomViewSet, basename='story-rooms')
router.register(r'release-notes', core_views.ReleaseNoteViewSet, basename='release-notes')

urlpatterns = [
    path('', include(router.urls)),
    path("download/<str:blob>/<path:name>/", core_views.DownloadView.as_view(), name="download"),
    path("data-connections/", core_views.DataConnectionListView.as_view(), name="data-connections"),
    path("data-connections/refresh-token/<str:data_connection_uuid>/",
         core_views.DataConnectionRefreshTokenView.as_view(),
         name="data-connections-refresh-token"),
    path("data-connections/folders/<str:data_connection_uuid>/",
         core_views.DataConnectionFoldersView.as_view(),
         name="data-connections-folders"),

    path("story-room/verify/", core_views.StoryRoomVerify.as_view(), name="story-room-verify"),
    path("story-room/upload/", core_views.StoryRoomUpload.as_view(), name="story-room-upload"),
    path("story/list/", core_views.StoryList.as_view(), name="story-list"),
    path("story/", core_views.Story.as_view(), name="story-detail"),

    path("donate/", views_donate.DonateView.as_view(), name="donate"),
    path("donate-return/", views_donate.DonateReturnView.as_view(), name="donate-return"),
    path("donate-cancel/", views_donate.DonateCancelView.as_view(), name="donate-cancel"),
    path("moonlight2024/", views_donate.stripe_webhook_view, name="stripe-webhook"),

    path("feedback/", views_feedback.FeedbackView.as_view(), name="feedback"),
    path("upload-report/", views_editor.UploadReportView.as_view(), name="upload-report"),
    path("upload-image-report/", views_editor.UploadReportImageView.as_view(), name="upload-image-report"),
    path("upload-image-url-report/", views_editor.SaveReportImageFromUrlView.as_view(), name="upload-image-report"),
    path("fetch-report/", views_editor.FetchReportView.as_view(), name="fetch-report"),
    path("fetch-image-report/", views_editor.FetchReportImageView.as_view(), name="fetch-report"),
    path("list-reports/", views_editor.ReportListView.as_view(), name="list-reports"),
    path("fetch-report-as-html/", views_editor.FetchReportAsHtmlView.as_view(), name="fetch-report-as-html"),

    path("news-feed/", core_views.NewsFeedView.as_view(), name="news-feed"),

]
