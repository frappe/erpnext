// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Hub Message', {
	refresh: function(frm) {
		if (frm.doc.status === 'Pending') {
			frm.add_custom_button('Resend', () =>
				frappe.call('erpnext.hub_node.doctype.hub_message.hub_message.resend',
					{message: frm.doc.name}));
		}
	}
});
