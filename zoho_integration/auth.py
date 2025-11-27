# Copyright (c) 2025, itsyosefali and contributors
# For license information, please see license.txt

import frappe
import requests
from frappe import _

def get_valid_access_token():
	"""
	Get a valid access token, automatically refreshing if needed.
	Returns the access token string or None if refresh fails.
	"""
	settings = frappe.get_doc("Zoho Books Settings", "Zoho Books Settings")
	
	if not settings.access_token:
		return None
	
	# Try to refresh the token automatically
	refresh_result = refresh_access_token_internal()
	if refresh_result.get("status") == "success":
		return refresh_result.get("access_token")
	
	# If refresh failed, try using existing token
	# It might still be valid
	return settings.get_password("access_token")

def refresh_access_token_internal():
	"""
	Internal function to refresh access token (without @frappe.whitelist)
	"""
	settings = frappe.get_doc("Zoho Books Settings", "Zoho Books Settings")
	
	if not settings.refresh_token:
		return {
			"status": "error",
			"message": "Refresh token not available"
		}
	
	if not settings.client_id or not settings.client_secret:
		return {
			"status": "error",
			"message": "Client ID and Client Secret are not configured"
		}
	
	client_secret = settings.get_password("client_secret")
	refresh_token = settings.get_password("refresh_token")
	
	url = "https://accounts.zoho.com/oauth/v2/token"
	
	data = {
		"grant_type": "refresh_token",
		"refresh_token": refresh_token,
		"client_id": settings.client_id,
		"client_secret": client_secret
	}
	
	try:
		response = requests.post(url, data=data)
		response.raise_for_status()
		token_data = response.json()
		
		if "access_token" in token_data:
			settings.access_token = token_data.get("access_token")
			settings.save()
			frappe.db.commit()
			
			return {
				"status": "success",
				"message": "Access token refreshed successfully",
				"access_token": token_data.get("access_token")
			}
		else:
			return {
				"status": "error",
				"message": f"Token refresh failed: {token_data.get('error', 'Unknown error')}"
			}
			
	except requests.exceptions.HTTPError as e:
		error_message = f"HTTP {e.response.status_code}: {e.response.text}"
		frappe.log_error(
			title="Zoho Integration Issue",
			message=f"Token refresh HTTP error: {error_message}"
		)
		return {
			"status": "error",
			"message": f"Token refresh failed: {error_message}"
		}
	except requests.exceptions.RequestException as e:
		frappe.log_error(
			title="Zoho Integration Issue",
			message=f"Token refresh request failed: {str(e)}"
		)
		return {
			"status": "error",
			"message": f"Token refresh failed: {str(e)}"
		}

def make_zoho_api_request(method, url, headers=None, params=None, data=None, json_data=None, retry_on_401=True):
	"""
	Make a Zoho API request with automatic token refresh on 401 errors.
	
	Args:
		method: HTTP method (GET, POST, PUT, DELETE)
		url: API endpoint URL
		headers: Request headers (will add Authorization if not present)
		params: URL parameters
		data: Form data
		json_data: JSON data
		retry_on_401: If True, automatically refresh token and retry on 401 error
		
	Returns:
		Response object
	"""
	settings = frappe.get_doc("Zoho Books Settings", "Zoho Books Settings")
	
	if not settings.access_token:
		frappe.throw(_("Access token not available. Please complete OAuth setup first."))
	
	# Get valid access token (will refresh if needed)
	access_token = get_valid_access_token()
	if not access_token:
		frappe.throw(_("Failed to get valid access token. Please refresh manually or complete OAuth setup."))
	
	# Prepare headers
	if headers is None:
		headers = {}
	
	# Add authorization header if not present
	if "Authorization" not in headers:
		headers["Authorization"] = f"Zoho-oauthtoken {access_token}"
	
	# Make the request
	try:
		if method.upper() == "GET":
			response = requests.get(url, headers=headers, params=params)
		elif method.upper() == "POST":
			response = requests.post(url, headers=headers, params=params, data=data, json=json_data)
		elif method.upper() == "PUT":
			response = requests.put(url, headers=headers, params=params, data=data, json=json_data)
		elif method.upper() == "DELETE":
			response = requests.delete(url, headers=headers, params=params)
		else:
			frappe.throw(_("Unsupported HTTP method: {0}").format(method))
		
		# If we get 401 and retry_on_401 is True, refresh token and retry once
		if response.status_code == 401 and retry_on_401:
			frappe.log_error(
				title="Zoho API 401 Error - Auto Refreshing Token",
				message=f"Received 401 error, attempting to refresh token and retry. URL: {url}"
			)
			
			# Refresh token
			refresh_result = refresh_access_token_internal()
			if refresh_result.get("status") == "success":
				# Update access token in headers
				new_access_token = refresh_result.get("access_token")
				headers["Authorization"] = f"Zoho-oauthtoken {new_access_token}"
				
				# Retry the request
				if method.upper() == "GET":
					response = requests.get(url, headers=headers, params=params)
				elif method.upper() == "POST":
					response = requests.post(url, headers=headers, params=params, data=data, json=json_data)
				elif method.upper() == "PUT":
					response = requests.put(url, headers=headers, params=params, data=data, json=json_data)
				elif method.upper() == "DELETE":
					response = requests.delete(url, headers=headers, params=params)
			else:
				# Refresh failed, raise the original 401 error
				response.raise_for_status()
		
		return response
		
	except requests.exceptions.RequestException as e:
		frappe.log_error(
			title="Zoho API Request Error",
			message=f"Request failed: {str(e)}\nURL: {url}\nMethod: {method}"
		)
		raise

