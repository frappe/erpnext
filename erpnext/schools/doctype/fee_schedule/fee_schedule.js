// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Fee Schedule', {
	setup: function(frm) {
		frm.add_fetch("fee_structure", "receivable_account", "receivable_account");
		frm.add_fetch("fee_structure", "income_account", "income_account");
		frm.add_fetch("fee_structure", "cost_center", "cost_center");
		frappe.realtime.on("fee_schedule_progress", function(data) {
			if (data.progress && data.progress === 0) {
				frappe.msgprint(__("Fee records will be created in the background. In case of any error the error message will be updated in the Schedule."));
			}
			if (data.progress) {
				frm.reload_doc();
				frm.dashboard.add_progress("Fee Creation Status", data.progress);
			}
		});
	},

	onload: function(frm) {
		frm.set_query("receivable_account", function(doc) {
			return {
				filters: {
					'account_type': 'Receivable',
					'is_group': 0,
					'company': doc.company
				}
			};
		});
		frm.set_query("income_account", function(doc) {
			return {
				filters: {
					'account_type': 'Income Account',
					'is_group': 0,
					'company': doc.company
				}
			};
		});
		frm.set_query("student_group", "student_groups", function() {
			return {
				"program": frm.doc.program,
				"academic_year": frm.doc.academic_year
			};
		});
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
		
		if (!frm.doc.__islocal && !frm.doc.fee_creation_status || frm.doc.fee_creation_status == "Failed") {
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

frappe.ui.form.on("Fee Schedule Student Group", {
	student_group: function(frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		frappe.call({
			method: "erpnext.schools.doctype.fee_schedule.fee_schedule.get_total_students",
			args: {
				"student_group": row.student_group,
				"student_category": frm.doc.student_category
			},
			callback: function(r) {
				if(!r.exc) {
					frappe.model.set_value(cdt, cdn, "total_students", r.message);
				}
			}
		})
	}
})