# Zoho Books OAuth Integration Setup

This document explains how to set up OAuth integration with Zoho Books for ERPNext.

## Prerequisites

1. A Zoho Books account
2. Access to Zoho Developer Console
3. ERPNext instance with Zoho Integration app installed

## Step 1: Create Zoho Connected App

1. Go to [Zoho Developer Console](https://api-console.zoho.com/)
2. Click "Add Client" and select "Server-based Applications"
3. Fill in the following details:
   - **Client Name**: ERPNext Integration
   - **Homepage URL**: `http://antpos.local:8000`
   - **Authorized Redirect URIs**: `http://antpos.local:8000/api/method/zoho_integration.auth.callback`
4. Click "Create"
5. Note down the **Client ID** and **Client Secret**

## Step 2: Configure ERPNext

1. Go to **Zoho Books Settings** in ERPNext
2. Enter your **Client ID** and **Client Secret** from Step 1
3. Set the **Redirect URL** to: `http://antpos.local:8000/api/method/zoho_integration.auth.callback`
4. Click **Setup OAuth** button
5. Complete the OAuth authorization in the popup window
6. The system will automatically:
   - Generate access and refresh tokens
   - Detect your organization ID
   - Test the API connection

## Step 3: Test the Integration

1. Click **Test Connection** to verify the setup
2. Use **Refresh Token** to get a new access token if needed
3. Use **Revoke Token** to disconnect the integration

## API Endpoints

The following API endpoints are available:

- `GET /api/method/zoho_integration.auth.get_authorization_url` - Get OAuth authorization URL
- `GET /api/method/zoho_integration.auth.callback` - OAuth callback handler
- `POST /api/method/zoho_integration.auth.refresh_access_token` - Refresh access token
- `POST /api/method/zoho_integration.auth.test_connection` - Test API connection
- `POST /api/method/zoho_integration.auth.revoke_token` - Revoke tokens

## OAuth Flow

1. **Authorization**: User clicks "Setup OAuth" → redirected to Zoho authorization page
2. **Callback**: Zoho redirects back with authorization code
3. **Token Exchange**: System exchanges code for access and refresh tokens
4. **API Access**: System can now make authenticated API calls to Zoho Books

## Token Management

- **Access Token**: Valid for 1 hour, used for API calls
- **Refresh Token**: Long-lived, used to get new access tokens
- **Auto-refresh**: System can automatically refresh access tokens when needed

## Troubleshooting

### Common Issues

1. **Invalid Client ID/Secret**: Verify credentials in Zoho Developer Console
2. **Invalid Redirect URI**: Ensure the redirect URI matches exactly
3. **Token Expired**: Use the refresh token to get a new access token
4. **API Connection Failed**: Check if the access token is valid and not expired

### Error Messages

- `Client ID is required`: Enter your Client ID from Zoho Developer Console
- `Client Secret is required`: Enter your Client Secret from Zoho Developer Console
- `OAuth authorization failed`: Check your redirect URI configuration
- `Failed to exchange authorization code`: Verify your Client ID and Secret

## Security Notes

- Client Secret is stored as a password field (encrypted)
- Access and Refresh tokens are stored as password fields (encrypted)
- All API calls use HTTPS
- Tokens can be revoked at any time

## Next Steps

After successful OAuth setup, you can:
1. Sync customers from ERPNext to Zoho Books
2. Sync items/products between systems
3. Create invoices in Zoho Books from ERPNext
4. Set up automated data synchronization
