frappe.provide('erpnext.hr');

erpnext.hr.EmployeeFilter = class EmployeeFilter{
	constructor(frm, method ,title, primary_action_label) {
		this.primary_action_label = primary_action_label;
		this.title = title;
		this.doctype = "Employee";
		this.method = method;
		this.frm = frm;
		frappe.model.with_doctype("Employee");
	}

	make_dialog(){
		this.fields = [
			{
				fieldname: "company",
				fieldtype: "Link",
				options: "Company",
				label: __("Company"),
				default: this.frm.doc.company,
				read_only:1
			},
			{
				fieldname: "assign_to",
				fieldtype: "Select",
				options: [
					{
						label: __('Select Employees'),
						value: 'select_emp'
					},
					{
						label: __('Filter Employees'),
						value: 'filter_emp'
					},
				],
				label: __("Assign To"),
				default: "Select Employee",
				onchange: function(){
					me.set_filters(d);
				}
			},
			{
				fieldname:'employees',
				fieldtype:'MultiSelectList',
				label: __('Employees'),
				get_data: function(txt) {
					return frappe.db.get_link_options('Employee', txt);
				},
				depends_on: "eval:doc.assign_to == 'select_emp'",
			},
			{
				fieldtype: 'HTML',
				fieldname: 'filter_area',
				depends_on: "eval:doc.assign_to == 'filter_emp'",
			}
		]
		if (this.frm.doc.doctype == "Salary Structure"){
			this.fields = this.fields.concat([
				{
					fieldname:'base_variable',
					fieldtype:'Section Break'
				},
				{
					fieldname:'from_date',
					fieldtype:'Date',
					label: __('From Date'),
					reqd: 1
				},
				{
					fieldname:'base_col_br',
					fieldtype:'Column Break'
				},
				{
					fieldname:'base',
					fieldtype:'Currency',
					label: __('Base')
				},
				{
					fieldname:'variable',
					fieldtype:'Currency',
					label: __('Variable')
				}
			]);
		}
		if (this.frm.doc.doctype == "Leave Period"){
			this.fields = this.fields.concat([
				{
					"fieldname": "sec_break",
					"fieldtype": "Section Break",
				},
				{
					"label": "Add unused leaves from previous allocations",
					"fieldname": "carry_forward",
					"fieldtype": "Check"
				}
			])
		}
		let me = this;
		var d = new frappe.ui.Dialog({
			title: __(this.title),
			fields: this.fields,
			primary_action: function() {
				var data = d.get_values();
				if (data.assign_to == "filter_emp"){
					data.employees = [];
					data.filters = me.get_filters();
				}
				frappe.call({
					doc: me.frm.doc,
					method: me.method,
					args: data,
					callback: function(r) {
						if(!r.exc) {
							me.frm.reload_doc();
						}
						d.hide();
						me.frm.refresh();

					}
				});
			},
			primary_action_label: __(this.primary_action_label)
		});
		this.make_filter_area(d);
		this.set_filters(d);
		d.show();
	}


	set_filters(d){
		if (d.fields_dict.assign_to.value == "filter_emp"){
			frappe.db.count("Employee", {filters: this.get_filters()}).then(value => {
				var message = __(cstr(value) + " Employees selected");
				d.set_df_property("assign_to", 'description', message);
			});
		}else{
			d.set_df_property("assign_to", 'description', " ");
		}
	}

	make_filter_area(dialog) {
		this.filter_group = new frappe.ui.FilterGroup({
			parent: dialog.get_field('filter_area').$wrapper,
			doctype: "Employee",
			on_change: () => {
				this.set_filters(dialog);
			}
		});
	}

	get_filters(){
		return this.filter_group.get_filters().reduce((acc, filter) => {
			return Object.assign(acc, {
				[filter[1]]: [filter[2], filter[3]]
			});
		}, {});
	}

}