def current_user_id(request):
    """Идентификатор текущего пользователя. Доменные модули берут только его."""
    user = getattr(request, "user", None)
    if not getattr(user, "is_authenticated", False):
        return None
    return user.pk


def user_exists(user_id):
    """Есть ли учётная запись с этим id. Доменные модули не читают модель входа."""
    from apps.identity.models import User

    if user_id is None:
        return False
    return User.objects.filter(pk=user_id).exists()


def user_label(user_id):
    """Имя для подписи на экране. Другие модули модель входа не читают."""
    from apps.identity.models import User

    if user_id is None:
        return ""
    user = User.objects.filter(pk=user_id).only("name").first()
    if user is None:
        return ""
    return user.name


def user_id_by_login(login):
    """Id учётной записи по логину. Для выбора человека на экране."""
    from apps.identity.models import User

    if not isinstance(login, str) or not login.strip():
        return None
    user = User.objects.filter(login=login.strip()).only("id").first()
    if user is None:
        return None
    return user.id
