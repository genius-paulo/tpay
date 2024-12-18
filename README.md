Asynchronous TPay payment module with Telegram interface, working in polling mode

### Quick Start Manual

1. Install Dependencies
`poetry install`
2. Create .env from template.env and fill in all fields
3. Run database container:
`docker run --name pg-container -e POSTGRES_DB=payment_db -e POSTGRES_USER=payment_user -e POSTGRES_PASSWORD=payment_password -p 5432:5432 -d postgres:15`
4. Run `main.py`
5. Write `/get_payment` to receive a payment link