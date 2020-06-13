// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Exotel Settings', {
	refresh: function(frm) {
		if (frm.doc.webhook_key) {
			const key = frm.doc.webhook_key;
			const site = window.location.origin;

			frm.set_df_property('integration_info', 'options', `
				<hr>
				<b>Note:</b> Use following link to setup call popup<br><br>
				<code>${site}/api/method/erpnext.erpnext_integrations.exotel_integration.handle_incoming_call/${key}</code><br><br>
			`);
		}
	}
});
