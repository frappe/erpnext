// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Fee Schedule', {
	setup: function(frm) {
		frm.add_fetch("company", "default_receivable_account", "debit_to");
		frm.add_fetch("company", "default_income_account", "against_income_account");
		frm.add_fetch("company", "cost_center", "cost_center");
	},

	refresh: function(frm) {
		if(!frm.doc.__islocal && frm.doc.__onload && frm.doc.__onload.dashboard_info &&
			frm.doc.fee_creation_status=="Successful") {
			var info = frm.doc.__onload.dashboard_info;
			frm.dashboard.add_indicator(__('Total Collected: {0}', [format_currency(info.total_paid,
				info.currency)]), 'blue');
			frm.dashboard.add_indicator(__('Total Outstanding: {0}', [format_currency(info.total_unpaid,
				info.currency)]), info.total_unpaid ? 'orange' : 'green');
		}
		if (!frm.doc.fee_creation_status || frm.doc.fee_creation_status == "Failed") {
			frm.add_custom_button(__('Create Fees'), function() {
				frappe.call({
					method: "create_fees",
					doc: frm.doc,
					callback: function() {
						frm.refresh();
					}
				});
			}, "fa fa-play", "btn-success");
		}
	},

	fee_structure: function(frm) {
		if (frm.doc.fee_structure) {
			frappe.call({
				method: "erpnext.schools.doctype.fee_schedule.fee_schedule.get_fee_structure",
				args: {
					"target_doc": frm.doc.name,
					"source_name": frm.doc.fee_structure
				},
				callback: function(r) {
					var doc = frappe.model.sync(r.message);
					frappe.set_route("Form", doc[0].doctype, doc[0].name);
				}
			});
		}
	}
});

frappe.ui.form.on("Fee Component", {
	refresh: function(frm) {
		frm.set_read_only();
	}
});

frappe.ui.form.on("Fee Schedule Student Group", {
	onload: function(frm) {
		frm.set_query("student_group",function(){
			return{
				"filters":{
					"group_based_on": "Batch"
				}
			};
		});
	}
});
