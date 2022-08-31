// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Work Order Invoice', {
	// refresh: function(frm) {

	// }
	onload: function(frm) {
		cur_frm.fields_dict['warehouse'].get_query = function(doc, cdt, cdn) {
			return {
				filters:{'company': doc.company}
			}
		}
	},

	setup: function(frm) {
		frm.set_query("item_code", "detail_one", function(doc, cdt, cdn) {
			return {
				filters:{"default_company": doc.company, "item_group": "Materiales"}
			};
		});

		frm.set_query("item_code", "detail_two", function(doc, cdt, cdn) {
			return {
				filters:{"default_company": doc.company, "item_group": "Pruebas"}
			};
		});
    },
});
