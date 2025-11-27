# Copyright (c) 2025, itsyosefali and contributors
# For license information, please see license.txt

import frappe
import requests
import json
from frappe import _


@frappe.whitelist()
def get_zoho_customers_simple(organization_id=None, page=1, per_page=200):
	"""
	Simple version to get customers from Zoho Invoice without complex filtering
	"""
	settings = frappe.get_doc("Zoho Books Settings", "Zoho Books Settings")
	
	if not settings.access_token:
		frappe.throw(_("Access token not available. Please complete OAuth setup first."))
	
	# Get the decrypted access token
	access_token = settings.get_password("access_token")
	
	# Use organization_id from settings if not provided
	if not organization_id:
		organization_id = settings.organization_id
	
	if not organization_id:
		frappe.throw(_("Organization ID not configured"))
	
	url = "https://www.zohoapis.com/books/v3/contacts"
	headers = {
		"Authorization": f"Zoho-oauthtoken {access_token}",
		"X-com-zoho-books-organizationid": str(organization_id)
	}
	
	params = {
		"page": page,
		"per_page": per_page,
		"contact_type": "customer"  # Only fetch customer-type contacts
	}
	
	try:
		response = requests.get(url, headers=headers, params=params)
		
		response.raise_for_status()
		
		customers_data = response.json()
		all_contacts = customers_data.get("contacts", [])
		
		# API already filters by contact_type="customer", but double-check to ensure only customers are returned
		# Use contact_id as the reference document from Zoho
		all_customers = []
		for contact in all_contacts:
			# Ensure contact_type is customer and has a valid contact_id (reference document)
			if contact.get("contact_type") == "customer" and contact.get("contact_id"):
				all_customers.append(contact)
		
		return {
			"status": "success",
			"message": f"Customers retrieved successfully. Found {len(all_customers)} customers",
			"customers": all_customers,
			"page_context": customers_data.get("page_context", {}),
			"total_customers": len(all_customers)
		}
		
	except requests.exceptions.HTTPError as e:
		error_message = f"HTTP {e.response.status_code}: {e.response.text}"
		frappe.log_error(
			title="Zoho Integration Issue",
			message=f"HTTP Error getting customers from Zoho: {error_message}\nURL: {url}\nParams: {params}"
		)
		frappe.throw(_("Failed to get customers from Zoho Books: {0}").format(error_message))
	except requests.exceptions.RequestException as e:
		frappe.log_error(
			title="Zoho Integration Issue",
			message=f"Request Error getting customers from Zoho: {str(e)}"
		)
		frappe.throw(_("Failed to get customers from Zoho Books"))


