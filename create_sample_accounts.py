#!/usr/bin/env python
"""Script to create sample bank accounts of each type"""

import os
import sys
import django
from decimal import Decimal
from datetime import date

# Setup Django
sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'budget_project.settings')
django.setup()

from django.contrib.auth.models import User
from budget.models import BankAccount

def create_sample_accounts():
    # Get or create a test user
    user, created = User.objects.get_or_create(
        username='testuser',
        defaults={
            'email': 'test@example.com',
            'is_staff': False,
            'is_superuser': False
        }
    )
    
    if created:
        user.set_password('testpass123')
        user.save()
        print(f"Created test user: testuser (password: testpass123)")
    else:
        print(f"Using existing user: {user.username}")
    
    # Check if accounts already exist
    existing_count = BankAccount.objects.filter(user=user).count()
    if existing_count > 0:
        print(f"User already has {existing_count} accounts. Skipping account creation.")
        print("\nYou can access the app at: http://localhost:8000")
        print("Login with username: testuser, password: testpass123")
        return
    
    # Sample accounts data
    sample_accounts = [
        {
            'name': 'Chase Checking',
            'account_type': 'checking',
            'bank_name': 'Chase Bank',
            'account_number': '****1234',
            'balance': Decimal('5420.50'),
            'opening_balance': Decimal('5000.00'),
            'account_setup_date': date(2024, 1, 1)
        },
        {
            'name': 'Wells Fargo Checking',
            'account_type': 'checking',
            'bank_name': 'Wells Fargo',
            'account_number': '****5678',
            'balance': Decimal('2180.75'),
            'opening_balance': Decimal('2000.00'),
            'account_setup_date': date(2024, 1, 1)
        },
        {
            'name': 'Chase Freedom Credit Card',
            'account_type': 'credit',
            'bank_name': 'Chase',
            'account_number': '****9012',
            'balance': Decimal('-1250.00'),
            'opening_balance': Decimal('0.00'),
            'account_setup_date': date(2024, 1, 1)
        },
        {
            'name': 'AmEx Platinum',
            'account_type': 'credit',
            'bank_name': 'American Express',
            'account_number': '****3456',
            'balance': Decimal('-890.25'),
            'opening_balance': Decimal('0.00'),
            'account_setup_date': date(2024, 1, 1)
        },
        {
            'name': 'Vanguard 401k',
            'account_type': 'investment',
            'bank_name': 'Vanguard',
            'account_number': '****7890',
            'balance': Decimal('45600.00'),
            'opening_balance': Decimal('40000.00'),
            'account_setup_date': date(2024, 1, 1)
        },
        {
            'name': 'Fidelity Brokerage',
            'account_type': 'investment',
            'bank_name': 'Fidelity',
            'account_number': '****2345',
            'balance': Decimal('12340.50'),
            'opening_balance': Decimal('10000.00'),
            'account_setup_date': date(2024, 1, 1)
        },
        {
            'name': 'Ally Savings Account',
            'account_type': 'savings',
            'bank_name': 'Ally Bank',
            'account_number': '****6789',
            'balance': Decimal('15230.80'),
            'opening_balance': Decimal('15000.00'),
            'account_setup_date': date(2024, 1, 1)
        },
        {
            'name': 'Marcus High Yield Savings',
            'account_type': 'savings',
            'bank_name': 'Marcus by Goldman Sachs',
            'account_number': '****0123',
            'balance': Decimal('8540.25'),
            'opening_balance': Decimal('8000.00'),
            'account_setup_date': date(2024, 1, 1)
        },
        {
            'name': 'Cash Wallet',
            'account_type': 'cash',
            'bank_name': '',
            'account_number': '',
            'balance': Decimal('340.00'),
            'opening_balance': Decimal('300.00'),
            'account_setup_date': date(2024, 1, 1)
        }
    ]
    
    # Create accounts
    created_accounts = []
    for account_data in sample_accounts:
        account = BankAccount.objects.create(
            user=user,
            name=account_data['name'],
            account_type=account_data['account_type'],
            bank_name=account_data['bank_name'],
            account_number=account_data['account_number'],
            balance=account_data['balance'],
            opening_balance=account_data['opening_balance'],
            account_setup_date=account_data['account_setup_date'],
            is_active=True
        )
        created_accounts.append(account)
        print(f"✓ Created {account.get_account_type_display()}: {account.name} - Balance: ${account.balance}")
    
    print(f"\n✅ Successfully created {len(created_accounts)} sample accounts!")
    print("\nAccount type breakdown:")
    print(f"  • Checking: 2 accounts")
    print(f"  • Credit Cards: 2 accounts")
    print(f"  • Investment: 2 accounts")
    print(f"  • Savings: 2 accounts")
    print(f"  • Cash: 1 account")
    
    print("\n" + "="*60)
    print("Access the application at: http://localhost:8000")
    print("Login credentials:")
    print("  Username: testuser")
    print("  Password: testpass123")
    print("="*60)

if __name__ == '__main__':
    create_sample_accounts()

