# Copyright (c) 2025, itsyosefali and contributors
# For license information, please see license.txt

import frappe
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

