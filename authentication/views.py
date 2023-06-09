import threading
from django.shortcuts import render, redirect
from django.contrib import auth
from django.urls import reverse
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from .utils import account_activation_token
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import send_mail
from django.views import View
import json
from django.http import JsonResponse
from django.contrib.auth.models import User
import json
from django.http import JsonResponse
from django.contrib.auth.models import User
from validate_email import validate_email
from django.contrib import messages
from django.core.mail import EmailMessage
from django.contrib.sites.shortcuts import get_current_site
from django.utils.encoding import force_bytes, force_str
from django.utils.encoding import DjangoUnicodeDecodeError


class EmailThread(threading.Thread):
    """
    The purpose of this class is to send an email message in a separate thread
    from the main application thread.
    """
    def __init__(self, email):
        self.email = email
        threading.Thread.__init__(self)

    def run(self):
        self.email.send(fail_silently=False)


class EmailValidationView(View):
    """
    Validate email addresses before allowing users to create new accounts
    """
    def post(self, request):
        data = json.loads(request.body)
        email = data['email']
        if not validate_email(email):
            return JsonResponse({'email_error': 'Email is invalid'},
                                status=400)
        if User.objects.filter(email=email).exists():
            return JsonResponse({'email_error':
                                'sorry email in use,choose another one! '},
                                status=409)
        return JsonResponse({'email_valid': True})


class UsernameValidationView(View):
    """
    Validate usernames before allowing users to create new account
    """
    def post(self, request):
        data = json.loads(request.body)
        username = data['username']
        if not str(username).isalnum():
            err_str = 'username should only contain alphanumeric characters!'
            return JsonResponse({'username_error': err_str}, status=400)
        if User.objects.filter(username=username).exists():
            err_str = 'sorry username in use, choose another one!'
            return JsonResponse({'username_error': err_str}, status=409)
        return JsonResponse({'username_valid': True})


class RegistrationView(View):
    """
    The view renders the registration form and returns it as an HTTP response,
    along with a success message indicating that the account has been created.
    If any of the validations fail, the view re-renders the registration form
    and returns it with an appropriate error message.
    """
    def get(self, request):
        return render(request, 'authentication/register.html')

    def post(self, request):
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']

        context = {
            'fieldValues': request.POST
        }

        if not User.objects.filter(username=username).exists():
            if not User.objects.filter(email=email).exists():
                if len(password) < 6:
                    messages.error(request, 'Password too short!')
                    return render(request, 'authentication/register.html',
                                  context)

                user = User.objects.create_user(username=username, email=email,
                                                password=password)
                user.set_password(password)
                user.is_active = False
                user.save()
                current_site = get_current_site(request)
                email_body = {
                    'user': user,
                    'domain': current_site.domain,
                    'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                    'token': account_activation_token.make_token(user),
                }

                link = reverse('activate', kwargs={
                               'uidb64': email_body['uid'],
                               'token': email_body['token']})

                email_subject = 'Activate your account.'
                activate_url = 'http://'+current_site.domain+link

                email = EmailMessage(
                    email_subject,
                    'Hi '+user.username +
                    ', Please the link below to activate your account \n' +
                    activate_url, 'noreply@cliexpenses.com', [email])
                EmailThread(email).start()
                messages.success(request, 'Email successfully sent. Please check your email.')
                return render(request, 'authentication/register.html')

        return render(request, 'authentication/register.html')


class VerificationView(View):
    """
    If the token is not valid, the user is redirected to the login page with
    a message indicating that the user has already been activated.
    If an error occurs during the process, the user is redirected
    to the login page without any action taken.
    """
    def get(self, request, uidb64, token):
        try:
            id = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=id)
            if not account_activation_token.check_token(user, token):
                return redirect('login' + '?message=' +
                                'User already activated.')
            if user.is_active:
                return redirect('login')
            user.is_active = True
            user.save()
            messages.success(request, 'Account activated successfully.')
            return redirect('login')
        except Exception as ex:
            pass
        return redirect('login')


