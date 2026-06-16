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
			frm.add_custom_button(__("Create New Version"), () => {
				frappe.model.open_mapped_doc({
					method: "erpnext.selling.doctype.product_bundle.product_bundle.make_new_version",
					frm: frm,
				});
			});
		}

		show_supersede_hint(frm);
	},

	new_item_code: function (frm) {
		show_supersede_hint(frm);
	},
});

function show_supersede_hint(frm) {
	// Warn (non-blocking) when the chosen Parent Item already has an active bundle:
	// submitting this draft will create a new version and deactivate that one.
	frm.set_intro("");
	if (frm.doc.docstatus !== 0 || !frm.doc.new_item_code) {
		return;
	}

	frappe.db
		.get_value(
			"Product Bundle",
			{
				new_item_code: frm.doc.new_item_code,
				is_active: 1,
				docstatus: 1,
			},
			"name"
		)
		.then((r) => {
			const active = r.message && r.message.name;
			if (active && active !== frm.doc.name) {
				frm.set_intro(
					__(
						"Item {0} already has an active Product Bundle ({1}). Submitting this will create a new version and deactivate {1}.",
						[frm.doc.new_item_code, active]
					),
					"orange"
				);
			}
		});
}
