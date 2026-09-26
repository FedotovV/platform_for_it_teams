import uuid

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, login, name, password=None):
        login = (login or "").strip()
        name = (name or "").strip()
        if not login:
            raise ValueError("Нужен логин")
        if not name:
            raise ValueError("Нужно имя")
        user = self.model(login=login, name=name)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, login, name, password=None):
        return self.create_user(login=login, name=name, password=password)


class User(AbstractBaseUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    login = models.CharField("логин", max_length=150, unique=True)
    name = models.CharField("имя", max_length=255)

    objects = UserManager()

    USERNAME_FIELD = "login"
    REQUIRED_FIELDS = ["name"]

    class Meta:
        verbose_name = "пользователь"
        verbose_name_plural = "пользователи"

    def __str__(self):
        return self.login
