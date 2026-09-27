from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_not_required
from django.http import HttpResponseNotAllowed
from django.shortcuts import redirect, render

from apps.identity.api import current_user_id, user_label
from apps.identity.forms import LoginForm
from apps.teams.api import (
    is_org_leader_of_team,
    membership_role,
    selected_team_id,
    team_payload,
    visible_teams,
)
from apps.workspace.labels import ROLE


def home(request):
    user_id = current_user_id(request)
    if user_id is None:
        return redirect("login")
    selected = selected_team_id(user_id)
    teams = []
    for team in visible_teams(user_id):
        payload = team_payload(team)
        role = membership_role(user_id, team.id)
        if role:
            payload["role_label"] = ROLE[role]
        elif is_org_leader_of_team(user_id, team.id):
            payload["role_label"] = "руководитель организации"
        else:
            payload["role_label"] = ""
        payload["selected"] = selected == team.id
        teams.append(payload)
    return render(
        request,
        "identity/home.html",
        {
            "user_id": user_id,
            "user_name": user_label(user_id),
            "teams": teams,
        },
    )


@login_not_required
def login_view(request):
    if current_user_id(request) is not None:
        return redirect("home")

    error = None
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            user = authenticate(
                request,
                username=form.cleaned_data["login"],
                password=form.cleaned_data["password"],
            )
            if user is not None:
                login(request, user)
                return redirect("home")
            error = "Неверный логин или пароль."
    else:
        form = LoginForm()

    return render(request, "identity/login.html", {"form": form, "error": error})


def logout_view(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    logout(request)
    return redirect("login")
