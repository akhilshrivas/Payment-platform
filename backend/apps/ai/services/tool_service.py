from django.db.models import Sum, Count, Max, Avg, Q
from django.utils import timezone
from dateutil.parser import parse as parse_date
import logging

logger = logging.getLogger(__name__)

class ToolService:
    @staticmethod
    def get_wallet_balance(user):
        """Returns the authenticated user's current wallet balance."""
        from apps.wallets.models import Wallet
        try:
            wallet = Wallet.objects.get(user=user)
            return {
                "balance": float(wallet.balance),
                "available_balance": float(wallet.available_balance),
                "currency": wallet.currency
            }
        except Wallet.DoesNotExist:
            return {"error": "Wallet not found for user."}

    @staticmethod
    def get_recent_transactions(user, limit=5):
        """Returns recent transactions belonging ONLY to request.user."""
        from apps.transactions.models import Transaction
        from apps.wallets.models import Wallet
        try:
            wallet = Wallet.objects.get(user=user)
        except Wallet.DoesNotExist:
            return {"error": "Wallet not found."}
        
        limit = min(int(limit), 20)
        
        txns = Transaction.objects.filter(
            Q(sender_wallet=wallet) | Q(receiver_wallet=wallet)
        ).order_by("-created_at")[:limit]
        
        return [
            {
                "reference": t.transaction_reference,
                "amount": float(t.amount),
                "type": t.transaction_type,
                "status": t.status,
                "date": t.created_at.isoformat(),
                "description": t.description
            } for t in txns
        ]

    @staticmethod
    def get_transactions_by_date_range(user, start_date, end_date):
        """Returns transactions within the requested range."""
        from apps.transactions.models import Transaction
        from apps.wallets.models import Wallet
        try:
            wallet = Wallet.objects.get(user=user)
            start = parse_date(start_date)
            end = parse_date(end_date)
        except Exception as e:
            return {"error": f"Invalid date format or wallet missing. {e}"}
            
        txns = Transaction.objects.filter(
            Q(sender_wallet=wallet) | Q(receiver_wallet=wallet),
            created_at__gte=start,
            created_at__lte=end
        ).order_by("-created_at")[:50] # limit to prevent huge payloads
        
        return [
            {
                "amount": float(t.amount),
                "type": t.transaction_type,
                "status": t.status,
                "date": t.created_at.isoformat()
            } for t in txns
        ]

    @staticmethod
    def get_deposit_summary(user, start_date=None, end_date=None):
        """Returns total, count, average, and largest deposit."""
        from apps.transactions.models import Transaction
        from apps.wallets.models import Wallet
        try:
            wallet = Wallet.objects.get(user=user)
        except Wallet.DoesNotExist:
            return {"error": "Wallet not found."}
            
        qs = Transaction.objects.filter(receiver_wallet=wallet, transaction_type="DEPOSIT", status="COMPLETED")
        
        if start_date:
            qs = qs.filter(created_at__gte=parse_date(start_date))
        if end_date:
            qs = qs.filter(created_at__lte=parse_date(end_date))
            
        agg = qs.aggregate(
            total_deposits=Sum("amount"),
            count=Count("id"),
            average_deposit=Avg("amount"),
            largest_deposit=Max("amount")
        )
        
        return {
            "total_deposits": float(agg["total_deposits"] or 0),
            "number_of_deposits": agg["count"],
            "average_deposit": float(agg["average_deposit"] or 0),
            "largest_deposit": float(agg["largest_deposit"] or 0)
        }

    @staticmethod
    def get_transfer_summary(user, start_date=None, end_date=None):
        """Returns total, count, average, and largest outgoing transfer."""
        from apps.transactions.models import Transaction
        from apps.wallets.models import Wallet
        try:
            wallet = Wallet.objects.get(user=user)
        except Wallet.DoesNotExist:
            return {"error": "Wallet not found."}
            
        qs = Transaction.objects.filter(sender_wallet=wallet, transaction_type="TRANSFER", status="COMPLETED")
        
        if start_date:
            qs = qs.filter(created_at__gte=parse_date(start_date))
        if end_date:
            qs = qs.filter(created_at__lte=parse_date(end_date))
            
        agg = qs.aggregate(
            total_transfers=Sum("amount"),
            count=Count("id"),
            average_transfer=Avg("amount"),
            largest_transfer=Max("amount")
        )
        
        return {
            "total_outgoing_transfers": float(agg["total_transfers"] or 0),
            "number_of_transfers": agg["count"],
            "average_transfer": float(agg["average_transfer"] or 0),
            "largest_transfer": float(agg["largest_transfer"] or 0)
        }

    @staticmethod
    def get_spending_summary(user, start_date=None, end_date=None):
        """Aggregate outgoing transactions (withdrawals, payments, transfers)."""
        from apps.transactions.models import Transaction
        from apps.wallets.models import Wallet
        try:
            wallet = Wallet.objects.get(user=user)
        except Wallet.DoesNotExist:
            return {"error": "Wallet not found."}
            
        qs = Transaction.objects.filter(sender_wallet=wallet, status="COMPLETED")
        
        if start_date:
            qs = qs.filter(created_at__gte=parse_date(start_date))
        if end_date:
            qs = qs.filter(created_at__lte=parse_date(end_date))
            
        agg = qs.aggregate(
            total_spent=Sum("amount"),
            count=Count("id")
        )
        
        return {
            "total_spent": float(agg["total_spent"] or 0),
            "transaction_count": agg["count"]
        }

    @staticmethod
    def compare_periods(user, period_1_start, period_1_end, period_2_start, period_2_end):
        """Compare spending/deposits between two periods."""
        p1_deposit = ToolService.get_deposit_summary(user, period_1_start, period_1_end)
        p2_deposit = ToolService.get_deposit_summary(user, period_2_start, period_2_end)
        
        p1_spent = ToolService.get_spending_summary(user, period_1_start, period_1_end)
        p2_spent = ToolService.get_spending_summary(user, period_2_start, period_2_end)
        
        return {
            "period_1": {
                "start": period_1_start,
                "end": period_1_end,
                "deposits": p1_deposit,
                "spending": p1_spent
            },
            "period_2": {
                "start": period_2_start,
                "end": period_2_end,
                "deposits": p2_deposit,
                "spending": p2_spent
            }
        }

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "get_wallet_balance",
            "description": "Returns the authenticated user's current wallet balance and available balance.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_recent_transactions",
            "description": "Returns recent transactions belonging to the user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of transactions to return (max 20)."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_transactions_by_date_range",
            "description": "Returns the authenticated user's transactions within the requested date range.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Start date in ISO format (e.g., 2023-01-01T00:00:00Z)"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date in ISO format (e.g., 2023-01-31T23:59:59Z)"
                    }
                },
                "required": ["start_date", "end_date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_deposit_summary",
            "description": "Returns total, count, average, and largest deposit for the user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Optional start date in ISO format."
                    },
                    "end_date": {
                        "type": "string",
                        "description": "Optional end date in ISO format."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_transfer_summary",
            "description": "Returns total, count, average, and largest outgoing transfer for the user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Optional start date in ISO format."
                    },
                    "end_date": {
                        "type": "string",
                        "description": "Optional end date in ISO format."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_spending_summary",
            "description": "Returns useful aggregate information about outgoing transactions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Optional start date in ISO format."
                    },
                    "end_date": {
                        "type": "string",
                        "description": "Optional end date in ISO format."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "compare_periods",
            "description": "Compare spending and deposits between two periods. Useful for 'This month vs last month'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "period_1_start": {"type": "string"},
                    "period_1_end": {"type": "string"},
                    "period_2_start": {"type": "string"},
                    "period_2_end": {"type": "string"}
                },
                "required": ["period_1_start", "period_1_end", "period_2_start", "period_2_end"]
            }
        }
    }
]
