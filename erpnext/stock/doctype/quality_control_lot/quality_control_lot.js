// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Quality Control Lot", {
	setup(frm) {
		frm.set_query("batch_no", function (doc) {
			return { filters: { item: doc.item_code } };
		});
	},

	refresh(frm) {
		if (!frm.is_new() && frm.doc.pending_qty > 0 && !frm.doc.quality_inspection) {
			frm.add_custom_button(__("Create Quality Inspection"), () => {
				frappe.new_doc("Quality Inspection", {
					inspection_type: "Incoming",
					reference_type: "Quality Control Lot",
					reference_name: frm.doc.name,
					item_code: frm.doc.item_code,
					batch_no: frm.doc.batch_no,
					inspection_basis: frm.doc.inspection_basis,
					sample_size: frm.doc.inspection_basis === "Each Quantity" ? 0 : frm.doc.pending_qty,
					quality_inspection_template: frm.doc.inspection_template,
				});
			});
		}

		if (frm.doc.quality_inspection) {
			frm.add_custom_button(__("Open Quality Inspection"), () => {
				frappe.set_route("Form", "Quality Inspection", frm.doc.quality_inspection);
			});
		}
	},
});
