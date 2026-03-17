from django import forms
from .models import Order
from .models import ReturnRequest, OrderItem

# orders/forms.py
# orders/forms.py
class OrderCreateForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ["address", "delivery_method"]  # ← Добавил delivery_method
        labels = {
            'address': 'Адрес доставки',
            'delivery_method': 'Способ доставки',
        }
        widgets = {
            'delivery_method': forms.RadioSelect(),  # Радио-кнопки
            # или forms.Select() для выпадающего списка
        }
    
   
    
class CheckoutProfileForm(forms.Form):
    first_name = forms.CharField(label="Имя", max_length=50, required=True)
    last_name = forms.CharField(label="Фамилия", max_length=50, required=False)
    phone = forms.CharField(label="Телефон", max_length=255, required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            f.widget.attrs.setdefault("class", "form-control") 
    
    


    



class ReturnRequestForm(forms.ModelForm):
    items = forms.ModelMultipleChoiceField(
        queryset=OrderItem.objects.none(),  # Будет установлен в __init__
        widget=forms.CheckboxSelectMultiple,
        label="Выберите товары для возврата"
    )
    
    class Meta:
        model = ReturnRequest
        fields = ["items", "reason", "photo", "phone", "email"]

    def __init__(self, *args, **kwargs):
        order = kwargs.pop("order", None)
        super().__init__(*args, **kwargs)
        
        if order:
            self.fields["items"].queryset = order.items.all()
        
        # Переопределяем label для каждого элемента
        self.fields['items'].label_from_instance = lambda obj: f"{obj.product.name} - {obj.quantity} шт. × {obj.price} руб."