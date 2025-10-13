from django.db import models, transaction
from django.db.models import F
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal


class BankAccount(models.Model):
    """Model for managing bank accounts"""
    ACCOUNT_TYPES = [
        ('savings', 'Savings Account'),
        ('checking', 'Checking Account'),
        ('credit', 'Credit Card'),
        ('cash', 'Cash'),
        ('investment', 'Investment Account'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bank_accounts')
    name = models.CharField(max_length=100)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    opening_balance = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0,
        help_text="The initial balance when the account was set up"
    )
    account_setup_date = models.DateField(
        help_text="Date when this account was created with its initial balance",
        null=True,
        blank=True
    )
    bank_name = models.CharField(max_length=100, blank=True)
    account_number = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.name} - ${self.balance}"
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        initial_balance = self.balance if is_new else None
        
        # Store opening balance for new accounts
        if is_new and initial_balance:
            self.opening_balance = initial_balance
        
        # Save the account first
        super().save(*args, **kwargs)
        
        # If this is a new account with a non-zero initial balance, create an income transaction
        # (Income can be positive for assets or negative for debts/liabilities)
        if is_new and initial_balance and initial_balance != 0 and self.account_setup_date:
            from decimal import Decimal
            
            # Get or create "Opening Balance" income category
            initial_category, created = Category.objects.get_or_create(
                user=self.user,
                name='Opening Balance',
                defaults={'category_type': 'income'}
            )
            
            # Ensure the category is set to income type
            if initial_category.category_type != 'income':
                initial_category.category_type = 'income'
                initial_category.save()
            
            # Set balance to 0 temporarily, then create income which will add it back
            self.balance = Decimal('0')
            BankAccount.objects.filter(pk=self.pk).update(balance=Decimal('0'))
            
            # Create income transaction (positive for assets, negative for debts)
            Income.objects.create(
                user=self.user,
                category=initial_category,
                bank_account=self,
                amount=initial_balance,  # Can be positive or negative
                description=f'Opening balance for {self.name}',
                date=self.account_setup_date
            )


