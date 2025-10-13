from django.contrib import admin
from .models import BankAccount, Category, Income, Expense, MonthlyBudget, Transfer


@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ['name', 'account_type', 'balance', 'user', 'is_active', 'created_at']
    list_filter = ['account_type', 'is_active', 'created_at']
    search_fields = ['name', 'bank_name', 'account_number']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'category_type', 'user', 'created_at']
    list_filter = ['category_type', 'created_at']
    search_fields = ['name', 'description']


@admin.register(Income)
class IncomeAdmin(admin.ModelAdmin):
    list_display = ['description', 'amount', 'category', 'bank_account', 'date', 'user']
    list_filter = ['category', 'bank_account', 'date']
    search_fields = ['description']
    date_hierarchy = 'date'
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ['description', 'amount', 'category', 'bank_account', 'date', 'user']
    list_filter = ['category', 'bank_account', 'date']
    search_fields = ['description']
    date_hierarchy = 'date'
    readonly_fields = ['created_at', 'updated_at']


@admin.register(MonthlyBudget)
class MonthlyBudgetAdmin(admin.ModelAdmin):
    list_display = ['category', 'month', 'budgeted_amount', 'user']
    list_filter = ['month', 'category']
    date_hierarchy = 'month'
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Transfer)
class TransferAdmin(admin.ModelAdmin):
    list_display = ['from_account', 'to_account', 'amount', 'date', 'user']
    list_filter = ['date']
    search_fields = ['description']
    date_hierarchy = 'date'
    readonly_fields = ['created_at']

