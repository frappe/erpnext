// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Leave Policy Assignment', {
	onload: function(frm) {
		frm.ignore_doctypes_on_cancel_all = ["Leave Ledger Entry"];

		frm.set_query('leave_policy', function() {
			return {
				filters: {
					"docstatus": 1
				}
			};
		});
		frm.set_query('leave_period', function() {
			return {
				filters: {
					"is_active": 1,
					"company": frm.doc.company
				}
			};
		});
	},

	assignment_based_on: function(frm) {
		if (frm.doc.assignment_based_on) {
			frm.events.set_effective_date(frm);
		} else {
			frm.set_value("effective_from", '');
			frm.set_value("effective_to", '');
		}
	},

	leave_period: function(frm) {
		if (frm.doc.leave_period) {
			frm.events.set_effective_date(frm);
		}
	},

	set_effective_date: function(frm) {
		if (frm.doc.assignment_based_on == "Leave Period" && frm.doc.leave_period) {
			frappe.model.with_doc("Leave Period", frm.doc.leave_period, function () {
				let from_date = frappe.model.get_value("Leave Period", frm.doc.leave_period, "from_date");
				let to_date = frappe.model.get_value("Leave Period", frm.doc.leave_period, "to_date");
				frm.set_value("effective_from", from_date);
				frm.set_value("effective_to", to_date);

			});
		} else if (frm.doc.assignment_based_on == "Joining Date" && frm.doc.employee) {
			frappe.model.with_doc("Employee", frm.doc.employee, function () {
				let from_date = frappe.model.get_value("Employee", frm.doc.employee, "date_of_joining");
				let from_date1 = frappe.model.get_value("Employee", frm.doc.employee, "confimation_date");
				frm.set_value("effective_from", from_date1);
				frm.set_value("effective_to", frappe.datetime.add_months(frm.doc.effective_from, 12));
			});
		}
		frm.refresh();
	}

});
// frappe.ui.form.on('Leave Policy Assignment', {
//     before_save: function(frm) {
//         frappe.call({
//             method: "erpnext.hr.doctype.leave_allocation.leave_allocation.get_carry_forwarded_leaves",
//             args: {
//                 employee: frm.doc.employee,
// 				date :frm.doc.effective_from,
// 				leave_type: "Privilege Leave",
// 				carry_forward : frm.doc.carry_forward
//             },
//             async: false, // Wait for the call to complete before saving
//             callback: function(r) {
//                 if (!r.exc && r.message) {
//                     // Update the "joining_opening_balance" field with the response value
//                     frm.doc.joining_opening_balance = r.message;
//                 }
//             }
//         });
//     }
// });
frappe.ui.form.on('Leave Policy Assignment', {
    effective_from: function(frm) {
        if (frm.doc.effective_from) {
            // Extract the year from the effective_from date
            var year = frm.doc.effective_from.split('-')[0];
			console.log(year)
            // Set the "year" field and refresh it
            frm.set_value('year', year);
            frm.refresh_field('year', year);
        }
    }
});