@frappe.whitelist()
def get_zoho_customers(organization_id=None, page=1, per_page=200, sync_from_date=None, only_new=False):
	"""
	Get customers from Zoho Invoice
	
	Args:
		organization_id: Zoho organization ID
		page: Page number for pagination
		per_page: Number of customers per page
		sync_from_date: Date to filter customers from (YYYY-MM-DD format)
		only_new: If True, only fetch customers that don't exist in ERPNext yet
	"""
	settings = frappe.get_doc("Zoho Books Settings", "Zoho Books Settings")
	
	if not settings.access_token:
		frappe.throw(_("Access token not available. Please complete OAuth setup first."))
	
	# Get the decrypted access token
	access_token = settings.get_password("access_token")
	
	# Use organization_id from settings if not provided
	if not organization_id:
		organization_id = settings.organization_id
	
	if not organization_id:
		frappe.throw(_("Organization ID not configured"))
	
	url = "https://www.zohoapis.com/books/v3/contacts"
	headers = {
		"Authorization": f"Zoho-oauthtoken {access_token}",
		"X-com-zoho-books-organizationid": str(organization_id)
	}
	
	params = {
		"page": page,
		"per_page": per_page,
		"contact_type": "customer"  # Only fetch customer-type contacts
	}
	
	try:
		# Log the request details for debugging
		frappe.log_error(
			title="Zoho Customer API Debug",
			message=f"Request URL: {url}\nHeaders: {headers}\nParams: {params}"
		)
		
		response = requests.get(url, headers=headers, params=params)
		
		# Log response details for debugging
		frappe.log_error(
			title="Zoho Customer API Debug",
			message=f"Response Status: {response.status_code}\nResponse Text: {response.text[:500]}"
		)
		
		response.raise_for_status()
		
		customers_data = response.json()
		all_contacts = customers_data.get("contacts", [])
		
		# API already filters by contact_type="customer", but double-check to ensure only customers are returned
		# Use contact_id as the reference document from Zoho
		all_customers = []
		for contact in all_contacts:
			# Ensure contact_type is customer and has a valid contact_id (reference document)
			if contact.get("contact_type") == "customer" and contact.get("contact_id"):
				all_customers.append(contact)
		
		# Filter out customers that already exist in ERPNext if only_new is True
		# Use zoho_contact_id (reference document) to check for existing customers
		if only_new:
			new_customers = []
			for customer in all_customers:
				zoho_contact_id = customer.get("contact_id")  # Reference document from Zoho
				if zoho_contact_id and not frappe.db.exists("Customer", {"zoho_contact_id": zoho_contact_id}):
					new_customers.append(customer)
			all_customers = new_customers
		
		return {
			"status": "success",
			"message": f"Customers retrieved successfully. Found {len(all_customers)} customers",
			"customers": all_customers,
			"page_context": customers_data.get("page_context", {}),
			"total_customers": len(all_customers),
			"only_new_filter": only_new
		}
		
	except requests.exceptions.HTTPError as e:
		error_message = f"HTTP {e.response.status_code}: {e.response.text}"
		frappe.log_error(
			title="Zoho Integration Issue",
			message=f"HTTP Error getting customers from Zoho: {error_message}\nURL: {url}\nParams: {params}"
		)
		frappe.throw(_("Failed to get customers from Zoho Books: {0}").format(error_message))
	except requests.exceptions.RequestException as e:
		frappe.log_error(
			title="Zoho Integration Issue",
			message=f"Request Error getting customers from Zoho: {str(e)}"
		)
		frappe.throw(_("Failed to get customers from Zoho Books"))


