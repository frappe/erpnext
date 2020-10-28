// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('E Invoice Settings', {
	refresh: function(frm) {
		if (!frm.doc.enable) return;
		frm.trigger("show_fetch_token_btn");
	},

	show_fetch_token_btn(frm) {
		const { token_expiry } = frm.doc;
		const now = frappe.datetime.now_datetime();
		const expiry_in_mins = moment(token_expiry).diff(now, "minute");
		if (expiry_in_mins <= 1 || !token_expiry) {
			frm.add_custom_button(__("Fetch Token"),
				() => {
					frm.call({
						method: 'erpnext.regional.india.e_invoice.utils.fetch_token',
						freeze: true,
						callback: () => frm.refresh()
					});
				}
			);
		}
	}
});
