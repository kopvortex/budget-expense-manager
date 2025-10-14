from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from datetime import datetime
from .models import BankAccount, Category, Income, Expense, MonthlyBudget, Transfer, Tag


class UserRegisterForm(UserCreationForm):
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']


class BankAccountForm(forms.ModelForm):
    # Add opening_balance field that will be shown when editing
    opening_balance = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control bg-light', 'readonly': True, 'step': '0.01'}),
        label='Opening Balance',
        help_text='The original balance when this account was set up (read-only)'
    )
    
    class Meta:
        model = BankAccount
        fields = ['name', 'account_type', 'opening_balance', 'balance', 'account_setup_date', 'bank_name', 'account_number', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'account_type': forms.Select(attrs={'class': 'form-control'}),
            'balance': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'account_setup_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'bank_name': forms.TextInput(attrs={'class': 'form-control'}),
            'account_number': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'balance': 'Opening Balance',
            'account_setup_date': 'Account Setup Date',
        }
        help_texts = {
            'balance': 'The opening balance when setting up this account',
            'account_setup_date': 'Date when you started tracking this account',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # If editing an existing account
        if self.instance and self.instance.pk:
            # Populate the opening_balance field with stored value
            self.fields['opening_balance'].initial = self.instance.opening_balance
            
            # Change balance field to show current balance (read-only)
            self.fields['balance'].widget.attrs['readonly'] = True
            self.fields['balance'].widget.attrs['class'] += ' bg-light'
            self.fields['balance'].widget.attrs['style'] = 'cursor: not-allowed; font-weight: 600; color: #0f5132;'
            self.fields['balance'].label = 'Current Balance'
            self.fields['balance'].help_text = '💰 Automatically calculated from transactions (read-only)'
            self.fields['balance'].disabled = True  # Prevent value from being submitted
            
            # Make opening balance editable with warning styling
            self.fields['opening_balance'].required = False
            self.fields['opening_balance'].widget.attrs['readonly'] = False
            self.fields['opening_balance'].widget.attrs['class'] = 'form-control bg-warning bg-opacity-10'
            self.fields['opening_balance'].widget.attrs['style'] = 'font-weight: 600; border: 2px solid #ffc107;'
            self.fields['opening_balance'].help_text = '⚠️ Changing this will update your initial balance transaction and recalculate your current balance'
            
            # Make setup date read-only
            self.fields['account_setup_date'].widget.attrs['readonly'] = True
            self.fields['account_setup_date'].widget.attrs['class'] += ' bg-light'
            self.fields['account_setup_date'].widget.attrs['style'] = 'cursor: not-allowed;'
            self.fields['account_setup_date'].help_text = '📅 Account setup date cannot be changed'
            self.fields['account_setup_date'].disabled = True  # Prevent value from being submitted
        else:
            # When creating a new account, hide the opening_balance field (it will be auto-populated)
            self.fields.pop('opening_balance')


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'category_type', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'category_type': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class IncomeForm(forms.ModelForm):
    tags_input = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter tags separated by commas (e.g., salary, bonus, freelance)'
        }),
        label='Tags',
        help_text='Optional: Add tags to categorize this income (comma-separated)'
    )
    
    class Meta:
        model = Income
        fields = ['category', 'bank_account', 'amount', 'description', 'date']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-control'}),
            'bank_account': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['category'].queryset = Category.objects.filter(user=user, category_type='income')
            self.fields['bank_account'].queryset = BankAccount.objects.filter(user=user, is_active=True)
        
        # Pre-populate tags if editing
        if self.instance and self.instance.pk:
            existing_tags = self.instance.tags.all()
            if existing_tags:
                self.fields['tags_input'].initial = ', '.join([tag.name for tag in existing_tags])
    
    def clean(self):
        cleaned_data = super().clean()
        bank_account = cleaned_data.get('bank_account')
        date = cleaned_data.get('date')
        
        if bank_account and date and bank_account.account_setup_date:
            if date < bank_account.account_setup_date:
                raise forms.ValidationError(
                    f'Transaction date cannot be before the account setup date ({bank_account.account_setup_date.strftime("%B %d, %Y")}). '
                    f'Please select a date on or after {bank_account.account_setup_date.strftime("%B %d, %Y")}.'
                )
        
        return cleaned_data


class ExpenseForm(forms.ModelForm):
    tags_input = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter tags separated by commas (e.g., groceries, utilities, entertainment)'
        }),
        label='Tags',
        help_text='Optional: Add tags to categorize this expense (comma-separated)'
    )
    
    class Meta:
        model = Expense
        fields = ['category', 'bank_account', 'amount', 'description', 'date']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-control'}),
            'bank_account': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['category'].queryset = Category.objects.filter(user=user, category_type='expense')
            self.fields['bank_account'].queryset = BankAccount.objects.filter(user=user, is_active=True)
        
        # Pre-populate tags if editing
        if self.instance and self.instance.pk:
            existing_tags = self.instance.tags.all()
            if existing_tags:
                self.fields['tags_input'].initial = ', '.join([tag.name for tag in existing_tags])
    
    def clean(self):
        cleaned_data = super().clean()
        bank_account = cleaned_data.get('bank_account')
        date = cleaned_data.get('date')
        
        if bank_account and date and bank_account.account_setup_date:
            if date < bank_account.account_setup_date:
                raise forms.ValidationError(
                    f'Transaction date cannot be before the account setup date ({bank_account.account_setup_date.strftime("%B %d, %Y")}). '
                    f'Please select a date on or after {bank_account.account_setup_date.strftime("%B %d, %Y")}.'
                )
        
        return cleaned_data


