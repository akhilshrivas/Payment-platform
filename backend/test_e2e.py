import requests
import json
import time
import hmac
import hashlib

API_URL = "http://127.0.0.1:8000/api"
WEBHOOK_SECRET = "dn4eSPfYHUK0Gx2LkaWGFKfVb-BNYGw9_Z5dvv-wD-c"

def test_flow():
    print("Starting End-to-End API Test against running Docker containers...")

    session_a = requests.Session()
    session_b = requests.Session()
    session_a.headers.update({"Host": "localhost", "X-Forwarded-Proto": "https"})
    session_b.headers.update({"Host": "localhost", "X-Forwarded-Proto": "https"})

    # 1. Register User A
    print("1. Registering User A...")
    res = session_a.post(f"{API_URL}/auth/register/", json={
        "email": "userg@example.com",
        "first_name": "User",
        "last_name": "A",
        "password": "securepassword123",
        "confirm_password": "securepassword123"
    })
    print("Register A:", res.status_code, res.text)
    
    # 2. Login User A
    print("2. Logging in User A...")
    res = session_a.post(f"{API_URL}/auth/login/", json={
        "email": "userg@example.com",
        "password": "securepassword123"
    })
    print("Login A:", res.status_code, res.text)
    token_a = res.json()["data"]["access"]
    session_a.headers.update({"Authorization": f"Bearer {token_a}"})
    
    user_a_id = session_a.get(f"{API_URL}/auth/me/").json()["data"]["id"]

    # 3. Add Money (Create Order)
    print("3. Creating Razorpay Order for ₹500...")
    res = session_a.post(f"{API_URL}/payments/create-order/", json={
        "amount": "500",
        "description": "Wallet Deposit"
    })
    assert res.status_code == 201, res.text
    order_data = res.json()["data"]
    order_id = order_data["razorpay_order_id"]
    payment_ref = order_data["payment_reference"]

    # 4. Simulate Razorpay Webhook (Payment Captured)
    print("4. Simulating Razorpay Webhook (Payment Captured)...")
    import uuid
    webhook_payload = {
        "event": "payment.captured",
        "id": f"evt_{uuid.uuid4().hex[:10]}",
        "payload": {
            "payment": {
                "entity": {
                    "id": f"pay_{uuid.uuid4().hex[:10]}",
                    "order_id": order_id,
                    "amount": 50000,
                    "currency": "INR",
                    "status": "captured",
                    "notes": {
                        "payment_reference": payment_ref
                    }
                }
            }
        }
    }
    payload_str = json.dumps(webhook_payload, separators=(',', ':'))
    signature = hmac.new(
        WEBHOOK_SECRET.encode(),
        payload_str.encode(),
        hashlib.sha256
    ).hexdigest()

    res = requests.post(
        f"{API_URL}/payments/webhook/",
        data=payload_str,
        headers={"Content-Type": "application/json", "X-Razorpay-Signature": signature, "Host": "localhost", "X-Forwarded-Proto": "https"}
    )
    assert res.status_code == 200, res.text

    # 5. Verify Wallet A balance
    print("5. Verifying User A Wallet Balance...")
    time.sleep(1) # wait for notification to be created
    res = session_a.get(f"{API_URL}/wallet/")
    balance_a = res.json()["data"]["balance"]
    assert float(balance_a) == 500.0, f"Expected 500, got {balance_a}"
    print("   User A balance is ₹500.00")

    # 6. Verify Notifications A
    res = session_a.get(f"{API_URL}/notifications/")
    notifications = res.json()["data"]
    assert len(notifications) > 0, "No notifications found"
    print(f"   Notification generated: {notifications[0]['title']}")

    # 7. Register/Login User B
    print("7. Registering and Logging in User B...")
    res = session_b.post(f"{API_URL}/auth/register/", json={
        "email": "userh@example.com",
        "first_name": "User",
        "last_name": "B",
        "password": "securepassword123",
        "confirm_password": "securepassword123"
    })
    res = session_b.post(f"{API_URL}/auth/login/", json={
        "email": "userh@example.com",
        "password": "securepassword123"
    })
    token_b = res.json()["data"]["access"]
    session_b.headers.update({"Authorization": f"Bearer {token_b}"})
    
    # 8. User A transfers ₹100 to User B
    print("8. Transferring ₹100 from User A to User B...")
    res = session_a.post(f"{API_URL}/wallet/transfer/", json={
        "receiver_email": "userh@example.com",
        "amount": "100",
        "description": "Pizza money"
    })
    assert res.status_code == 200, res.text

    # 9. Verify Balances
    balance_a = float(session_a.get(f"{API_URL}/wallet/").json()["data"]["balance"])
    balance_b = float(session_b.get(f"{API_URL}/wallet/").json()["data"]["balance"])
    assert balance_a == 400.0, f"User A balance is {balance_a}"
    assert balance_b == 100.0, f"User B balance is {balance_b}"
    print(f"   User A balance: ₹{balance_a}")
    print(f"   User B balance: ₹{balance_b}")

    # 10. Test Failure Cases
    print("10. Testing Failure Cases...")
    # Insufficient Balance
    res = session_b.post(f"{API_URL}/wallet/transfer/", json={
        "receiver_email": "userg@example.com",
        "amount": "1000",
        "description": "Too much"
    })
    assert res.status_code == 400
    print("   Insufficient balance rejected properly.")

    # Self Transfer
    res = session_a.post(f"{API_URL}/wallet/transfer/", json={
        "receiver_email": "userg@example.com",
        "amount": "10"
    })
    assert res.status_code == 400
    print("   Self-transfer rejected properly.")

    # 11. Test Recurring Payments
    print("11. Testing Recurring Payments...")
    res = session_a.post(f"{API_URL}/recurring-payments/", json={
        "receiver_email": "userh@example.com",
        "amount": "50",
        "frequency": "DAILY",
        "start_date": "2026-08-10",
        "description": "Daily allowance"
    })
    assert res.status_code == 201, res.text
    rp_id = res.json()["data"]["id"]
    print("   Recurring payment created successfully.")

    res = session_a.post(f"{API_URL}/recurring-payments/{rp_id}/pause/")
    assert res.json()["data"]["status"] == "PAUSED"
    print("   Recurring payment paused.")

    res = session_a.post(f"{API_URL}/recurring-payments/{rp_id}/resume/")
    assert res.json()["data"]["status"] == "ACTIVE"
    print("   Recurring payment resumed.")

    res = session_a.delete(f"{API_URL}/recurring-payments/{rp_id}/")
    assert res.status_code == 200
    print("   Recurring payment cancelled.")

    print("\n✅ All End-to-End API tests PASSED!")

if __name__ == "__main__":
    test_flow()
