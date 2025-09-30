# Copyright (c) 2025, itsyosefali and contributors
# For license information, please see license.txt

import frappe
import requests
from frappe import _
@frappe.whitelist()
def refresh_access_token():
	"""
	Refresh the access token using refresh token
	"""
	settings = frappe.get_doc(
		"Zoho Books Settings", "Zoho Books Settings",
	)
	
	if not settings.refresh_token:
		frappe.throw(_("Refresh token not available"))
	
	if not settings.client_id or not settings.client_secret:
		frappe.throw(_("Client ID and Client Secret are not configured"))
	
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


@frappe.whitelist()
def test_connection():
	"""
	Test the Zoho Books API connection
	"""
	settings = frappe.get_doc(
		"Zoho Books Settings", "Zoho Books Settings",
	)
	
	if not settings.access_token:
		frappe.throw(_("Access token not available. Please complete OAuth setup first."))
	
	access_token = settings.get_password("access_token")
	
	url = "https://www.zohoapis.com/books/v3/organizations"
	headers = {
		"Authorization": f"Zoho-oauthtoken {access_token}"
	}
	
	try:
		response = requests.get(url, headers=headers)
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

