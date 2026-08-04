// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Bin", {
	refresh(frm) {
		frm.trigger("recalculate_values");
	},

	recalculate_values(frm) {
		frm.add_custom_button(__("Recalculate Values"), () => {
			frappe.call({
				method: "recalculate_values",
				freeze: true,
				doc: frm.doc,
				callback: function (r) {
					frappe.show_alert(__("Bin Values Recalculated"), 2);
				},
			});
		});
	},
});
