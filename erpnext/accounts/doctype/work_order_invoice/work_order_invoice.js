// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Work Order Invoice', {
	// refresh: function(frm) {

	// }
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
