from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Message
from .forms import MessageForm
from accounts.models import User

@login_required
def inbox(request):
    # Show messages for the logged-in user
    messages = request.user.received_messages.order_by('-timestamp')
    return render(request, 'messaging/inbox.html', {'messages': messages})


@login_required
def send_message(request, user_id):
    receiver = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        form = MessageForm(request.POST)
        if form.is_valid():
            msg = form.save(commit=False)
            msg.sender = request.user
            msg.receiver = receiver
            msg.save()
            return redirect('inbox')
    else:
        form = MessageForm()

    return render(request, 'messaging/send_message.html', {
        'form': form,
        'receiver': receiver
    })
