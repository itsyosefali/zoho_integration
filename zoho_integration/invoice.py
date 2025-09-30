# Copyright (c) 2025, itsyosefali and contributors
# For license information, please see license.txt

import frappe
import requests
import json
from frappe import _


@frappe.whitelist()
def create_zoho_contact(customer_name, email=None, phone=None, mobile=None, company_name=None):
	"""
	Create a contact in Zoho Books/Invoice if it doesn't exist
	"""
	settings = frappe.get_doc("Zoho Books Settings", "Zoho Books Settings")
	
	if not settings.access_token:
		frappe.log_error(
			title="Zoho Integration Issue",
			message="Access token not available for creating contact"
		)
		return None
	
	access_token = settings.get_password("access_token")
	organization_id = settings.organization_id
	
	if not organization_id:
		frappe.log_error(
			title="Zoho Integration Issue",
			message="Organization ID not configured"
		)
		return None
	
	url = "https://www.zohoapis.com/books/v3/contacts"
	headers = {
		"Authorization": f"Zoho-oauthtoken {access_token}",
		"X-com-zoho-books-organizationid": str(organization_id),
		"Content-Type": "application/json"
	}
	
	# Prepare contact data
	contact_data = {
		"contact_name": customer_name,
		"contact_type": "customer",
		"customer_sub_type": "business" if company_name else "individual"
	}
	
	if email:
		contact_data["email"] = email
	if phone:
		contact_data["phone"] = phone
	if mobile:
		contact_data["mobile"] = mobile
	if company_name:
		contact_data["company_name"] = company_name
		contact_data["customer_name"] = company_name
		contact_data["vendor_name"] = company_name
	
	try:
		response = requests.post(url, headers=headers, data=json.dumps(contact_data))
		
		if response.status_code == 201:
			contact_response = response.json()
			contact_id = contact_response.get("contact", {}).get("contact_id")
			
			frappe.log_error(
				title="Zoho Contact Created",
				message=f"Contact created successfully: {customer_name} (ID: {contact_id})"
			)
			
			return contact_id
		else:
			frappe.log_error(
				title="Zoho Integration Issue",
				message=f"Failed to create contact: {response.status_code} - {response.text}"
			)
			return None
			
	except Exception as e:
		frappe.log_error(
			title="Zoho Integration Issue",
			message=f"Error creating contact: {str(e)}"
		)
		return None


@frappe.whitelist()
def find_zoho_contact_id(customer_name, email=None):
	"""
	Find existing contact ID in Zoho Books
	"""
	settings = frappe.get_doc("Zoho Books Settings", "Zoho Books Settings")
	
	if not settings.access_token:
		return None
	
	access_token = settings.get_password("access_token")
	organization_id = settings.organization_id
	
	if not organization_id:
		return None
	
	url = "https://www.zohoapis.com/books/v3/contacts"
	headers = {
		"Authorization": f"Zoho-oauthtoken {access_token}",
		"X-com-zoho-books-organizationid": str(organization_id)
	}
	
	params = {
		"per_page": 200,
		"search_text": customer_name
	}
	
	try:
		response = requests.get(url, headers=headers, params=params)
		
		if response.status_code == 200:
			contacts_data = response.json()
			contacts = contacts_data.get("contacts", [])
			
			# Search for exact match by name or email
			for contact in contacts:
				if (contact.get("contact_name") == customer_name or 
					(email and contact.get("email") == email)):
					return contact.get("contact_id")
			
			return None
		else:
			frappe.log_error(
				title="Zoho Integration Issue",
				message=f"Failed to search contacts: {response.status_code} - {response.text}"
			)
			return None
			
	except Exception as e:
		frappe.log_error(
			title="Zoho Integration Issue",
			message=f"Error searching contacts: {str(e)}"
		)
		return None


@frappe.whitelist()
def send_invoice_to_zoho(invoice_id):
	"""
	Send invoice from ERPNext to Zoho Books/Invoice
	"""
	try:
		# Get the invoice document
		invoice_doc = frappe.get_doc("Sales Invoice", invoice_id)
		
		# Get customer details
		customer_doc = frappe.get_doc("Customer", invoice_doc.customer)
		
		# Find or create Zoho contact
		zoho_contact_id = find_zoho_contact_id(
			customer_doc.customer_name, 
			customer_doc.email_id
		)
		
		if not zoho_contact_id:
			# Create new contact in Zoho
			zoho_contact_id = create_zoho_contact(
				customer_name=customer_doc.customer_name,
				email=customer_doc.email_id,
				phone=customer_doc.mobile_no,
				mobile=customer_doc.mobile_no,
				company_name=customer_doc.customer_name if customer_doc.customer_type == "Company" else None
			)
		
		if not zoho_contact_id:
			frappe.log_error(
				title="Zoho Integration Issue",
				message=f"Could not find or create Zoho contact for customer: {customer_doc.customer_name}"
			)
			return {"status": "error", "message": "Could not find or create Zoho contact"}
		
		# Create invoice in Zoho
		invoice_result = create_zoho_invoice(invoice_doc, zoho_contact_id)
		
		if invoice_result.get("status") == "success":
			# Update ERPNext invoice with Zoho invoice ID and sync status
			invoice_doc.db_set("zoho_invoice_id", invoice_result.get("invoice_id"))
			invoice_doc.db_set("zoho_invoice_number", invoice_result.get("invoice_number"))
			invoice_doc.db_set("zoho_sync_status", "Synced")
			frappe.db.commit()
			
			return {
				"status": "success",
				"message": f"Invoice sent to Zoho successfully (ID: {invoice_result.get('invoice_id')})",
				"zoho_invoice_id": invoice_result.get("invoice_id"),
				"zoho_invoice_number": invoice_result.get("invoice_number")
			}
		else:
			# Set sync status to failed
			invoice_doc.db_set("zoho_sync_status", "Failed")
			frappe.db.commit()
			return invoice_result
			
	except Exception as e:
		# Set sync status to failed
		invoice_doc.db_set("zoho_sync_status", "Failed")
		frappe.db.commit()
		
		frappe.log_error(
			title="Zoho Integration Issue",
			message=f"Error sending invoice to Zoho: {str(e)}"
		)
		return {"status": "error", "message": str(e)}


