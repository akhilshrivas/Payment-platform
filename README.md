# Fullstack Payment Platform

A complete, production-ready full-stack payment application demonstrating a robust architecture for handling wallets, money transfers, recurring payments, and secure Razorpay payment gateway integration.

## Architecture

This platform implements a modern, decoupled architecture:
- **Frontend**: React + Vite + TypeScript, using standard REST API communication via Axios. Tailored with a custom fintech-themed design.
- **Backend**: Django + Django REST Framework (DRF) handling all business logic, data models, and API endpoints.
- **Database**: PostgreSQL for robust relational data storage and strict transactional integrity (using row-level locking with `select_for_update`).
- **Asynchronous Task Queue**: Redis + Celery for background processing (e.g., executing recurring scheduled payments and sending notifications without blocking the API).
- **Payment Gateway**: Razorpay integration strictly enforced via server-side order generation and webhook signature verification.

## Project Structure

```text
payment-platform/
├── backend/                  # Django backend
│   ├── apps/                 # Modular Django apps
│   │   ├── accounts/         # Custom User, JWT Auth
│   │   ├── common/           # Pagination, custom exceptions
│   │   ├── notifications/    # In-app notifications
│   │   ├── payments/         # Razorpay Gateway + Webhooks
│   │   ├── recurring_payments/ # Scheduled auto-transfers
│   │   ├── transactions/     # Transaction Ledger API
│   │   └── wallets/          # Wallet models, balances, transfers
│   ├── config/               # Settings (base, development, production)
│   ├── tests/                # Pytest comprehensive test suite
│   ├── manage.py
│   └── requirements.txt
├── frontend/                 # React frontend
│   ├── src/
│   │   ├── api/              # Axios clients & interceptors
│   │   ├── components/       # Reusable UI components & layouts
│   │   ├── context/          # React contexts (e.g., AuthContext)
│   │   ├── pages/            # Page components (Dashboard, Wallet, Transfer)
│   │   └── types/            # TypeScript interfaces
│   ├── package.json
│   └── vite.config.ts
├── docker-compose.yml        # Development Docker topology
└── docker-compose.prod.yml   # Production Docker topology (planned)
```

## Local Setup

### Environment Variables

Both the backend and frontend require environment configuration.

**Backend (`backend/.env`)**
Create a `.env` file in the `backend/` directory with the following (or use `docker-compose` defaults):
```env
DEBUG=True
SECRET_KEY=your_django_secret_key
POSTGRES_DB=payment_platform
POSTGRES_USER=payment_user
POSTGRES_PASSWORD=payment_pass
POSTGRES_HOST=localhost

# Razorpay Test Mode Credentials
RAZORPAY_KEY_ID=rzp_test_YourKeyID
RAZORPAY_KEY_SECRET=YourSecretKey
RAZORPAY_WEBHOOK_SECRET=YourWebhookSecret
```

**Frontend**
The frontend utilizes Vite's environment variables. By default, it expects the backend at `http://localhost:8000`. You can override this by creating `frontend/.env`:
```env
VITE_API_URL=http://localhost:8000
```
*Note: The frontend does NOT hold `RAZORPAY_KEY_ID` in `.env`. It securely receives it from the backend when an order is created.*

### Razorpay Test Mode & Webhook Setup

