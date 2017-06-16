// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Payroll", {
	onload: function(frm) {
		frm.doc.posting_date = frappe.datetime.nowdate();
		frm.toggle_reqd(['payroll_frequency'], !frm.doc.salary_slip_based_on_timesheet);
	},

	setup: function(frm) {
		frm.set_query("payment_account", function() {
			var account_types = ["Bank", "Cash"];
			return {
				filters: {
					"account_type": ["in", account_types],
					"is_group": 0,
					"company": frm.doc.company
				}
			}
		}),
		frm.set_query("cost_center", function() {
			return {
				filters: {
					"is_group": 0,
					company: frm.doc.company
				}
			}
		}),
		frm.set_query("project", function() {
			return {
				filters: {
					company: frm.doc.company
				}
			}
		})
	},
	payroll_frequency: function(frm) {
		frm.trigger("set_start_end_dates");
	},

	start_date: function(frm) {
		frm.trigger("set_start_end_dates");
	},

	end_date: function(frm) {
		frm.trigger("set_start_end_dates");
	},

	salary_slip_based_on_timesheet: function(frm) {
		frm.toggle_reqd(['payroll_frequency'], !frm.doc.salary_slip_based_on_timesheet);
	},

	set_start_end_dates: function(frm) {
		if (!frm.doc.salary_slip_based_on_timesheet){
			frappe.call({
				method:'erpnext.hr.doctype.payroll.payroll.get_start_end_dates',
				args:{
					payroll_frequency: frm.doc.payroll_frequency,
					start_date: frm.doc.start_date || frm.doc.posting_date
				},
				callback: function(r){
					if (r.message){
						frm.set_value('start_date', r.message.start_date);
						frm.set_value('end_date', r.message.end_date);
					}
				}
			})
		}
	},
	
	refresh: function(frm) {
		if (frm.doc.status == "Unpaid") {
			frm.add_custom_button("Create Salary Slip", function() {
				frm.trigger("create_salary_slips");
			});
			frm.add_custom_button("Submit Salary Slip", function() {
				frm.trigger("submit_salary_slips");
			});
			frm.add_custom_button("Make Accrual Entry", function() {
				frm.trigger("make_accural_jv_entry");
			});
			frm.add_custom_button("Make Payment Entry", function() {
				frm.trigger("make_payment_entry");
			});
		}
	},

	create_salary_slips: function(frm) {
		frappe.call({
			args: {
				"start_date": frm.doc.start_date,
				"end_date": frm.doc.end_date,
				"company": frm.doc.company,
				"salary_slip_based_on_timesheet": frm.doc.salary_slip_based_on_timesheet,
				"payroll_frequency": frm.doc.payroll_frequency,
				"posting_date": frm.doc.posting_date,
				"branch": frm.doc.branch,
				"department": frm.doc.department,
				"designation": frm.doc.designation
			},
			method: "erpnext.hr.doctype.payroll.payroll.create_salary_slips",
			callback: function(r) {
				if(r.message) {
					$.each(r.message, function(i, d) {
						var row = frm.add_child("salary_slips");
						row.employee = d.employee;
						row.employee_name = d.employee_name;
						row.salary_slip = d.name;
						row.salary_slip_status = d.status;
						row.net_pay = d.net_pay
					});
				refresh_field("salary_slips");
				frm.save()
				}
			}
		})
	},

	submit_salary_slips: function(frm) {
		frappe.call({
			args: {
				"name": frm.doc.name
			},
			method: "erpnext.hr.doctype.payroll.payroll.submit_salary_slips",
			callback: function(r) {
				if(r.message) {
					$.each(r.message, function(i, d) {
						frappe.model.set_value("Payroll Salary Slip", d, "salary_slip_status", "Submitted");
					});
				refresh_field("salary_slips");
				frm.save()
				}
			}
		})
	},

	make_accural_jv_entry: function(frm){
		frappe.call({
			args: {
				"name": frm.doc.name,
				"company": frm.doc.company,
				"start_date": frm.doc.start_date,
				"end_date": frm.doc.end_date,
				"cost_center": frm.doc.cost_center,
				"project": frm.doc.project
			},
			method: "erpnext.hr.doctype.payroll.payroll.make_accural_jv_entry",
			callback: function(r) {
				if(!r.exc && r.message)
					var doc = frappe.model.sync(r.message)[0];
					frappe.set_route("Form", doc.doctype, doc.name);
			}
		});
	},
	make_payment_entry: function(frm){
		if(!frm.doc.payment_account) frappe.throw(__("Please select Payment Account"));
		frappe.call({
			args: {
				"name": frm.doc.name,
				"start_date": frm.doc.start_date,
				"end_date": frm.doc.end_date,
				"company": frm.doc.company,
				"payment_account": frm.doc.payment_account
			},
			method: "erpnext.hr.doctype.payroll.payroll.make_payment_entry",
			callback: function(r) {
				if (r.message)
					var doc = frappe.model.sync(r.message)[0];
					frappe.set_route("Form", doc.doctype, doc.name);
			}
		});
	}
});