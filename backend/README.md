# Rentozz Backend (MVP foundation)

FastAPI backend for Rentozz. Uses Supabase Auth for phone OTP identity and Supabase-hosted PostgreSQL for application data.

## Included

- Health endpoint and OpenAPI docs
- Verified Supabase access-token authentication
- Profile creation from verified auth claims; new users default to `renter`
- Rental partner application submission and admin review
- Equipment listing/browsing
- Booking creation with an availability-overlap check and automatic confirmation
- Security deposits set per equipment listing
- Rent & Buy listing fields

## Not yet implemented

Payment collection, commissions, partner payouts, private identity-document upload/storage, bundle bookings, operator bookings, purchase checkout, cancellation/refund workflows, and robust concurrency-safe booking locks. Do not accept real payments until the payment flow and payout/compliance requirements are implemented and tested.

## Setup (Windows PowerShell)

1. Create/activate a virtual environment in this folder:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. Install packages:

   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env` and set:
   - `SUPABASE_URL`: Project URL from Supabase project settings.
   - `DATABASE_URL`: PostgreSQL connection string from Supabase Connect. Keep credentials private.

4. In Supabase Authentication settings, enable Phone login and configure an SMS provider. SMS may cost money. Do not put a Supabase service-role key in this app's `.env`; this backend verifies user access tokens using the public JWKS endpoint.

5. Run:

   ```powershell
   uvicorn app.main:app --reload
   ```

6. Visit `http://127.0.0.1:8000/docs` and `http://127.0.0.1:8000/api/health`.

The database tables are created automatically on startup for local MVP development. For production, replace `create_all` with reviewed Alembic migrations before deploying schema changes.

## Admin setup

Never allow a client to choose the `admin` role. After creating your own account through Supabase phone OTP and signing in once (which creates its `profiles` row), manually promote that profile to admin in the Supabase SQL Editor after verifying the profile ID:

```sql
UPDATE public.profiles
SET role = 'admin'
WHERE id = 'YOUR_AUTH_USER_UUID';
```

Replace the placeholder with your verified user UUID. Never expose this ability in a public API endpoint.

## Important implementation notes

- The current booking overlap check is an MVP check, not a concurrency-proof reservation lock. Before launch, implement a PostgreSQL exclusion constraint or equivalent transaction-safe locking to prevent simultaneous requests from double-booking equipment.
- Identity-document URLs are currently accepted as strings. Before partner onboarding goes live, upload documents to a private storage bucket and issue short-lived signed URLs; never use public document URLs.
- The current booking price is calculated from the daily rate and exact duration in days. Decide and implement rounding/minimum-duration policy before launch.
- The 12-hour partner review goal is an operational target, not an automatic SLA timer yet.