1. **Dashboard**: Go to the [Razorpay Dashboard](https://dashboard.razorpay.com/), switch to **Test Mode**, and generate API Keys.
2. **Backend**: Place your `Key Id` and `Key Secret` in `backend/.env`.
3. **Webhook**: Go to **Settings > Webhooks** in Razorpay. Set the URL to your publicly accessible backend URL (e.g., using ngrok: `https://your-ngrok-url.app/api/payments/webhook/`).
4. **Events**: Subscribe to `payment.captured`, `payment.failed`, `order.paid`, `refund.processed`, and `refund.failed`. Set a webhook secret and place it in `RAZORPAY_WEBHOOK_SECRET`.

### Docker Setup (Recommended)

You can launch the entire stack (PostgreSQL, Redis, Django API, Celery Worker, Celery Beat, React Frontend) via Docker Compose:

```bash
# Build and start all services
docker-compose up --build

# Run migrations inside the backend container
docker-compose exec backend python manage.py migrate

# Create a superuser
docker-compose exec backend python manage.py createsuperuser
```
The frontend will be available at `http://localhost:5173` and the backend at `http://localhost:8000`.

### Manual Setup (Without Docker)

#### Database Setup
Ensure PostgreSQL is running and create a database matching your `.env` configuration.

#### Redis/Celery Setup
Ensure Redis is running locally on port `6379`.

#### Running Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # (or .venv\Scripts\activate on Windows)
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

#### Running Celery (In separate terminals)
```bash
cd backend
celery -A config worker --loglevel=info
celery -A config beat --loglevel=info
```

#### Running Frontend
```bash
cd frontend
npm install
npm run dev
```

### Running Tests
The backend contains a rigorous suite of `pytest` tests validating business logic, locking, idempotency, and edge cases.
```bash
cd backend
pytest
```
To run frontend type-checks:
```bash
cd frontend
npm run build
```

## Manual End-to-End Payment Test

1. Ensure the full stack is running.
2. Open the browser at `http://localhost:5173`.
3. **Register** a new account and log in.
4. Go to **Add Money** (Wallet Deposit) and enter `₹500`. Click "Proceed to Pay".
5. The Razorpay checkout modal will appear. Use the test card `4111 1111 1111 1111` with any future expiry and CVV.
6. Complete the mock 3D Secure authentication.
7. Razorpay will send a webhook to the backend. The backend verifies the signature, applies database row-level locking, and increments the wallet.
8. The UI will show a **Notification** (bell icon top-right) confirming the successful deposit, and the dashboard will reflect the `₹500` balance.
9. Open an incognito window, create a second user, and use the **Send Money** feature to transfer `₹100` from User 1 to User 2. Both balances and transaction ledgers will update instantly.

## Production Deployment Checklist

Before deploying to production, ensure the following checklist is strictly followed:

- [ ] **Razorpay Keys**: Swap out Test mode keys for Live mode keys. Ensure `RAZORPAY_KEY_SECRET` and `RAZORPAY_WEBHOOK_SECRET` are strictly injected via server environment variables.
- [ ] **DEBUG**: Ensure `DEBUG=False` in the backend environment.
- [ ] **ALLOWED_HOSTS**: Explicitly list your frontend and API domains.
- [ ] **CORS**: Restrict `CORS_ALLOWED_ORIGINS` to your production frontend URL.
- [ ] **HTTPS**: Terminate SSL/TLS at a reverse proxy (e.g., Nginx) or load balancer.
- [ ] **Secrets**: Rotate `SECRET_KEY` and never commit `.env` files to version control (verified via `.gitignore`).
## Security Notes
- **Idempotency**: All webhook events are tracked in the `RazorpayWebhookEvent` model. Duplicate webhook deliveries will not result in double wallet credits.
- **Database Transactions**: Any operation involving wallet balances (wallet funding, user transfers, scheduled recurring payments) is wrapped in `transaction.atomic()` blocks and utilizes `.select_for_update()` to enforce row-level locks, fully mitigating race conditions.
- **Frontend Independence**: The frontend is treated as untrusted. The backend never blindly accepts "Payment Success" assertions from the frontend; wallet credit ONLY occurs upon cryptographic verification of the Razorpay webhook payload.

## Phase 15: AI Financial Assistant

The AI Financial Assistant allows users to query their financial data using natural language. It securely retrieves data using tool calls while enforcing strict authentication and authorization.

### Architecture
1. **React UI**: A dedicated chat interface (/assistant) mimicking ChatGPT with conversation history.
2. **Django Backend**: A modular apps.ai service orchestrating LLM calls and tool execution.
3. **LLM Provider**: Abstracted AI provider capable of tool calling (defaults to OpenAI).
4. **Security**: The assistant runs read-only operations, relies entirely on Django's ORM aggregation to perform math, and automatically passes the authenticated request.user to all tools, rendering unauthorized access impossible.

## Production Deployment

This application uses decoupled architecture and can be easily deployed to a combination of managed services (e.g., Vercel for Frontend, Render/Railway for Backend).

### 1. Architecture
- **Frontend**: Deployed as a static site (Vercel/Netlify).
- **Backend API**: Deployed as a Dockerized web service.
- **Background Workers**: Celery Worker and Celery Beat deployed as separate background services connecting to the same Redis/PostgreSQL instances.
- **Database**: Managed PostgreSQL.
- **Cache/Broker**: Managed Redis.

### 2. Frontend deployment
1. Deploy the `frontend/` directory to Vercel/Netlify.
2. Override the Build Command if necessary: `npm run build`.
3. Set the Environment Variable:
   - `VITE_API_URL`: `https://your-backend-domain.com`

### 3. Backend deployment
Deploy the `backend/` directory using the provided `Dockerfile` (or `docker-compose.prod.yml`).
For platforms like Render:
- Build Command: Built automatically via Dockerfile if supported, or via Python environment.
- Start Command (Web):
  ```bash
  gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3
  ```

### 4. PostgreSQL setup
Use a managed PostgreSQL database. Provide the connection string or individual variables (`POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`) to the Backend, Worker, and Beat services. Before full usage, run migrations:
```bash
python manage.py migrate
```
**Do not destroy or reset the production database.**

### 5. Redis setup
Use a managed Redis instance (or Valkey). Provide the `REDIS_URL` and `CELERY_BROKER_URL` to all backend services.

### 6. Celery worker
Deploy as a background worker process.
Start Command:
```bash
celery -A config worker --loglevel=info --concurrency=4
```

### 7. Celery Beat
Deploy as a background scheduler process.
Start Command:
```bash
celery -A config beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

### 8. Environment variables
The backend requires the following configuration exclusively from environment variables:
- `SECRET_KEY`: A strong, unique secret.
- `DEBUG`: Must be `False`.
- `ALLOWED_HOSTS`: E.g., `your-backend-domain.com`.
- `CORS_ALLOWED_ORIGINS`: E.g., `https://your-frontend-domain.com`.
- `CSRF_TRUSTED_ORIGINS`: E.g., `https://your-frontend-domain.com,https://your-backend-domain.com`.
- `POSTGRES_*` / `DATABASE_URL`: Database credentials.
- `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`: Redis credentials.
- `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET`: Razorpay credentials.
- `AI_PROVIDER`, `AI_API_KEY`, `AI_MODEL`: AI Assistant settings.

### 9. Razorpay test webhook
Keep Razorpay in TEST MODE for initial deployment.
In the Razorpay Dashboard, configure the webhook URL:
`https://your-backend-domain.com/api/payments/webhook/`
Ensure `RAZORPAY_WEBHOOK_SECRET` matches your backend environment variable.

### 10. Health check
The backend exposes a public, unauthenticated health check endpoint at `/api/health/`. Verify deployment success by querying this endpoint.

### 11. CORS configuration
Configure CORS strictly. Do not use wildcards (`*`).
- Local: `http://localhost:5173`
- Production: `https://your-vercel-domain.com`

### 12. Security notes
- **Never expose secrets to Vite**: Ensure `VITE_` variables only contain public URLs.
- **Never commit `.env`**: Environment files are ignored by git.
- **HTTPS Enforcement**: The production Django settings automatically enforce secure cookies and SSL redirects. Ensure your hosting platform provides HTTPS.
