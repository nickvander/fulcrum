# Future Work: Mercado Pago Checkout API Integration

## Overview

This document outlines the research and integration plan for enabling "Checkout
Transparente" (Custom Checkout) using the Mercado Pago Checkout API. This will
allow the future e-commerce storefront to process payments directly without
redirecting users to an external page.

## Integration Steps

### 1. Account & Application Setup

- **Seller Account**: A Mercado Pago seller account is required.
- **Application**: Create an application in the
  [Mercado Pago Developer Panel](https://www.mercadopago.com/developers/panel).
- **Credentials**: Obtain the `Public Key` (for frontend) and `Access Token`
  (for backend).

### 2. Backend Implementation (FastAPI)

- **Dependency**: Use the official SDK `mercadopago` or direct REST calls.
- **Preference Creation**: The backend must generate a "Preference" or process a
  "Payment" directly.
- **Endpoints Needed**:
  - `POST /api/v1/payments/`: Receives tokenized card data and order details.
  - `POST /api/v1/webhooks/mercadopago`: Receives async payment status updates.

### 3. Frontend Implementation (Angular)

- **SDK**: Include `Main.js` or `Secure Fields` from Mercado Pago.
- **Tokenization**:
  - Use the SDK to securely collect card details (Number, Expiration, CVV,
    Cardholder Name).
  - Convert these details into a secure `token_id` _client-side_.
  - **Crucial**: Never send raw card data to the backend. Only send the
    `token_id`.
- **User Flow**:
  1. User enters card info.
  2. SDK generates token.
  3. Frontend sends Token + Order Info to Backend.
  4. Backend processes payment.
  5. Frontend displays success/failure.

### 4. Testing

- **Test Cards**: Use Mercado Libre's provided test credit cards (e.g., Visa,
  Mastercard) with specific prefixes.
- **Status Simulation**: Use specific "Cardholder Names" to simulate outcomes:
  - `APRO` -> Approved
  - `APRO` -> Rejected
  - `CONT` -> Pending

## Resources

- [Checkout API Overview](https://www.mercadopago.com.ar/developers/en/docs/checkout-api/landing)
- [Test Cards](https://www.mercadopago.com.ar/developers/en/docs/checkout-api/integration-test/test-cards)
