from django import forms
from kidsafe_app.models import InventoryItem

class InventoryItemForm(forms.ModelForm):
    class Meta:
        model = InventoryItem
        fields = ['name', 'image', 'quantity', 'price', 'description']