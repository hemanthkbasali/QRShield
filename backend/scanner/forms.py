from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .validators import validate_uploaded_qr_image


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=80, required=False)

    class Meta:
        model = User
        fields = ("username", "email", "first_name", "password1", "password2")

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email


class QRUploadForm(forms.Form):
    image = forms.ImageField(
        validators=[validate_uploaded_qr_image],
        error_messages={
            "required": "Upload a QR image to analyze.",
            "invalid_image": "The uploaded file is not a readable image.",
        },
    )


class ProfileSettingsForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "email")

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        qs = User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("That email is already used by another account.")
        return email