class MonthlyBudgetForm(forms.ModelForm):
    # Override month field to accept YYYY-MM format
    month = forms.CharField(
        widget=forms.DateInput(attrs={
            'class': 'form-control', 
            'type': 'month',
            'min': '2020-01',
            'max': '2025-12'
        }),
        help_text='Select the month for this budget (2020-2025)'
    )
    
    class Meta:
        model = MonthlyBudget
        fields = ['category', 'month', 'budgeted_amount']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-control'}),
            'budgeted_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['category'].queryset = Category.objects.filter(user=user, category_type='expense')
        
        # Format the month field for display in YYYY-MM format when editing
        if self.instance and self.instance.pk and self.instance.month:
            self.fields['month'].initial = self.instance.month.strftime('%Y-%m')
    
    def clean_month(self):
        """Convert YYYY-MM format to date object (first day of month)"""
        month_str = self.cleaned_data.get('month')
        if month_str:
            try:
                # Parse YYYY-MM and convert to first day of month
                date_obj = datetime.strptime(month_str, '%Y-%m')
                return date_obj.date()
            except ValueError:
                raise forms.ValidationError('Enter a valid date in YYYY-MM format.')
        raise forms.ValidationError('This field is required.')


class TransferForm(forms.ModelForm):
    class Meta:
        model = Transfer
        fields = ['from_account', 'to_account', 'amount', 'description', 'date']
        widgets = {
            'from_account': forms.Select(attrs={'class': 'form-control'}),
            'to_account': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['from_account'].queryset = BankAccount.objects.filter(user=user, is_active=True)
            self.fields['to_account'].queryset = BankAccount.objects.filter(user=user, is_active=True)
    
    def clean(self):
        cleaned_data = super().clean()
        from_account = cleaned_data.get('from_account')
        to_account = cleaned_data.get('to_account')
        date = cleaned_data.get('date')
        amount = cleaned_data.get('amount')
        
        # Check account setup dates
        if from_account and date and from_account.account_setup_date:
            if date < from_account.account_setup_date:
                raise forms.ValidationError(
                    f'Transfer date cannot be before the "from account" setup date ({from_account.account_setup_date.strftime("%B %d, %Y")}). '
                    f'Please select a date on or after {from_account.account_setup_date.strftime("%B %d, %Y")}.'
                )
        
        if to_account and date and to_account.account_setup_date:
            if date < to_account.account_setup_date:
                raise forms.ValidationError(
                    f'Transfer date cannot be before the "to account" setup date ({to_account.account_setup_date.strftime("%B %d, %Y")}). '
                    f'Please select a date on or after {to_account.account_setup_date.strftime("%B %d, %Y")}.'
                )
        
        # Check same account
        if from_account and to_account and from_account == to_account:
            raise forms.ValidationError("Cannot transfer to the same account.")
        
        # Check balance (for new transfers or when account changes)
        if from_account and amount:
            # Refresh balance from database to get current state
            from_account.refresh_from_db()
            available_balance = from_account.balance
            
            # If editing an existing transfer and the from_account hasn't changed,
            # add back the old transfer amount to available balance
            if self.instance and self.instance.pk:
                if self.instance.from_account == from_account:
                    available_balance += self.instance.amount
            
            if available_balance < amount:
                raise forms.ValidationError(
                    f"Insufficient balance in {from_account.name}. "
                    f"Available: ${available_balance:.2f}"
                )
        
        return cleaned_data


class TagForm(forms.ModelForm):
    class Meta:
        model = Tag
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter tag name (e.g., Salary, Rent, Groceries)'
            }),
        }
        help_texts = {
            'name': 'Tag names will be automatically converted to camelCase (e.g., "monthly bills" → "MonthlyBills"). A color will be automatically assigned.'
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
    
    def clean_name(self):
        name = self.cleaned_data.get('name')
        if name:
            # Normalize to camelCase
            normalized_name = Tag.normalize_tag_name(name)
            if not normalized_name:
                raise forms.ValidationError('Tag name cannot be empty')
            
            # Get the user from instance or from the form initialization
            user = self.instance.user if self.instance.pk else self.user
            
            # Check if tag already exists for this user (case-insensitive)
            if user:
                query = Tag.objects.filter(user=user, name__iexact=normalized_name)
                if self.instance.pk:
                    # Editing existing tag - exclude current instance
                    query = query.exclude(pk=self.instance.pk)
                
                if query.exists():
                    raise forms.ValidationError(f'Tag "{normalized_name}" already exists')
            
            return normalized_name
        return name