@frappe.whitelist()
def sync_customers_from_zoho_to_erpnext(organization_id=None, page=1, per_page=None, sync_from_date=None, only_new=True):
	"""
	Sync customers from Zoho Invoice to ERPNext
	
	Args:
		organization_id: Zoho organization ID
		page: Page number for pagination
		per_page: Number of customers per page
		sync_from_date: Date to filter customers from (YYYY-MM-DD format)
		only_new: If True, only sync customers that don't exist in ERPNext yet
	"""
	settings = frappe.get_doc("Zoho Books Settings", "Zoho Books Settings")
	
	if not settings.access_token:
		frappe.throw(_("Access token not available. Please complete OAuth setup first."))
	
	# Use organization_id from settings if not provided
	if not organization_id:
		organization_id = settings.organization_id
	
	if not organization_id:
		frappe.throw(_("Organization ID not configured"))
	
	# Use settings for pagination and date filtering
	if per_page is None:
		per_page = 50  # Default page size
	
	if sync_from_date is None:
		sync_from_date = settings.sync_from_date
	
	# Get customers from Zoho Books
	zoho_customers_response = get_zoho_customers_simple(organization_id, page, per_page)
	zoho_customers = zoho_customers_response.get("customers", [])
	
	# Log how many customers were fetched from Zoho
	total_fetched = len(zoho_customers)
	frappe.log_error(
		title="Zoho Customer Sync Debug",
		message=f"Fetched {total_fetched} customers from Zoho (contact_type=customer)"
	)
	
	# Filter out customers that already exist in ERPNext if only_new is True
	# Use zoho_contact_id (reference document) to check for existing customers
	existing_count = 0
	if only_new:
		new_customers = []
		for customer in zoho_customers:
			zoho_contact_id = customer.get("contact_id")  # Reference document from Zoho
			if zoho_contact_id:
				if frappe.db.exists("Customer", {"zoho_contact_id": zoho_contact_id}):
					existing_count += 1
				else:
					new_customers.append(customer)
			else:
				# Log customers without contact_id
				frappe.log_error(
					title="Zoho Customer Sync Warning",
					message=f"Customer {customer.get('contact_name')} has no contact_id (reference document), skipping"
				)
		zoho_customers = new_customers
		frappe.log_error(
			title="Zoho Customer Sync Debug",
			message=f"After filtering: {len(zoho_customers)} new customers, {existing_count} already exist"
		)
	else:
		# When only_new=False, count existing customers for reporting
		for customer in zoho_customers:
			zoho_contact_id = customer.get("contact_id")  # Reference document from Zoho
			if zoho_contact_id and frappe.db.exists("Customer", {"zoho_contact_id": zoho_contact_id}):
				existing_count += 1
		frappe.log_error(
			title="Zoho Customer Sync Debug",
			message=f"Processing all customers: {len(zoho_customers)} total, {existing_count} already exist (will be updated)"
		)
	
	synced_count = 0
	updated_count = 0
	error_count = 0
	
	for zoho_customer in zoho_customers:
		try:
			# Map Zoho customer to ERPNext customer format
			erpnext_customer_data = {
				"doctype": "Customer",
				"customer_name": zoho_customer.get("contact_name"),
				"customer_type": "Individual" if zoho_customer.get("contact_type") == "customer" else "Company",
				"customer_group": "All Customer Groups",
				"territory": "All Territories",
				"disabled": 0 if zoho_customer.get("status") == "active" else 1,
				"is_internal_customer": 0,
				"default_currency": zoho_customer.get("currency_code", "AED"),  # Fetch from Zoho, default to AED (UAE Dirham)
				"default_price_list": "Standard Selling",
				"zoho_contact_id": zoho_customer.get("contact_id"),  # Reference document from Zoho
				"zoho_contact_name": zoho_customer.get("contact_name"),
				"zoho_contact_type": zoho_customer.get("contact_type"),
				"zoho_company_name": zoho_customer.get("company_name", ""),
				"zoho_first_name": zoho_customer.get("first_name", ""),
				"zoho_last_name": zoho_customer.get("last_name", ""),
				"zoho_email": zoho_customer.get("email", ""),
				"zoho_phone": zoho_customer.get("phone", ""),
				"zoho_mobile": zoho_customer.get("mobile", ""),
				"zoho_fax": zoho_customer.get("fax", ""),
				"zoho_website": zoho_customer.get("website", ""),
				"zoho_billing_address": zoho_customer.get("billing_address", ""),
				"zoho_shipping_address": zoho_customer.get("shipping_address", ""),
				"zoho_payment_terms": zoho_customer.get("payment_terms", 0),
				"zoho_payment_terms_label": zoho_customer.get("payment_terms_label", ""),
				"zoho_currency_id": zoho_customer.get("currency_id", ""),
				"zoho_currency_code": zoho_customer.get("currency_code", ""),
				"zoho_currency_symbol": zoho_customer.get("currency_symbol", ""),
				"zoho_currency_format": zoho_customer.get("currency_format", ""),
				"zoho_price_precision": zoho_customer.get("price_precision", 2),
				"zoho_outstanding_receivable_amount": zoho_customer.get("outstanding_receivable_amount", 0),
				"zoho_outstanding_payable_amount": zoho_customer.get("outstanding_payable_amount", 0),
				"zoho_unused_credits_receivable_amount": zoho_customer.get("unused_credits_receivable_amount", 0),
				"zoho_unused_credits_payable_amount": zoho_customer.get("unused_credits_payable_amount", 0),
				"zoho_last_synced": frappe.utils.now()
			}
			
			# Check if customer already exists in ERPNext by zoho_contact_id (reference document from Zoho)
			existing_customer_by_zoho_id = None
			zoho_contact_id = zoho_customer.get("contact_id")  # Reference document from Zoho
			if zoho_contact_id:
				existing_customer_by_zoho_id = frappe.db.exists("Customer", {"zoho_contact_id": zoho_contact_id})
			
			# Also check by customer name to prevent duplicates
			existing_customer_by_name = None
			if zoho_customer.get("contact_name"):
				existing_customer_by_name = frappe.db.exists("Customer", {"customer_name": zoho_customer.get("contact_name")})
			
			# Use whichever existing customer we found
			existing_customer = existing_customer_by_zoho_id or existing_customer_by_name
			
			if existing_customer:
				# Update existing customer
				customer_doc = frappe.get_doc("Customer", existing_customer)
				customer_doc.update(erpnext_customer_data)
				customer_doc.save()
				updated_count += 1
				frappe.msgprint(f"Updated customer: {zoho_customer.get('contact_name')}")
			else:
				# Double-check before creating to prevent race conditions
				# Use zoho_contact_id (reference document) to verify customer doesn't exist
				zoho_contact_id = zoho_customer.get("contact_id")  # Reference document from Zoho
				if zoho_contact_id and frappe.db.exists("Customer", {"zoho_contact_id": zoho_contact_id}):
					frappe.msgprint(f"Customer {zoho_customer.get('contact_name')} already exists, skipping creation")
					continue
				
				if zoho_customer.get("contact_name") and frappe.db.exists("Customer", {"customer_name": zoho_customer.get("contact_name")}):
					frappe.msgprint(f"Customer {zoho_customer.get('contact_name')} already exists, skipping creation")
					continue
				
				# Create new customer
				customer_doc = frappe.get_doc(erpnext_customer_data)
				customer_doc.insert()
				synced_count += 1
				frappe.msgprint(f"Created customer: {zoho_customer.get('contact_name')}")
			
		except Exception as e:
			error_message = str(e)
			
			# Log detailed error information
			frappe.log_error(
				title="Zoho Integration Issue",
				message=f"Failed to sync customer {zoho_customer.get('contact_name')} from Zoho: {error_message}\nCustomer data: {zoho_customer}"
			)
			
			# Show user-friendly error message
			if "required" in error_message.lower():
				frappe.msgprint(f"Error with customer {zoho_customer.get('contact_name')}: Required field missing - {error_message}")
			elif "duplicate" in error_message.lower():
				frappe.msgprint(f"Error with customer {zoho_customer.get('contact_name')}: Duplicate customer - {error_message}")
			else:
				frappe.msgprint(f"Error with customer {zoho_customer.get('contact_name')}: {error_message}")
			
			error_count += 1
	
	return {
		"status": "success",
		"message": f"Customers sync completed. Created: {synced_count}, Updated: {updated_count}, Errors: {error_count}",
		"synced_count": synced_count,
		"updated_count": updated_count,
		"error_count": error_count,
		"total_fetched_from_zoho": total_fetched,
		"existing_customers_skipped": existing_count if only_new else 0,
		"customers_processed": len(zoho_customers) if not only_new else (total_fetched - existing_count)
	}


