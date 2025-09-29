// Copyright (c) 2025, itsyosefali and contributors
// For license information, please see license.txt

frappe.ui.form.on("Zoho Books Settings", {
	refresh(frm) {
		// Add OAuth setup button if not configured
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
		
		// Add test connection button
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
			
			// Add revoke token button
			frm.add_custom_button(__("Revoke Token"), function() {
				frappe.confirm(__("Are you sure you want to revoke the current token?"), function() {
					frappe.call({
						method: "zoho_integration.auth.revoke_token",
						callback: function(r) {
							if (r.message && r.message.status === "success") {
								frappe.msgprint(__("Token revoked successfully!"));
								frm.reload_doc();
							}
						}
					});
				});
			}, __("Revoke"));
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
