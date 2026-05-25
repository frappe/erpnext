// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Party Specific Item", {
	setup: function (frm) {
		frm.trigger("party_type");
	},

	party_type: function (frm) {
		if (["Customer Group", "Supplier Group"].includes(frm.doc.party_type)) {
			frm.set_query("party", function () {
				return {
					filters: {
						is_group: 0,
					},
				};
			});
		} else {
			frm.set_query("party", null);
		}
	},
});
