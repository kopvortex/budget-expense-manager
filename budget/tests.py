from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from decimal import Decimal
from datetime import date
from .models import BankAccount, Category, Income, Expense


class BankAccountUpdateTestCase(TestCase):
    """Test cases for BankAccount update functionality"""
    
    def setUp(self):
        """Set up test data"""
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')
        
        # Create a bank account with opening balance
        # This will trigger the model's save() which creates the Opening Balance transaction
        self.account = BankAccount(
            user=self.user,
            name='Test Checking',
            account_type='checking',
            balance=Decimal('1000.00'),  # This becomes the opening balance
            bank_name='Test Bank',
            account_number='123456',
            account_setup_date=date(2025, 1, 1),
            is_active=True
        )
        self.account.save()  # This will create the Opening Balance income transaction
    
    def test_account_update_url_exists(self):
        """Test that the account update URL is accessible"""
        response = self.client.get(
            reverse('bank_account_update', kwargs={'pk': self.account.pk})
        )
        self.assertEqual(response.status_code, 200)
    
    def test_account_update_view_uses_correct_template(self):
        """Test that the correct template is used"""
        response = self.client.get(
            reverse('bank_account_update', kwargs={'pk': self.account.pk})
        )
        self.assertTemplateUsed(response, 'budget/bank_account_form.html')
    
    def test_account_update_name(self):
        """Test updating the account name"""
        response = self.client.post(
            reverse('bank_account_update', kwargs={'pk': self.account.pk}),
            {
                'name': 'Updated Checking Account',
                'account_type': 'checking',
                'opening_balance': '1000.00',
                'bank_name': 'Test Bank',
                'account_number': '123456',
                'is_active': True,
            }
        )
        
        # Check redirect
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('bank_account_list'))
        
        # Verify account was updated
        self.account.refresh_from_db()
        self.assertEqual(self.account.name, 'Updated Checking Account')
    
    def test_account_update_bank_details(self):
        """Test updating bank name and account number"""
        response = self.client.post(
            reverse('bank_account_update', kwargs={'pk': self.account.pk}),
            {
                'name': 'Test Checking',
                'account_type': 'checking',
                'opening_balance': '1000.00',
                'bank_name': 'New Bank Name',
                'account_number': '789012',
                'is_active': True,
            }
        )
        
        self.assertEqual(response.status_code, 302)
        
        # Verify changes
        self.account.refresh_from_db()
        self.assertEqual(self.account.bank_name, 'New Bank Name')
        self.assertEqual(self.account.account_number, '789012')
    
    def test_account_update_account_type(self):
        """Test changing account type"""
        response = self.client.post(
            reverse('bank_account_update', kwargs={'pk': self.account.pk}),
            {
                'name': 'Test Checking',
                'account_type': 'savings',  # Changed from checking
                'opening_balance': '1000.00',
                'bank_name': 'Test Bank',
                'account_number': '123456',
                'is_active': True,
            }
        )
        
        self.assertEqual(response.status_code, 302)
        
        # Verify type was changed
        self.account.refresh_from_db()
        self.assertEqual(self.account.account_type, 'savings')
    
    def test_account_update_active_status(self):
        """Test changing account active status"""
        response = self.client.post(
            reverse('bank_account_update', kwargs={'pk': self.account.pk}),
            {
                'name': 'Test Checking',
                'account_type': 'checking',
                'opening_balance': '1000.00',
                'bank_name': 'Test Bank',
                'account_number': '123456',
                'is_active': False,  # Deactivate account
            }
        )
        
        self.assertEqual(response.status_code, 302)
        
        # Verify status was changed
        self.account.refresh_from_db()
        self.assertFalse(self.account.is_active)
    
    def test_account_update_preserves_balance(self):
        """Test that updating account preserves the current balance"""
        # Add some transactions to change balance
        category = Category.objects.create(
            user=self.user,
            name='Salary',
            category_type='income'
        )
        Income.objects.create(
            user=self.user,
            category=category,
            bank_account=self.account,
            amount=Decimal('500.00'),
            description='Test income',
            date=date(2025, 10, 1)
        )
        
        self.account.refresh_from_db()
        balance_before_update = self.account.balance
        
        # Update account details
        response = self.client.post(
            reverse('bank_account_update', kwargs={'pk': self.account.pk}),
            {
                'name': 'Updated Name',
                'account_type': 'checking',
                'opening_balance': '1000.00',
                'bank_name': 'Test Bank',
                'account_number': '123456',
                'is_active': True,
            }
        )
        
        self.assertEqual(response.status_code, 302)
        
        # Verify balance is preserved
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, balance_before_update)
        self.assertEqual(self.account.balance, Decimal('1500.00'))
    
    def test_account_update_preserves_opening_balance(self):
        """Test that updating account preserves the opening balance"""
        opening_balance_before = self.account.opening_balance
        
        response = self.client.post(
            reverse('bank_account_update', kwargs={'pk': self.account.pk}),
            {
                'name': 'Updated Name',
                'account_type': 'checking',
                'opening_balance': '1000.00',  # Keep same
                'bank_name': 'Test Bank',
                'account_number': '123456',
                'is_active': True,
            }
        )
        
        self.assertEqual(response.status_code, 302)
        
        # Verify opening balance is unchanged
        self.account.refresh_from_db()
        self.assertEqual(self.account.opening_balance, opening_balance_before)
        self.assertEqual(self.account.opening_balance, Decimal('1000.00'))
    
    def test_account_update_preserves_setup_date(self):
        """Test that updating account preserves the account setup date"""
        setup_date_before = self.account.account_setup_date
        
        response = self.client.post(
            reverse('bank_account_update', kwargs={'pk': self.account.pk}),
            {
                'name': 'Updated Name',
                'account_type': 'checking',
                'opening_balance': '1000.00',
                'bank_name': 'Test Bank',
                'account_number': '123456',
                'is_active': True,
            }
        )
        
        self.assertEqual(response.status_code, 302)
        
        # Verify setup date is preserved
        self.account.refresh_from_db()
        self.assertEqual(self.account.account_setup_date, setup_date_before)
        self.assertEqual(self.account.account_setup_date, date(2025, 1, 1))
    
    def test_account_update_requires_login(self):
        """Test that updating accounts requires authentication"""
        self.client.logout()
        response = self.client.get(
            reverse('bank_account_update', kwargs={'pk': self.account.pk})
        )
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)
    
    def test_account_update_only_own_accounts(self):
        """Test that users can only update their own accounts"""
        # Create another user and account
        other_user = User.objects.create_user(
            username='otheruser',
            password='otherpass123'
        )
        other_account = BankAccount.objects.create(
            user=other_user,
            name='Other Account',
            account_type='checking',
            balance=Decimal('1000.00'),
            opening_balance=Decimal('1000.00'),
            account_setup_date=date(2025, 1, 1)
        )
        
        # Try to update other user's account
        response = self.client.get(
            reverse('bank_account_update', kwargs={'pk': other_account.pk})
        )
        
        # Should return 404
        self.assertEqual(response.status_code, 404)
    
    def test_account_update_with_transactions_maintains_balance(self):
        """Test that balance remains correct after multiple transactions and updates"""
        # Create categories
        income_cat = Category.objects.create(
            user=self.user,
            name='Salary',
            category_type='income'
        )
        expense_cat = Category.objects.create(
            user=self.user,
            name='Food',
            category_type='expense'
        )
        
        # Add income
        Income.objects.create(
            user=self.user,
            category=income_cat,
            bank_account=self.account,
            amount=Decimal('500.00'),
            description='Salary',
            date=date(2025, 10, 1)
        )
        
        # Add expense
        Expense.objects.create(
            user=self.user,
            category=expense_cat,
            bank_account=self.account,
            amount=Decimal('100.00'),
            description='Groceries',
            date=date(2025, 10, 2)
        )
        
        self.account.refresh_from_db()
        expected_balance = Decimal('1000.00') + Decimal('500.00') - Decimal('100.00')
        self.assertEqual(self.account.balance, expected_balance)
        
        # Update account
        response = self.client.post(
            reverse('bank_account_update', kwargs={'pk': self.account.pk}),
            {
                'name': 'Updated Checking',
                'account_type': 'checking',
                'bank_name': 'Updated Bank',
                'account_number': '999999',
                'is_active': True,
                'opening_balance': '1000.00',  # Keep same opening balance
            }
        )
        
        self.assertEqual(response.status_code, 302)
        
        # Verify balance is still correct
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, expected_balance)
        self.assertEqual(self.account.balance, Decimal('1400.00'))
    
    def test_account_update_opening_balance_updates_transaction(self):
        """Test that changing opening balance updates the corresponding income transaction"""
        # Find the opening balance income transaction
        opening_category = Category.objects.get(
            user=self.user,
            name='Opening Balance',
            category_type='income'
        )
        opening_income = Income.objects.get(
            user=self.user,
            bank_account=self.account,
            category=opening_category
        )
        
        # Verify initial state
        self.assertEqual(opening_income.amount, Decimal('1000.00'))
        self.assertEqual(self.account.opening_balance, Decimal('1000.00'))
        self.assertEqual(self.account.balance, Decimal('1000.00'))
        
        # Update opening balance
        response = self.client.post(
            reverse('bank_account_update', kwargs={'pk': self.account.pk}),
            {
                'name': 'Test Checking',
                'account_type': 'checking',
                'bank_name': 'Test Bank',
                'account_number': '123456',
                'is_active': True,
                'opening_balance': '1500.00',  # Change from 1000 to 1500
            }
        )
        
        self.assertEqual(response.status_code, 302)
        
        # Verify opening balance was updated
        self.account.refresh_from_db()
        self.assertEqual(self.account.opening_balance, Decimal('1500.00'))
        
        # Verify income transaction was updated
        opening_income.refresh_from_db()
        self.assertEqual(opening_income.amount, Decimal('1500.00'))
        
        # Verify current balance was recalculated
        self.assertEqual(self.account.balance, Decimal('1500.00'))
    
    def test_account_update_opening_balance_with_other_transactions(self):
        """Test opening balance update when account has other transactions"""
        # Add other transactions
        salary_cat = Category.objects.create(
            user=self.user,
            name='Salary',
            category_type='income'
        )
        Income.objects.create(
            user=self.user,
            category=salary_cat,
            bank_account=self.account,
            amount=Decimal('500.00'),
            description='Salary',
            date=date(2025, 10, 1)
        )
        
        self.account.refresh_from_db()
        # Balance should be 1000 (opening) + 500 (salary) = 1500
        self.assertEqual(self.account.balance, Decimal('1500.00'))
        
        # Change opening balance from 1000 to 2000
        response = self.client.post(
            reverse('bank_account_update', kwargs={'pk': self.account.pk}),
            {
                'name': 'Test Checking',
                'account_type': 'checking',
                'bank_name': 'Test Bank',
                'account_number': '123456',
                'is_active': True,
                'opening_balance': '2000.00',
            }
        )
        
        self.assertEqual(response.status_code, 302)
        
        # Verify balance is now 2000 (new opening) + 500 (salary) = 2500
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal('2500.00'))
        self.assertEqual(self.account.opening_balance, Decimal('2000.00'))


