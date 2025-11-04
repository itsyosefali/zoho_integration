frappe.ui.form.on('Sales Invoice', {
	refresh: function(frm) {
		// Add button to push invoice to Zoho
		if (!frm.is_new() && frm.doc.docstatus === 1) {
			frm.add_custom_button(__('Push to Zoho Books'), function() {
				frappe.confirm(
					__('Are you sure you want to push this invoice to Zoho Books?'),
					function() {
						frappe.call({
							method: 'zoho_integration.invoice.send_invoice_to_zoho',
							args: {
								invoice_id: frm.doc.name
							},
							freeze: true,
							freeze_message: __('Pushing invoice to Zoho Books...'),
							callback: function(r) {
								if (r.message && r.message.status === 'success') {
									frappe.show_alert({
										message: __('Invoice pushed to Zoho Books successfully'),
										indicator: 'green'
									});
									frm.reload_doc();
								} else if (r.message && r.message.message) {
									frappe.msgprint({
										title: __('Error'),
										message: r.message.message,
										indicator: 'red'
									});
								}
							}
						});
					}
				);
			}, __('Zoho Integration'));
			
			// Show Zoho Invoice ID if exists
			if (frm.doc.zoho_invoice_id) {
				frm.add_custom_button(__('View in Zoho Books'), function() {
					// Open Zoho Books invoice in new tab (you may need to adjust the URL based on your organization)
					window.open('https://books.zoho.com/app#/invoices/' + frm.doc.zoho_invoice_id, '_blank');
				}, __('Zoho Integration'));
			}
		}
		
		// Show sync status indicator
		if (frm.doc.zoho_sync_status) {
			var color_map = {
				'Synced': 'green',
				'Not Synced': 'orange',
				'Failed': 'red'
			};
			
			frm.dashboard.add_indicator(__('Zoho Sync: {0}', [frm.doc.zoho_sync_status]), 
				color_map[frm.doc.zoho_sync_status] || 'grey');
		}
	}
});

