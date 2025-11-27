// Copyright (c) 2025, itsyosefali and contributors
// For license information, please see license.txt

frappe.ui.form.on("Zoho Books Settings", {
	refresh(frm) {
		if (!frm.doc.access_token) {
			frm.add_custom_button(__("Setup OAuth"), function() {
				if (!frm.doc.redirect_url) {
					frappe.msgprint(__("Please configure the Redirect URL first"));
					return;
				}
				frappe.call({
					method: "zoho_integration.auth.get_authorization_url",
					callback: function(r) {
						if (r.message && r.message.authorization_url) {
							window.open(r.message.authorization_url, '_blank');
							frappe.msgprint(__("Please complete the OAuth authorization in the new window"));
						}
					}
				});
			}, __("OAuth Setup"));
		}
		
		if (frm.doc.access_token) {
			frm.add_custom_button(__("Test Connection"), function() {
				frappe.call({
					method: "zoho_integration.auth.test_connection",
					callback: function(r) {
						if (r.message && r.message.status === "success") {
							frappe.msgprint(__("Connection successful!"));
						}
					}
				});
			}, __("Test"));
			
			// Add refresh token button
			frm.add_custom_button(__("Refresh Token"), function() {
				frappe.call({
					method: "zoho_integration.auth.refresh_access_token",
					callback: function(r) {
						if (r.message && r.message.status === "success") {
							frappe.msgprint(__("Access token refreshed successfully!"));
							frm.reload_doc();
						}
					}
				});
			}, __("Refresh"));
			
			frm.add_custom_button(__("Get Zoho Customers"), function() {
                        frappe.call({
                            method: "zoho_integration.customer.sync_customers_from_zoho_to_erpnext",
                            args: {
                                organization_id: frm.doc.organization_id,
                                per_page: frm.doc.customers_per_page || 50,
                                only_new: true
                            },
                            callback: function(r) {
                                if (r.message && r.message.status === "success") {
                                    frappe.msgprint(__("Customers synced successfully! Created: {0}, Updated: {1}, Errors: {2}", 
                                        [r.message.synced_count, r.message.updated_count, r.message.error_count]));
                                    frm.set_value("last_sync_date", frappe.datetime.now_datetime());
                                    frm.save();
                                }
                            }
                        });
                    }, __("Get Customers"));
			
			frm.add_custom_button(__("Get Zoho Items"), function() {
                        frappe.call({
                            method: "zoho_integration.item.sync_items_from_zoho_to_erpnext",
                            args: {
                                organization_id: frm.doc.organization_id,
                                per_page: frm.doc.items_per_page || 50,
                                sync_from_date: frm.doc.sync_from_date
                            },
                            callback: function(r) {
                                if (r.message && r.message.status === "success") {
                                    frappe.msgprint(__("Items synced successfully! Created: {0}, Updated: {1}, Errors: {2}", 
                                        [r.message.synced_count, r.message.updated_count, r.message.error_count]));
                                    // Update last sync date
                                    frm.set_value("last_sync_date", frappe.datetime.now_datetime());
                                    frm.save();
                                }
                            }
                        });
                    }, __("Get Items"));
		}
	},
	
	client_id(frm) {
		// Clear tokens when client ID changes
		if (frm.doc.client_id && (frm.doc.access_token || frm.doc.refresh_token)) {
			frm.set_value("access_token", "");
			frm.set_value("refresh_token", "");
		}
	}
});
