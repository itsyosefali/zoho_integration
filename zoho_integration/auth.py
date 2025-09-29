# Copyright (c) 2025, itsyosefali and contributors
# For license information, please see license.txt

import frappe
import requests
import json
from frappe import _
from frappe.utils import get_url
from urllib.parse import urlencode, quote


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
	
	client_secret = settings.client_secret
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
			frappe.log_error(
				title="Zoho Integration Issue",
				message=f"Token refresh failed: {token_data}"
			)
			frappe.throw(_("Failed to refresh access token"))
			
	except requests.exceptions.RequestException as e:
		frappe.log_error(
			title="Zoho Integration Issue",
			message=f"Token refresh request failed: {str(e)}"
		)
		frappe.throw(_("Failed to refresh access token"))


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


@frappe.whitelist()
def revoke_token():
	"""
	Revoke the current access/refresh token
	"""
	settings = frappe.get_doc(
		"Zoho Books Settings", "Zoho Books Settings",
	)
	
	if not settings.access_token:
		frappe.throw(_("No token to revoke"))
	
	access_token = settings.get_password("access_token")
	
	url = "https://accounts.zoho.com/oauth/v2/token/revoke"
	data = {
		"token": access_token
	}
	
	try:
		response = requests.post(url, data=data)
		response.raise_for_status()
		
		settings.access_token = ""
		settings.refresh_token = ""
		settings.save()
		frappe.db.commit()
		
		return {
			"status": "success",
			"message": "Token revoked successfully"
		}
		
	except requests.exceptions.RequestException as e:
		frappe.log_error(
			title="Zoho Integration Issue",
			message=f"Token revocation failed: {str(e)}"
		)
		frappe.throw(_("Failed to revoke token"))
