// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Exotel Settings', {
	refresh: function(frm) {
		if (frm.doc.webhook_key) {
			const key = frm.doc.webhook_key;
			const site = window.location.origin;

			frm.get_field('integration_info').$wrapper.html(`
				<hr>
				<b>Note:</b>Use following link to setup call popup<br><br>
				<code class="cursor-pointer" style="word-break: break-all">${site}/api/method/erpnext.erpnext_integrations.exotel_integration.handle_incoming_call/${key}</code><br><br>
			`).find('code').click(e => {
				let text = $(e.currentTarget).text();
				frappe.utils.copy_to_clipboard(text);
			});
		}
	}
});
