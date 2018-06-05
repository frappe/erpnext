// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Employee Tax Exemption Declaration', {
	refresh: function(frm){
		if(frm.doc.__islocal){
			frm.set_df_property('hra_declaration_section', 'hidden', 1);
		}
	},
	setup: function(frm) {
		frm.set_query('employee', function() {
			return {
				filters: {
					'status': "Active"
				}
			}
		});
		frm.set_query('payroll_period', function() {
			const fields = {'employee': 'Employee', 'company': 'Company'};

			for (let [field, label] of Object.entries(fields)) {
				if (!frm.doc[field]) {
					frappe.msgprint(__("Please select {0}", [label]))
				}
			};

			if (frm.doc.employee && frm.doc.company){
				return {
					filters: {
						'company': frm.doc.company
					}
				}
			}
		});
		frm.set_query('exemption_sub_category', 'declarations', function() {
			return {
				filters: {
					'is_active': 1
				}
			}
		});
	},
	employee: function(frm){
		frm.trigger('set_null_value');
	},
	company: function(frm) {
		if(frm.doc.company){
			frappe.call({
				method: "frappe.client.get_value",
				args: {
					doctype: "Company",
					filters: {"name": frm.doc.company},
					fieldname: "hra_component"
				},
				callback: function(r){
					if(r.message.hra_component){
						frm.set_df_property('hra_declaration_section', 'hidden', 0);
					}
				}
			});
		}
	},
	monthly_house_rent: function(frm) {
		frm.trigger("calculate_hra_exemption");
	},
	rented_in_metro_city: function(frm) {
		frm.trigger("calculate_hra_exemption");
	},
	calculate_hra_exemption: function(frm) {
		frappe.call({
			method: "calculate_hra_exemption",
			doc: frm.doc,
			callback: function(r) {
				if (!r.exc){
					frm.refresh_fields();
				}
			}
		});
	},
	set_null_value(frm){
		let fields = ['salary_structure_hra', 'monthly_house_rent','annual_hra_exemption',
			'monthly_hra_exemption', 'total_exemption_amount', 'payroll_period'];
		fields.forEach(function(field) {
			frm.set_value(field, '');
		});
	}
});
