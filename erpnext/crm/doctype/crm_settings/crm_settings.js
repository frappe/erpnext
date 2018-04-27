// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('CRM Settings', {
	refresh: function(frm) {
		frappe.realtime.on('show_popup', (popup_data) => {
			frappe.msgprint({
				title: __('Incoming Call'),
				message: __(popup_data)
			});
			$('.modal-backdrop').unbind('click');
		});
	}
});