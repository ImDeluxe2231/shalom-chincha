from django import forms

from .models import Customer


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = (
            "customer_type",
            "document_type",
            "document_number",
            "first_name",
            "last_name",
            "business_name",
            "phone",
            "secondary_phone",
            "email",
            "department",
            "province",
            "district",
            "address",
            "reference",
            "notes",
            "is_active",
        )
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3}),
            "address": forms.TextInput(attrs={"autocomplete": "street-address"}),
            "email": forms.EmailInput(attrs={"autocomplete": "email"}),
            "phone": forms.TextInput(attrs={"inputmode": "numeric", "maxlength": "9"}),
            "document_number": forms.TextInput(attrs={"autocomplete": "off"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = "form-check-input"
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs["class"] = "form-select"
            else:
                field.widget.attrs["class"] = "form-control"
            field.widget.attrs.setdefault("placeholder", field.label)

    def clean_document_number(self):
        number = self.cleaned_data.get("document_number", "").strip().upper()
        existing = Customer.objects.filter(document_number=number)
        if self.instance.pk:
            existing = existing.exclude(pk=self.instance.pk)
        if existing.exists():
            customer = existing.first()
            raise forms.ValidationError(
                f"Este documento ya pertenece a {customer.display_name}."
            )
        return number
