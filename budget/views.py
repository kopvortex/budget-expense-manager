from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Q
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from .models import BankAccount, Category, Income, Expense, MonthlyBudget, Transfer
from .forms import (
    UserRegisterForm, BankAccountForm, CategoryForm, IncomeForm,
    ExpenseForm, MonthlyBudgetForm, TransferForm
)


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
        form = BankAccountForm(request.POST, instance=account)
        if form.is_valid():
            form.save()
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
    
    total_income = incomes.aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
    categories = Category.objects.filter(user=request.user, category_type='income')
    accounts = BankAccount.objects.filter(user=request.user)
    
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
            messages.success(request, 'Income added successfully!')
            return redirect('income_list')
    else:
        form = IncomeForm(user=request.user)
    return render(request, 'budget/income_form.html', {'form': form, 'action': 'Add'})


@login_required
def income_update(request, pk):
    """Update an income"""
    income = get_object_or_404(Income, pk=pk, user=request.user)
    if request.method == 'POST':
        form = IncomeForm(request.POST, instance=income, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Income updated successfully!')
            return redirect('income_list')
    else:
        form = IncomeForm(instance=income, user=request.user)
    return render(request, 'budget/income_form.html', {'form': form, 'action': 'Update'})


@login_required
def income_delete(request, pk):
    """Delete an income"""
    income = get_object_or_404(Income, pk=pk, user=request.user)
    if request.method == 'POST':
        # Balance update now handled atomically in model's delete() method
        income.delete()
        messages.success(request, 'Income deleted successfully!')
        return redirect('income_list')
    return render(request, 'budget/income_confirm_delete.html', {'income': income})


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
    
    total_expense = expenses.aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
    categories = Category.objects.filter(user=request.user, category_type='expense')
    accounts = BankAccount.objects.filter(user=request.user)
    
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
            messages.success(request, 'Expense added successfully!')
            return redirect('expense_list')
    else:
        form = ExpenseForm(user=request.user)
    return render(request, 'budget/expense_form.html', {'form': form, 'action': 'Add'})


@login_required
def expense_update(request, pk):
    """Update an expense"""
    expense = get_object_or_404(Expense, pk=pk, user=request.user)
    if request.method == 'POST':
        form = ExpenseForm(request.POST, instance=expense, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Expense updated successfully!')
            return redirect('expense_list')
    else:
        form = ExpenseForm(instance=expense, user=request.user)
    return render(request, 'budget/expense_form.html', {'form': form, 'action': 'Update'})


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
    income_by_category = incomes.values('category__name').annotate(total=Sum('amount')).order_by('-total')
    total_income = incomes.aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
    
    # Expense summary
    expenses = Expense.objects.filter(user=request.user, date__year=year, date__month=month)
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
    }
    
    return render(request, 'budget/monthly_summary.html', context)


@login_required
def annual_summary(request):
    """Annual summary report"""
    year = request.GET.get('year', 2025)
    
    try:
        year = int(year)
    except:
        year = 2025
    
    # Annual totals
    total_income = Income.objects.filter(
        user=request.user, date__year=year
    ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
    
    total_expense = Expense.objects.filter(
        user=request.user, date__year=year
    ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
    
    annual_savings = total_income - total_expense
    
    # Monthly breakdown
    monthly_data = []
    for month in range(1, 13):
        month_income = Income.objects.filter(
            user=request.user, date__year=year, date__month=month
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        
        month_expense = Expense.objects.filter(
            user=request.user, date__year=year, date__month=month
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        
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
    
    # Category breakdown
    income_by_category = Income.objects.filter(
        user=request.user, date__year=year
    ).values('category__name').annotate(total=Sum('amount')).order_by('-total')
    
    expense_by_category = Expense.objects.filter(
        user=request.user, date__year=year
    ).values('category__name').annotate(total=Sum('amount')).order_by('-total')
    
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
    }
    
    return render(request, 'budget/annual_summary.html', context)