class Category(models.Model):
    """Model for income and expense categories"""
    CATEGORY_TYPES = [
        ('income', 'Income'),
        ('expense', 'Expense'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=100)
    category_type = models.CharField(max_length=10, choices=CATEGORY_TYPES)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Categories'
        
    def __str__(self):
        return f"{self.name} ({self.category_type})"


class Income(models.Model):
    """Model for tracking income"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='incomes')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='incomes')
    bank_account = models.ForeignKey(BankAccount, on_delete=models.SET_NULL, null=True, related_name='incomes')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField()
    date = models.DateField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date', '-created_at']
        
    def __str__(self):
        return f"{self.description} - ${self.amount}"
    
    @transaction.atomic
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        old_amount = None
        old_account = None
        
        if not is_new:
            # Lock the row for update to prevent race conditions
            old_income = Income.objects.select_for_update().get(pk=self.pk)
            old_amount = old_income.amount
            old_account = old_income.bank_account
        
        super().save(*args, **kwargs)
        
        # Update bank account balance using F() expressions for atomicity
        if self.bank_account:
            if is_new:
                # New income - add to balance
                BankAccount.objects.filter(pk=self.bank_account.pk).update(
                    balance=F('balance') + self.amount
                )
                # Refresh the instance to get updated balance
                self.bank_account.refresh_from_db()
            else:
                # Existing income - handle updates
                if old_account and old_account != self.bank_account:
                    # Account changed - reverse from old, add to new
                    BankAccount.objects.filter(pk=old_account.pk).update(
                        balance=F('balance') - old_amount
                    )
                    BankAccount.objects.filter(pk=self.bank_account.pk).update(
                        balance=F('balance') + self.amount
                    )
                    # Refresh both accounts
                    old_account.refresh_from_db()
                    self.bank_account.refresh_from_db()
                elif old_amount != self.amount:
                    # Amount changed - adjust balance
                    amount_diff = self.amount - old_amount
                    BankAccount.objects.filter(pk=self.bank_account.pk).update(
                        balance=F('balance') + amount_diff
                    )
                    # Refresh the instance
                    self.bank_account.refresh_from_db()
    
    @transaction.atomic
    def delete(self, *args, **kwargs):
        # Reverse balance change before deleting (only if account still exists)
        if self.bank_account:
            try:
                BankAccount.objects.filter(pk=self.bank_account.pk).update(
                    balance=F('balance') - self.amount
                )
            except BankAccount.DoesNotExist:
                pass  # Account already deleted, can't reverse
        super().delete(*args, **kwargs)


class Expense(models.Model):
    """Model for tracking expenses"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='expenses')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='expenses')
    bank_account = models.ForeignKey(BankAccount, on_delete=models.SET_NULL, null=True, related_name='expenses')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField()
    date = models.DateField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date', '-created_at']
        
    def __str__(self):
        return f"{self.description} - ${self.amount}"
    
    @transaction.atomic
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        old_amount = None
        old_account = None
        
        if not is_new:
            # Lock the row for update to prevent race conditions
            old_expense = Expense.objects.select_for_update().get(pk=self.pk)
            old_amount = old_expense.amount
            old_account = old_expense.bank_account
        
        super().save(*args, **kwargs)
        
        # Update bank account balance using F() expressions for atomicity
        if self.bank_account:
            if is_new:
                # New expense - subtract from balance
                BankAccount.objects.filter(pk=self.bank_account.pk).update(
                    balance=F('balance') - self.amount
                )
                # Refresh the instance to get updated balance
                self.bank_account.refresh_from_db()
            else:
                # Existing expense - handle updates
                if old_account and old_account != self.bank_account:
                    # Account changed - reverse from old, subtract from new
                    BankAccount.objects.filter(pk=old_account.pk).update(
                        balance=F('balance') + old_amount
                    )
                    BankAccount.objects.filter(pk=self.bank_account.pk).update(
                        balance=F('balance') - self.amount
                    )
                    # Refresh both accounts
                    old_account.refresh_from_db()
                    self.bank_account.refresh_from_db()
                elif old_amount != self.amount:
                    # Amount changed - adjust balance
                    amount_diff = self.amount - old_amount
                    BankAccount.objects.filter(pk=self.bank_account.pk).update(
                        balance=F('balance') - amount_diff
                    )
                    # Refresh the instance
                    self.bank_account.refresh_from_db()
    
    @transaction.atomic
    def delete(self, *args, **kwargs):
        # Reverse balance change before deleting (only if account still exists)
        if self.bank_account:
            try:
                BankAccount.objects.filter(pk=self.bank_account.pk).update(
                    balance=F('balance') + self.amount
                )
            except BankAccount.DoesNotExist:
                pass  # Account already deleted, can't reverse
        super().delete(*args, **kwargs)


class MonthlyBudget(models.Model):
    """Model for setting monthly budgets"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='monthly_budgets')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='monthly_budgets')
    month = models.DateField()
    budgeted_amount = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-month']
        unique_together = ['user', 'category', 'month']
        
    def __str__(self):
        return f"{self.category.name} - {self.month.strftime('%B %Y')} - ${self.budgeted_amount}"
    
    def get_spent_amount(self):
        """Calculate total spent for this category in this month"""
        if self.category.category_type == 'expense':
            total = Expense.objects.filter(
                user=self.user,
                category=self.category,
                date__year=self.month.year,
                date__month=self.month.month
            ).aggregate(models.Sum('amount'))['amount__sum'] or Decimal('0')
            return total
        return Decimal('0')
    
    def get_remaining_amount(self):
        """Calculate remaining budget"""
        return self.budgeted_amount - self.get_spent_amount()
    
    def get_percentage_used(self):
        """Calculate percentage of budget used"""
        if self.budgeted_amount > 0:
            return (self.get_spent_amount() / self.budgeted_amount) * 100
        return 0


class Transfer(models.Model):
    """Model for tracking transfers between accounts"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transfers')
    from_account = models.ForeignKey(BankAccount, on_delete=models.CASCADE, related_name='transfers_out')
    to_account = models.ForeignKey(BankAccount, on_delete=models.CASCADE, related_name='transfers_in')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField(blank=True)
    date = models.DateField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-date', '-created_at']
        
    def __str__(self):
        return f"Transfer ${self.amount} from {self.from_account.name} to {self.to_account.name}"
    
    @transaction.atomic
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        old_amount = None
        old_from_account = None
        old_to_account = None
        
        if not is_new:
            # Lock the row for update to prevent race conditions
            old_transfer = Transfer.objects.select_for_update().get(pk=self.pk)
            old_amount = old_transfer.amount
            old_from_account = old_transfer.from_account
            old_to_account = old_transfer.to_account
        
        super().save(*args, **kwargs)
        
        if is_new:
            # New transfer - deduct from source, add to destination
            BankAccount.objects.filter(pk=self.from_account.pk).update(
                balance=F('balance') - self.amount
            )
            BankAccount.objects.filter(pk=self.to_account.pk).update(
                balance=F('balance') + self.amount
            )
            # Refresh both accounts to get updated balances
            self.from_account.refresh_from_db()
            self.to_account.refresh_from_db()
        else:
            # Existing transfer - handle updates
            accounts_changed = (old_from_account != self.from_account or 
                              old_to_account != self.to_account)
            amount_changed = old_amount != self.amount
            
            if accounts_changed:
                # Accounts changed - reverse old transfer, apply new one
                # Reverse old transfer
                BankAccount.objects.filter(pk=old_from_account.pk).update(
                    balance=F('balance') + old_amount
                )
                BankAccount.objects.filter(pk=old_to_account.pk).update(
                    balance=F('balance') - old_amount
                )
                # Apply new transfer
                BankAccount.objects.filter(pk=self.from_account.pk).update(
                    balance=F('balance') - self.amount
                )
                BankAccount.objects.filter(pk=self.to_account.pk).update(
                    balance=F('balance') + self.amount
                )
                # Refresh all accounts
                old_from_account.refresh_from_db()
                old_to_account.refresh_from_db()
                self.from_account.refresh_from_db()
                self.to_account.refresh_from_db()
            elif amount_changed:
                # Amount changed - adjust both accounts
                amount_diff = self.amount - old_amount
                BankAccount.objects.filter(pk=self.from_account.pk).update(
                    balance=F('balance') - amount_diff
                )
                BankAccount.objects.filter(pk=self.to_account.pk).update(
                    balance=F('balance') + amount_diff
                )
                # Refresh accounts
                self.from_account.refresh_from_db()
                self.to_account.refresh_from_db()
    
    @transaction.atomic
    def delete(self, *args, **kwargs):
        # Reverse transfer before deleting (only if accounts still exist)
        try:
            if self.from_account:
                BankAccount.objects.filter(pk=self.from_account.pk).update(
                    balance=F('balance') + self.amount
                )
        except BankAccount.DoesNotExist:
            pass  # Account already deleted, can't reverse
        
        try:
            if self.to_account:
                BankAccount.objects.filter(pk=self.to_account.pk).update(
                    balance=F('balance') - self.amount
                )
        except BankAccount.DoesNotExist:
            pass  # Account already deleted, can't reverse
        
        super().delete(*args, **kwargs)