class BankAccountFormReadOnlyFieldsTestCase(TestCase):
    """Test cases for read-only fields in BankAccount form"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')
        
        self.account = BankAccount(
            user=self.user,
            name='Test Account',
            account_type='checking',
            balance=Decimal('1000.00'),  # This becomes the opening balance
            account_setup_date=date(2025, 1, 1),
            is_active=True
        )
        self.account.save()  # This will create the Opening Balance income transaction
    
    def test_form_shows_current_balance_as_readonly(self):
        """Test that the form displays current balance as read-only"""
        response = self.client.get(
            reverse('bank_account_update', kwargs={'pk': self.account.pk})
        )
        
        # Check that the response contains the account balance
        self.assertContains(response, '1000.00')
        # Check for read-only indicators
        self.assertContains(response, 'Current Balance')
        self.assertContains(response, 'read-only')
    
    def test_tampering_balance_does_not_change_it(self):
        """Test that attempting to change balance via form doesn't work"""
        # Try to post with a different balance
        response = self.client.post(
            reverse('bank_account_update', kwargs={'pk': self.account.pk}),
            {
                'name': 'Test Account',
                'account_type': 'checking',
                'opening_balance': '1000.00',
                'balance': '99999.99',  # Try to tamper with balance
                'bank_name': 'Test Bank',
                'account_number': '123456',
                'is_active': True,
            }
        )
        
        # Verify balance was NOT changed
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal('1000.00'))
        self.assertNotEqual(self.account.balance, Decimal('99999.99'))
    
    def test_opening_balance_can_be_changed(self):
        """Test that opening balance can now be changed and updates income transaction"""
        # Find the opening balance income transaction
        opening_category = Category.objects.get(
            user=self.user,
            name='Opening Balance',
            category_type='income'
        )
        opening_income = Income.objects.get(
            user=self.user,
            bank_account=self.account,
            category=opening_category
        )
        
        initial_amount = opening_income.amount
        self.assertEqual(initial_amount, Decimal('1000.00'))
        
        # Change opening balance
        response = self.client.post(
            reverse('bank_account_update', kwargs={'pk': self.account.pk}),
            {
                'name': 'Test Account',
                'account_type': 'checking',
                'opening_balance': '50000.00',  # Change to 50000
                'bank_name': 'Test Bank',
                'account_number': '123456',
                'is_active': True,
            }
        )
        
        # Verify opening balance WAS changed
        self.account.refresh_from_db()
        self.assertEqual(self.account.opening_balance, Decimal('50000.00'))
        
        # Verify income transaction was updated
        opening_income.refresh_from_db()
        self.assertEqual(opening_income.amount, Decimal('50000.00'))
        
        # Verify balance was recalculated
        self.assertEqual(self.account.balance, Decimal('50000.00'))
    
    def test_tampering_setup_date_does_not_change_it(self):
        """Test that attempting to change setup date doesn't work"""
        response = self.client.post(
            reverse('bank_account_update', kwargs={'pk': self.account.pk}),
            {
                'name': 'Test Account',
                'account_type': 'checking',
                'opening_balance': '1000.00',
                'account_setup_date': '2025-12-31',  # Try to tamper
                'bank_name': 'Test Bank',
                'account_number': '123456',
                'is_active': True,
            }
        )
        
        # Verify setup date was NOT changed
        self.account.refresh_from_db()
        self.assertEqual(self.account.account_setup_date, date(2025, 1, 1))
        self.assertNotEqual(self.account.account_setup_date, date(2025, 12, 31))

