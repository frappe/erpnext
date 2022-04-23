// Copyright (c) 2016, ESS LLP and contributors
// For license information, please see license.txt

frappe.ui.form.on('Healthcare Practitioner', {
	setup: function(frm) {
		frm.set_query('account', 'accounts', function(doc, cdt, cdn) {
			let d = locals[cdt][cdn];
			return {
				filters: {
					'root_type': 'Income',
					'company': d.company,
					'is_group': 0
				}
			};
		});
	},
	refresh: function(frm) {
		frappe.dynamic_link = {doc: frm.doc, fieldname: 'name', doctype: 'Healthcare Practitioner'};

		if (!frm.is_new()) {
			frappe.contacts.render_address_and_contact(frm);
		} else {
			frappe.contacts.clear_address_and_contact(frm);
		}

		frm.set_query('service_unit', 'practitioner_schedules', function(){
			return {
				filters: {
					'is_group': false,
					'allow_appointments': true
				}
			};
		});

		set_query_service_item(frm, 'inpatient_visit_charge_item');
		set_query_service_item(frm, 'op_consulting_charge_item');
	}
});

let set_query_service_item = function(frm, service_item_field) {
	frm.set_query(service_item_field, function() {
		return {
			filters: {
				'is_sales_item': 1,
				'is_stock_item': 0
			}
		};
	});
};

frappe.ui.form.on('Healthcare Practitioner', 'user_id',function(frm) {
	if (frm.doc.user_id) {
		frappe.call({
			'method': 'frappe.client.get',
			args: {
				doctype: 'User',
				name: frm.doc.user_id
			},
			callback: function (data) {

				frappe.model.get_value('Employee', {'user_id': frm.doc.user_id}, 'name',
					function(data) {
						if (data) {
							if (!frm.doc.employee || frm.doc.employee != data.name)
								frappe.model.set_value(frm.doctype, frm.docname, 'employee', data.name);
						} else {
							frappe.model.set_value(frm.doctype, frm.docname, 'employee', '');
						}
					}
				);

				if (!frm.doc.first_name || frm.doc.first_name != data.message.first_name)
					frappe.model.set_value(frm.doctype,frm.docname, 'first_name', data.message.first_name);
				if (!frm.doc.middle_name || frm.doc.middle_name != data.message.middle_name)
					frappe.model.set_value(frm.doctype,frm.docname, 'middle_name', data.message.middle_name);
				if (!frm.doc.last_name || frm.doc.last_name != data.message.last_name)
					frappe.model.set_value(frm.doctype,frm.docname, 'last_name', data.message.last_name);
				if (!frm.doc.mobile_phone || frm.doc.mobile_phone != data.message.mobile_no)
					frappe.model.set_value(frm.doctype,frm.docname, 'mobile_phone', data.message.mobile_no);
			}
		});
	}
});

frappe.ui.form.on('Healthcare Practitioner', 'employee', function(frm) {
	if (frm.doc.employee){
		frappe.call({
			'method': 'frappe.client.get',
			args: {
				doctype: 'Employee',
				name: frm.doc.employee
			},
			callback: function (data) {
				if (!frm.doc.user_id || frm.doc.user_id != data.message.user_id)
					frm.set_value('user_id', data.message.user_id);
				if (!frm.doc.designation || frm.doc.designation != data.message.designation)
					frappe.model.set_value(frm.doctype,frm.docname, 'designation', data.message.designation);
				if (!frm.doc.first_name || !frm.doc.user_id){
					frappe.model.set_value(frm.doctype,frm.docname, 'first_name', data.message.first_name);
					frappe.model.set_value(frm.doctype,frm.docname, 'middle_name', '');
					frappe.model.set_value(frm.doctype,frm.docname, 'last_name', data.message.last_name);
				}
				if (!frm.doc.mobile_phone || !frm.doc.user_id)
					frappe.model.set_value(frm.doctype,frm.docname, 'mobile_phone', data.message.cell_number);
				if (!frm.doc.address || frm.doc.address != data.message.current_address)
					frappe.model.set_value(frm.doctype,frm.docname, 'address', data.message.current_address);
			}
		});
	}
});

frappe.tour['Healthcare Practitioner'] = [
	{
		fieldname: 'employee',
		title: __('Employee'),
		description: __('If you want to track Payroll and other HRMS operations for a Practitoner, create an Employee and link it here.')
	},
	{
		fieldname: 'practitioner_schedules',
		title: __('Practitioner Schedules'),
		description: __('Set the Practitioner Schedule you just created. This will be used while booking appointments.')
	},
	{
		fieldname: 'op_consulting_charge_item',
		title: __('Out Patient Consulting Charge Item'),
		description: __('Create a service item for Out Patient Consulting.')
	},
	{
		fieldname: 'inpatient_visit_charge_item',
		title: __('Inpatient Visit Charge Item'),
		description: __('If this Healthcare Practitioner works for the In-Patient Department, create a service item for Inpatient Visits.')
	},
	{
		fieldname: 'op_consulting_charge',
		title: __('Out Patient Consulting Charge'),
		description: __('Set the Out Patient Consulting Charge for this Practitioner.')

	},
	{
		fieldname: 'inpatient_visit_charge',
		title: __('Inpatient Visit Charge'),
		description: __('If this Healthcare Practitioner also works for the In-Patient Department, set the inpatient visit charge for this Practitioner.')
	}
];

