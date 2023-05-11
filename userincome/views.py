from django.shortcuts import render, redirect
from .models import Source, UserIncome
from django.core.paginator import Paginator
from userpreferences.models import UserPreference
from django.contrib import messages
from django.contrib.auth.decorators import login_required
import json
from django.http import JsonResponse, HttpResponse
from userpreferences.models import UserPreference
import datetime
import csv
import xlwt
from django.template.loader import render_to_string
from expenses.models import Category, Expense

# Create your views here.

# It first checks if the request method is POST, and then extracts
# the search string from the POST request body using the json.loads function.


def search_income(request):
    if request.method == 'POST':
        search_str = json.loads(request.body).get('searchText')
        income = UserIncome.objects.filter(
            amount__istartswith=search_str, owner=request.user) | UserIncome.objects.filter(
            date__istartswith=search_str, owner=request.user) | UserIncome.objects.filter(
            description__icontains=search_str, owner=request.user) | UserIncome.objects.filter(
            source__icontains=search_str, owner=request.user)
        data = income.values()
        return JsonResponse(list(data), safe=False)


@login_required(login_url='/authentication/login')
def index(request):
    categories = Source.objects.all()
    income = UserIncome.objects.filter(owner=request.user)
    paginator = Paginator(income, 5)
    page_number = request.GET.get('page')
    page_obj = Paginator.get_page(paginator, page_number)

    if UserPreference.objects.filter(user=request.user).exists():
        currency = UserPreference.objects.get(user=request.user).currency
    else:
        currency = 'INR - Indian Rupee'

    context = {
        'income': income,
        'page_obj': page_obj,
        'currency': currency
    }

    return render(request, 'income/index.html', context)


@login_required(login_url='/authentication/login')
def add_income(request):
    sources = Source.objects.all()
    context = {
        'sources': sources,
        'values': request.POST
    }
    if request.method == 'GET':
        return render(request, 'income/add_income.html', context)

    if request.method == 'POST':
        amount = request.POST['amount']

        if not amount:
            messages.error(request, 'Amount is required')
            return render(request, 'income/add_income.html', context)
        description = request.POST['description']
        date = request.POST['income_date']
        source = request.POST['source']

        if not description:
            messages.error(request, 'description is required')
            return render(request, 'income/add_income.html', context)

        UserIncome.objects.create(owner=request.user, amount=amount, date=date,
                                  source=source, description=description)
        messages.success(request, 'Record saved successfully')

        return redirect('income')


@login_required(login_url='/authentication/login')
def income_edit(request, id):

    # Retrieve the income record to be edited based on the id parameter

    income = UserIncome.objects.get(pk=id)

    # Get all sources for the source dropdown list in the form
    sources = Source.objects.all()

    # Set the context dictionary to be used in rendering the template
    context = {
        'income': income,
        'values': income,
        'sources': sources
    }
    if request.method == 'GET':
        return render(request, 'income/edit_income.html', context)
    if request.method == 'POST':
        amount = request.POST['amount']

     # If amount is not provided, display an error message and render the edit_income.html template
        if not amount:
            messages.error(request, 'Amount is required')
            return render(request, 'income/edit_income.html', context)
        description = request.POST['description']
        date = request.POST['income_date']
        source = request.POST['source']

        if not description:
            messages.error(request, 'description is required')
            return render(request, 'income/edit_income.html', context)
        income.amount = amount
        income. date = date
        income.source = source
        income.description = description

        income.save()
        messages.success(request, 'Record updated  successfully')

        return redirect('income')


def delete_income(request, id):
    income = UserIncome.objects.get(pk=id)
    income.delete()
    messages.success(request, 'record removed')
    return redirect('income')


def expense_source_summary(request):
    todays_date = datetime.date.today()
    six_months_ago = todays_date-datetime.timedelta(days=30*6)
    incomes = UserIncome.objects.filter(owner=request.user,
                                        date__gte=six_months_ago, date__lte=todays_date)

    finalrep = {}

    def get_category(income):
        return income.source
    category_list = list(set(map(get_category, incomes)))

    def get_income_category_amount(source):
        amount = 0
        filtered_by_category = incomes.filter(source=source)

        for item in filtered_by_category:
            amount += item.amount

        return amount

    for x in incomes:
        for y in category_list:
            finalrep[y] = get_income_category_amount(y)

    return JsonResponse({'expense_category_data': finalrep}, safe=False)


def hexstats_view(request):
    return render(request, 'income/hexstats.html')


def export_csv(request):
    response = HttpResponse(content_type='text/csv')

    response['Content-Disposition'] = 'attachment; filename="Incomes{}.csv"'.format(str(datetime.datetime.now()))

    writer = csv.writer(response)
    writer.writerow(['Amount', 'Description', 'Source', 'Date'])

    incomes_Exp = UserIncome.objects.filter(owner=request.user)

    for income in incomes_Exp:
        writer.writerow([income.amount, income.description,
                         income.source, income.date])

    return response


def export_excel(request):
    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = 'attachment; filename="Incomes{}.xls"'.format(str(datetime.datetime.now()))
    wb = xlwt.Workbook(encoding='utf-8')
    ws = wb.add_sheet('Incomes')
    row_num = 0
    font_style = xlwt.XFStyle()
    font_style.font.bold = True

    columns = ['Amount', 'Description', 'Source', 'Date']

    for col_num in range(len(columns)):
        ws.write(row_num, col_num, columns[col_num], font_style)

    font_style = xlwt.XFStyle()

    rows = UserIncome.objects.filter(owner=request.user).values_list('amount', 'description', 'source', 'date')

    for row in rows:
        row_num += 1

        for col_num in range(len(row)):
            ws.write(row_num, col_num, str(row[col_num]), font_style)
    wb.save(response)

    return response
