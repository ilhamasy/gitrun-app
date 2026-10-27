# API Reference

Complete endpoint specifications for `payment-gateway` HTTP/REST service.

## Standard Headers

Every mutating request must include:
- `Authorization: Bearer <jwt_token>`
- `Idempotency-Key: <unique_uuid_v4>`
- `Content-Type: application/json`

---

## 1. Create Payment Intent

Initiates authorization for card or alternative payment method.

`POST /api/v1/payments`

### Request Body
```json
{
  "account_id": "acc_8f7b2c91-4d1a-4293-8f6a-9f5b2489c7d1",
  "amount_cents": 4999,
  "currency": "USD",
  "payment_method": {
    "type": "card",
    "token": "tok_visa_4242"
  },
  "metadata": {
    "order_id": "ord_1029384"
  }
}
```

### Response `201 Created`
```json
{
  "id": "pay_98234710-1284-482a-bc72-491290bbcf82",
  "status": "SUCCEEDED",
  "amount_cents": 4999,
  "currency": "USD",
  "psp_reference": "ch_3N8c1t2eZvKYlo2C1gQp",
  "created_at": "2026-10-26T14:32:01Z"
}
```

---

## 2. Refund Payment

Submits full or partial refund against captured transaction.

`POST /api/v1/payments/{payment_id}/refunds`

### Request Body
```json
{
  "amount_cents": 1500,
  "reason": "customer_requested"
}
```

### Response `200 OK`
```json
{
  "refund_id": "ref_839210-4821-bcfa-1029384",
  "payment_id": "pay_98234710-1284-482a-bc72-491290bbcf82",
  "amount_refunded_cents": 1500,
  "status": "PROCESSED"
}
```

---

## Error Handling

Standard RFC 7807 problem details:

| Status Code | Code | Description |
| :--- | :--- | :--- |
| `400 Bad Request` | `INVALID_PAYLOAD` | Missing required fields or invalid currency format |
| `409 Conflict` | `IDEMPOTENCY_CONFLICT` | Key re-used with different request payload |
| `422 Unprocessable` | `PSP_DECLINED` | Card declined or insufficient funds |
| `502 Bad Gateway` | `PSP_TIMEOUT` | Upstream provider failed to acknowledge in SLA |
