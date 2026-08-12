# Habot LSA Booking API

Backend prototype for HabotConnect's Learning Support Assistant booking module.

This project implements a Django REST API for parents to book Learning Support Assistants, search available LSAs by skill, and update booking states through a mock payment webhook.

## Candidate Details

Name: Mathavan M  
Email: maddymathavan345@gmail.com  
GitHub: https://github.com/MMathavan/habot-lsa-booking-api

## Tech Stack

- Python 3.13
- Django 6.1
- Django REST Framework
- SQLite for local development
- Requests for mock third-party payment integration
- Django TestCase and DRF APIClient for automated tests
- GitHub Actions for CI

## Features

- Normalized relational schema for Parents, LSAs, Skills, Bookings, and Payments
- Booking API with validation for invalid time ranges and overlapping sessions
- LSA search API filtered by skills and optional time window
- Optimized ORM queries using `prefetch_related` and indexed fields
- Mock payment gateway service using Python `requests`
- Payment webhook that updates booking status dynamically
- Admin panel registration for all core models
- Demo data command for local testing
- Automated test suite with 6 test cases

## Project Structure

```text
habot_lsa_booking_api/
  bookings/
    management/commands/seed_demo_data.py
    admin.py
    models.py
    serializers.py
    services.py
    tests.py
    urls.py
    views.py
  habot_lsa_booking_api/
    settings.py
    urls.py
  .github/workflows/tests.yml
  manage.py
  requirements.txt
```

## Setup Instructions

Clone the repository:

```bash
git clone https://github.com/MMathavan/habot-lsa-booking-api.git
cd habot-lsa-booking-api
```

Create and activate a virtual environment:

```bash
python -m venv venv
```

Windows:

```bash
venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Apply migrations:

```bash
python manage.py migrate
```

Create demo data:

```bash
python manage.py seed_demo_data
```

Create an admin user:

```bash
python manage.py createsuperuser
```

Run the server:

```bash
python manage.py runserver
```

Admin panel:

```text
http://127.0.0.1:8000/admin/
```

## API Documentation

Base URL:

```text
http://127.0.0.1:8000/api/v1/
```

### Search LSAs

```http
GET /api/v1/lsas/search/
```

Query parameters:

- `skills`: comma-separated skill names
- `start_time`: optional ISO datetime
- `end_time`: optional ISO datetime

Example:

```text
GET http://127.0.0.1:8000/api/v1/lsas/search/?skills=Autism Support
```

Example with time window:

```text
GET http://127.0.0.1:8000/api/v1/lsas/search/?skills=Autism Support&start_time=2026-08-15T10:00:00Z&end_time=2026-08-15T12:00:00Z
```

### Create Booking

```http
POST /api/v1/bookings/
```

Request body:

```json
{
  "parent_id": 1,
  "lsa_id": 1,
  "start_time": "2026-08-15T10:00:00Z",
  "end_time": "2026-08-15T12:00:00Z",
  "special_requirements": "Need support with reading and classroom routines."
}
```

Successful response:

```json
{
  "id": 1,
  "parent": {},
  "lsa": {},
  "start_time": "2026-08-15T10:00:00Z",
  "end_time": "2026-08-15T12:00:00Z",
  "status": "pending_payment",
  "special_requirements": "Need support with reading and classroom routines.",
  "payment": {
    "provider_reference": "mock_reference",
    "amount": "240.00",
    "currency": "AED",
    "status": "initiated"
  }
}
```

Validation rules:

- Start time cannot be in the past
- End time must be after start time
- LSA must be available
- Same LSA cannot have overlapping active bookings

### Payment Webhook

```http
POST /api/v1/payments/webhook/
```

Success event:

```json
{
  "provider_reference": "demo_payment_reference_001",
  "status": "success",
  "raw_payload": {
    "event": "payment.succeeded"
  }
}
```

Failure event:

```json
{
  "provider_reference": "demo_payment_reference_001",
  "status": "failed",
  "raw_payload": {
    "event": "payment.failed"
  }
}
```

Status transitions:

- Payment `success` changes booking status to `confirmed`
- Payment `failed` changes booking status to `payment_failed`

## Database Relationships

- `Parent` has many `BookingRequest` records
- `LSAProfile` has many `BookingRequest` records
- `LSAProfile` has many `Skill` records through a many-to-many relationship
- `BookingRequest` has one `Payment`
- `Payment` belongs to one `BookingRequest`

Main entities:

- `Parent`: parent and child details
- `Skill`: searchable skill labels such as Autism Support or Reading Intervention
- `LSAProfile`: LSA profile, hourly rate, experience, availability, and skills
- `BookingRequest`: parent, LSA, booking time, status, and requirements
- `Payment`: provider reference, amount, currency, status, and raw webhook data

## Query Optimization

The LSA search endpoint uses:

```python
prefetch_related("skills")
```

This prevents the N+1 query problem when serializing LSAs with their skills. Instead of querying skills separately for every LSA, Django prefetches related skills in a small number of queries.

The schema also includes indexes for fields commonly used in filtering and lookup:

- Parent email and name
- Skill name
- LSA email, availability status, and hourly rate
- Booking LSA, start time, end time, parent, and status
- Payment provider reference, status, and created date

The booking overlap check uses the standard time-window rule:

```text
existing.start_time < requested.end_time
existing.end_time > requested.start_time
```

This blocks double-bookings for the same LSA while allowing cancelled and payment-failed bookings to stop blocking future availability.

## Mock Third-Party Payment Integration

Payment integration is implemented in:

```text
bookings/services.py
```

`MockPaymentGatewayClient` uses Python's `requests.post()` when `MOCK_PAYMENT_GATEWAY_URL` is configured. If no URL is configured, it returns a local mock payment response so the project can run without an external service.

The service includes:

- Request timeout handling
- Exception logging
- Invalid JSON handling
- Missing provider reference validation

## Django MVT Design Choice

This project uses Django and Django REST Framework, so the architecture follows Django's MVT pattern:

- Model: database schema and business validation in `models.py`
- View: API request handling in `views.py`
- Template: not used for the API layer, because responses are JSON

In Flask MVC, controllers and routes are usually more manually assembled. Django MVT was chosen because the assignment requires ORM models, migrations, admin support, validation, and REST API structure. Django provides these pieces in a consistent framework, which keeps the prototype reliable and easier to evaluate.

## Running Tests

Run the full test suite:

```bash
python manage.py test
```

Current test coverage includes:

- Booking creation success
- Invalid booking time blocked
- Overlapping booking blocked
- LSA search by skill
- Payment webhook success
- Payment webhook failure

Expected result:

```text
Ran 6 tests
OK
```

## GitHub Actions

The workflow file is located at:

```text
.github/workflows/tests.yml
```

It runs on push and pull request to `main`:

- Install dependencies
- Check migrations
- Run Django tests

## Demo Commands

Seed demo data:

```bash
python manage.py seed_demo_data
```

Search demo LSAs:

```text
http://127.0.0.1:8000/api/v1/lsas/search/?skills=Autism Support
```

Demo payment reference:

```text
demo_payment_reference_001
```
