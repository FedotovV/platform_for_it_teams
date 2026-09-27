from django.urls import path

from apps.access import views

urlpatterns = [
    path("api/teams/<uuid:team_id>/grants/", views.grants_view, name="team-grants"),
    path(
        "api/teams/<uuid:team_id>/actions/<slug:action_code>/",
        views.action_view,
        name="team-action",
    ),
]
