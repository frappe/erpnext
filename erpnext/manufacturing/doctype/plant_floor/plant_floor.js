// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Plant Floor", {
	setup(frm) {
		frm.trigger("setup_queries");
	},

	setup_queries(frm) {
		frm.set_query("warehouse", (doc) => {
			if (!doc.company) {
				frappe.throw(__("Please select Company first"));
			}

			return {
				filters: {
					is_group: 0,
					company: doc.company,
				},
			};
		});
	},

	refresh(frm) {
		if (frappe._from_link?.field_obj?.df?.options === frm.doctype) return;

		frappe.route_flags.replace_route = true;
		frappe.set_route("plant-builder", frm.is_new() ? "new" : frm.doc.name);
	},
});
