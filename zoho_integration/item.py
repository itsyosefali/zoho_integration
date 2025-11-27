# Copyright (c) 2025, itsyosefali and contributors
# For license information, please see license.txt

import frappe
import requests
import json
from frappe import _
from zoho_integration.auth import make_zoho_api_request, get_valid_access_token


@frappe.whitelist()
def get_zoho_items(organization_id=None, page=1, per_page=200, sync_from_date=None):
	"""
	Get items from Zoho Books
	"""
	settings = frappe.get_doc("Zoho Books Settings", "Zoho Books Settings")
	
	if not settings.access_token:
		frappe.throw(_("Access token not available. Please complete OAuth setup first."))
	
	# Use organization_id from settings if not provided
	if not organization_id:
		organization_id = settings.organization_id
	
	if not organization_id:
		frappe.throw(_("Organization ID not configured"))
	
	url = "https://www.zohoapis.com/books/v3/items"
	headers = {
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
		response = make_zoho_api_request("GET", url, headers=headers, params=params)
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
			# Zoho Fields Mapping:
			# - rate: Selling Price (maps to standard_rate)
			# - purchase_rate: Cost Price (maps to valuation_rate)
			# - inventory_valuation_method: FIFO/LIFO
			
			purchase_rate = zoho_item.get("purchase_rate", 0) or 0
			selling_rate = zoho_item.get("rate", 0) or 0
			
			# Map inventory valuation method from Zoho to ERPNext
			zoho_valuation = zoho_item.get("inventory_valuation_method", "").upper()
			erpnext_valuation = "FIFO"  # Default
			if "LIFO" in zoho_valuation:
				erpnext_valuation = "LIFO"
			elif "FIFO" in zoho_valuation:
				erpnext_valuation = "FIFO"
			elif "AVERAGE" in zoho_valuation or "WEIGHTED" in zoho_valuation:
				erpnext_valuation = "Moving Average"
			
			# Check if this is a new item or existing
			existing_item = frappe.db.exists("Item", {"zoho_item_id": zoho_item.get("item_id")})
			
			# For new items, always maintain stock. For existing items, keep their current setting
			is_stock_item = 1  # Default to maintain stock for all new items
			if existing_item:
				# For existing items, keep their current stock setting
				is_stock_item = frappe.db.get_value("Item", existing_item, "is_stock_item") or 1
			
			erpnext_item_data = {
				"doctype": "Item",
				"item_code": zoho_item.get("sku") or zoho_item.get("item_id"),
				"item_name": zoho_item.get("name"),
				"description": zoho_item.get("description", ""),
				"stock_uom": unit,  # Use the validated unit
				"is_stock_item": is_stock_item,  # Maintain stock for all new items
				"valuation_rate": purchase_rate,  # Cost price from Zoho
				"standard_rate": selling_rate,    # Selling price from Zoho
				"valuation_method": erpnext_valuation,  # Always set valuation method
				"disabled": 0 if zoho_item.get("status") == "active" else 1,
				"is_sales_item": 1,  # Default to sales item
				"is_purchase_item": 1,  # Default to purchase item
				"item_group": item_group,
				"purchase_uom": unit,  # Use the validated unit
				"sales_uom": unit,     # Use the validated unit
				"is_taxable": zoho_item.get("tax_percentage", 0) > 0,
				"tax_category": "Standard",
				"zoho_item_id": zoho_item.get("item_id"),
				"zoho_sku": zoho_item.get("sku"),
				"zoho_name": zoho_item.get("name"),
				"zoho_account_id": zoho_item.get("account_id"),
				"zoho_account_name": zoho_item.get("account_name", ""),
				"zoho_purchase_account_id": zoho_item.get("purchase_account_id"),
				"zoho_purchase_account_name": zoho_item.get("purchase_account_name", ""),
				"zoho_inventory_account_id": zoho_item.get("inventory_account_id"),
				"zoho_inventory_account_name": zoho_item.get("inventory_account_name", ""),
				"zoho_item_type": zoho_item.get("item_type"),
				"zoho_product_type": zoho_item.get("product_type"),
				"zoho_track_inventory": zoho_item.get("track_inventory", False),
				"zoho_stock_on_hand": zoho_item.get("stock_on_hand", 0),
				"zoho_reorder_level": zoho_item.get("reorder_level", 0) or 0,
				"zoho_purchase_rate": purchase_rate,
				"zoho_selling_rate": selling_rate,
				"zoho_valuation_method": zoho_item.get("inventory_valuation_method", ""),
				"zoho_last_synced": frappe.utils.now()
			}
			
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
				
				# Add Item Defaults with warehouse (Stores - E for ETMS company)
				item_doc.append("item_defaults", {
					"company": "Big Man Collections",
					"default_warehouse": "Stores - BMC"
				})
				
				item_doc.insert()
				synced_count += 1
				frappe.msgprint(f"Created item: {zoho_item.get('name')}")
			
			# Update stock for items that maintain stock
			if item_doc.is_stock_item and zoho_item.get("stock_on_hand") is not None:
				try:
					zoho_qty = zoho_item.get("stock_on_hand", 0)
					# Use purchase_rate (cost price) for valuation, fallback to selling rate if not available
					cost_rate = purchase_rate if purchase_rate > 0 else selling_rate
					
					# Get default warehouse from Item Defaults table
					default_warehouse = None
					if item_doc.item_defaults:
						for item_default in item_doc.item_defaults:
							if item_default.default_warehouse:
								default_warehouse = item_default.default_warehouse
								break
					
					# If no warehouse found in item defaults, skip stock update
					if not default_warehouse:
						frappe.msgprint(f"Warning: No default warehouse configured for item {zoho_item.get('name')}. Please set it in Item Defaults. Skipping stock update.")
					elif existing_item:
						# For existing items, use Stock Reconciliation to update quantities
						# Get current stock quantity
						
						# Check if warehouse exists
						if not frappe.db.exists("Warehouse", default_warehouse):
							frappe.msgprint(f"Warning: Warehouse '{default_warehouse}' does not exist. Skipping stock update for {zoho_item.get('name')}")
						else:
							current_qty = frappe.db.get_value("Bin", 
								{"item_code": item_doc.item_code, "warehouse": default_warehouse}, 
								"actual_qty") or 0
							
							# Only create reconciliation if quantity has changed
							if float(current_qty) != float(zoho_qty):
								stock_reconciliation = frappe.get_doc({
									"doctype": "Stock Reconciliation",
									"purpose": "Stock Reconciliation",
									"posting_date": frappe.utils.today(),
									"posting_time": frappe.utils.now_datetime().strftime("%H:%M:%S"),
									"items": [{
										"item_code": item_doc.item_code,
										"warehouse": default_warehouse,
										"qty": zoho_qty,
										"valuation_rate": cost_rate or item_doc.valuation_rate or 0
									}]
								})
								stock_reconciliation.insert()
								stock_reconciliation.submit()
								frappe.msgprint(f"Updated stock for {zoho_item.get('name')}: {current_qty} → {zoho_qty} units (Cost: {cost_rate})")
					elif not existing_item:
						# For new items, create opening stock entry
						if zoho_qty > 0:
							# Check if warehouse exists
							if not frappe.db.exists("Warehouse", default_warehouse):
								frappe.msgprint(f"Warning: Warehouse '{default_warehouse}' does not exist. Skipping stock creation for {zoho_item.get('name')}")
							else:
								stock_entry = frappe.get_doc({
									"doctype": "Stock Entry",
									"stock_entry_type": "Material Receipt",
									"posting_date": frappe.utils.today(),
									"posting_time": frappe.utils.now_datetime().strftime("%H:%M:%S"),
									"purpose": "Material Receipt",
									"items": [{
										"item_code": item_doc.item_code,
										"qty": zoho_qty,
										"t_warehouse": default_warehouse,
										"basic_rate": cost_rate or 0,
										"valuation_rate": cost_rate or 0
									}]
								})
								stock_entry.insert()
								stock_entry.submit()
								frappe.msgprint(f"Created opening stock for {zoho_item.get('name')}: {zoho_qty} units (Cost: {cost_rate})")
					
				except Exception as e:
					frappe.log_error(
						title="Zoho Integration Issue",
						message=f"Failed to update stock for {zoho_item.get('name')}: {str(e)}\nZoho Item: {zoho_item}"
					)
					frappe.msgprint(f"Warning: Could not update stock for {zoho_item.get('name')}: {str(e)}")
			
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


@frappe.whitelist()
def push_item_to_zoho(item_code):
	"""
	Push an item from ERPNext to Zoho Books
	"""
	settings = frappe.get_doc("Zoho Books Settings", "Zoho Books Settings")
	
	if not settings.access_token:
		frappe.throw(_("Access token not available. Please complete OAuth setup first."))
	
	organization_id = settings.organization_id
	
	if not organization_id:
		frappe.throw(_("Organization ID not configured"))
	
	# Get item from ERPNext
	item = frappe.get_doc("Item", item_code)
	
	# Check if item already exists in Zoho
	if item.zoho_item_id:
		# Update existing item
		url = f"https://www.zohoapis.com/books/v3/items/{item.zoho_item_id}"
		method = "PUT"
		action = "updated"
	else:
		# Create new item
		url = "https://www.zohoapis.com/books/v3/items"
		method = "POST"
		action = "created"
	
	headers = {
		"X-com-zoho-books-organizationid": str(organization_id),
		"Content-Type": "application/json"
	}
	
	# Prepare item data
	item_data = {
		"name": item.item_name,
		"description": item.description or "",
		"unit": item.stock_uom or "Nos",
		"item_type": "inventory" if item.is_stock_item else "service"
	}
	
	# Add SKU if available
	if item.item_code:
		item_data["sku"] = item.item_code
	
	# Always send selling price (rate) if available
	if item.standard_rate and item.standard_rate > 0:
		item_data["rate"] = float(item.standard_rate)
	else:
		item_data["rate"] = 0
	
	# Always send purchase rate (valuation rate) if available
	if item.valuation_rate and item.valuation_rate > 0:
		item_data["purchase_rate"] = float(item.valuation_rate)
	elif item.last_purchase_rate and item.last_purchase_rate > 0:
		item_data["purchase_rate"] = float(item.last_purchase_rate)
	else:
		item_data["purchase_rate"] = 0
	
	# Add stock information if it's a stock item
	if item.is_stock_item:
		item_data["track_inventory"] = True
		
		# Get default warehouse from item defaults
		default_warehouse = None
		if item.item_defaults:
			for item_default in item.item_defaults:
				if item_default.default_warehouse:
					default_warehouse = item_default.default_warehouse
					break
		
		# For NEW items only, send opening stock
		if method == "POST":
			# Get opening stock from Stock Ledger Entry or current stock
			opening_stock = 0
			opening_stock_rate = item.valuation_rate or item.last_purchase_rate or 0
			
			if default_warehouse:
				# Get current stock quantity from the default warehouse
				stock_qty = frappe.db.get_value("Bin", 
					{"item_code": item.item_code, "warehouse": default_warehouse}, 
					"actual_qty") or 0
				opening_stock = stock_qty
			
			# Send opening stock only if we have stock
			if opening_stock > 0:
				item_data["initial_stock"] = float(opening_stock)
				item_data["initial_stock_rate"] = float(opening_stock_rate)
	
	try:
		response = make_zoho_api_request(method, url, headers=headers, json_data=item_data)
		response.raise_for_status()
		
		item_response = response.json()
		zoho_item = item_response.get("item", {})
		zoho_item_id = zoho_item.get("item_id")
		
		# Update item with Zoho item ID
		if zoho_item_id:
			item.zoho_item_id = zoho_item_id
			item.zoho_name = zoho_item.get("name")
			item.zoho_sku = zoho_item.get("sku")
			item.zoho_last_synced = frappe.utils.now()
			item.save()
			
			frappe.msgprint(_(f"Item {action} in Zoho Books successfully! Item ID: {zoho_item_id}"))
			return {
				"status": "success",
				"message": f"Item {action} successfully",
				"zoho_item_id": zoho_item_id
			}
		else:
			frappe.throw(_("Failed to get item ID from Zoho response"))
	
	except requests.exceptions.HTTPError as e:
		error_message = f"HTTP {e.response.status_code}: {e.response.text}"
		frappe.log_error(
			title="Zoho Item Push Failed",
			message=f"Failed to push item {item_code} to Zoho: {error_message}"
		)
		frappe.throw(_(f"Failed to push item to Zoho Books: {error_message}"))
	except Exception as e:
		frappe.log_error(
			title="Zoho Item Push Failed",
			message=f"Error pushing item {item_code} to Zoho: {str(e)}"
		)
		frappe.throw(_(f"Failed to push item to Zoho Books: {str(e)}"))


def push_item_on_submit(doc, method):
	"""
	Hook function to automatically push item to Zoho when submitted/saved
	"""
	try:
		# Check if Zoho integration is enabled
		settings = frappe.get_doc("Zoho Books Settings", "Zoho Books Settings")
		if settings.enabled and settings.auto_sync_item:
			# Only push if not already synced to Zoho
			if not doc.zoho_item_id:
				result = push_item_to_zoho(doc.item_code)
				
				if result.get("status") == "success":
					frappe.msgprint(f"Item synced to Zoho successfully: {result.get('zoho_item_id')}", alert=True)
				else:
					frappe.log_error(
						title="Zoho Item Auto-Sync Failed",
						message=f"Failed to auto-sync item {doc.item_code} to Zoho: {result.get('message')}"
					)
	except Exception as e:
		frappe.log_error(
			title="Zoho Integration Hook Error",
			message=f"Error in push_item_on_submit hook: {str(e)}"
		)
