from django.urls import path

from apps.workspace import views

urlpatterns = [
    path("workspace/teams/select/", views.select_team_view, name="workspace-select-team"),
    path("workspace/teams/<uuid:team_id>/", views.team_page, name="workspace-team"),
    path("workspace/teams/<uuid:team_id>/grants/", views.grants_page, name="workspace-grants"),
    path("workspace/cycles/", views.cycles_page, name="workspace-cycles"),
    path("workspace/cycles/<uuid:cycle_id>/", views.cycle_page, name="workspace-cycle"),
    path("workspace/problems/", views.problems_page, name="workspace-problems"),
    path("workspace/problems/<uuid:problem_id>/", views.problem_page, name="workspace-problem"),
    path("workspace/actions/<uuid:action_id>/", views.action_page, name="workspace-action"),
    path("workspace/organization/", views.organization_page, name="workspace-organization"),
    path("workspace/attachments/", views.attachment_post, name="workspace-attachment"),
]
