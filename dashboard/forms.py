from django import forms
from django.forms import inlineformset_factory
from catalog.models import Product, ProductImage
from catalog.models import Category
from orders.models import PromoCode

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["name", "slug", "description", "price", "category", "on_main_page", "stock", "is_active",]
        widgets = {
            "name": forms.TextInput(attrs={"class": "input"}),
            "slug": forms.TextInput(attrs={"class": "input"}),
            "description": forms.Textarea(attrs={"class": "textarea"}),
            "price": forms.NumberInput(attrs={"class": "input", "step": "0.01"}),
            "category": forms.Select(attrs={"class": "select"}),
        }


class ProductImageForm(forms.ModelForm):
    class Meta:
        model = ProductImage
        fields = ("image", "is_main")


ProductImageFormSet = inlineformset_factory(
    Product,
    ProductImage,
    form=ProductImageForm,
    extra=3,          # сколько пустых слотов показать
    can_delete=True,  # можно удалять фото
)



class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "slug", "description", "icon", "order", "parent"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "input"}),
            "slug": forms.TextInput(attrs={"class": "input"}),
            "description": forms.Textarea(attrs={"class": "input", "rows": 4}),
            "icon": forms.TextInput(attrs={"class": "input", "placeholder": "Например: 🕯️"}),
            "order": forms.NumberInput(attrs={"class": "input"}),
            "parent": forms.Select(attrs={"class": "input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["parent"].required = False
        self.fields["parent"].label = "Родительская категория"
        self.fields["parent"].queryset = Category.objects.all().order_by("order", "name")

        if self.instance and self.instance.pk:
            self.fields["parent"].queryset = self.fields["parent"].queryset.exclude(pk=self.instance.pk)

    def clean_parent(self):
        parent = self.cleaned_data.get("parent")

        if self.instance and self.instance.pk and parent:
            if parent.pk == self.instance.pk:
                raise forms.ValidationError("Категория не может быть родителем самой себя.")

        return parent

class PromoCodeForm(forms.ModelForm):
    class Meta:
        model = PromoCode
        fields = "__all__"
        widgets = {
            "code": forms.TextInput(attrs={"class": "form-control"}),
            "discount": forms.NumberInput(attrs={"class": "form-control"}),
            "active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }