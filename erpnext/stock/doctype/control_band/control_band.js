// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Control Band', {
	setup: function(frm) {
		frm.set_query("item_code", "ppe", function(doc, cdt, cdn) {
			let d = locals[cdt][cdn];
			return {
				filters: [
					['Item', 'is_ppe', '=', 1]
				]
			};
		});
	},
});
