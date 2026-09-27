from django.urls import path

from apps.history import views

urlpatterns = [
    path("api/teams/<uuid:team_id>/history/", views.history_api, name="team-history"),
    path("teams/<uuid:team_id>/history/", views.history_page, name="team-history-page"),
    path("api/attachments/", views.attachments_view, name="attachments"),
    path("api/attachments/<uuid:attachment_id>/", views.attachment_view, name="attachment"),
    path("api/status-changes/", views.status_changes_view, name="status-changes"),
]
