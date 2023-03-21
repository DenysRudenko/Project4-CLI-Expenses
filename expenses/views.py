from django.shortcuts import render
from django.contrib.auth.decorators import login_required

# Create your views here.


# Protect the root
@login_required(login_url='/authentication/login')
# taking requests and taking back responses
def index(request):
    return render(request, 'expenses/index.html')

def add_expense(request):
    return render(request, 'expenses/add_expense.html')    