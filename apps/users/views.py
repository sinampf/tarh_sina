from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from .forms import LoginForm

def login_view(request):
    role = request.GET.get("role", "").lower()  # operator یا expert
    form = LoginForm()

    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password"]
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                if role == "operator":
                    return redirect('users:operator')
                elif role == "expert":
                    return redirect('users:expert')
            else:
                return render(request, 'users/admin_login.html', {
                    "form": form,
                    "error": "نام کاربری یا رمز اشتباه است",
                    "role": role
                })

    return render(request, 'users/admin_login.html', {"form": form, "role": role})

@login_required
def operator_panel(request):
    return render(request, 'users/operator.html')

@login_required
def expert_panel(request):
    return render(request, 'users/expert.html')