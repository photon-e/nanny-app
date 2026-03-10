from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import User
from .forms import MessageForm
from .models import Message


@login_required
def inbox(request):
    all_messages = (
        Message.objects.filter(Q(sender=request.user) | Q(receiver=request.user))
        .select_related("sender", "receiver")
        .order_by("-timestamp")
    )

    conversations = []
    seen_user_ids = set()
    for msg in all_messages:
        other_user = msg.receiver if msg.sender_id == request.user.id else msg.sender
        if other_user.id in seen_user_ids:
            continue
        seen_user_ids.add(other_user.id)
        unread_count = Message.objects.filter(
            sender=other_user, receiver=request.user, read=False
        ).count()
        conversations.append(
            {
                "other_user": other_user,
                "last_message": msg,
                "unread_count": unread_count,
            }
        )

    return render(request, "messaging/inbox.html", {"conversations": conversations})


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
