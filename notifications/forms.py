from django import forms

from accounts.models import Department, User


class DirectMessageForm(forms.Form):
    subject = forms.CharField(max_length=160)
    department = forms.ModelChoiceField(
        queryset=Department.objects.none(),
        empty_label="Select a department",
    )
    recipient_mode = forms.ChoiceField(
        choices=(("all", "All employees in this department"), ("individual", "Selected employees")),
        widget=forms.RadioSelect,
        initial="all",
    )
    recipients = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),
        widget=forms.SelectMultiple(attrs={"size": 8}),
        label="Employees",
        required=False,
        help_text="Hold Ctrl or Command to select more than one employee.",
    )
    body = forms.CharField(max_length=5000, widget=forms.Textarea(attrs={"rows": 7}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["department"].queryset = Department.objects.filter(is_active=True).order_by("name")
        self.fields["recipients"].queryset = User.objects.filter(
            is_active=True, department__is_active=True
        ).select_related("department").order_by("staff_id")

    def clean(self):
        cleaned = super().clean()
        department = cleaned.get("department")
        mode = cleaned.get("recipient_mode")
        recipients = cleaned.get("recipients")
        if department and mode == "individual":
            selected = list(recipients or [])
            if not selected:
                self.add_error("recipients", "Select at least one employee.")
            elif any(user.department_id != department.pk for user in selected):
                self.add_error("recipients", "Employees must belong to the selected department.")
        return cleaned
