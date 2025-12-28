# Marketplace Integration Research (Notes)

These notes summarize the research for connecting Fulcrum to Amazon and MercadoLibre.

## 1. Amazon Selling Partner API (SP-API)

To connect Amazon, you must have an **Amazon Professional Selling Account**.

### Prerequisites
1.  **Professional Seller Account**: Upgrade your individual account if necessary.
2.  **AWS Account**: Required for SP-API security credentials.

### Setup Steps
1.  **Create a Developer Profile**:
    - Log in to Seller Central.
    - Go to **Apps and Services** > **Develop Apps**.
    - Click **Developer Central** and create your profile. Select **Private Developer**.
2.  **AWS IAM User**:
    - In your AWS Console, create an IAM User with a policy allowing `execute-api:Invoke` on the SP-API resources.
    - Create an IAM Role that can be assumed by this user.
3.  **Register Application**:
    - In Developer Central, click **Add new app**.
    - Select **SP-API** as the API type.
    - Copy your **Client ID** and **Client Secret**.

---

## 2. MercadoLibre API

MercadoLibre uses a standard OAuth 2.0 flow.

### Setup Steps
1.  **Register Application**:
    - Go to the [MercadoLibre DevCenter](https://developers.mercadolibre.com).
    - Click **Create New Application**.
2.  **Get Credentials**:
    - Copy your **Client ID** (App ID) and **Client Secret**.

---

## Testing (For Developers)

### MercadoLibre Test Users
You can create up to 10 test users via the API.
```bash
curl -X POST -H "Authorization: Bearer $ACCESS_TOKEN" \
     -d '{"site_id":"MLA"}' \
     https://api.mercadolibre.com/users/test_user
```
**Important**: Save the password immediately; it cannot be retrieved later.
