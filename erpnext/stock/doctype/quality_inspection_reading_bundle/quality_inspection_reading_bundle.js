// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Quality Inspection Reading Bundle", {
	refresh(frm) {
		frm.trigger("toggle_populate_button");

		// a born-linked bundle freezes with its inspection's verdict
		if (frm.doc.docstatus === 0 && frm.doc.quality_inspection) {
			frm.set_intro(
				__(
					"This reading bundle is submitted automatically when Quality Inspection {0} is submitted.",
					[frappe.utils.get_form_link("Quality Inspection", frm.doc.quality_inspection, true)]
				)
			);
		}
	},

	quality_inspection_template(frm) {
		frm.trigger("toggle_populate_button");
	},

	quantity(frm) {
		frm.trigger("toggle_populate_button");
	},

	toggle_populate_button(frm) {
		frm.remove_custom_button(__("Populate Units"));
		if (frm.doc.quality_inspection_template && frm.doc.quantity > 0) {
			frm.add_custom_button(__("Populate Units"), () => {
				frm.call("populate_units").then(() => {
					frm.refresh_field("entries");
					frm.dirty();
				});
			});
		}
	},
});
