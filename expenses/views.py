from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Category, Expense
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.paginator import Paginator
import json
from django.http import JsonResponse, HttpResponse
from userpreferences.models import UserPreference
import datetime
import csv
import xlwt
from django.template.loader import render_to_string


def search_expenses(request):
    """
    This is a function that handles a POST request to search
    for expenses based on user input.
    The function expects a JSON object containing a "searchText"
    key with the search string as its value.
    The function queries the Expense model to find all expenses that match
    the search criteria, including expenses with the search string as a prefix
    for the amount or date fields, or as a substring in the description or
    category fields. The expenses are filtered based on the current user.
    The function returns a JSON response containing the matched expenses data.
    If no expenses match the search criteria, an empty list is returned.
    The function assumes that the Expense model has fields named amount, date,
    description, category, and owner.
    """
    if request.method == 'POST':
        search_str = json.loads(request.body).get('searchText')
        cond1 = Expense.objects.filter(
            amount__istartswith=search_str, owner=request.user)
        cond2 = Expense.objects.filter(
            date__istartswith=search_str, owner=request.user)
        cond3 = Expense.objects.filter(
            description__icontains=search_str, owner=request.user)
        cond4 = Expense.objects.filter(
            category__icontains=search_str, owner=request.user)
        expenses = cond1 | cond2 | cond3 | cond4

        data = expenses.values()
        return JsonResponse(list(data), safe=False)


@login_required(login_url='/authentication/login')
def index(request):
    """
    This is a function that renders the
    index page for the expenses app.
    The function requires the user to be logged in and redirects to the login
    page if the user is not authenticated.
    The function queries the Category and Expense models to retrieve all
    categories and expenses associated with
    the current user. The expenses are paginated to display only
    five items per page. The function checks the user's currency preference
    (if available) and uses it to format the expense amounts in the appropriate
    currency. If no currency preference is available,
    the default currency is set to Indian Rupee (INR). The function passes
    the categories, expenses, paginated
    page object, and currency to the index template for rendering.
    """
    categories = Category.objects.all()
    expenses = Expense.objects.filter(owner=request.user)
    paginator = Paginator(expenses, 5)
    page_number = request.GET.get('page')
    page_obj = Paginator.get_page(paginator, page_number)

    if UserPreference.objects.filter(user=request.user).exists():
        currency = UserPreference.objects.get(user=request.user).currency
    else:
        currency = 'INR - Indian Rupee'

    context = {
        'expenses': expenses,
        'page_obj': page_obj,
        'currency': currency
    }
    return render(request, 'expenses/index.html', context)


@login_required(login_url='/authentication/login')
def add_expense(request):
    """
    This is a view function that allows logged-in users to add expenses.
    It takes in a request object and checks if the request method is GET
    or POST.
    If it is GET, it renders a template with a form to add an expense.
    If it is POST, it validates the form data, creates a new expense object
    and saves it to the database, then redirects to the expenses page.
    If there are any validation errors, it renders the same template with
    the form data and error messages. It also uses messages to show success
    or error messages after the form is submitted.
    """
    categories = Category.objects.all()
    context = {
        'categories': categories,
        'values': request.POST
    }
    if request.method == 'GET':
        return render(request, 'expenses/add_expense.html', context)

    if request.method == 'POST':
        amount = request.POST['amount']

        if not amount:
            messages.error(request, 'Amount is required')
            return render(request, 'expenses/add_expense.html', context)
        description = request.POST['description']
        date = request.POST['expense_date']
        category = request.POST['category']
        
        if not isinstance(amount, (int, float)):
            messages.error(request, 'Amount is not number')
            return render(request, 'expenses/add_expense.html', context)
            
        if not description:
            messages.error(request, 'description is required')
            return render(request, 'expenses/add_expense.html', context)

        Expense.objects.create(owner=request.user, amount=amount, date=date,
                               category=category, description=description)
        messages.success(request, 'Expense saved successfully')

        return redirect('expenses')