@frappe.whitelist()
def push_customer_to_zoho(customer_name):
	"""
	Push a customer from ERPNext to Zoho Books
	"""
	settings = frappe.get_doc("Zoho Books Settings", "Zoho Books Settings")
	
	if not settings.access_token:
		frappe.throw(_("Access token not available. Please complete OAuth setup first."))
	
	# Get the decrypted access token
	access_token = settings.get_password("access_token")
	organization_id = settings.organization_id
	
	if not organization_id:
		frappe.throw(_("Organization ID not configured"))
	
	# Get customer from ERPNext
	customer = frappe.get_doc("Customer", customer_name)
	
	# Check if customer already exists in Zoho
	if customer.zoho_contact_id:
		# Update existing contact
		url = f"https://www.zohoapis.com/books/v3/contacts/{customer.zoho_contact_id}"
		method = "PUT"
		action = "updated"
	else:
		# Create new contact
		url = "https://www.zohoapis.com/books/v3/contacts"
		method = "POST"
		action = "created"
	
	headers = {
		"Authorization": f"Zoho-oauthtoken {access_token}",
		"X-com-zoho-books-organizationid": str(organization_id),
		"Content-Type": "application/json"
	}
	
	# Prepare contact data
	contact_data = {
		"contact_name": customer.customer_name,
		"contact_type": "customer",
		"customer_sub_type": "business" if customer.customer_type == "Company" else "individual",
		"currency_code": customer.default_currency or "AED"
	}
	
	# Add optional fields if available
	if customer.email_id:
		contact_data["email"] = customer.email_id
	if customer.mobile_no:
		contact_data["mobile"] = customer.mobile_no
	if customer.primary_address:
		address = frappe.get_doc("Address", customer.primary_address)
		if address:
			billing_address = {
				"address": address.address_line1 or "",
				"street2": address.address_line2 or "",
				"city": address.city or "",
				"state": address.state or "",
				"zip": address.pincode or "",
				"country": address.country or ""
			}
			contact_data["billing_address"] = billing_address
	
	try:
		if method == "POST":
			response = requests.post(url, headers=headers, data=json.dumps(contact_data))
		else:
			response = requests.put(url, headers=headers, data=json.dumps(contact_data))
		
		response.raise_for_status()
		
		contact_response = response.json()
		zoho_contact = contact_response.get("contact", {})
		zoho_contact_id = zoho_contact.get("contact_id")
		
		# Update customer with Zoho contact ID
		if zoho_contact_id:
			customer.zoho_contact_id = zoho_contact_id
			customer.zoho_contact_name = zoho_contact.get("contact_name")
			customer.zoho_last_synced = frappe.utils.now()
			customer.save()
			
			frappe.msgprint(_(f"Customer {action} in Zoho Books successfully! Contact ID: {zoho_contact_id}"))
			return {
				"status": "success",
				"message": f"Customer {action} successfully",
				"zoho_contact_id": zoho_contact_id
			}
		else:
			frappe.throw(_("Failed to get contact ID from Zoho response"))
	
	except requests.exceptions.HTTPError as e:
		error_message = f"HTTP {e.response.status_code}: {e.response.text}"
		frappe.log_error(
			title="Zoho Customer Push Failed",
			message=f"Failed to push customer {customer_name} to Zoho: {error_message}"
		)
		frappe.throw(_(f"Failed to push customer to Zoho Books: {error_message}"))
	except Exception as e:
		frappe.log_error(
			title="Zoho Customer Push Failed",
			message=f"Error pushing customer {customer_name} to Zoho: {str(e)}"
		)
		frappe.throw(_(f"Failed to push customer to Zoho Books: {str(e)}"))


def push_customer_on_submit(doc, method):
	"""
	Hook function to automatically push customer to Zoho when submitted/saved
	"""
	try:
		# Check if Zoho integration is enabled
		settings = frappe.get_doc("Zoho Books Settings", "Zoho Books Settings")
		if settings.enabled and settings.auto_sync_customer:
			# Only push if not already synced to Zoho
			if not doc.zoho_contact_id:
				result = push_customer_to_zoho(doc.name)
				
				if result.get("status") == "success":
					frappe.msgprint(f"Customer synced to Zoho successfully: {result.get('zoho_contact_id')}", alert=True)
				else:
					frappe.log_error(
						title="Zoho Customer Auto-Sync Failed",
						message=f"Failed to auto-sync customer {doc.name} to Zoho: {result.get('message')}"
					)
	except Exception as e:
		frappe.log_error(
			title="Zoho Integration Hook Error",
			message=f"Error in push_customer_on_submit hook: {str(e)}"
		)