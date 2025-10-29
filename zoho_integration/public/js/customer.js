frappe.ui.form.on('Customer', {
	refresh: function(frm) {
		// Add button to push customer to Zoho
		if (!frm.is_new()) {
			frm.add_custom_button(__('Push to Zoho Books'), function() {
				frappe.confirm(
					__('Are you sure you want to push this customer to Zoho Books?'),
					function() {
						frappe.call({
							method: 'zoho_integration.customer.push_customer_to_zoho',
							args: {
								customer_name: frm.doc.name
							},
							freeze: true,
							freeze_message: __('Pushing customer to Zoho Books...'),
							callback: function(r) {
								if (r.message && r.message.status === 'success') {
									frappe.show_alert({
										message: __('Customer pushed to Zoho Books successfully'),
										indicator: 'green'
									});
									frm.reload_doc();
								}
							}
						});
					}
				);
			}, __('Zoho Integration'));
			
			// Show Zoho Contact ID if exists
			if (frm.doc.zoho_contact_id) {
				frm.add_custom_button(__('View in Zoho Books'), function() {
					// Open Zoho Books contact in new tab (you may need to adjust the URL based on your organization)
					window.open('https://books.zoho.com/app#/contacts/' + frm.doc.zoho_contact_id, '_blank');
				}, __('Zoho Integration'));
			}
		}
	}
});

