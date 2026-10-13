// Copyright (c) 2018, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on("Quality Review", {
	goal: function (frm) {
		frappe.call({
			method: "frappe.client.get",
			args: {
				doctype: "Quality Goal",
				name: frm.doc.goal,
			},
			callback: function (data) {
				frm.clear_table("reviews");
				for (const d of data.message.objectives) {
					frm.add_child("reviews", { objective: d.objective, target: d.target, uom: d.uom });
				}
				frm.refresh();
			},
		});
	},
});
