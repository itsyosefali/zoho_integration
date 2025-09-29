# Copyright (c) 2025, itsyosefali and contributors
# For license information, please see license.txt

import frappe
from frappe.integrations.utils import *
from frappe.model.document import Document
from frappe import _


class ZohoBooksSettings(Document):
	
	def validate(self):
		if self.enabled:
			self.validate_oauth_setup()
	
	def validate_oauth_setup(self):
		"""Validate OAuth setup"""
		if not self.client_id:
			frappe.throw(_("Client ID is required"))
		
		if not self.client_secret:
			frappe.throw(_("Client Secret is required"))
		
		if not self.redirect_url:
			frappe.throw(_("Redirect URL is required"))
		
		# If we have access token, test the connection
		if self.access_token:
			self.test_api_connection()
	
	def test_api_connection(self):
		"""Test API connection using current access token"""
		import requests
		
		url = "https://www.zohoapis.com/books/v3/organizations"
		headers = {
			"Authorization": f"Zoho-oauthtoken {self.access_token}"
		}
		
		try:
			response = requests.get(url, headers=headers)
			if response.status_code == 200:
				frappe.msgprint(_("API connection successful"))
			else:
				frappe.throw(_("API connection failed. Please check your access token."))
		except Exception as e:
			frappe.throw(_("Failed to test API connection: {0}").format(str(e)))
	
	def get_authorization_url(self):
		"""Get OAuth authorization URL"""
		if not self.redirect_url:
			frappe.throw(_("Redirect URL is not configured"))
		
		return f"https://accounts.zoho.com/oauth/v2/auth?scope=ZohoBooks.fullaccess.all&client_id={self.client_id}&response_type=code&redirect_uri={self.redirect_url}&access_type=offline"
	
	def refresh_access_token(self):
		"""Refresh access token using refresh token"""
		import requests
		
		if not self.refresh_token:
			frappe.throw(_("Refresh token not available"))
		
		url = "https://accounts.zoho.com/oauth/v2/token"
		data = {
			"grant_type": "refresh_token",
			"refresh_token": self.refresh_token,
			"client_id": self.client_id,
			"client_secret": self.client_secret
		}
		
		try:
			response = requests.post(url, data=data)
			response.raise_for_status()
			
			token_data = response.json()
			
			if "access_token" in token_data:
				self.access_token = token_data.get("access_token")
				self.save()
				frappe.db.commit()
				return True
			else:
				frappe.throw(_("Failed to refresh access token"))
				
		except requests.exceptions.RequestException as e:
			frappe.throw(_("Failed to refresh access token: {0}").format(str(e)))