@frappe.whitelist()
def refresh_access_token():
	"""
	Refresh the access token using refresh token (public API endpoint)
	"""
	return refresh_access_token_internal()


@frappe.whitelist()
def test_connection():
	"""
	Test the Zoho Books API connection with automatic token refresh
	"""
	settings = frappe.get_doc("Zoho Books Settings", "Zoho Books Settings")
	
	if not settings.access_token:
		frappe.throw(_("Access token not available. Please complete OAuth setup first."))
	
	url = "https://www.zohoapis.com/books/v3/organizations"
	
	try:
		response = make_zoho_api_request("GET", url)
		response.raise_for_status()
		
		organizations = response.json().get("organizations", [])
		
		if organizations:
			if not settings.organization_id and len(organizations) > 0:
				settings.organization_id = organizations[0].get("organization_id")
				settings.save()
				frappe.db.commit()
		
		return {
			"status": "success",
			"message": "Connection successful",
			"organizations": organizations
		}
		
	except requests.exceptions.RequestException as e:
		frappe.log_error(
			title="Zoho Integration Issue",
			message=f"API connection test failed: {str(e)}"
		)
		frappe.throw(_("Failed to connect to Zoho Books API"))

@frappe.whitelist(allow_guest=True)
def get_authorization_url():
	"""
	Generate the authorization URL for Zoho Books OAuth
	"""
	settings = frappe.get_doc(
		"Zoho Books Settings", "Zoho Books Settings",
	)
	
	if not settings.client_id:
		frappe.throw(_("Client ID is not configured"))
	
	if not settings.redirect_url:
		frappe.throw(_("Redirect URL is not configured"))
	
	params = {
		"scope": "ZohoBooks.fullaccess.all",
		"client_id": settings.client_id,
		"response_type": "code",
		"redirect_uri": settings.redirect_url,
		"access_type": "offline"
	}
	
	auth_url = f"https://accounts.zoho.com/oauth/v2/auth?scope={params['scope']}&client_id={params['client_id']}&response_type={params['response_type']}&redirect_uri={params['redirect_uri']}&access_type={params['access_type']}"
	
	return {
		"authorization_url": auth_url,
		"message": "Please visit the authorization URL to complete OAuth setup"
	}

@frappe.whitelist(allow_guest=True)
def callback(code=None, error=None):
	"""
	Handle OAuth callback from Zoho Books
	"""
	if error:
		frappe.throw(_("OAuth authorization failed: {0}").format(error))
	
	if not code:
		frappe.throw(_("Authorization code not received"))
	
	frappe.log_error(
		title="Zoho Integration Issue",
		message=f"OAuth callback received - code: {code}"
	)
	
	settings = frappe.get_doc(
		"Zoho Books Settings", "Zoho Books Settings",
	)

	if not settings.client_id or not settings.client_secret:
		frappe.throw(_("Client ID and Client Secret are not configured"))
	
	client_secret = settings.get_password("client_secret")
	
	frappe.log_error(
		title="Zoho Integration Issue",
		message=f"OAuth settings - client_id: {settings.client_id}, redirect_url: {settings.redirect_url}"
	)
	token_data = exchange_code_for_token(code, settings.client_id, client_secret, settings.redirect_url)
	
	if token_data:
		settings.access_token = token_data.get("access_token")
		settings.refresh_token = token_data.get("refresh_token")
		settings.save()
		
		frappe.db.commit()
		
		return {
			"status": "success",
			"message": "OAuth setup completed successfully",
			"access_token": token_data.get("access_token"),
			"refresh_token": token_data.get("refresh_token")
		}
	else:
		frappe.throw(_("Failed to exchange authorization code for access token"))

def exchange_code_for_token(code, client_id, client_secret, redirect_uri):
	"""
	Exchange authorization code for access token
	"""
	url = "https://accounts.zoho.com/oauth/v2/token"
	data = {
		"grant_type": "authorization_code",
		"client_id": client_id,
		"client_secret": client_secret,
		"redirect_uri": redirect_uri,
		"code": code
	}
	
	try:
		response = requests.post(url, data=data)
		frappe.log_error(
			title="Zoho Integration Issue",
			message=f"Token exchange response status: {response.status_code}"
		)
		frappe.log_error(
			title="Zoho Integration Issue",
			message=f"Token exchange response text: {response.text}"
		)
		
		response.raise_for_status()
		
		token_data = response.json()
		
		if "access_token" in token_data:
			return token_data
		else:
			frappe.log_error(
				title="Zoho Integration Issue",
				message=f"Token exchange failed: {token_data}"
			)
			return None
			
	except requests.exceptions.RequestException as e:
		frappe.log_error(
			title="Zoho Integration Issue",
			message=f"Token exchange request failed: {str(e)}"
		)
		return None
