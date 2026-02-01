from django import forms
from .models import Review

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ("rating", "text")
        widgets = {
            "rating": forms.Select(choices=[(i, str(i)) for i in range(1, 6)]),
            "text": forms.Textarea(attrs={"rows": 3, "placeholder": "Напишите пару слов (необязательно)"}),
        }
