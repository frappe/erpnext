// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.add_fetch('employee','employee_name','employee_name');
cur_frm.add_fetch('employee','company','company');

frappe.ui.form.on("Leave Application", {
	onload: function(frm) {
		if (!frm.doc.posting_date) {
			frm.set_value("posting_date", get_today());
		}

		frm.set_query("leave_approver", function() {
			return {
				query: "erpnext.hr.doctype.leave_application.leave_application.get_approvers",
				filters: {
					employee: frm.doc.employee
				}
			};
		});

		frm.set_query("employee", erpnext.queries.employee);

	},

	refresh: function(frm) {
		if (frm.is_new()) {
			frm.set_value("status", "Open");
			frm.trigger("calculate_total_days");
		}

		frm.set_intro("");
		if (frm.is_new() && !in_list(user_roles, "HR User")) {
			frm.set_intro(__("Fill the form and save it"));
		} else {
			if(frm.doc.docstatus==0 && frm.doc.status=="Open") {
				if(user==frm.doc.leave_approver) {
					frm.set_intro(__("You are the Leave Approver for this record. Please Update the 'Status' and Save"));
					frm.toggle_enable("status", true);
				} else {
					frm.set_intro(__("This Leave Application is pending approval. Only the Leave Approver can update status."))
					frm.toggle_enable("status", false);
				}
			}
		}
	},

	leave_approver: function(frm) {
		frm.set_value("leave_approver_name", frappe.user.full_name(frm.doc.leave_approver));
	},

	employee: function(frm) {
		frm.trigger("get_leave_balance");
	},

	leave_type: function(frm) {
		frm.trigger("get_leave_balance");
	},

	half_day: function(frm) {
		if (frm.doc.from_date) {
			frm.set_value("to_date", frm.doc.from_date);
			frm.trigger("calculate_total_days");
		}
	},

	from_date: function(frm) {
		if (cint(frm.doc.half_day)==1) {
			frm.set_value("to_date", frm.doc.from_date);
		}
		frm.trigger("calculate_total_days");
	},

	to_date: function(frm) {
		if (cint(frm.doc.half_day)==1 && cstr(frm.doc.from_date) && frm.doc.from_date != frm.doc.to_date) {
			msgprint(__("To Date should be same as From Date for Half Day leave"));
			frm.set_value("to_date", frm.doc.from_date);
		}

		frm.trigger("calculate_total_days");
	},

	get_leave_balance: function(frm) {
		if(frm.doc.docstatus==0 && frm.doc.employee && frm.doc.leave_type && frm.doc.from_date && frm.doc.to_date) {
			return frm.call({
				method: "get_leave_balance",
				args: {
					employee: frm.doc.employee,
					from_date: frm.doc.from_date,
					to_date: frm.doc.to_date,
					leave_type: frm.doc.leave_type
				}
			});
		}
	},

	calculate_total_days: function(frm) {
		if(frm.doc.from_date && frm.doc.to_date) {
			if (cint(frm.doc.half_day)==1) {
				frm.set_value("total_leave_days", 0.5);
			} else {
				// server call is done to include holidays in leave days calculations
				return frappe.call({
					method: 'erpnext.hr.doctype.leave_application.leave_application.get_total_leave_days',
					args: { leave_app: frm.doc },
					callback: function(response) {
						if (response && response.message) {
							frm.set_value('total_leave_days', response.message.total_leave_days);
							frm.trigger("get_leave_balance");
						}
					}
				});
			}
		}
	},

});
