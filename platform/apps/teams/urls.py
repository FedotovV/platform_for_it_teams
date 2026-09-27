from django.urls import path

from apps.teams import views

urlpatterns = [
    path("api/teams/", views.teams_view, name="teams"),
    path("api/teams/selection/", views.selection_view, name="team-selection"),
    path("api/teams/<uuid:team_id>/", views.team_view, name="team"),
    path("api/teams/<uuid:team_id>/memberships/", views.memberships_view, name="team-memberships"),
]
