// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Leave Period', {
	refresh: (frm)=>{
		frm.set_df_property("grant_leaves", "hidden", frm.doc.__islocal ? 1:0);
		if(!frm.is_new()) {
			frm.add_custom_button(__('Grant Leaves'), function () {
				frm.trigger("grant_leaves");
			});
		}
	},
	from_date: (frm)=>{
		if (frm.doc.from_date && !frm.doc.to_date) {
			var a_year_from_start = frappe.datetime.add_months(frm.doc.from_date, 12);
			frm.set_value("to_date", frappe.datetime.add_days(a_year_from_start, -1));
		}
	},
	onload: (frm) => {
		frm.set_query("department", function() {
			return {
				"filters": {
					"company": frm.doc.company,
				}
			}
		})
	},
	grant_leaves: function(frm) {
		var d = new frappe.ui.Dialog({
			title: __('Grant Leaves'),
			fields: [
				{
					"label": "Filter Employees By (Optional)",
					"fieldname": "sec_break",
					"fieldtype": "Section Break",
				},
				{
					"label": "Employee Grade",
					"fieldname": "grade",
					"fieldtype": "Link",
					"options": "Employee Grade"
				},
				{
					"label": "Department",
					"fieldname": "department",
					"fieldtype": "Link",
					"options": "Department"
				},
				{
					"fieldname": "col_break",
					"fieldtype": "Column Break",
				},
				{
					"label": "Designation",
					"fieldname": "designation",
					"fieldtype": "Link",
					"options": "Designation"
				},
				{
					"label": "Employee",
					"fieldname": "employee",
					"fieldtype": "Link",
					"options": "Employee"
				},
				{
					"fieldname": "sec_break",
					"fieldtype": "Section Break",
				},
				{
					"label": "Add unused leaves from previous allocations",
					"fieldname": "carry_forward_leaves",
					"fieldtype": "Check"
				}
			],
			primary_action: function() {
				var data = d.get_values();

				frappe.call({
					doc: frm.doc,
					method: "grant_leave_allocation",
					args: data,
					callback: function(r) {
						if(!r.exc) {
							d.hide();
							frm.reload_doc();
						}
					}
				});
			},
			primary_action_label: __('Grant')
		});
		d.show();
	}
});
