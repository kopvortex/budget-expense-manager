from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Q
from django.db.models.functions import Coalesce
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import random
from .models import BankAccount, Category, Income, Expense, MonthlyBudget, Transfer, Tag
from .forms import (
    UserRegisterForm, BankAccountForm, CategoryForm, IncomeForm,
    ExpenseForm, MonthlyBudgetForm, TransferForm, TagForm
)


def get_random_tag_color():
    """Get a random color for a new tag"""
    available_colors = [color[0] for color in Tag.COLOR_CHOICES]
    return random.choice(available_colors)


def register(request):
    """User registration view"""
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Account created for {user.username}!')
            
            # Create default categories
            default_income_categories = ['Salary', 'Freelance', 'Investment', 'Other Income']
            default_expense_categories = ['Food', 'Transportation', 'Housing', 'Utilities', 
                                         'Entertainment', 'Healthcare', 'Shopping', 'Other']
            
            for cat in default_income_categories:
                Category.objects.create(user=user, name=cat, category_type='income')
            
            for cat in default_expense_categories:
                Category.objects.create(user=user, name=cat, category_type='expense')
            
            return redirect('dashboard')
    else:
        form = UserRegisterForm()
    return render(request, 'budget/register.html', {'form': form})


@login_required
def dashboard(request):
    """Main dashboard view with summary statistics"""
    user = request.user
    
    # Get current date
    today = timezone.now().date()
    current_month = today.month
    current_year = today.year
    
    # Monthly statistics
    monthly_income = Income.objects.filter(
        user=user,
        date__year=current_year,
        date__month=current_month
    ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
    
    monthly_expense = Expense.objects.filter(
        user=user,
        date__year=current_year,
        date__month=current_month
    ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
    
    monthly_savings = monthly_income - monthly_expense
    
    # Monthly investments (income to investment accounts + transfers to investment accounts)
    investment_accounts = BankAccount.objects.filter(
        user=user,
        is_active=True,
        account_type='investment'
    )
    
    monthly_investment_income = Income.objects.filter(
        user=user,
        bank_account__in=investment_accounts,
        date__year=current_year,
        date__month=current_month
    ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
    
    monthly_investment_transfers = Transfer.objects.filter(
        user=user,
        to_account__in=investment_accounts,
        date__year=current_year,
        date__month=current_month
    ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
    
    monthly_investments = monthly_investment_income + monthly_investment_transfers
    
    # Annual statistics
    annual_income = Income.objects.filter(
        user=user,
        date__year=current_year
    ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
    
    annual_expense = Expense.objects.filter(
        user=user,
        date__year=current_year
    ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
    
    annual_savings = annual_income - annual_expense
    
    # Account balances
    total_balance = BankAccount.objects.filter(
        user=user,
        is_active=True
    ).aggregate(Sum('balance'))['balance__sum'] or Decimal('0')
    
    accounts = BankAccount.objects.filter(user=user, is_active=True)[:5]
    
    # Group accounts by type with colors
    all_accounts = BankAccount.objects.filter(user=user, is_active=True)
    accounts_by_type = {}
    
    type_colors = {
        'savings': '#10b981',      # Green
        'checking': '#3b82f6',     # Blue
        'investment': '#8b5cf6',   # Purple
        'credit': '#ef4444',       # Red
        'cash': '#f59e0b',         # Amber
    }
    
    type_display_names = {
        'savings': 'Savings',
        'checking': 'Checking',
        'investment': 'Investment',
        'credit': 'Credit Cards',
        'cash': 'Cash',
    }
    
    for account in all_accounts:
        acc_type = account.account_type
        if acc_type not in accounts_by_type:
            accounts_by_type[acc_type] = {
                'balance': Decimal('0'),
                'count': 0,
                'color': type_colors.get(acc_type, '#6b7280'),
                'display_name': type_display_names.get(acc_type, acc_type.title()),
                'accounts': [],
            }
        accounts_by_type[acc_type]['balance'] += account.balance
        accounts_by_type[acc_type]['count'] += 1
        accounts_by_type[acc_type]['accounts'].append(account)
    
    # Sort by balance (descending)
    accounts_by_type = dict(sorted(accounts_by_type.items(), key=lambda x: x[1]['balance'], reverse=True))
    
    # Recent transactions
    recent_incomes = Income.objects.filter(user=user)[:5]
    recent_expenses = Expense.objects.filter(user=user)[:5]
    
    # Budget tracking
    budgets = MonthlyBudget.objects.filter(
        user=user,
        month__year=current_year,
        month__month=current_month
    )
    
    budget_data = []
    for budget in budgets:
        budget_data.append({
            'budget': budget,
            'spent': budget.get_spent_amount(),
            'remaining': budget.get_remaining_amount(),
            'percentage': budget.get_percentage_used(),
        })
    
    # Calculate daily running balance per account for current month
    from calendar import monthrange
    from datetime import date, timedelta
    
    first_day = date(current_year, current_month, 1)
    last_day = date(current_year, current_month, monthrange(current_year, current_month)[1])
    
    # Get all active accounts
    active_accounts = BankAccount.objects.filter(user=user, is_active=True)
    
    # Prepare data structure for each account
    account_balance_data = {}
    daily_dates = []
    
    # Generate date labels
    current_date = first_day
    while current_date <= min(last_day, today):
        daily_dates.append(current_date)
        current_date += timedelta(days=1)
    
    # Calculate running balance for each account
    for account in active_accounts:
        # Calculate starting balance for this account
        month_income = Income.objects.filter(
            user=user,
            bank_account=account,
            date__year=current_year,
            date__month=current_month
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        
        month_expense = Expense.objects.filter(
            user=user,
            bank_account=account,
            date__year=current_year,
            date__month=current_month
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        
        month_transfers_in = Transfer.objects.filter(
            user=user,
            to_account=account,
            date__year=current_year,
            date__month=current_month
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        
        month_transfers_out = Transfer.objects.filter(
            user=user,
            from_account=account,
            date__year=current_year,
            date__month=current_month
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        
        # Starting balance = current balance - net change this month
        starting_balance = account.balance - (month_income - month_expense + month_transfers_in - month_transfers_out)
        
        # Build daily balance data for this account
        daily_balances = []
        account_balance = starting_balance
        
        for check_date in daily_dates:
            # Get transactions for this day for this account
            day_income = Income.objects.filter(
                user=user,
                bank_account=account,
                date=check_date
            ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
            
            day_expense = Expense.objects.filter(
                user=user,
                bank_account=account,
                date=check_date
            ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
            
            day_transfers_in = Transfer.objects.filter(
                user=user,
                to_account=account,
                date=check_date
            ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
            
            day_transfers_out = Transfer.objects.filter(
                user=user,
                from_account=account,
                date=check_date
            ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
            
            # Update balance
            account_balance += day_income - day_expense + day_transfers_in - day_transfers_out
            daily_balances.append(float(account_balance))
        
        account_balance_data[account.name] = daily_balances
    
    daily_balance_dates = daily_dates
    
    import json
    
    # Calculate net worth history (end of each month for past year)
    networth_history = []
    from dateutil.relativedelta import relativedelta
    
    # Go back 12 months
    start_date = today - relativedelta(months=12)
    current_date = start_date.replace(day=1)
    
    while current_date <= today:
        # Calculate net worth at end of this month
        from calendar import monthrange
        last_day = monthrange(current_date.year, current_date.month)[1]
        end_of_month = date(current_date.year, current_date.month, last_day)
        
        # Don't calculate future months
        if end_of_month > today:
            end_of_month = today
        
        # Calculate balance at this point in time
        month_balance = Decimal('0')
        for account in BankAccount.objects.filter(user=user, is_active=True, account_setup_date__lte=end_of_month):
            # Start with current balance
            historical_balance = account.balance
            
            # Subtract income added after the target date
            future_income = Income.objects.filter(
                user=user,
                bank_account=account,
                date__gt=end_of_month
            ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
            historical_balance -= future_income
            
            # Add back expenses paid after the target date
            future_expenses = Expense.objects.filter(
                user=user,
                bank_account=account,
                date__gt=end_of_month
            ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
            historical_balance += future_expenses
            
            # Adjust for transfers after the target date
            future_transfers_out = Transfer.objects.filter(
                user=user,
                from_account=account,
                date__gt=end_of_month
            ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
            historical_balance += future_transfers_out
            
            future_transfers_in = Transfer.objects.filter(
                user=user,
                to_account=account,
                date__gt=end_of_month
            ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
            historical_balance -= future_transfers_in
            
            month_balance += historical_balance
        
        networth_history.append({
            'date': end_of_month.isoformat(),
            'label': end_of_month.strftime('%b %Y'),
            'value': float(month_balance)
        })
        
        # Move to next month
        current_date += relativedelta(months=1)
        
        if current_date > today:
            break
    
    # Format networth data for JavaScript
    networth_data = {
        'dates': [item['date'] for item in networth_history],
        'labels': [item['label'] for item in networth_history],
        'values': [item['value'] for item in networth_history]
    }
    
    # Calculate spending comparison data (current month vs previous month)
    from calendar import monthrange
    from datetime import date
    
    # Get previous month
    if current_month == 1:
        prev_month = 12
        prev_year = current_year - 1
    else:
        prev_month = current_month - 1
        prev_year = current_year
    
    # Get days in each month
    current_month_days = monthrange(current_year, current_month)[1]
    prev_month_days = monthrange(prev_year, prev_month)[1]
    max_days = max(current_month_days, prev_month_days)
    
    # Calculate cumulative spending for each day
    current_month_spending = []
    prev_month_spending = []
    days_labels = []
    
    for day in range(1, max_days + 1):
        days_labels.append(str(day))
        
        # Current month cumulative spending up to this day
        if day <= current_month_days:
            current_day_total = Expense.objects.filter(
                user=user,
                date__year=current_year,
                date__month=current_month,
                date__day__lte=day
            ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
            current_month_spending.append(float(current_day_total))
        else:
            current_month_spending.append(None)
        
        # Previous month cumulative spending up to this day
        if day <= prev_month_days:
            prev_day_total = Expense.objects.filter(
                user=user,
                date__year=prev_year,
                date__month=prev_month,
                date__day__lte=day
            ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
            prev_month_spending.append(float(prev_day_total))
        else:
            prev_month_spending.append(None)
    
    from datetime import datetime
    spending_comparison_data = {
        'days': days_labels,
        'current_month': current_month_spending,
        'previous_month': prev_month_spending,
        'current_month_label': datetime(current_year, current_month, 1).strftime('%B %Y'),
        'previous_month_label': datetime(prev_year, prev_month, 1).strftime('%B %Y'),
    }
    
    context = {
        'monthly_income': monthly_income,
        'monthly_expense': monthly_expense,
        'monthly_savings': monthly_savings,
        'monthly_investments': monthly_investments,
        'annual_income': annual_income,
        'annual_expense': annual_expense,
        'annual_savings': annual_savings,
        'total_balance': total_balance,
        'accounts': accounts,
        'recent_incomes': recent_incomes,
        'recent_expenses': recent_expenses,
        'budget_data': budget_data,
        'account_balance_data': json.dumps(account_balance_data),
        'daily_balance_dates': daily_balance_dates,
        'networth_data': json.dumps(networth_data),
        'spending_comparison_data': json.dumps(spending_comparison_data),
    }
    
    return render(request, 'budget/dashboard.html', context)


# Bank Account Views
@login_required
def bank_account_list(request):
    """List all bank accounts"""
    user = request.user
    accounts = BankAccount.objects.filter(user=user)
    
    # Calculate total balance
    total_balance = BankAccount.objects.filter(
        user=user,
        is_active=True
    ).aggregate(Sum('balance'))['balance__sum'] or Decimal('0')
    
    # Group accounts by type with colors
    all_accounts = BankAccount.objects.filter(user=user, is_active=True)
    accounts_by_type = {}
    
    type_colors = {
        'savings': '#10b981',      # Green
        'checking': '#3b82f6',     # Blue
        'investment': '#8b5cf6',   # Purple
        'credit': '#ef4444',       # Red
        'cash': '#f59e0b',         # Amber
    }
    
    type_display_names = {
        'savings': 'Savings',
        'checking': 'Checking',
        'investment': 'Investment',
        'credit': 'Credit Cards',
        'cash': 'Cash',
    }
    
    for account in all_accounts:
        acc_type = account.account_type
        if acc_type not in accounts_by_type:
            accounts_by_type[acc_type] = {
                'balance': Decimal('0'),
                'count': 0,
                'color': type_colors.get(acc_type, '#6b7280'),
                'display_name': type_display_names.get(acc_type, acc_type.title()),
                'accounts': [],
            }
        accounts_by_type[acc_type]['balance'] += account.balance
        accounts_by_type[acc_type]['count'] += 1
        accounts_by_type[acc_type]['accounts'].append(account)
    
    # Sort by balance (descending)
    accounts_by_type = dict(sorted(accounts_by_type.items(), key=lambda x: x[1]['balance'], reverse=True))
    
    return render(request, 'budget/bank_account_list.html', {
        'accounts': accounts,
        'accounts_by_type': accounts_by_type,
        'total_balance': total_balance,
    })


@login_required
def bank_account_create(request):
    """Create a new bank account"""
    if request.method == 'POST':
        form = BankAccountForm(request.POST)
        if form.is_valid():
            account = form.save(commit=False)
            account.user = request.user
            account.save()
            messages.success(request, 'Bank account created successfully!')
            return redirect('bank_account_list')
    else:
        form = BankAccountForm()
    return render(request, 'budget/bank_account_form.html', {'form': form, 'action': 'Create'})


@login_required
def bank_account_update(request, pk):
    """Update a bank account"""
    account = get_object_or_404(BankAccount, pk=pk, user=request.user)
    
    if request.method == 'POST':
        # Save old values BEFORE form processing (form.save(commit=False) modifies instance in place!)
        old_opening_balance = account.opening_balance
        old_balance = account.balance
        old_setup_date = account.account_setup_date
        
        form = BankAccountForm(request.POST, instance=account)
        if form.is_valid():
            new_opening_balance = form.cleaned_data.get('opening_balance')
            
            # Preserve read-only fields to prevent tampering
            updated_account = form.save(commit=False)
            updated_account.balance = old_balance
            updated_account.account_setup_date = old_setup_date
            updated_account.opening_balance = new_opening_balance or old_opening_balance
            
            # Handle opening balance change
            opening_balance_changed = (
                new_opening_balance is not None and 
                new_opening_balance != old_opening_balance
            )
            
            if opening_balance_changed:
                # Find and update the opening balance income transaction
                try:
                    opening_income = Income.objects.select_related('category').get(
                        user=request.user,
                        bank_account=account,
                        category__name='Opening Balance',
                        category__category_type='income',
                        date=old_setup_date
                    )
                    
                    # Save account changes first
                    updated_account.save(update_fields=[
                        'name', 'account_type', 'bank_name', 'account_number', 
                        'is_active', 'opening_balance', 'updated_at'
                    ])
                    
                    # Update income transaction (automatically recalculates balance)
                    opening_income.amount = new_opening_balance
                    opening_income.description = f'Opening balance for {updated_account.name}'
                    opening_income.save()
                    
                    messages.success(
                        request, 
                        f'Opening balance updated from ${old_opening_balance} to ${new_opening_balance}. '
                        f'Current balance recalculated.'
                    )
                except Income.DoesNotExist:
                    # No existing opening balance transaction found - create a new one
                    # Get or create "Opening Balance" income category
                    initial_category, created = Category.objects.get_or_create(
                        user=request.user,
                        name='Opening Balance',
                        defaults={'category_type': 'income'}
                    )
                    
                    # Ensure the category is set to income type
                    if initial_category.category_type != 'income':
                        initial_category.category_type = 'income'
                        initial_category.save()
                    
                    # Save account changes first
                    updated_account.save(update_fields=[
                        'name', 'account_type', 'bank_name', 'account_number', 
                        'is_active', 'opening_balance', 'updated_at'
                    ])
                    
                    # Calculate net effect of all OTHER transactions (excluding opening balance)
                    # so we can preserve them when creating the new opening balance transaction
                    # Using Coalesce to handle NULL values directly in the database
                    other_incomes = Income.objects.filter(
                        user=request.user,
                        bank_account=account
                    ).exclude(category__name='Opening Balance').aggregate(
                        total=Coalesce(Sum('amount'), Decimal('0'))
                    )['total']
                    
                    other_expenses = Expense.objects.filter(
                        user=request.user,
                        bank_account=account
                    ).aggregate(total=Coalesce(Sum('amount'), Decimal('0')))['total']
                    
                    transfers_in = Transfer.objects.filter(
                        user=request.user,
                        to_account=account
                    ).aggregate(total=Coalesce(Sum('amount'), Decimal('0')))['total']
                    
                    transfers_out = Transfer.objects.filter(
                        user=request.user,
                        from_account=account
                    ).aggregate(total=Coalesce(Sum('amount'), Decimal('0')))['total']
                    
                    # Net effect of other transactions
                    other_transactions_net = other_incomes - other_expenses + transfers_in - transfers_out
                    
                    # Set balance to the net of other transactions (temporarily, before adding OB)
                    BankAccount.objects.filter(pk=account.pk).update(balance=other_transactions_net)
                    
                    # Create new opening balance income transaction
                    # This will add the opening balance amount to the current balance
                    Income.objects.create(
                        user=request.user,
                        category=initial_category,
                        bank_account=account,
                        amount=new_opening_balance,
                        description=f'Opening balance for {updated_account.name}',
                        date=old_setup_date
                    )
                    
                    messages.success(
                        request, 
                        f'Opening balance set to ${new_opening_balance}. '
                        f'Opening balance transaction created. Current balance recalculated.'
                    )
            else:
                # No opening balance change - just save account updates
                updated_account.save(update_fields=[
                    'name', 'account_type', 'bank_name', 'account_number', 
                    'is_active', 'opening_balance', 'updated_at'
                ])
                messages.success(request, 'Bank account updated successfully!')
            
            return redirect('bank_account_list')
    else:
        form = BankAccountForm(instance=account)
    
    return render(request, 'budget/bank_account_form.html', {'form': form, 'action': 'Update'})


@login_required
def bank_account_delete(request, pk):
    """Delete a bank account"""
    account = get_object_or_404(BankAccount, pk=pk, user=request.user)
    if request.method == 'POST':
        account.delete()
        messages.success(request, 'Bank account deleted successfully!')
        return redirect('bank_account_list')
    return render(request, 'budget/bank_account_confirm_delete.html', {'account': account})


# Category Views
@login_required
def category_list(request):
    """List all categories"""
    income_categories = Category.objects.filter(user=request.user, category_type='income')
    expense_categories = Category.objects.filter(user=request.user, category_type='expense')
    return render(request, 'budget/category_list.html', {
        'income_categories': income_categories,
        'expense_categories': expense_categories
    })


@login_required
def category_create(request):
    """Create a new category"""
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save(commit=False)
            category.user = request.user
            category.save()
            messages.success(request, 'Category created successfully!')
            return redirect('category_list')
    else:
        form = CategoryForm()
    return render(request, 'budget/category_form.html', {'form': form, 'action': 'Create'})


@login_required
def category_update(request, pk):
    """Update a category"""
    category = get_object_or_404(Category, pk=pk, user=request.user)
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, 'Category updated successfully!')
            return redirect('category_list')
    else:
        form = CategoryForm(instance=category)
    return render(request, 'budget/category_form.html', {'form': form, 'action': 'Update'})


@login_required
def category_delete(request, pk):
    """Delete a category"""
    category = get_object_or_404(Category, pk=pk, user=request.user)
    if request.method == 'POST':
        category.delete()
        messages.success(request, 'Category deleted successfully!')
        return redirect('category_list')
    return render(request, 'budget/category_confirm_delete.html', {'category': category})


# Income Views
@login_required
def income_list(request):
    """List all incomes with filtering"""
    from django.utils import timezone
    current_date = timezone.now()
    
    incomes = Income.objects.filter(user=request.user)
    
    # Filtering with defaults to current month and 2025
    category_filter = request.GET.get('category')
    month_filter = request.GET.get('month', str(current_date.month))
    year_filter = request.GET.get('year', '2025')
    account_filter = request.GET.get('account')
    min_amount = request.GET.get('min_amount')
    max_amount = request.GET.get('max_amount')
    tag_filters = request.GET.getlist('tag')  # Get list of tag IDs
    
    if category_filter:
        incomes = incomes.filter(category_id=category_filter)
    if month_filter:
        incomes = incomes.filter(date__month=month_filter)
    if year_filter:
        incomes = incomes.filter(date__year=year_filter)
    if account_filter:
        incomes = incomes.filter(bank_account_id=account_filter)
    if min_amount:
        incomes = incomes.filter(amount__gte=Decimal(min_amount))
    if max_amount:
        incomes = incomes.filter(amount__lte=Decimal(max_amount))
    if tag_filters:
        incomes = incomes.filter(tags__id__in=tag_filters).distinct()
    
    total_income = incomes.aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
    categories = Category.objects.filter(user=request.user, category_type='income')
    accounts = BankAccount.objects.filter(user=request.user)
    all_tags = Tag.objects.filter(user=request.user).order_by('name')
    
    # Get month name if month_filter exists
    month_name = None
    if month_filter:
        month_names = ['', 'January', 'February', 'March', 'April', 'May', 'June',
                      'July', 'August', 'September', 'October', 'November', 'December']
        month_name = month_names[int(month_filter)]
    
    context = {
        'incomes': incomes,
        'total_income': total_income,
        'categories': categories,
        'accounts': accounts,
        'selected_month': month_filter,
        'selected_year': year_filter,
        'month_name': month_name,
        'all_tags': all_tags,
        'selected_tags': [int(t) for t in tag_filters if t],
    }
    return render(request, 'budget/income_list.html', context)


@login_required
def income_create(request):
    """Create a new income"""
    if request.method == 'POST':
        form = IncomeForm(request.POST, user=request.user)
        if form.is_valid():
            income = form.save(commit=False)
            income.user = request.user
            income.save()
            
            # Handle tags
            tags_input = form.cleaned_data.get('tags_input', '')
            if tags_input:
                tag_names = [tag.strip() for tag in tags_input.split(',') if tag.strip()]
                for tag_name in tag_names:
                    # Normalize to camelCase
                    normalized_name = Tag.normalize_tag_name(tag_name)
                    if normalized_name:
                        # Get or create tag (case-insensitive search)
                        tag, created = Tag.objects.get_or_create(
                            user=request.user,
                            name__iexact=normalized_name,
                            defaults={
                                'name': normalized_name,
                                'color': get_random_tag_color()
                            }
                        )
                        # If tag was found with different casing, use existing
                        if not created:
                            tag = Tag.objects.get(user=request.user, name__iexact=normalized_name)
                        income.tags.add(tag)
            
            messages.success(request, 'Income added successfully!')
            return redirect('income_list')
    else:
        form = IncomeForm(user=request.user)
    
    # Get all existing tags for autocomplete
    existing_tags = Tag.objects.filter(user=request.user).order_by('name').values_list('name', flat=True)
    return render(request, 'budget/income_form.html', {
        'form': form,
        'action': 'Add',
        'existing_tags': list(existing_tags)
    })


@login_required
def income_update(request, pk):
    """Update an income"""
    income = get_object_or_404(Income, pk=pk, user=request.user)
    if request.method == 'POST':
        form = IncomeForm(request.POST, instance=income, user=request.user)
        if form.is_valid():
            income = form.save()
            
            # Update tags atomically
            tags_input = form.cleaned_data.get('tags_input', '')
            tag_objects = []
            if tags_input:
                tag_names = [tag.strip() for tag in tags_input.split(',') if tag.strip()]
                for tag_name in tag_names:
                    # Normalize to camelCase
                    normalized_name = Tag.normalize_tag_name(tag_name)
                    if normalized_name:
                        # Get or create tag (case-insensitive search)
                        tag, created = Tag.objects.get_or_create(
                            user=request.user,
                            name__iexact=normalized_name,
                            defaults={
                                'name': normalized_name,
                                'color': get_random_tag_color()
                            }
                        )
                        # If tag was found with different casing, use existing
                        if not created:
                            tag = Tag.objects.get(user=request.user, name__iexact=normalized_name)
                        tag_objects.append(tag)
            # Atomic replace - either set new tags or clear all
            income.tags.set(tag_objects)
            
            messages.success(request, 'Income updated successfully!')
            return redirect('income_list')
    else:
        form = IncomeForm(instance=income, user=request.user)
    
    # Get all existing tags for autocomplete
    existing_tags = Tag.objects.filter(user=request.user).order_by('name').values_list('name', flat=True)
    return render(request, 'budget/income_form.html', {
        'form': form,
        'action': 'Update',
        'existing_tags': list(existing_tags)
    })


@login_required
def income_clone(request, pk):
    """Clone an income transaction"""
    original_income = get_object_or_404(Income, pk=pk, user=request.user)
    
    if request.method == 'POST':
        form = IncomeForm(request.POST, user=request.user)
        if form.is_valid():
            income = form.save(commit=False)
            income.user = request.user
            income.save()
            
            # Handle tags
            tags_input = form.cleaned_data.get('tags_input', '')
            if tags_input:
                tag_names = [tag.strip() for tag in tags_input.split(',') if tag.strip()]
                for tag_name in tag_names:
                    # Normalize to camelCase
                    normalized_name = Tag.normalize_tag_name(tag_name)
                    if normalized_name:
                        # Get or create tag (case-insensitive search)
                        tag, created = Tag.objects.get_or_create(
                            user=request.user,
                            name__iexact=normalized_name,
                            defaults={
                                'name': normalized_name,
                                'color': get_random_tag_color()
                            }
                        )
                        # If tag was found with different casing, use existing
                        if not created:
                            tag = Tag.objects.get(user=request.user, name__iexact=normalized_name)
                        income.tags.add(tag)
            
            messages.success(request, 'Income cloned successfully!')
            return redirect('income_list')
    else:
        # Get original tags
        original_tags = original_income.tags.all()
        tags_string = ', '.join([tag.name for tag in original_tags])
        
        # Create a form with original data but without the instance (so it creates a new one)
        form = IncomeForm(
            initial={
                'category': original_income.category,
                'bank_account': original_income.bank_account,
                'amount': original_income.amount,
                'description': f"Copy of: {original_income.description}",
                'date': original_income.date,
                'tags_input': tags_string,
            },
            user=request.user
        )
        
        messages.info(request, f'Cloning income transaction. Review and modify as needed before saving.')
    
    # Get all existing tags for autocomplete
    existing_tags = Tag.objects.filter(user=request.user).order_by('name').values_list('name', flat=True)
    
    return render(request, 'budget/income_form.html', {
        'form': form,
        'action': 'Clone',
        'existing_tags': list(existing_tags),
        'is_clone': True,
    })


@login_required
def income_delete(request, pk):
    """Delete an income"""
    income = get_object_or_404(Income, pk=pk, user=request.user)
    
    # Protect Opening Balance transactions
    if income.is_opening_balance():
        messages.error(request, 'Cannot delete Opening Balance transaction! To change the opening balance, edit the account instead.')
        return redirect('income_list')
    
    if request.method == 'POST':
        # Balance update now handled atomically in model's delete() method
        income.delete()
        messages.success(request, 'Income deleted successfully!')
        return redirect('income_list')
    return render(request, 'budget/income_confirm_delete.html', {'income': income})


@login_required
def income_bulk_tag(request):
    """Bulk add or remove tags from selected incomes"""
    if request.method == 'POST':
        income_ids = request.POST.getlist('income_ids')
        action = request.POST.get('action')
        tag_ids = request.POST.get('tags', '').split(',')
        
        if not income_ids:
            messages.error(request, 'No income transactions selected')
            return redirect('income_list')
        
        if not tag_ids or tag_ids == ['']:
            messages.error(request, 'No tags selected')
            return redirect('income_list')
        
        # Get the selected incomes and tags
        incomes = Income.objects.filter(pk__in=income_ids, user=request.user)
        tags = Tag.objects.filter(pk__in=tag_ids, user=request.user)
        
        count = 0
        if action == 'add':
            for income in incomes:
                for tag in tags:
                    income.tags.add(tag)
                count += 1
            messages.success(request, f'Tags added to {count} income transaction(s)')
        elif action == 'remove':
            for income in incomes:
                for tag in tags:
                    income.tags.remove(tag)
                count += 1
            messages.success(request, f'Tags removed from {count} income transaction(s)')
        else:
            messages.error(request, 'Invalid action')
        
        return redirect('income_list')
    
    return redirect('income_list')


@login_required
def income_bulk_delete(request):
    """Bulk delete selected incomes"""
    if request.method == 'POST':
        income_ids = request.POST.getlist('income_ids')
        
        if not income_ids:
            messages.error(request, 'No income transactions selected')
            return redirect('income_list')
        
        # Get the selected incomes
        incomes = Income.objects.filter(pk__in=income_ids, user=request.user)
        
        # Separate Opening Balance transactions from regular ones
        protected_count = 0
        deleted_count = 0
        
        # Delete each income individually to trigger model's delete method
        # which handles balance updates, but skip Opening Balance transactions
        for income in incomes:
            if income.is_opening_balance():
                protected_count += 1
            else:
                income.delete()
                deleted_count += 1
        
        # Show appropriate messages
        if deleted_count > 0:
            messages.success(request, f'Successfully deleted {deleted_count} income transaction(s)')
        if protected_count > 0:
            messages.warning(request, f'Skipped {protected_count} Opening Balance transaction(s) - these are protected and can only be changed by editing the account')
        
        if deleted_count == 0 and protected_count == 0:
            messages.info(request, 'No transactions were deleted')
        
        return redirect('income_list')
    
    return redirect('income_list')


# Expense Views
@login_required
def expense_list(request):
    """List all expenses with filtering"""
    from django.utils import timezone
    current_date = timezone.now()
    
    expenses = Expense.objects.filter(user=request.user)
    
    # Filtering with defaults to current month and 2025
    category_filter = request.GET.get('category')
    month_filter = request.GET.get('month', str(current_date.month))
    year_filter = request.GET.get('year', '2025')
    account_filter = request.GET.get('account')
    min_amount = request.GET.get('min_amount')
    max_amount = request.GET.get('max_amount')
    tag_filters = request.GET.getlist('tag')  # Get list of tag IDs
    
    if category_filter:
        expenses = expenses.filter(category_id=category_filter)
    if month_filter:
        expenses = expenses.filter(date__month=month_filter)
    if year_filter:
        expenses = expenses.filter(date__year=year_filter)
    if account_filter:
        expenses = expenses.filter(bank_account_id=account_filter)
    if min_amount:
        expenses = expenses.filter(amount__gte=Decimal(min_amount))
    if max_amount:
        expenses = expenses.filter(amount__lte=Decimal(max_amount))
    if tag_filters:
        expenses = expenses.filter(tags__id__in=tag_filters).distinct()
    
    total_expense = expenses.aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
    categories = Category.objects.filter(user=request.user, category_type='expense')
    accounts = BankAccount.objects.filter(user=request.user)
    all_tags = Tag.objects.filter(user=request.user).order_by('name')
    
    # Get month name if month_filter exists
    month_name = None
    if month_filter:
        month_names = ['', 'January', 'February', 'March', 'April', 'May', 'June',
                      'July', 'August', 'September', 'October', 'November', 'December']
        month_name = month_names[int(month_filter)]
    
    context = {
        'expenses': expenses,
        'total_expense': total_expense,
        'categories': categories,
        'accounts': accounts,
        'selected_month': month_filter,
        'selected_year': year_filter,
        'month_name': month_name,
        'all_tags': all_tags,
        'selected_tags': [int(t) for t in tag_filters if t],
    }
    return render(request, 'budget/expense_list.html', context)


@login_required
def expense_create(request):
    """Create a new expense"""
    if request.method == 'POST':
        form = ExpenseForm(request.POST, user=request.user)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.user = request.user
            expense.save()
            
            # Handle tags
            tags_input = form.cleaned_data.get('tags_input', '')
            if tags_input:
                tag_names = [tag.strip() for tag in tags_input.split(',') if tag.strip()]
                for tag_name in tag_names:
                    # Normalize to camelCase
                    normalized_name = Tag.normalize_tag_name(tag_name)
                    if normalized_name:
                        # Get or create tag (case-insensitive search)
                        tag, created = Tag.objects.get_or_create(
                            user=request.user,
                            name__iexact=normalized_name,
                            defaults={
                                'name': normalized_name,
                                'color': get_random_tag_color()
                            }
                        )
                        # If tag was found with different casing, use existing
                        if not created:
                            tag = Tag.objects.get(user=request.user, name__iexact=normalized_name)
                        expense.tags.add(tag)
            
            messages.success(request, 'Expense added successfully!')
            return redirect('expense_list')
    else:
        form = ExpenseForm(user=request.user)
    
    # Get all existing tags for autocomplete
    existing_tags = Tag.objects.filter(user=request.user).order_by('name').values_list('name', flat=True)
    return render(request, 'budget/expense_form.html', {
        'form': form,
        'action': 'Add',
        'existing_tags': list(existing_tags)
    })


@login_required
def expense_update(request, pk):
    """Update an expense"""
    expense = get_object_or_404(Expense, pk=pk, user=request.user)
    if request.method == 'POST':
        form = ExpenseForm(request.POST, instance=expense, user=request.user)
        if form.is_valid():
            expense = form.save()
            
            # Update tags atomically
            tags_input = form.cleaned_data.get('tags_input', '')
            tag_objects = []
            if tags_input:
                tag_names = [tag.strip() for tag in tags_input.split(',') if tag.strip()]
                for tag_name in tag_names:
                    # Normalize to camelCase
                    normalized_name = Tag.normalize_tag_name(tag_name)
                    if normalized_name:
                        # Get or create tag (case-insensitive search)
                        tag, created = Tag.objects.get_or_create(
                            user=request.user,
                            name__iexact=normalized_name,
                            defaults={
                                'name': normalized_name,
                                'color': get_random_tag_color()
                            }
                        )
                        # If tag was found with different casing, use existing
                        if not created:
                            tag = Tag.objects.get(user=request.user, name__iexact=normalized_name)
                        tag_objects.append(tag)
            # Atomic replace - either set new tags or clear all
            expense.tags.set(tag_objects)
            
            messages.success(request, 'Expense updated successfully!')
            return redirect('expense_list')
    else:
        form = ExpenseForm(instance=expense, user=request.user)
    
    # Get all existing tags for autocomplete
    existing_tags = Tag.objects.filter(user=request.user).order_by('name').values_list('name', flat=True)
    return render(request, 'budget/expense_form.html', {
        'form': form,
        'action': 'Update',
        'existing_tags': list(existing_tags)
    })


@login_required
def expense_clone(request, pk):
    """Clone an expense transaction"""
    original_expense = get_object_or_404(Expense, pk=pk, user=request.user)
    
    if request.method == 'POST':
        form = ExpenseForm(request.POST, user=request.user)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.user = request.user
            expense.save()
            
            # Handle tags
            tags_input = form.cleaned_data.get('tags_input', '')
            if tags_input:
                tag_names = [tag.strip() for tag in tags_input.split(',') if tag.strip()]
                for tag_name in tag_names:
                    # Normalize to camelCase
                    normalized_name = Tag.normalize_tag_name(tag_name)
                    if normalized_name:
                        # Get or create tag (case-insensitive search)
                        tag, created = Tag.objects.get_or_create(
                            user=request.user,
                            name__iexact=normalized_name,
                            defaults={
                                'name': normalized_name,
                                'color': get_random_tag_color()
                            }
                        )
                        # If tag was found with different casing, use existing
                        if not created:
                            tag = Tag.objects.get(user=request.user, name__iexact=normalized_name)
                        expense.tags.add(tag)
            
            messages.success(request, 'Expense cloned successfully!')
            return redirect('expense_list')
    else:
        # Get original tags
        original_tags = original_expense.tags.all()
        tags_string = ', '.join([tag.name for tag in original_tags])
        
        # Create a form with original data but without the instance (so it creates a new one)
        form = ExpenseForm(
            initial={
                'category': original_expense.category,
                'bank_account': original_expense.bank_account,
                'amount': original_expense.amount,
                'description': f"Copy of: {original_expense.description}",
                'date': original_expense.date,
                'tags_input': tags_string,
            },
            user=request.user
        )
        
        messages.info(request, f'Cloning expense transaction. Review and modify as needed before saving.')
    
    # Get all existing tags for autocomplete
    existing_tags = Tag.objects.filter(user=request.user).order_by('name').values_list('name', flat=True)
    
    return render(request, 'budget/expense_form.html', {
        'form': form,
        'action': 'Clone',
        'existing_tags': list(existing_tags),
        'is_clone': True,
    })


@login_required
def expense_delete(request, pk):
    """Delete an expense"""
    expense = get_object_or_404(Expense, pk=pk, user=request.user)
    if request.method == 'POST':
        # Balance update now handled atomically in model's delete() method
        expense.delete()
        messages.success(request, 'Expense deleted successfully!')
        return redirect('expense_list')
    return render(request, 'budget/expense_confirm_delete.html', {'expense': expense})


@login_required
def expense_bulk_tag(request):
    """Bulk add or remove tags from selected expenses"""
    if request.method == 'POST':
        expense_ids = request.POST.getlist('expense_ids')
        action = request.POST.get('action')
        tag_ids = request.POST.get('tags', '').split(',')
        
        if not expense_ids:
            messages.error(request, 'No expense transactions selected')
            return redirect('expense_list')
        
        if not tag_ids or tag_ids == ['']:
            messages.error(request, 'No tags selected')
            return redirect('expense_list')
        
        # Get the selected expenses and tags
        expenses = Expense.objects.filter(pk__in=expense_ids, user=request.user)
        tags = Tag.objects.filter(pk__in=tag_ids, user=request.user)
        
        count = 0
        if action == 'add':
            for expense in expenses:
                for tag in tags:
                    expense.tags.add(tag)
                count += 1
            messages.success(request, f'Tags added to {count} expense transaction(s)')
        elif action == 'remove':
            for expense in expenses:
                for tag in tags:
                    expense.tags.remove(tag)
                count += 1
            messages.success(request, f'Tags removed from {count} expense transaction(s)')
        else:
            messages.error(request, 'Invalid action')
        
        return redirect('expense_list')
    
    return redirect('expense_list')


@login_required
def expense_bulk_delete(request):
    """Bulk delete selected expenses"""
    if request.method == 'POST':
        expense_ids = request.POST.getlist('expense_ids')
        
        if not expense_ids:
            messages.error(request, 'No expense transactions selected')
            return redirect('expense_list')
        
        # Get the selected expenses
        expenses = Expense.objects.filter(pk__in=expense_ids, user=request.user)
        count = expenses.count()
        
        # Delete each expense individually to trigger model's delete method
        # which handles balance updates
        for expense in expenses:
            expense.delete()
        
        messages.success(request, f'Successfully deleted {count} expense transaction(s)')
        return redirect('expense_list')
    
    return redirect('expense_list')


# Budget Views
@login_required
def budget_list(request):
    """List all monthly budgets"""
    from django.utils import timezone
    from datetime import datetime
    
    # Get current month and year as defaults
    now = timezone.now()
    default_year = str(now.year)
    default_month = str(now.month)
    
    year_filter = request.GET.get('year', default_year)
    month_filter = request.GET.get('month', default_month)
    
    budgets = MonthlyBudget.objects.filter(user=request.user)
    
    # Filter by year and month if provided
    if year_filter and month_filter:
        filter_date = datetime(int(year_filter), int(month_filter), 1).date()
        budgets = budgets.filter(month=filter_date)
    
    # Order by category name
    budgets = budgets.order_by('category__name')
    
    budget_data = []
    for budget in budgets:
        budget_data.append({
            'budget': budget,
            'spent': budget.get_spent_amount(),
            'remaining': budget.get_remaining_amount(),
            'percentage': budget.get_percentage_used(),
        })
    
    return render(request, 'budget/budget_list.html', {
        'budget_data': budget_data,
        'selected_year': year_filter,
        'selected_month': month_filter
    })


@login_required
def budget_create(request):
    """Create a new monthly budget"""
    if request.method == 'POST':
        form = MonthlyBudgetForm(request.POST, user=request.user)
        if form.is_valid():
            budget = form.save(commit=False)
            budget.user = request.user
            try:
                budget.save()
                messages.success(request, 'Budget created successfully!')
                return redirect('budget_list')
            except:
                messages.error(request, 'Budget for this category and month already exists!')
    else:
        form = MonthlyBudgetForm(user=request.user)
    return render(request, 'budget/budget_form.html', {'form': form, 'action': 'Create'})


@login_required
def budget_update(request, pk):
    """Update a monthly budget"""
    budget = get_object_or_404(MonthlyBudget, pk=pk, user=request.user)
    if request.method == 'POST':
        form = MonthlyBudgetForm(request.POST, instance=budget, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Budget updated successfully!')
            return redirect('budget_list')
    else:
        form = MonthlyBudgetForm(instance=budget, user=request.user)
    return render(request, 'budget/budget_form.html', {'form': form, 'action': 'Update'})


@login_required
def budget_delete(request, pk):
    """Delete a monthly budget"""
    budget = get_object_or_404(MonthlyBudget, pk=pk, user=request.user)
    if request.method == 'POST':
        budget.delete()
        messages.success(request, 'Budget deleted successfully!')
        return redirect('budget_list')
    return render(request, 'budget/budget_confirm_delete.html', {'budget': budget})


@login_required
def budget_copy_previous(request):
    """Copy budgets from previous month to current/selected month"""
    from django.utils import timezone
    from datetime import datetime
    from dateutil.relativedelta import relativedelta
    
    if request.method == 'POST':
        year = request.POST.get('year')
        month = request.POST.get('month')
        
        if year and month:
            target_date = datetime(int(year), int(month), 1).date()
            previous_date = target_date - relativedelta(months=1)
            
            # Get previous month's budgets
            previous_budgets = MonthlyBudget.objects.filter(
                user=request.user,
                month=previous_date
            )
            
            if not previous_budgets.exists():
                messages.error(request, f'No budgets found for {previous_date.strftime("%B %Y")}')
                return redirect(f'budget_list?year={year}&month={month}')
            
            # Check if target month already has budgets
            existing_budgets = MonthlyBudget.objects.filter(
                user=request.user,
                month=target_date
            )
            
            if existing_budgets.exists():
                messages.warning(request, f'Budgets already exist for {target_date.strftime("%B %Y")}')
                return redirect(f'budget_list?year={year}&month={month}')
            
            # Copy budgets
            copied_count = 0
            for prev_budget in previous_budgets:
                MonthlyBudget.objects.create(
                    user=request.user,
                    category=prev_budget.category,
                    month=target_date,
                    budgeted_amount=prev_budget.budgeted_amount
                )
                copied_count += 1
            
            messages.success(request, f'Successfully copied {copied_count} budget(s) from {previous_date.strftime("%B %Y")}')
            return redirect(f'budget_list?year={year}&month={month}')
    
    return redirect('budget_list')


# Transfer Views
@login_required
def transfer_list(request):
    """List all transfers with filtering"""
    from django.utils import timezone
    current_date = timezone.now()
    
    transfers = Transfer.objects.filter(user=request.user)
    
    # Filtering with defaults
    from_account_filter = request.GET.get('from_account')
    to_account_filter = request.GET.get('to_account')
    month_filter = request.GET.get('month', str(current_date.month))
    year_filter = request.GET.get('year', '2025')
    min_amount = request.GET.get('min_amount')
    max_amount = request.GET.get('max_amount')
    
    if from_account_filter:
        transfers = transfers.filter(from_account_id=from_account_filter)
    if to_account_filter:
        transfers = transfers.filter(to_account_id=to_account_filter)
    if month_filter:
        transfers = transfers.filter(date__month=month_filter)
    if year_filter:
        transfers = transfers.filter(date__year=year_filter)
    if min_amount:
        transfers = transfers.filter(amount__gte=Decimal(min_amount))
    if max_amount:
        transfers = transfers.filter(amount__lte=Decimal(max_amount))
    
    accounts = BankAccount.objects.filter(user=request.user)
    
    # Get month name if month_filter exists
    month_name = None
    if month_filter:
        month_names = ['', 'January', 'February', 'March', 'April', 'May', 'June',
                      'July', 'August', 'September', 'October', 'November', 'December']
        month_name = month_names[int(month_filter)]
    
    context = {
        'transfers': transfers,
        'accounts': accounts,
        'month_name': month_name,
        'selected_month': month_filter,
        'selected_year': year_filter,
    }
    return render(request, 'budget/transfer_list.html', context)


@login_required
def transfer_create(request):
    """Create a new transfer"""
    if request.method == 'POST':
        form = TransferForm(request.POST, user=request.user)
        if form.is_valid():
            transfer = form.save(commit=False)
            transfer.user = request.user
            transfer.save()
            messages.success(request, 'Transfer completed successfully!')
            return redirect('transfer_list')
    else:
        form = TransferForm(user=request.user)
    return render(request, 'budget/transfer_form.html', {'form': form, 'action': 'Create'})


@login_required
def transfer_update(request, pk):
    """Update a transfer"""
    transfer = get_object_or_404(Transfer, pk=pk, user=request.user)
    if request.method == 'POST':
        form = TransferForm(request.POST, instance=transfer, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Transfer updated successfully!')
            return redirect('transfer_list')
    else:
        form = TransferForm(instance=transfer, user=request.user)
    return render(request, 'budget/transfer_form.html', {'form': form, 'action': 'Update'})


@login_required
def transfer_clone(request, pk):
    """Clone a transfer transaction"""
    original_transfer = get_object_or_404(Transfer, pk=pk, user=request.user)
    
    if request.method == 'POST':
        form = TransferForm(request.POST, user=request.user)
        if form.is_valid():
            transfer = form.save(commit=False)
            transfer.user = request.user
            transfer.save()
            messages.success(request, 'Transfer cloned successfully!')
            return redirect('transfer_list')
    else:
        # Create a form with original data but without the instance (so it creates a new one)
        form = TransferForm(
            initial={
                'from_account': original_transfer.from_account,
                'to_account': original_transfer.to_account,
                'amount': original_transfer.amount,
                'description': f"Copy of: {original_transfer.description}" if original_transfer.description else "Copy of transfer",
                'date': original_transfer.date,
            },
            user=request.user
        )
        
        messages.info(request, f'Cloning transfer transaction. Review and modify as needed before saving.')
    
    return render(request, 'budget/transfer_form.html', {
        'form': form,
        'action': 'Clone',
        'is_clone': True,
    })


@login_required
def transfer_delete(request, pk):
    """Delete a transfer"""
    transfer = get_object_or_404(Transfer, pk=pk, user=request.user)
    if request.method == 'POST':
        # Balance reversal now handled atomically in model's delete() method
        transfer.delete()
        messages.success(request, 'Transfer deleted successfully!')
        return redirect('transfer_list')
    return render(request, 'budget/transfer_confirm_delete.html', {'transfer': transfer})


# Report Views
@login_required
def monthly_summary(request):
    """Monthly summary report"""
    month_select = request.GET.get('month_select', None)
    year_select = request.GET.get('year_select', None)
    tag_filters = request.GET.getlist('tag')  # Get list of tag IDs
    
    if month_select and year_select:
        try:
            year = int(year_select)
            month = int(month_select)
        except:
            year = 2025
            month = timezone.now().month
    else:
        year = 2025
        month = timezone.now().month
    
    # Income summary
    incomes = Income.objects.filter(user=request.user, date__year=year, date__month=month)
    if tag_filters:
        # Filter by multiple tags (OR logic - transactions with ANY of the selected tags)
        incomes = incomes.filter(tags__id__in=tag_filters).distinct()
    income_by_category = incomes.values('category__name').annotate(total=Sum('amount')).order_by('-total')
    total_income = incomes.aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
    
    # Expense summary
    expenses = Expense.objects.filter(user=request.user, date__year=year, date__month=month)
    if tag_filters:
        # Filter by multiple tags (OR logic - transactions with ANY of the selected tags)
        expenses = expenses.filter(tags__id__in=tag_filters).distinct()
    expense_by_category_raw = expenses.values('category__name', 'category_id').annotate(total=Sum('amount')).order_by('-total')
    total_expense = expenses.aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
    
    # Add budget information to each category
    from datetime import date
    expense_by_category = []
    for item in expense_by_category_raw:
        category_id = item['category_id']
        spent = item['total']
        
        # Find budget for this category and month
        try:
            budget = MonthlyBudget.objects.get(
                user=request.user,
                category_id=category_id,
                month=date(year, month, 1)
            )
            budgeted = budget.budgeted_amount
            remaining = budgeted - spent
        except MonthlyBudget.DoesNotExist:
            budgeted = None
            remaining = None
        
        expense_by_category.append({
            'category__name': item['category__name'],
            'total': spent,
            'budget': budgeted,
            'remaining': remaining
        })
    
    # Savings
    savings = total_income - total_expense
    
    # Calculate total investments (income + transfers to investment accounts)
    investments_from_income = Income.objects.filter(
        user=request.user,
        date__year=year,
        date__month=month,
        bank_account__account_type='investment'
    ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
    
    investments_from_transfers = Transfer.objects.filter(
        user=request.user,
        date__year=year,
        date__month=month,
        to_account__account_type='investment'
    ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
    
    total_investments = investments_from_income + investments_from_transfers
    
    # Calculate historical account balances as of end of selected month
    from calendar import monthrange
    last_day = monthrange(year, month)[1]
    end_of_month = datetime(year, month, last_day).date()
    
    # Only include accounts that existed at the end of the selected month
    accounts = BankAccount.objects.filter(
        user=request.user, 
        is_active=True,
        account_setup_date__lte=end_of_month
    )
    account_balances = []
    total_balance = Decimal('0')
    
    for account in accounts:
        # Start with current balance
        historical_balance = account.balance
        
        # Subtract income added after the target month
        future_income = Income.objects.filter(
            user=request.user,
            bank_account=account,
            date__gt=end_of_month
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        historical_balance -= future_income
        
        # Add back expenses paid after the target month
        future_expenses = Expense.objects.filter(
            user=request.user,
            bank_account=account,
            date__gt=end_of_month
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        historical_balance += future_expenses
        
        # Adjust for transfers after the target month
        future_transfers_out = Transfer.objects.filter(
            user=request.user,
            from_account=account,
            date__gt=end_of_month
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        historical_balance += future_transfers_out
        
        future_transfers_in = Transfer.objects.filter(
            user=request.user,
            to_account=account,
            date__gt=end_of_month
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        historical_balance -= future_transfers_in
        
        account_balances.append({
            'account': account,
            'balance': historical_balance
        })
        total_balance += historical_balance
    
    # Get earliest account setup date for min date validation
    earliest_account = BankAccount.objects.filter(user=request.user).order_by('account_setup_date').first()
    min_date = earliest_account.account_setup_date if earliest_account else None
    
    # Get all user tags for filter dropdown
    all_tags = Tag.objects.filter(user=request.user).order_by('name')
    
    context = {
        'year': year,
        'month': month,
        'month_name': datetime(year, month, 1).strftime('%B'),
        'income_by_category': income_by_category,
        'expense_by_category': expense_by_category,
        'total_income': total_income,
        'total_expense': total_expense,
        'savings': savings,
        'total_investments': total_investments,
        'account_balances': account_balances,
        'total_balance': total_balance,
        'min_date': min_date,
        'all_tags': all_tags,
        'selected_tags': [int(t) for t in tag_filters if t],  # Convert to integers
    }
    
    return render(request, 'budget/monthly_summary.html', context)


@login_required
def annual_summary(request):
    """Annual summary report"""
    year = request.GET.get('year', 2025)
    tag_filters = request.GET.getlist('tag')  # Get list of tag IDs
    
    try:
        year = int(year)
    except:
        year = 2025
    
    # Annual totals with tag filtering
    income_query = Income.objects.filter(user=request.user, date__year=year)
    if tag_filters:
        income_query = income_query.filter(tags__id__in=tag_filters).distinct()
    total_income = income_query.aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
    
    expense_query = Expense.objects.filter(user=request.user, date__year=year)
    if tag_filters:
        expense_query = expense_query.filter(tags__id__in=tag_filters).distinct()
    total_expense = expense_query.aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
    
    annual_savings = total_income - total_expense
    
    # Monthly breakdown with tag filtering
    monthly_data = []
    for month in range(1, 13):
        month_income_query = Income.objects.filter(
            user=request.user, date__year=year, date__month=month
        )
        if tag_filters:
            month_income_query = month_income_query.filter(tags__id__in=tag_filters).distinct()
        month_income = month_income_query.aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        
        month_expense_query = Expense.objects.filter(
            user=request.user, date__year=year, date__month=month
        )
        if tag_filters:
            month_expense_query = month_expense_query.filter(tags__id__in=tag_filters).distinct()
        month_expense = month_expense_query.aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        
        # Calculate monthly investments (income + transfers to investment accounts)
        month_investment_income = Income.objects.filter(
            user=request.user,
            date__year=year,
            date__month=month,
            bank_account__account_type='investment'
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        
        month_investment_transfers = Transfer.objects.filter(
            user=request.user,
            date__year=year,
            date__month=month,
            to_account__account_type='investment'
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        
        month_investment = month_investment_income + month_investment_transfers
        
        monthly_data.append({
            'month': datetime(year, month, 1).strftime('%B'),
            'income': month_income,
            'expense': month_expense,
            'savings': month_income - month_expense,
            'investment': month_investment,
        })
    
    # Category breakdown with tag filtering
    income_by_category_query = Income.objects.filter(user=request.user, date__year=year)
    if tag_filters:
        income_by_category_query = income_by_category_query.filter(tags__id__in=tag_filters).distinct()
    income_by_category = income_by_category_query.values('category__name').annotate(total=Sum('amount')).order_by('-total')
    
    expense_by_category_query = Expense.objects.filter(user=request.user, date__year=year)
    if tag_filters:
        expense_by_category_query = expense_by_category_query.filter(tags__id__in=tag_filters).distinct()
    expense_by_category = expense_by_category_query.values('category__name').annotate(total=Sum('amount')).order_by('-total')
    
    # Calculate historical net worth as of end of selected year
    end_of_year = datetime(year, 12, 31).date()
    
    # Only include accounts that existed at the end of the selected year
    accounts = BankAccount.objects.filter(
        user=request.user, 
        is_active=True,
        account_setup_date__lte=end_of_year
    )
    account_balances = []
    total_balance = Decimal('0')
    
    for account in accounts:
        # Start with current balance
        historical_balance = account.balance
        
        # Subtract income added after the target year
        future_income = Income.objects.filter(
            user=request.user,
            bank_account=account,
            date__gt=end_of_year
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        historical_balance -= future_income
        
        # Add back expenses paid after the target year
        future_expenses = Expense.objects.filter(
            user=request.user,
            bank_account=account,
            date__gt=end_of_year
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        historical_balance += future_expenses
        
        # Adjust for transfers after the target year
        future_transfers_out = Transfer.objects.filter(
            user=request.user,
            from_account=account,
            date__gt=end_of_year
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        historical_balance += future_transfers_out
        
        future_transfers_in = Transfer.objects.filter(
            user=request.user,
            to_account=account,
            date__gt=end_of_year
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        historical_balance -= future_transfers_in
        
        account_balances.append({
            'account': account,
            'balance': historical_balance
        })
        total_balance += historical_balance
    
    # Calculate total investments (income + transfers to investment accounts)
    investments_from_income = Income.objects.filter(
        user=request.user,
        date__year=year,
        bank_account__account_type='investment'
    ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
    
    investments_from_transfers = Transfer.objects.filter(
        user=request.user,
        date__year=year,
        to_account__account_type='investment'
    ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
    
    total_investments = investments_from_income + investments_from_transfers
    
    # Get earliest account setup date for min date validation
    earliest_account = BankAccount.objects.filter(user=request.user).order_by('account_setup_date').first()
    min_year = earliest_account.account_setup_date.year if earliest_account else None
    
    # Get all user tags for filter dropdown
    all_tags = Tag.objects.filter(user=request.user).order_by('name')
    
    context = {
        'year': year,
        'total_income': total_income,
        'total_expense': total_expense,
        'annual_savings': annual_savings,
        'total_investments': total_investments,
        'monthly_data': monthly_data,
        'income_by_category': income_by_category,
        'expense_by_category': expense_by_category,
        'net_worth': total_balance,
        'account_balances': account_balances,
        'min_year': min_year,
        'all_tags': all_tags,
        'selected_tags': [int(t) for t in tag_filters if t],  # Convert to integers
    }
    
    return render(request, 'budget/annual_summary.html', context)


@login_required
def tag_list(request):
    """List all tags"""
    from django.db.models import Count
    
    # Optimize with annotation to prevent N+1 queries
    tags = Tag.objects.filter(user=request.user).annotate(
        income_count=Count('incomes', distinct=True),
        expense_count=Count('expenses', distinct=True)
    ).order_by('name')
    
    # Calculate total usage
    tag_usage = []
    for tag in tags:
        tag_usage.append({
            'tag': tag,
            'income_count': tag.income_count,
            'expense_count': tag.expense_count,
            'total_count': tag.income_count + tag.expense_count
        })
    
    return render(request, 'budget/tag_list.html', {'tag_usage': tag_usage})


@login_required
def tag_create(request):
    """Create a new tag"""
    if request.method == 'POST':
        form = TagForm(request.POST, user=request.user)
        if form.is_valid():
            tag = form.save(commit=False)
            tag.user = request.user
            # Randomly assign a color from available choices
            tag.color = get_random_tag_color()
            try:
                tag.save()
                messages.success(request, f'Tag "{tag.name}" created successfully!')
                return redirect('tag_list')
            except Exception as e:
                messages.error(request, f'Error creating tag: {str(e)}')
    else:
        form = TagForm(user=request.user)
    
    return render(request, 'budget/tag_form.html', {'form': form, 'action': 'Create'})


@login_required
def tag_update(request, pk):
    """Update a tag"""
    tag = get_object_or_404(Tag, pk=pk, user=request.user)
    
    if request.method == 'POST':
        form = TagForm(request.POST, instance=tag, user=request.user)
        if form.is_valid():
            tag = form.save()
            messages.success(request, f'Tag "{tag.name}" updated successfully!')
            return redirect('tag_list')
    else:
        form = TagForm(instance=tag, user=request.user)
    
    return render(request, 'budget/tag_form.html', {'form': form, 'action': 'Update', 'tag': tag})


@login_required
def tag_delete(request, pk):
    """Delete a tag"""
    tag = get_object_or_404(Tag, pk=pk, user=request.user)
    
    if request.method == 'POST':
        tag_name = tag.name
        tag.delete()
        messages.success(request, f'Tag "{tag_name}" deleted successfully!')
        return redirect('tag_list')
    
    # Count related transactions
    income_count = tag.incomes.count()
    expense_count = tag.expenses.count()
    
    return render(request, 'budget/tag_confirm_delete.html', {
        'tag': tag,
        'income_count': income_count,
        'expense_count': expense_count,
        'total_count': income_count + expense_count
    })

