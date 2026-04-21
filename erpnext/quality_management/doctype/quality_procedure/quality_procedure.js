// Copyright (c) 2018, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on("Quality Procedure", {
	refresh: function (frm) {
		frm.set_query("procedure", "processes", (frm) => {
			return {
				filters: {
					name:
						frm.parent_quality_procedure == null
							? ["!=", frm.name]
							: ["not in", [frm.name, frm.parent_quality_procedure]],
				},
			};
		});
		frm.set_query("parent_quality_procedure", function () {
			return {
				filters: {
					is_group: 1,
					name: ["!=", frm.doc.name],
				},
			};
		});
	},
});
