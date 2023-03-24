from django.urls import path
from . import views

from django.views.decorators.csrf import csrf_exempt

urlpatterns = [
    path('', views.index, name="income"),
    path('add-income', views.add_income, name="add-income"),
    path('edit-income/<int:id>', views.income_edit, name="income-edit"),
    path('income-delete/<int:id>', views.delete_income, name="income-delete"),
    path('search-income', csrf_exempt(views.search_income),
         name="search_income"),
    path('export_csv', views.export_csv , name='export-csv'),
    path('export_excel', views.export_excel, name="export-excel"),
    path('expense_source_summary', views.expense_source_summary, name='expense_source_summary'),
    path('hexstats', views.hexstats_view, name='hexstats'),
]