// Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Project Template', {
	onload: function(frm) {
		frm.events.setup_queries(frm);
	},

	setup_queries: function (frm) {
		frm.set_query("applicable_item_code", "applicable_items", function (doc, cdt, cdn) {
			return erpnext.queries.item();
		});

		frm.set_query("applicable_uom", "applicable_items", function(doc, cdt, cdn) {
			var d = locals[cdt][cdn];
			return {
				query : "erpnext.controllers.queries.item_uom_query",
				filters: {
					item_code: d.applicable_item_code
				}
			}
		});
	},
});

frappe.ui.form.on('Project Template Item', {
	applicable_item_code: function (frm, cdt, cdn) {
		var row = frappe.get_doc(cdt, cdn);
		if (!row.applicable_item_code) {
			frappe.model.set_value(cdt, cdn, 'applicable_item_name', null);
		}
	},

	applies_to_item: function (frm, cdt, cdn) {
		var row = frappe.get_doc(cdt, cdn);
		if (!row.applies_to_item) {
			frappe.model.set_value(cdt, cdn, 'applies_to_item_name', null);
		}
	},
});
