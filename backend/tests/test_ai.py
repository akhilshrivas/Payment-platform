import pytest
from rest_framework import status
from django.urls import reverse
from apps.ai.models import AIConversation, AIMessage
from apps.wallets.models import Wallet
from apps.transactions.models import Transaction
from decimal import Decimal
from unittest.mock import patch
from datetime import timedelta
from django.utils import timezone
import uuid

@pytest.fixture
def chat_url():
    return reverse('ai-chat')

@pytest.fixture
def conversations_url():
    return reverse('ai-conversations-list')

@pytest.mark.django_db
class TestAIAssistant:

    def test_unauthenticated_access_rejected(self, api_client, chat_url):
        res = api_client.post(chat_url, {"message": "hello"})
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    def test_authenticated_access_allowed(self, auth_client, chat_url):
        client, user = auth_client
        with patch('apps.ai.services.llm_provider.AIProvider.generate_response') as mock_llm:
            mock_llm.return_value = {"content": "Hello! How can I help you?"}
            res = client.post(chat_url, {"message": "hello"})
            assert res.status_code == status.HTTP_200_OK
            assert "conversation_id" in res.data
            assert res.data["message"] == "Hello! How can I help you?"

    def test_conversation_isolation(self, user, another_user, api_client, chat_url):
        # User 1 creates conversation
        api_client.force_authenticate(user=user)
        with patch('apps.ai.services.llm_provider.AIProvider.generate_response') as mock_llm:
            mock_llm.return_value = {"content": "Response"}
            res = api_client.post(chat_url, {"message": "hello"})
            conv_id = res.data["conversation_id"]

        # User 2 tries to access it
        api_client.force_authenticate(user=another_user)
        res = api_client.post(chat_url, {"message": "hi", "conversation_id": conv_id})
        assert res.status_code == status.HTTP_404_NOT_FOUND

    def test_wallet_balance_tool(self, user):
        from apps.ai.services.tool_service import ToolService
        wallet = Wallet.objects.get(user=user)
        wallet.balance = Decimal("1500.50")
        wallet.available_balance = Decimal("1500.50")
        wallet.save()

        res = ToolService.get_wallet_balance(user)
        assert res["balance"] == 1500.50

    def test_deposit_summary_tool(self, user):
        from apps.ai.services.tool_service import ToolService
        wallet = Wallet.objects.get(user=user)
        Transaction.objects.create(
            receiver_wallet=wallet, amount=Decimal("100"), transaction_type="DEPOSIT", status="COMPLETED", transaction_reference=uuid.uuid4()
        )
        Transaction.objects.create(
            receiver_wallet=wallet, amount=Decimal("200"), transaction_type="DEPOSIT", status="COMPLETED", transaction_reference=uuid.uuid4()
        )
        # Should ignore pending
        Transaction.objects.create(
            receiver_wallet=wallet, amount=Decimal("500"), transaction_type="DEPOSIT", status="PENDING", transaction_reference=uuid.uuid4()
        )

        res = ToolService.get_deposit_summary(user)
        assert res["total_deposits"] == 300.0
        assert res["number_of_deposits"] == 2
        assert res["largest_deposit"] == 200.0

    def test_transfer_summary_tool(self, user, another_user):
        from apps.ai.services.tool_service import ToolService
        w1 = Wallet.objects.get(user=user)
        w2 = Wallet.objects.get(user=another_user)
        
        Transaction.objects.create(
            sender_wallet=w1, receiver_wallet=w2, amount=Decimal("50"), transaction_type="TRANSFER", status="COMPLETED", transaction_reference=uuid.uuid4()
        )

        res = ToolService.get_transfer_summary(user)
        assert res["total_outgoing_transfers"] == 50.0

    def test_recent_transactions_isolation(self, user, another_user):
        from apps.ai.services.tool_service import ToolService
        w1 = Wallet.objects.get(user=user)
        w2 = Wallet.objects.get(user=another_user)

        t1 = Transaction.objects.create(
            receiver_wallet=w1, amount=Decimal("10"), transaction_type="DEPOSIT", status="COMPLETED", transaction_reference=uuid.uuid4()
        )
        t2 = Transaction.objects.create(
            receiver_wallet=w2, amount=Decimal("20"), transaction_type="DEPOSIT", status="COMPLETED", transaction_reference=uuid.uuid4()
        )

        res1 = ToolService.get_recent_transactions(user)
        assert len(res1) == 1
        assert res1[0]["amount"] == 10.0

        res2 = ToolService.get_recent_transactions(another_user)
        assert len(res2) == 1
        assert res2[0]["amount"] == 20.0

    def test_missing_api_key_fails_safely(self, auth_client, chat_url, settings):
        client, user = auth_client
        settings.AI_API_KEY = ""
        res = client.post(chat_url, {"message": "hello"})
        assert res.status_code == status.HTTP_200_OK
        assert "error" in res.data["message"].lower() or "unavailable" in res.data["message"].lower()

    def test_conversation_persistence(self, auth_client, chat_url, conversations_url):
        client, user = auth_client
        with patch('apps.ai.services.llm_provider.AIProvider.generate_response') as mock_llm:
            mock_llm.return_value = {"content": "Response"}
            res = client.post(chat_url, {"message": "hello 1"})
            conv_id = res.data["conversation_id"]

            res2 = client.post(chat_url, {"message": "hello 2", "conversation_id": conv_id})
            assert res2.data["conversation_id"] == conv_id

            # Verify in DB
            conv = AIConversation.objects.get(id=conv_id)
            assert conv.messages.count() == 4 # User1, Asst1, User2, Asst2

            list_res = client.get(conversations_url)
            data = list_res.data.get("data", list_res.data)
            assert len(data) == 1

    def test_provider_url_selection_groq(self, settings):
        settings.AI_PROVIDER = "groq"
        settings.AI_BASE_URL = "https://api.groq.com/openai/v1"
        settings.AI_API_KEY = "test_key"
        from apps.ai.services.llm_provider import AIProvider
        provider = AIProvider()
        assert provider.base_url == "https://api.groq.com/openai/v1"
        
        with patch('requests.post') as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {"choices": [{"message": {"content": "Test"}}]}
            provider.generate_response([{"role": "user", "content": "hi"}])
            mock_post.assert_called_once()
            args, kwargs = mock_post.call_args
            assert args[0] == "https://api.groq.com/openai/v1/chat/completions"

    def test_provider_url_selection_openai(self, settings):
        settings.AI_PROVIDER = "openai"
        settings.AI_BASE_URL = "https://api.openai.com/v1"
        settings.AI_API_KEY = "test_key"
        from apps.ai.services.llm_provider import AIProvider
        provider = AIProvider()
        assert provider.base_url == "https://api.openai.com/v1"
        
        with patch('requests.post') as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {"choices": [{"message": {"content": "Test"}}]}
            provider.generate_response([{"role": "user", "content": "hi"}])
            mock_post.assert_called_once()
            args, kwargs = mock_post.call_args
            assert args[0] == "https://api.openai.com/v1/chat/completions"