def create_zoho_invoice(invoice_doc, customer_id):
	"""
	Create invoice in Zoho Books/Invoice
	"""
	settings = frappe.get_doc("Zoho Books Settings", "Zoho Books Settings")
	
	access_token = settings.get_password("access_token")
	organization_id = settings.organization_id
	
	url = "https://www.zohoapis.com/books/v3/invoices"
	headers = {
		"Authorization": f"Zoho-oauthtoken {access_token}",
		"X-com-zoho-books-organizationid": str(organization_id),
		"Content-Type": "application/json"
	}
	
	# Add query parameter to ignore auto number generation
	params = {
		"ignore_auto_number_generation": "true"
	}
	
	# Prepare line items
	line_items = []
	for item in invoice_doc.items:
		line_item = {
			"item_id": "",  # You might want to map ERPNext items to Zoho items
			"name": item.item_name,
			"description": item.description or item.item_name,
			"rate": float(item.rate),
			"quantity": float(item.qty),
			"unit": item.uom or "Nos"
		}
		line_items.append(line_item)
	
	# Prepare invoice data
	invoice_data = {
		"customer_id": customer_id,
		"date": invoice_doc.posting_date.strftime("%Y-%m-%d"),
		"invoice_number": invoice_doc.name,
		"reference_number": invoice_doc.name,
		"line_items": line_items,
		"notes": invoice_doc.remarks or "",
		"terms": "Thank you for your business!",
		"payment_terms": 0,  # Due on receipt
		"payment_terms_label": "Due on Receipt"
	}
	
	# Add due date if available
	if invoice_doc.due_date:
		invoice_data["due_date"] = invoice_doc.due_date.strftime("%Y-%m-%d")
	
	# Add discount if applicable
	if invoice_doc.discount_amount and invoice_doc.discount_amount > 0:
		invoice_data["discount"] = float(invoice_doc.discount_amount)
		invoice_data["is_discount_before_tax"] = True
	
	# Add tax information
	if invoice_doc.total_taxes_and_charges and invoice_doc.total_taxes_and_charges > 0:
		invoice_data["tax_total"] = float(invoice_doc.total_taxes_and_charges)
	
	try:
		response = requests.post(url, headers=headers, params=params, data=json.dumps(invoice_data))
		
		if response.status_code == 201:
			invoice_response = response.json()
			zoho_invoice_id = invoice_response.get("invoice", {}).get("invoice_id")
			zoho_invoice_number = invoice_response.get("invoice", {}).get("invoice_number")
			
			frappe.log_error(
				title="Zoho Invoice Created",
				message=f"Invoice created successfully: {invoice_doc.name} -> Zoho #{zoho_invoice_number} (ID: {zoho_invoice_id})"
			)
			
			return {
				"status": "success",
				"invoice_id": zoho_invoice_id,
				"invoice_number": zoho_invoice_number
			}
		else:
			error_msg = f"Failed to create invoice: {response.status_code} - {response.text}"
			frappe.log_error(
				title="Zoho Integration Issue",
				message=error_msg
			)
			return {"status": "error", "message": error_msg}
			
	except Exception as e:
		error_msg = f"Error creating invoice: {str(e)}"
		frappe.log_error(
			title="Zoho Integration Issue",
			message=error_msg
		)
		return {"status": "error", "message": error_msg}


def send_invoice_on_update(doc, method):
	"""
	Hook function to automatically send invoice to Zoho when created or updated
	"""
	try:
		# Only send if not already sent to Zoho and invoice is submitted
		if not doc.zoho_invoice_id :
			# Check if Zoho integration is enabled
			settings = frappe.get_doc("Zoho Books Settings", "Zoho Books Settings")
			if settings.enabled:
				# Set initial sync status
				doc.db_set("zoho_sync_status", "Not Synced")
				
				result = send_invoice_to_zoho(doc.name)
				
				if result.get("status") == "success":
					frappe.msgprint(f"Invoice sent to Zoho successfully: {result.get('message')}")
				else:
					frappe.msgprint(f"Failed to send invoice to Zoho: {result.get('message')}", alert=True)
					
	except Exception as e:
		frappe.log_error(
			title="Zoho Integration Hook Error",
			message=f"Error in send_invoice_on_update hook: {str(e)}"
		)