from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Authentication
    path('', views.dashboard, name='dashboard'),
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='budget/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    # Bank Accounts
    path('accounts/', views.bank_account_list, name='bank_account_list'),
    path('accounts/create/', views.bank_account_create, name='bank_account_create'),
    path('accounts/<int:pk>/update/', views.bank_account_update, name='bank_account_update'),
    path('accounts/<int:pk>/delete/', views.bank_account_delete, name='bank_account_delete'),
    
    # Categories
    path('categories/', views.category_list, name='category_list'),
    path('categories/create/', views.category_create, name='category_create'),
    path('categories/<int:pk>/update/', views.category_update, name='category_update'),
    path('categories/<int:pk>/delete/', views.category_delete, name='category_delete'),
    
    # Tags
    path('tags/', views.tag_list, name='tag_list'),
    path('tags/create/', views.tag_create, name='tag_create'),
    path('tags/<int:pk>/update/', views.tag_update, name='tag_update'),
    path('tags/<int:pk>/delete/', views.tag_delete, name='tag_delete'),
    
    # Income
    path('income/', views.income_list, name='income_list'),
    path('income/create/', views.income_create, name='income_create'),
    path('income/<int:pk>/update/', views.income_update, name='income_update'),
    path('income/<int:pk>/delete/', views.income_delete, name='income_delete'),
    path('income/bulk-tag/', views.income_bulk_tag, name='income_bulk_tag'),
    path('income/bulk-delete/', views.income_bulk_delete, name='income_bulk_delete'),
    
    # Expenses
    path('expenses/', views.expense_list, name='expense_list'),
    path('expenses/create/', views.expense_create, name='expense_create'),
    path('expenses/<int:pk>/update/', views.expense_update, name='expense_update'),
    path('expenses/<int:pk>/delete/', views.expense_delete, name='expense_delete'),
    path('expenses/bulk-tag/', views.expense_bulk_tag, name='expense_bulk_tag'),
    path('expenses/bulk-delete/', views.expense_bulk_delete, name='expense_bulk_delete'),
    
    # Budgets
    path('budgets/', views.budget_list, name='budget_list'),
    path('budgets/create/', views.budget_create, name='budget_create'),
    path('budgets/<int:pk>/update/', views.budget_update, name='budget_update'),
    path('budgets/<int:pk>/delete/', views.budget_delete, name='budget_delete'),
    path('budgets/copy-previous/', views.budget_copy_previous, name='budget_copy_previous'),
    
    # Transfers
    path('transfers/', views.transfer_list, name='transfer_list'),
    path('transfers/create/', views.transfer_create, name='transfer_create'),
    path('transfers/<int:pk>/update/', views.transfer_update, name='transfer_update'),
    path('transfers/<int:pk>/delete/', views.transfer_delete, name='transfer_delete'),
    
    # Reports
    path('reports/monthly/', views.monthly_summary, name='monthly_summary'),
    path('reports/annual/', views.annual_summary, name='annual_summary'),
]

