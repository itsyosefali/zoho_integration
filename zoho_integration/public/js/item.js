frappe.ui.form.on('Item', {
	refresh: function(frm) {
		// Add button to push item to Zoho
		if (!frm.is_new()) {
			frm.add_custom_button(__('Push to Zoho Books'), function() {
				frappe.confirm(
					__('Are you sure you want to push this item to Zoho Books?'),
					function() {
						frappe.call({
							method: 'zoho_integration.item.push_item_to_zoho',
							args: {
								item_code: frm.doc.name
							},
							freeze: true,
							freeze_message: __('Pushing item to Zoho Books...'),
							callback: function(r) {
								if (r.message && r.message.status === 'success') {
									frappe.show_alert({
										message: __('Item pushed to Zoho Books successfully'),
										indicator: 'green'
									});
									frm.reload_doc();
								}
							}
						});
					}
				);
			}, __('Zoho Integration'));
			
			// Show Zoho Item ID if exists
			if (frm.doc.zoho_item_id) {
				frm.add_custom_button(__('View in Zoho Books'), function() {
					// Open Zoho Books item in new tab (you may need to adjust the URL based on your organization)
					window.open('https://books.zoho.com/app#/inventory/items/' + frm.doc.zoho_item_id, '_blank');
				}, __('Zoho Integration'));
			}
		}
	}
});

