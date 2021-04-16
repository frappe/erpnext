// Copyright (c) 2020, earthians and contributors
// For license information, please see license.txt

frappe.ui.form.on('Healthcare Service Order', {
	onload: function(frm) {
		frm.set_query('order_group', function () {
			return {
				filters: {
					'docstatus': 1,
					'patient': frm.doc.patient,
					'practitioner': frm.doc.ordered_by
				}
			};
		});

		frm.set_query('order_doctype', function() {
			let service_order_doctypes = ['Medication', 'Therapy Type', 'Lab Test Template',
				'Clinical Procedure Template'];
			return {
				filters: {
					name: ['in', service_order_doctypes]
				}
			};
		});

		frm.set_query('patient', function () {
			return {
				filters: {
					'status': 'Active'
				}
			};
		});

		frm.set_query('staff_role', function () {
			return {
				filters: {
					'restrict_to_domain': 'Healthcare'
				}
			};
		});
	},

	patient: function(frm) {
		if (!frm.doc.patient) {
			frm.set_values ({
				'patient_name': '',
				'gender': '',
				'patient_age': '',
				'mobile': '',
				'email': '',
				'inpatient_record': '',
				'inpatient_status': '',
			});
		}
	},

	birth_date: function(frm) {
		age_str = calculate_age(frm.doc.birth_date);
		frm.set_value('patient_age', age_str);
	}
});


let calculate_age = function(birth) {
	let ageMS = Date.parse(Date()) - Date.parse(birth);
	let age = new Date();
	age.setTime(ageMS);
	let years =  age.getFullYear() - 1970;
	return `${years} ${__('Years(s)')} ${age.getMonth()} ${__('Month(s)')} ${age.getDate()} ${__('Day(s)')}`;
};
