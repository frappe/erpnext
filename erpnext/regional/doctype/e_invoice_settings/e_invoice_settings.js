// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('E Invoice Settings', {
	refresh: function(frm) {
		if (!frm.doc.enable) return;

		frm.trigger("show_fetch_token_btn");
		frm.add_custom_button(__("Get GSTIN Details"), 
			() => {
				frm.call({
					doc: frm.doc,
					method: 'get_gstin_details',
					args: {
						'gstin': '36AAECF1151A1ZC'
					},
					freeze: true,
					callback: (res) => console.log(res)
				});
			});
		
		frm.add_custom_button(__("Generate IRN"), 
			() => {
				frm.call({
					doc: frm.doc,
					method: 'generate_irn',
					args: {
						'invoice': 'SINV-20-21-0051'
					},
					freeze: true,
					callback: (res) => console.log(res)
				});
			});
		
		frm.add_custom_button(__("Fetch IRN Details"), 
			() => {
				frm.call({
					doc: frm.doc,
					method: 'get_irn_details',
					args: {
						'irn': 'c63d9e180dfdaa9242e29e2e1e0a8d76f20e116ed3de179a2e9120f384e1b432'
					},
					freeze: true,
					callback: (res) => console.log(res)
				});
			});
	},

	show_fetch_token_btn(frm) {
		const { token_expiry } = frm.doc;
		const now = frappe.datetime.now_datetime();
		const expiry_in_mins = moment(token_expiry).diff(now, "minute");
		if (expiry_in_mins <= 1) {
			frm.add_custom_button(__("Fetch Token"),
				() => {
					frm.call({
						doc: frm.doc,
						method: 'make_authentication_request',
						freeze: true,
						callback: () => frm.refresh()
					});
				}
			);
		}
	}
});
