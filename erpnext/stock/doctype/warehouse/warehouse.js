// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.list_route = "Tree/Warehouse";

frappe.ui.form.on("Warehouse", {
	refresh: function(frm) {
		frm.toggle_display('warehouse_name', frm.doc.__islocal);

		frm.add_custom_button(__("Stock Balance"), function() {
			frappe.set_route("query-report", "Stock Balance", {"warehouse": frm.doc.name});
		});
 		if(frm.doc.__onload && frm.doc.__onload.account) {
	 		frm.add_custom_button(__("General Ledger"), function() {
				frappe.route_options = {
					"account": frm.doc.__onload.account,
					"company": frm.doc.company
				}
				frappe.set_route("query-report", "General Ledger");
			});
 		}
		
		frm.fields_dict['parent_warehouse'].get_query = function(doc) {
			return {
				filters: {
					"is_group": "Yes",
				}
			}
		}
	}
});




cur_frm.set_query("create_account_under", function() {
	return {
		filters: {
			"company": cur_frm.doc.company,
			'is_group': 1
		}
	}
})
