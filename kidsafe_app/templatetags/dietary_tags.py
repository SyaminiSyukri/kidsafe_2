from django import template
from kidsafe_app.models import Dietary
import json

register = template.Library()

@register.filter(name='get_allergy_display')
def get_allergy_display(value):
    for choice in Dietary.FOOD_ALLERGY_CHOICES:
        if choice[0] == value:
            return choice[1]
    return value

@register.filter(name='get_restriction_display')
def get_restriction_display(value):
    for choice in Dietary.DIETARY_RESTRICTION_CHOICES:
        if choice[0] == value:
            return choice[1]
    return value

@register.filter(name='json_serialize')
def json_serialize(value):
    """Convert a value to a JSON string"""
    if value is None:
        return '[]'
    try:
        return json.dumps(value)
    except (TypeError, ValueError):
        return '[]'