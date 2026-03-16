from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import User
from .forms import MessageForm
from .models import Message


@login_required
def inbox(request):
    inbox_messages = request.user.received_messages.select_related("sender").order_by('-timestamp')
    sent_messages = request.user.sent_messages.select_related("receiver").order_by('-timestamp')

    conversation_map = {}

    for message in inbox_messages:
        conversation_map.setdefault(message.sender_id, message)

    for message in sent_messages:
        conversation_map.setdefault(message.receiver_id, message)

    conversations = sorted(conversation_map.values(), key=lambda msg: msg.timestamp, reverse=True)

    return render(
        request,
        'messaging/inbox.html',
        {
            'inbox_messages': inbox_messages,
            'conversations': conversations,
        },
    )


@login_required
def send_message(request, user_id):
    other_user = get_object_or_404(User, id=user_id)

    if other_user == request.user:
        messages.error(request, "You cannot message yourself.")
        return redirect("inbox")

    if request.method == "POST":
        form = MessageForm(request.POST)
        if form.is_valid():
            msg = form.save(commit=False)
            msg.sender = request.user
            msg.receiver = other_user
            msg.save()
            messages.success(request, "Message sent.")
            return redirect("send_message", user_id=other_user.id)
    else:
        form = MessageForm()

    thread_messages = (
        Message.objects.filter(
            Q(sender=request.user, receiver=other_user)
            | Q(sender=other_user, receiver=request.user)
        )
        .select_related("sender", "receiver")
        .order_by("timestamp")
    )

    Message.objects.filter(sender=other_user, receiver=request.user, read=False).update(read=True)

    return render(
        request,
        "messaging/send_message.html",
        {
            "form": form,
            "receiver": other_user,
            "thread_messages": thread_messages,
        },
    )
