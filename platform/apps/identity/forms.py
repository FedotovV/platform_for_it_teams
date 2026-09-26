from django import forms


class LoginForm(forms.Form):
    login = forms.CharField(label="Логин", max_length=150)
    password = forms.CharField(label="Пароль", widget=forms.PasswordInput)

    def clean_login(self):
        return self.cleaned_data["login"].strip()
