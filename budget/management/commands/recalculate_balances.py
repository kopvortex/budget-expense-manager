from django.core.management.base import BaseCommand
from django.db import models
from budget.models import BankAccount, Income, Expense, Transfer
from decimal import Decimal


class Command(BaseCommand):
    help = 'Recalculates all account balances from their transactions'

    def handle(self, *args, **kwargs):
        self.stdout.write('Recalculating account balances from transactions...\n')
        
        accounts = BankAccount.objects.filter(is_active=True)
        fixed_count = 0
        
        for account in accounts:
            # Calculate balance from all transactions
            income_total = Income.objects.filter(bank_account=account).aggregate(
                total=models.Sum('amount')
            )['total'] or Decimal('0')
            
            expense_total = Expense.objects.filter(bank_account=account).aggregate(
                total=models.Sum('amount')
            )['total'] or Decimal('0')
            
            transfers_in = Transfer.objects.filter(to_account=account).aggregate(
                total=models.Sum('amount')
            )['total'] or Decimal('0')
            
            transfers_out = Transfer.objects.filter(from_account=account).aggregate(
                total=models.Sum('amount')
            )['total'] or Decimal('0')
            
            calculated_balance = income_total - expense_total + transfers_in - transfers_out
            
            # Check if balance needs updating
            if account.balance != calculated_balance:
                old_balance = account.balance
                account.balance = calculated_balance
                account.save(update_fields=['balance'])
                
                self.stdout.write(
                    f'{account.name}: ${old_balance:,.2f} → ${calculated_balance:,.2f}'
                )
                fixed_count += 1
        
        if fixed_count == 0:
            self.stdout.write(self.style.SUCCESS('\n✓ All account balances are correct.'))
        else:
            self.stdout.write(
                self.style.SUCCESS(f'\n✓ Updated {fixed_count} account balance(s).')
            )