class LoginView(View):
    """
    It displays a message asking the user to check their
    email for activation. If authentication fails, it displays an error
    message asking the user to try again.
    """
    def get(self, request):
        return render(request, 'authentication/login.html')

    def post(self, request):
        username = request.POST['username']
        password = request.POST['password']

        if username and password:
            user = auth.authenticate(username=username, password=password)
            if user:
                if user.is_active:
                    auth.login(request, user)
                    messages.success(request, 'Welcome ' +
                                     user.username +
                                     '. You are now logged in.')
                    return redirect('expenses')
                err_str = 'Account is not active, please check your email.'
                messages.error(request, err_str)
                return render(request, 'authentication/login.html')

            messages.error(request, 'Invalid credentials, try again.')
            return render(request, 'authentication/login.html')

        messages.error(request, 'Please fill all fields')
        return render(request, 'authentication/login.html')


class LogoutView(View):
    def post(self, request):
        auth.logout(request)
        messages.success(request, 'You have been logged out.')
        return redirect('login')


class RequestPasswordResetEmail(View):
    """
    If the user object exists, the view creates a password reset link with
    the user's primary key and a token.
    If the email is sent successfully, the view returns a success message
    to the user on the same page, instructing them to check their email for
    further instructions.
    """
    def get(self, request):
        return render(request, 'authentication/reset-password.html')

    def post(self, request):
        email = request.POST['email']
        context = {
            'values': request.POST
        }

        if not validate_email(email):
            messages.error(request, 'Please supply a valid email.')
            return render(request, 'authentication/reset-password.html',
                          context)

        current_site = get_current_site(request)
        user = User.objects.filter(email=email)

        if user.exists():
            email_contents = {
                'user': user[0],
                'domain': current_site.domain,
                'uid': urlsafe_base64_encode(force_bytes(user[0].pk)),
                'token': PasswordResetTokenGenerator().make_token(user[0]),
                }

            link = reverse('reset-user-password', kwargs={
                            'uidb64': email_contents['uid'],
                            'token': email_contents['token']})

            email_subject = 'Password Reset Instructions'

            reset_url = 'http://'+current_site.domain+link

            email = EmailMessage(
                email_subject,
                'Hi, Please follow the link below to reset your password \n' +
                reset_url,
                'cliexpensesrequest@gmail.com',
                [email],
            )
            EmailThread(email).start()

        inf_str = 'We have sent you an email to reset your password.'
        messages.success(request, inf_str)
        return render(request, 'authentication/reset-password.html')


class CompletePasswordReset(View):
    def get(self, request, uidb64, token):
        context = {
            'uidb64': uidb64,
            'token': token,
        }

        try:
            user_id = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=user_id)

            if not PasswordResetTokenGenerator().check_token(user, token):
                err_str = 'Password link is invalid! Please request a new one!'
                messages.info(request, err_str)
                return render(request, 'authentication/reset-password.html')
        except Exception as identifier:

            pass

        return render(request, 'authentication/set-new-password.html', context)

    def post(self, request, uidb64, token):
        """
        This implementation checks if the passwords
        match and if they have at least six characters.
        It then sets the new password and saves the user object.
        """

        context = {
            'uidb64': uidb64,
            'token': token,
        }

        password = request.POST['password']
        password2 = request.POST['password2']

        if password != password2:
            messages.error(request, 'Password do not match!')
            return render(request, 'authentication/set-new-password.html',
                          context)

        if len(password) < 6:
            messages.error(request, 'Password too short')
            return render(request, 'authentication/set-new-password.html',
                          context)

        try:
            user_id = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=user_id)
            user.set_password(password)
            user.save()

            messages.success(request,
                             'Password reset successfull, you can login!')
            return redirect('login')
        except Exception as identifier:
            messages.info(request, 'Something went wrong!')
            return render(request,
                          'authentication/set-new-password.html', context)
