frappe.listview_settings['Leave Policy Assignment'] = {
	onload: function (list_view) {
		let me = this;
		list_view.page.add_inner_button(__("Bulk Leave Policy Assignment"), function () {
			me.dialog = new frappe.ui.form.MultiSelectDialog({
				doctype: "Employee",
				target: cur_list,
				setters: {
					employee_name: '',
					company: '',
					department: '',
				},
				data_fields: [{
					fieldname: 'leave_policy',
					fieldtype: 'Link',
					options: 'Leave Policy',
					label: __('Leave Policy'),
					reqd: 1
				},
				{
					fieldname: 'assignment_based_on',
					fieldtype: 'Select',
					options: ["", "Leave Period"],
					label: __('Assignment Based On'),
					onchange: () => {
						if (cur_dialog.fields_dict.assignment_based_on.value === "Leave Period") {
							cur_dialog.set_df_property("effective_from", "read_only", 1);
							cur_dialog.set_df_property("leave_period", "reqd", 1);
							cur_dialog.set_df_property("effective_to", "read_only", 1);
						} else {
							cur_dialog.set_df_property("effective_from", "read_only", 0);
							cur_dialog.set_df_property("leave_period", "reqd", 0);
							cur_dialog.set_df_property("effective_to", "read_only", 0);
							cur_dialog.set_value("effective_from", "");
							cur_dialog.set_value("effective_to", "");
						}
					}
				},
				{
					fieldname: "leave_period",
					fieldtype: 'Link',
					options: "Leave Period",
					label: __('Leave Period'),
					depends_on: doc => {
						return doc.assignment_based_on == 'Leave Period';
					},
					onchange: () => {
						if (cur_dialog.fields_dict.leave_period.value) {
							me.set_effective_date();
						}
					}
				},
				{
					fieldtype: "Column Break"
				},
				{
					fieldname: 'effective_from',
					fieldtype: 'Date',
					label: __('Effective From'),
					reqd: 1
				},
				{
					fieldname: 'effective_to',
					fieldtype: 'Date',
					label: __('Effective To'),
					reqd: 1
				},
				{
					fieldname: 'carry_forward',
					fieldtype: 'Check',
					label: __('Add unused leaves from previous allocations')
				}
				],
				get_query() {
					return {
						filters: {
							status: ['=', 'Active']
						}
					};
				},
				add_filters_group: 1,
				primary_action_label: "Assign",
				action(employees, data) {
					frappe.call({
						method: 'erpnext.hr.doctype.leave_policy_assignment.leave_policy_assignment.create_assignment_for_multiple_employees',
						async: false,
						args: {
							employees: employees,
							data: data
						}
					});
					cur_dialog.hide();
				}
			});
		});
	},

	set_effective_date: function () {
		if (cur_dialog.fields_dict.assignment_based_on.value === "Leave Period" && cur_dialog.fields_dict.leave_period.value) {
			frappe.model.with_doc("Leave Period", cur_dialog.fields_dict.leave_period.value, function () {
				let from_date = frappe.model.get_value("Leave Period", cur_dialog.fields_dict.leave_period.value, "from_date");
				let to_date = frappe.model.get_value("Leave Period", cur_dialog.fields_dict.leave_period.value, "to_date");
				cur_dialog.set_value("effective_from", from_date);
				cur_dialog.set_value("effective_to", to_date);
			});
		}
	}
};
