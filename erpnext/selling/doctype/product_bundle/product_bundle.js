// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Product Bundle", {
	refresh: function (frm) {
		frm.toggle_enable("new_item_code", frm.is_new());
		frm.set_query("new_item_code", () => {
			return {
				query: "erpnext.selling.doctype.product_bundle.product_bundle.get_new_item_code",
			};
		});

		// A submitted bundle is immutable. To change it, create a new version
		// (a fresh draft copied from this one) and submit that instead.
		if (frm.doc.docstatus === 1) {
			frm.add_custom_button(
				__("New Version"),
				() => {
					frappe.model.open_mapped_doc({
						method: "erpnext.selling.doctype.product_bundle.product_bundle.make_new_version",
						frm: frm,
					});
				},
				__("Actions")
			);
		}
	},
});
