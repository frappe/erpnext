// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Bin", {
	refresh(frm) {
		frm.trigger("recalculate_bin_quantity");
	},

	recalculate_bin_quantity(frm) {
		if (!frappe.model.can_write("Repost Item Valuation")) {
			return;
		}

		frm.add_custom_button(__("Recalculate Bin Qty"), () => {
			frappe.call({
				method: "recalculate_qty",
				freeze: true,
				doc: frm.doc,
				callback: function (r) {
					frappe.show_alert(__("Bin Qty Recalculated"), 2);
				},
			});
		});
	},
});
