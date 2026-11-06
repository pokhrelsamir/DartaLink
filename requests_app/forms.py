from django import forms

from accounts.models import Department

from .models import AdministrativeRequest


class RequestForm(forms.ModelForm):
    class Meta:
        model = AdministrativeRequest
        fields = ["title", "category", "priority", "description", "requested_amount", "required_by",
                  "customer_name", "customer_contact"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 6}),
            "required_by": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "customer_name": forms.TextInput(attrs={
                "autocomplete": "name",
                "pattern": r"[A-Za-z ]+",
                "title": "Use alphabetic characters and spaces only.",
            }),
            "customer_contact": forms.TextInput(attrs={
                "autocomplete": "tel",
                "inputmode": "numeric",
                "maxlength": 10,
                "pattern": r"[0-9]{1,10}",
                "title": "Enter up to 10 digits only.",
            }),
        }

    def __init__(self, *args, **kwargs):
        self.intake_user = kwargs.pop("intake_user", None)
        super().__init__(*args, **kwargs)
        if "customer_contact" in self.fields:
            self.fields["customer_contact"].error_messages["max_length"] = (
                "Customer contact must contain up to 10 digits only."
            )
        if self.intake_user is not None and self.intake_user.is_darta:
            self.fields["department"] = forms.ModelChoiceField(
                label="Receiving branch / Sakha",
                queryset=Department.objects.filter(is_active=True).exclude(is_registry=True),
                required=True,
                help_text="The selected Sakha Pramukh will verify the request after Darta registration.",
            )
            if self.instance and self.instance.department_id:
                self.fields["department"].initial = self.instance.department_id
            self.fields["customer_name"].required = True
        else:
            self.fields.pop("customer_name")
            self.fields.pop("customer_contact")

    def clean_requested_amount(self):
        amount = self.cleaned_data.get("requested_amount")
        if amount is not None and amount < 0:
            raise forms.ValidationError("Amount cannot be negative.")
        return amount

    def clean_customer_name(self):
        value = self.cleaned_data.get("customer_name", "").strip()
        if value and not all(character.isalpha() or character == " " for character in value):
            raise forms.ValidationError("Customer name must contain alphabetic characters and spaces only.")
        return value

    def clean_customer_contact(self):
        value = self.cleaned_data.get("customer_contact", "").strip()
        if value and (not value.isascii() or not value.isdigit() or len(value) > 10):
            raise forms.ValidationError("Customer contact must contain up to 10 digits only.")
        return value