@login_required(login_url='/authentication/login')
def expense_edit(request, id):
    """
    Retrieve all categories from the database.
    Create a dictionary containing the categories and the form values.
    If the request method is GET, render the add_expense.html
    template with the context.
    If the request method is POST:
    Get the amount, description, date, and category from the POST data.
    Validate the amount and description.
    Create a new Expense object with the owner, amount, date,
    category and description.
    Save the Expense object to the database.
    Display a success message.
    """
    expense = Expense.objects.get(pk=id)
    categories = Category.objects.all()
    context = {
        'expense': expense,
        'values': expense,
        'categories': categories
    }
    if request.method == 'GET':
        return render(request, 'expenses/edit-expense.html', context)
    if request.method == 'POST':
        amount = request.POST['amount']

        if not amount:
            messages.error(request, 'Amount is required')
            return render(request, 'expenses/edit-expense.html', context)
        description = request.POST['description']
        date = request.POST['expense_date']
        category = request.POST['category']

        if not description:
            messages.error(request, 'description is required')
            return render(request, 'expenses/edit-expense.html', context)

        expense.owner = request.user
        expense.amount = amount
        expense. date = date
        expense.category = category
        expense.description = description

        expense.save()
        messages.success(request, 'Expense updated  successfully')

        return redirect('expenses')


#  Allows you do delete expense
def delete_expense(request, id):
    if not request.user.is_authenticated:
        return redirect('login')

    expense = Expense.objects.get(pk=id)
    expense.delete()
    messages.success(request, 'Expense removed')
    return redirect('expenses')


def expense_category_summary(request):
    """
    This function generates a summary report of expenses grouped by category
    It filters the expenses of the user for the last 6 months
    It creates a dictionary to store the total expenses for each category
    It iterates over each expense and each category to calculate
    the total amount spent on that category
    Finally, it returns a JsonResponse containing the
    dictionary of expenses grouped by category.
    """
    todays_date = datetime.date.today()
    six_months_ago = todays_date-datetime.timedelta(days=30*6)
    expenses = Expense.objects.filter(owner=request.user,
                                      date__gte=six_months_ago,
                                      date__lte=todays_date)
    finalrep = {}

    def get_category(expense):
        return expense.category
    category_list = list(set(map(get_category, expenses)))

    def get_expense_category_amount(category):
        amount = 0
        filtered_by_category = expenses.filter(category=category)

        for item in filtered_by_category:
            amount += item.amount

        return amount

    for x in expenses:
        for y in category_list:
            finalrep[y] = get_expense_category_amount(y)

    return JsonResponse({'expense_category_data': finalrep}, safe=False)


def exstats_view(request):
    return render(request, 'expenses/exstats.html')


def export_csv(request):
    """
    This function generates a CSV file containing
    the expenses of the current user and downloads it.
    """
    response = HttpResponse(content_type='text/csv')

    response['Content-Disposition'] = 'attachment; filename="Expenses{}.csv"'.\
        format(str(datetime.datetime.now()))
    writer = csv.writer(response)
    writer.writerow(['Amount', 'Description', 'Category', 'Date'])

    expenses = Expense.objects.filter(owner=request.user)

    for expense in expenses:
        writer.writerow([expense.amount, expense.description,
                         expense.category, expense.date])

    return response


def export_excel(request):
    """
    This is a function exports the user's expenses data to an excel file.
    It takes a request object as a parameter and returns an HTTP response
    containing the generated excel file.
    """
    response = HttpResponse(content_type='application/ms_excel')
    response['Content-Disposition'] = 'attachment; filename="Expenses{}.xls"'.\
                                      format(str(datetime.datetime.now()))
    wb = xlwt.Workbook(encoding='utf-8')
    ws = wb.add_sheet('Expenses')
    row_num = 0
    font_style = xlwt.XFStyle()
    font_style.font.bold = True

    columns = ['Amount', 'Description', 'Category', 'Date']

    for col_num in range(len(columns)):
        ws.write(row_num, col_num, columns[col_num], font_style)

    font_style = xlwt.XFStyle()

    rows = Expense.objects.\
        filter(owner=request.user).\
        values_list('amount', 'description', 'category', 'date')

    for row in rows:
        row_num += 1

        for col_num in range(len(row)):
            ws.write(row_num, col_num, str(row[col_num]), font_style)
    wb.save(response)

    return response
