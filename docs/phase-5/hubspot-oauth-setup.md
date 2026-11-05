# HubSpot OAuth 2.0 Configuration Guide — Outmate GTM

**Target Service:** HubSpot Developer Portal & Nango Dashboard  
**Integration Type:** Public App (OAuth 2.0)  

---

## 1. Prerequisites

1. A **HubSpot Developer Account** ([developers.hubspot.com](https://developers.hubspot.com)).
2. A **Nango Cloud or Self-Hosted Account** ([app.nango.dev](https://app.nango.dev)).

---

## 2. Step-by-Step Setup in HubSpot Developer Portal

1. Log in to your HubSpot Developer Account.
2. Navigate to **Apps** → Click **Create app**.
3. Under **App Info**:
   - App Name: `Outmate GTM Intelligence`
   - Description: `Read-only B2B Go-To-Market research and account intelligence connector.`
4. Under **Auth**:
   - Set **Redirect URL** to your Nango OAuth callback URL:
     - Nango Cloud: `https://api.nango.dev/oauth/callback`
     - Self-Hosted: `https://<your-nango-domain>/oauth/callback`
5. Select Required Scopes (**Strictly Read-Only**):
   - `crm.objects.companies.read`
   - `crm.objects.contacts.read`
   - `crm.objects.deals.read`
   *(Do NOT select any write, delete, email, or marketing scopes)*
6. Copy the generated **Client ID** and **Client Secret**.

---

## 3. Configuring HubSpot in Nango Dashboard

1. Log in to the Nango Dashboard ([app.nango.dev](https://app.nango.dev)).
2. Navigate to **Integrations** → Click **Add Integration**.
3. Select **HubSpot** from the provider catalog.
4. Set **Unique Integration Key**: `hubspot` (must match `NANGO_INTEGRATION_ID_HUBSPOT` in `.env`).
5. Enter your HubSpot **Client ID** and **Client Secret**.
6. Set the Requested Scopes:
   `crm.objects.companies.read crm.objects.contacts.read crm.objects.deals.read`
7. Save the configuration.

---

## 4. Local Environment Configuration (`.env`)

Add the following environment variables to your `.env` file:

```env
# Nango Secret Key obtained from Nango Dashboard Settings -> API Keys
NANGO_SECRET_KEY=nango_sec_xxxxxxxxxxxxxxxxxxxx
NANGO_BASE_URL=https://api.nango.dev
NANGO_INTEGRATION_ID_HUBSPOT=hubspot
NANGO_CONNECT_SESSION_ENABLED=true
HUBSPOT_INTEGRATION_ENABLED=true
HUBSPOT_READ_ONLY=true

# Outmate Application URLs
OUTMATE_PUBLIC_BASE_URL=http://localhost:8000
OUTMATE_FRONTEND_URL=http://localhost:3000
```

