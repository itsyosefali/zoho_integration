# Copyright (c) 2025, itsyosefali and contributors
# For license information, please see license.txt

import frappe
import requests
from frappe import _


@frappe.whitelist()
def get_zoho_items(organization_id=None, page=1, per_page=200, sync_from_date=None):
	"""
	Get items from Zoho Books
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
	
	url = "https://www.zohoapis.com/books/v3/items"
	headers = {
		"Authorization": f"Zoho-oauthtoken {access_token}",
		"X-com-zoho-books-organizationid": str(organization_id)
	}
	
	params = {
		"page": page,
		"per_page": per_page
	}
	
	# Note: Date filtering removed to avoid API issues
	# if sync_from_date:
	# 	# Date filtering functionality can be added later if needed
	
	try:
		# Log the request details for debugging
		frappe.log_error(
			title="Zoho Items API Debug",
			message=f"Request URL: {url}\nHeaders: {headers}\nParams: {params}"
		)
		
		response = requests.get(url, headers=headers, params=params)
		response.raise_for_status()
		
		items_data = response.json()
		
		return {
			"status": "success",
			"message": "Items retrieved successfully",
			"items": items_data.get("items", []),
			"page_context": items_data.get("page_context", {})
		}
		
	except requests.exceptions.HTTPError as e:
		error_message = f"HTTP {e.response.status_code}: {e.response.text}"
		frappe.log_error(
			title="Zoho Integration Issue",
			message=f"HTTP Error getting items from Zoho: {error_message}\nURL: {url}\nParams: {params}"
		)
		frappe.throw(_("Failed to get items from Zoho Books: {0}").format(error_message))
	except requests.exceptions.RequestException as e:
		frappe.log_error(
			title="Zoho Integration Issue",
			message=f"Request Error getting items from Zoho: {str(e)}"
		)
		frappe.throw(_("Failed to get items from Zoho Books"))


@frappe.whitelist()
def sync_items_from_zoho_to_erpnext(organization_id=None, page=1, per_page=None, sync_from_date=None):
	"""
	Sync items from Zoho Books to ERPNext
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
	
	# Use settings for pagination and date filtering
	if per_page is None:
		per_page = settings.items_per_page or 50
	
	if sync_from_date is None:
		sync_from_date = settings.sync_from_date
	
	# Get items from Zoho Books
	zoho_items_response = get_zoho_items(organization_id, page, per_page, sync_from_date)
	zoho_items = zoho_items_response.get("items", [])
	
	synced_count = 0
	updated_count = 0
	error_count = 0
	
	for zoho_item in zoho_items:
		try:
			# Ensure item group exists
			item_group = "Zoho Items"  # Default item group for Zoho items
			if not frappe.db.exists("Item Group", item_group):
				frappe.get_doc({
					"doctype": "Item Group",
					"item_group_name": item_group,
					"parent_item_group": "All Item Groups",
					"is_group": 0
				}).insert()
			
			# Ensure UOM exists
			unit = zoho_item.get("unit") or "Nos"  # Default to "Nos" if empty
			if not unit or unit.strip() == "":
				unit = "Nos"
			
			if not frappe.db.exists("UOM", unit):
				frappe.get_doc({
					"doctype": "UOM",
					"uom_name": unit,
					"must_be_whole_number": 1
				}).insert()
			
			# Map Zoho item to ERPNext item format
			erpnext_item_data = {
				"doctype": "Item",
				"item_code": zoho_item.get("sku") or zoho_item.get("item_id"),
				"item_name": zoho_item.get("name"),
				"description": zoho_item.get("description", ""),
				"stock_uom": unit,  # Use the validated unit
				"is_stock_item": 1 if zoho_item.get("item_type") == "inventory" else 0,
				"valuation_rate": zoho_item.get("rate", 0),
				"standard_rate": zoho_item.get("rate", 0),  # This is the selling rate
				"disabled": 0 if zoho_item.get("status") == "active" else 1,
				"is_sales_item": 1 if zoho_item.get("can_be_sold", False) else 0,
				"is_purchase_item": 1 if zoho_item.get("can_be_purchased", False) else 0,
				"item_group": item_group,
				"purchase_uom": unit,  # Use the validated unit
				"sales_uom": unit,     # Use the validated unit
				"is_taxable": zoho_item.get("tax_percentage", 0) > 0,
				"tax_category": "Standard",
				"zoho_item_id": zoho_item.get("item_id"),
				"zoho_sku": zoho_item.get("sku"),
				"zoho_name": zoho_item.get("name"),
				"zoho_account_id": zoho_item.get("account_id"),
				"zoho_purchase_account_id": zoho_item.get("purchase_account_id"),
				"zoho_item_type": zoho_item.get("item_type"),
				"zoho_product_type": zoho_item.get("product_type"),
				"zoho_track_inventory": zoho_item.get("track_inventory", False),
				"zoho_stock_on_hand": zoho_item.get("stock_on_hand", 0),
				"zoho_reorder_level": zoho_item.get("reorder_level", 0) or 0,
				"zoho_last_synced": frappe.utils.now()
			}
			
			# Check if item already exists in ERPNext
			existing_item = frappe.db.exists("Item", {"zoho_item_id": zoho_item.get("item_id")})
			
			if existing_item:
				# Update existing item
				item_doc = frappe.get_doc("Item", existing_item)
				item_doc.update(erpnext_item_data)
				item_doc.save()
				updated_count += 1
				frappe.msgprint(f"Updated item: {zoho_item.get('name')}")
			else:
				# Create new item
				item_doc = frappe.get_doc(erpnext_item_data)
				item_doc.insert()
				synced_count += 1
				frappe.msgprint(f"Created item: {zoho_item.get('name')}")
			
			# Create stock entry for inventory items with stock
			if (zoho_item.get("item_type") == "inventory" and 
				zoho_item.get("stock_on_hand", 0) > 0 and 
				not existing_item):  # Only for new items
				
				try:
					# Create opening stock entry
					stock_entry = frappe.get_doc({
						"doctype": "Stock Entry",
						"stock_entry_type": "Material Receipt",
						"posting_date": frappe.utils.today(),
						"posting_time": frappe.utils.now_datetime().strftime("%H:%M:%S"),
						"purpose": "Material Receipt",
						"items": [{
							"item_code": item_doc.item_code,
							"qty": zoho_item.get("stock_on_hand", 0),
							"t_warehouse": "Stores - ANT",  # Default warehouse
							"basic_rate": zoho_item.get("rate", 0),
							"valuation_rate": zoho_item.get("rate", 0)
						}]
					})
					stock_entry.insert()
					stock_entry.submit()
					frappe.msgprint(f"Created opening stock entry for {zoho_item.get('name')}: {zoho_item.get('stock_on_hand', 0)} units")
					
				except Exception as e:
					frappe.log_error(
						title="Zoho Integration Issue",
						message=f"Failed to create stock entry for {zoho_item.get('name')}: {str(e)}"
					)
					frappe.msgprint(f"Warning: Could not create stock entry for {zoho_item.get('name')}")
			
		except Exception as e:
			error_message = str(e)
			
			# Log detailed error information
			frappe.log_error(
				title="Zoho Integration Issue",
				message=f"Failed to sync item {zoho_item.get('name')} from Zoho: {error_message}\nItem data: {zoho_item}"
			)
			
			# Show user-friendly error message
			if "stock_uom" in error_message:
				frappe.msgprint(f"Error with item {zoho_item.get('name')}: UOM issue - {error_message}")
			elif "UOM" in error_message:
				frappe.msgprint(f"Error with item {zoho_item.get('name')}: Unit of Measure issue - {error_message}")
			elif "required" in error_message.lower():
				frappe.msgprint(f"Error with item {zoho_item.get('name')}: Required field missing - {error_message}")
			else:
				frappe.msgprint(f"Error with item {zoho_item.get('name')}: {error_message}")
			
			error_count += 1
	
	return {
		"status": "success",
		"message": f"Items sync completed. Created: {synced_count}, Updated: {updated_count}, Errors: {error_count}",
		"synced_count": synced_count,
		"updated_count": updated_count,
		"error_count": error_count
	}
