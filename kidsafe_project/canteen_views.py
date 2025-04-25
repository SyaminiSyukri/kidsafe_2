from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from kidsafe_app.models import Card, StudentAccount, InventoryItem, Dietary, Transaction, Canteen, CanteenNotification, FeedbackToAdmin
from decimal import Decimal, InvalidOperation
from django.utils import timezone
from datetime import datetime
import json

@login_required(login_url='/')
def home(request):
    """Render the canteen staff dashboard/home page."""
    return render(request, 'canteen/home.html')


@login_required(login_url='/')
def inventory_management(request):
    """
    Display all inventory items sorted by name.
    Used for viewing and managing the canteen's product inventory.
    """
    inventory_items = InventoryItem.objects.all().order_by('name')
    return render(request, 'canteen/inventory_management.html', {'inventory_items': inventory_items})


@login_required(login_url='/')
def inventory_item_detail(request, item_id):
    """
    Show detailed information about a specific inventory item.
    Includes all item attributes like price, description, dietary info.
    """
    item = get_object_or_404(InventoryItem, id=item_id)
    return render(request, 'canteen/inventory_item_detail.html', {'item': item})


@login_required(login_url='/')
def add_inventory_item(request):
    """
    Handle creation of new inventory items.
    Processes form data and creates new InventoryItem record.
    """
    if request.method == 'POST':
        # Extract all form data
        name = request.POST.get('name')
        image = request.FILES.get('image')
        price = request.POST.get('price')
        description = request.POST.get('description')
        allergies = request.POST.get('allergies')
        restrictions = request.POST.get('restrictions')

        # Create new inventory item with provided data
        InventoryItem.objects.create(
            name=name,
            image=image,
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
    """
    Handle updating existing inventory items.
    Supports partial updates (e.g., changing just the price or image).
    """
    item = get_object_or_404(InventoryItem, id=item_id)
    if request.method == 'POST':
        # Update item fields with new values (keeping old ones if not provided)
        item.name = request.POST.get('name')
        item.image = request.FILES.get('image', item.image)  # Keep existing image if new one not provided
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
    """
    Handle deletion of inventory items.
    Uses POST method to prevent accidental deletions via GET requests.
    """
    item = get_object_or_404(InventoryItem, id=item_id)
    if request.method == 'POST':
        item.delete()
        messages.success(request, 'Inventory item deleted successfully!')
    return redirect('inventory_management')


@login_required(login_url='/')
def process_payment(request):
    """
    Handle student payment processing in the canteen.
    Supports both checking balance and making purchases.
    Returns JSON response for AJAX calls from the frontend.
    """
    if request.method == 'POST':
        card_id = request.POST.get('card_id')
        amount = request.POST.get('amount')
        items = request.POST.get('items')  # Cart items as JSON string

        try:
            # Retrieve student card and associated account
            card = Card.objects.get(card_id=card_id)
            student_account = StudentAccount.objects.get(student=card.student)

            # Fetch dietary restrictions for the student (for food safety)
            dietary_details = Dietary.objects.filter(student=card.student).first()
            food_allergy = dietary_details.food_allergy if dietary_details else None
            dietary_restriction = dietary_details.dietary_restriction if dietary_details else None

            if amount:
                try:
                    amount_decimal = Decimal(amount)
                    # Validate amount is positive
                    if amount_decimal < 0:
                        return JsonResponse({'success': False, 'error': 'Amount cannot be negative.'})

                    # Check sufficient balance
                    if student_account.balance < amount_decimal:
                        return JsonResponse({'success': False, 'error': 'Insufficient balance.'})

                    # Deduct amount from account
                    student_account.balance -= amount_decimal
                    student_account.save()

                    # Parse and format cart items for transaction record
                    cart_items = json.loads(items)  # Convert JSON string to Python list
                    formatted_items = ", ".join([f"{item['name'].strip()} (x{item['quantity']})" for item in cart_items])

                    # Record transaction
                    Transaction.objects.create(
                        student=card.student,
                        items=formatted_items,
                        total_amount=amount_decimal,
                    )

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
                # If no amount provided, just return student info (balance check)
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

    # GET request - show payment page with inventory items
    inventory_items = InventoryItem.objects.all().order_by('name')
    return render(request, 'canteen/process_payment.html', {'inventory_items': inventory_items})


@login_required(login_url='/')
def transaction_history(request):
    """
    Display transaction history with date filtering and search capabilities.
    Defaults to showing today's transactions if no date is specified.
    """
    # Get filter parameters from request
    selected_date = request.GET.get('date', timezone.localdate().isoformat())
    search_query = request.GET.get('search', '')  # For student name search

    try:
        # Convert date string to date object
        filter_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
    except ValueError:
        # Fallback to today's date if invalid format
        filter_date = timezone.localdate()

    # Base query - transactions for selected date
    transactions = Transaction.objects.filter(transaction_date__date=filter_date).select_related('student__admin', 'student__classroom_id')

    # Apply name search if query exists
    if search_query:
        transactions = transactions.filter(
            student__admin__first_name__icontains=search_query
        ) | transactions.filter(
            student__admin__last_name__icontains=search_query
        )

    context = {
        'transactions': transactions,
        'selected_date': selected_date,
        'search_query': search_query,
    }
    return render(request, 'canteen/transaction_history.html', context)


@login_required(login_url='/')
def view_canteen_notifications(request):
    """
    Display notifications for canteen staff.
    Shows both read and unread notifications, with unread count.
    """
    canteen = Canteen.objects.get(admin=request.user)  # Get current canteen staff
    notifications = CanteenNotification.objects.filter(canteen=canteen).order_by('-created_at')
    
    # Count unread notifications for badge display
    unread_count = CanteenNotification.objects.filter(canteen=request.user.canteen, read=False).count()

    context = {
        'notifications': notifications,
        'unread_count': unread_count,
    }
    return render(request, 'canteen/view_canteen_notifications.html', context)


@login_required(login_url='/')
def mark_notification_as_read(request, notification_id):
    """
    Mark a specific notification as read.
    Typically called via AJAX when user views a notification.
    """
    notification = get_object_or_404(CanteenNotification, id=notification_id)
    notification.read = True
    notification.save()
    return redirect('view_canteen_notifications')


@login_required
def send_canteen_feedback(request):
    """
    Handle sending feedback from canteen staff to admin.
    Supports text messages and optional file attachments.
    """
    if request.method == 'POST':
        FeedbackToAdmin.objects.create(
            sender=request.user,
            sender_type='canteen',
            title=request.POST.get('title'),
            message=request.POST.get('message'),
            attachment=request.FILES.get('attachment')
        )
        messages.success(request, 'Feedback sent to admin!')
        return redirect('send_canteen_feedback')
    
    return render(request, 'canteen/send_feedback.html')