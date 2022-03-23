// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.add_fetch('employee', 'employee_name', 'employee_name');

frappe.ui.form.on("Leave Allocation", {
	onload: function(frm) {
		// Ignore cancellation of doctype on cancel all.
		frm.ignore_doctypes_on_cancel_all = ["Leave Ledger Entry"];

		if (!frm.doc.from_date) frm.set_value("from_date", frappe.datetime.get_today());

		frm.set_query("employee", function() {
			return {
				query: "erpnext.controllers.queries.employee_query"
			};
		});
		frm.set_query("leave_type", function() {
			return {
				filters: {
					is_lwp: 0
				}
			};
		});
	},

	refresh: function(frm) {
		if (frm.doc.docstatus === 1 && frm.doc.expired) {
			var valid_expiry = moment(frappe.datetime.get_today()).isBetween(frm.doc.from_date, frm.doc.to_date);
			if (valid_expiry) {
				// expire current allocation
				frm.add_custom_button(__('Expire Allocation'), function() {
					frm.trigger("expire_allocation");
				});
			}
		}
	},

	expire_allocation: function(frm) {
		frappe.call({
			method: 'erpnext.hr.doctype.leave_ledger_entry.leave_ledger_entry.expire_allocation',
			args: {
				'allocation': frm.doc,
				'expiry_date': frappe.datetime.get_today()
			},
			freeze: true,
			callback: function(r) {
				if (!r.exc) {
					frappe.msgprint(__("Allocation Expired!"));
				}
				frm.refresh();
			}
		});
	},

	employee: function(frm) {
		frm.trigger("calculate_total_leaves_allocated");
	},

	leave_type: function(frm) {
		frm.trigger("leave_policy");
		frm.trigger("calculate_total_leaves_allocated");
	},

	carry_forward: function(frm) {
		frm.trigger("calculate_total_leaves_allocated");
	},

	unused_leaves: function(frm) {
		frm.set_value("total_leaves_allocated",
			flt(frm.doc.unused_leaves) + flt(frm.doc.new_leaves_allocated));
	},

	new_leaves_allocated: function(frm) {
		frm.set_value("total_leaves_allocated",
			flt(frm.doc.unused_leaves) + flt(frm.doc.new_leaves_allocated));
	},

	leave_policy: function(frm) {
		if (frm.doc.leave_policy && frm.doc.leave_type) {
			frappe.db.get_value("Leave Policy Detail", {
				'parent': frm.doc.leave_policy,
				'leave_type': frm.doc.leave_type
			}, 'annual_allocation', (r) => {
				if (r && !r.exc) frm.set_value("new_leaves_allocated", flt(r.annual_allocation));
			}, "Leave Policy");
		}
	},
	calculate_total_leaves_allocated: function(frm) {
		if (cint(frm.doc.carry_forward) == 1 && frm.doc.leave_type && frm.doc.employee) {
			return frappe.call({
				method: "set_total_leaves_allocated",
				doc: frm.doc,
				callback: function() {
					frm.refresh_fields();
				}
			});
		} else if (cint(frm.doc.carry_forward) == 0) {
			frm.set_value("unused_leaves", 0);
			frm.set_value("total_leaves_allocated", flt(frm.doc.new_leaves_allocated));
		}
	}
});

frappe.tour["Leave Allocation"] = [
	{
		fieldname: "employee",
		title: "Employee",
		description: __("Select the Employee for which you want to allocate leaves.")
	},
	{
		fieldname: "leave_type",
		title: "Leave Type",
		description: __("Select the Leave Type like Sick leave, Privilege Leave, Casual Leave, etc.")
	},
	{
		fieldname: "from_date",
		title: "From Date",
		description: __("Select the date from which this Leave Allocation will be valid.")
	},
	{
		fieldname: "to_date",
		title: "To Date",
		description: __("Select the date after which this Leave Allocation will expire.")
	},
	{
		fieldname: "new_leaves_allocated",
		title: "New Leaves Allocated",
		description: __("Enter the number of leaves you want to allocate for the period.")
	}
];
