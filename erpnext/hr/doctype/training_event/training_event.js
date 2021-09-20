// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Training Event', {
	onload_post_render: function (frm) {
		frm.get_field("employees").grid.set_multiple_add("employee");
	},
	refresh: function (frm) {
		if (!frm.doc.__islocal) {
			frm.add_custom_button(__("Training Result"), function () {
				frappe.route_options = {
					training_event: frm.doc.name
				};
				frappe.set_route("List", "Training Result");
			});
			frm.add_custom_button(__("Training Feedback"), function () {
				frappe.route_options = {
					training_event: frm.doc.name
				};
				frappe.set_route("List", "Training Feedback");
			});
		}
		frm.events.set_employee_query(frm);
	},
	

	start_time: function (frm) {
		frappe.call({
			method: "erpnext.nepali_date.get_converted_date",
			args: {
				date: frm.doc.start_time
			},
			callback: function (resp) {
				if (resp.message) {
					cur_frm.set_value("start_time_nepal", resp.message)
				}
			}
		})
	},
	end_time: function (frm) {
		frappe.call({
			method: "erpnext.nepali_date.get_converted_date",
			args: {
				date: frm.doc.end_time
			},
			callback: function (resp) {
				if (resp.message) {
					cur_frm.set_value("end_time_nepal", resp.message)
				}
			}
		})
	},


	set_employee_query: function(frm) {
		let emp = [];
		for (let d in frm.doc.employees) {
			if (frm.doc.employees[d].employee) {
				emp.push(frm.doc.employees[d].employee);
			}
		}
		frm.set_query("employee", "employees", function () {
			return {
				filters: {
					name: ["NOT IN", emp],
					status: "Active"
				}
			};
		});
	}
});

frappe.ui.form.on("Training Event Employee", {
	employee: function(frm) {
		frm.events.set_employee_query(frm);
	}
});
