from django.shortcuts import render

# Create your views here.

# taking requests and taking back responses
def index(request):
    return render(request, 'expenses/index.html')

def add_expense(request):
    return render(request, 'expenses/add_expense.html')    