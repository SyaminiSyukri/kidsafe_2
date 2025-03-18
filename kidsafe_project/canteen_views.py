from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from kidsafe_app.models import Card, StudentAccount, InventoryItem, Dietary
from decimal import Decimal, InvalidOperation
from django.utils import timezone

@login_required(login_url='/')
def home(request):
    return render(request, 'canteen/home.html')

@login_required(login_url='/')
def inventory_management(request):
    inventory_items = InventoryItem.objects.all().order_by('name')
    return render(request, 'canteen/inventory_management.html', {'inventory_items': inventory_items})

@login_required(login_url='/')
def inventory_item_detail(request, item_id):
    item = get_object_or_404(InventoryItem, id=item_id)
    return render(request, 'canteen/inventory_item_detail.html', {'item': item})

@login_required(login_url='/')
def add_inventory_item(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        image = request.FILES.get('image')
        quantity = request.POST.get('quantity')
        price = request.POST.get('price')
        description = request.POST.get('description')
        allergies = request.POST.get('allergies')
        restrictions = request.POST.get('restrictions')

        InventoryItem.objects.create(
            name=name,
            image=image,
            quantity=quantity,
            price=price,
            description=description,
            allergies=allergies,
            restrictions=restrictions
        )
        messages.success(request, 'Inventory item added successfully!')
        return redirect('inventory_management')
    return render(request, 'canteen/add_inventory_item.html')


@login_required(login_url='/')
def edit_inventory_item(request, item_id):
    item = get_object_or_404(InventoryItem, id=item_id)
    if request.method == 'POST':
        item.name = request.POST.get('name')
        item.image = request.FILES.get('image', item.image)
        item.quantity = request.POST.get('quantity')
        item.price = request.POST.get('price')
        item.description = request.POST.get('description')
        item.allergies = request.POST.get('allergies')
        item.restrictions = request.POST.get('restrictions')
        item.save()
        messages.success(request, 'Item updated successfully!')
        return redirect('inventory_item_detail', item_id=item.id)
    return render(request, 'canteen/edit_inventory_item.html', {'item': item})


@login_required(login_url='/')
def delete_inventory_item(request, item_id):
    item = get_object_or_404(InventoryItem, id=item_id)
    if request.method == 'POST':
        item.delete()
        messages.success(request, 'Inventory item deleted successfully!')
    return redirect('inventory_management')


@login_required(login_url='/')
def process_payment(request):
    if request.method == 'POST':
        card_id = request.POST.get('card_id')
        amount = request.POST.get('amount')

        try:
            card = Card.objects.get(card_id=card_id)

            student_account = StudentAccount.objects.get(student=card.student)

            # Fetch dietary details for the student
            dietary_details = Dietary.objects.filter(student=card.student).first()
            food_allergy = dietary_details.food_allergy if dietary_details else None
            dietary_restriction = dietary_details.dietary_restriction if dietary_details else None

            if amount:
                try:
                    amount_decimal = Decimal(amount)
                    if amount_decimal < 0:
                        return JsonResponse({'success': False, 'error': 'Amount cannot be negative.'})

                    if student_account.balance < amount_decimal:
                        return JsonResponse({'success': False, 'error': 'Insufficient balance.'})

                    student_account.balance -= amount_decimal
                    student_account.save()

                    return JsonResponse({
                        'success': True,
                        'message': f'Payment of ${amount} processed successfully. New balance: ${student_account.balance}',
                        'new_balance': str(student_account.balance),
                        'student_name': f"{card.student.admin.first_name} {card.student.admin.last_name}",
                        'food_allergy': food_allergy,
                        'dietary_restriction': dietary_restriction,
                    })
                except InvalidOperation:
                    return JsonResponse({'success': False, 'error': 'Invalid amount. Please enter a valid number.'})
            else:
                return JsonResponse({
                    'success': True,
                    'student_name': f"{card.student.admin.first_name} {card.student.admin.last_name}",
                    'current_balance': str(student_account.balance),
                    'food_allergy': food_allergy,
                    'dietary_restriction': dietary_restriction,
                })

        except Card.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Card not found.'}, status=404)
        except StudentAccount.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Student account not found.'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

    # Fetch inventory items for the dropdown
    inventory_items = InventoryItem.objects.all().order_by('name')
    return render(request, 'canteen/process_payment.html', {'inventory_items': inventory_items})