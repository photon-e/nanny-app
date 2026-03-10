from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Message


User = get_user_model()


class MessagingFeatureTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user(username="alice", password="pass123")
        self.bob = User.objects.create_user(username="bob", password="pass123")
        self.cara = User.objects.create_user(username="cara", password="pass123")

        Message.objects.create(sender=self.bob, receiver=self.alice, content="Hi Alice", read=False)
        Message.objects.create(sender=self.alice, receiver=self.bob, content="Hi Bob", read=True)
        Message.objects.create(sender=self.cara, receiver=self.alice, content="Hello", read=False)

    def test_inbox_groups_conversations(self):
        self.client.login(username="alice", password="pass123")
        response = self.client.get(reverse("inbox"))
        self.assertEqual(response.status_code, 200)
        conversations = response.context["conversations"]
        self.assertEqual(len(conversations), 2)

    def test_opening_thread_marks_messages_as_read(self):
        self.client.login(username="alice", password="pass123")
        self.client.get(reverse("send_message", args=[self.bob.id]))
        self.assertFalse(
            Message.objects.filter(sender=self.bob, receiver=self.alice, read=False).exists()
        )

    def test_cannot_message_self(self):
        self.client.login(username="alice", password="pass123")
        response = self.client.get(reverse("send_message", args=[self.alice.id]))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("inbox"))
