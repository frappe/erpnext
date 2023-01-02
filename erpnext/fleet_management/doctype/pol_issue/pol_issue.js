// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('POL Issue', {
	refresh: function(frm) {
		if(frm.doc.docstatus == 1 && cint(frm.doc.out_source) == 0) {
			cur_frm.add_custom_button(__('POL Ledger'), function() {
				frappe.route_options = {
					branch: frm.doc.branch,
					from_date: frm.doc.posting_date,
					to_date: frm.doc.posting_date,
					equipment: frm.doc.tanker
				};
				frappe.set_route("query-report", "POL Ledger");
			}, __("View"));
		}
		set_equipment_filter(frm)
	},
	branch:function(frm){
		set_equipment_filter(frm)
	},
});

cur_frm.set_query("pol_type", function() {
	return {
		"filters": {
		"disabled": 0,
		"is_pol_item":1
		}
	};
});

var set_equipment_filter=function(frm){
	frm.set_query("tanker", function() {
		return {
			query: "erpnext.fleet_management.fleet_utils.get_container_filtered",
			filters:{
				"branch":frm.doc.branch
			}
		};
	});
}