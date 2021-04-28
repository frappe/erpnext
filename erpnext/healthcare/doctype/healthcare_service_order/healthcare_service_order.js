// Copyright (c) 2020, earthians and contributors
// For license information, please see license.txt

frappe.ui.form.on('Healthcare Service Order', {
	refresh: function(frm) {
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

		frm.trigger('setup_status_buttons');
	},

	setup_status_buttons: function(frm) {
		if (frm.doc.docstatus === 1) {

			if (frm.doc.status === 'Active') {
				frm.add_custom_button(__('On Hold'), function() {
					frm.events.set_status(frm, status='On Hold')
				}, __('Status'));

				frm.add_custom_button(__('Completed'), function() {
					frm.events.set_status(frm, status='Completed')
				}, __('Status'));
			}

			if (frm.doc.status === 'On Hold') {
				frm.add_custom_button(__('Active'), function() {
					frm.events.set_status(frm, status='Active')
				}, __('Status'));

				frm.add_custom_button(__('Completed'), function() {
					frm.events.set_status(frm, status='Completed')
				}, __('Status'));
			}

		} else if (frm.doc.docstatus === 2) {

			frm.add_custom_button(__('Revoked'), function() {
				frm.events.set_status(frm, status='Revoked')
			}, __('Status'));

			frm.add_custom_button(__('Replaced'), function() {
				frm.events.set_status(frm, status='Replaced')
			}, __('Status'));

			frm.add_custom_button(__('Entered in Error'), function() {
				frm.events.set_status(frm, status='Entered in Error')
			}, __('Status'));

			frm.add_custom_button(__('Unknown'), function() {
				frm.events.set_status(frm, status='Unknown')
			}, __('Status'));

		}
	},

	set_status: function(frm, status) {
		frappe.call({
			method: 'erpnext.healthcare.doctype.healthcare_service_order.healthcare_service_order.set_status',
			async: false,
			freeze: true,
			args: {
				docname: frm.doc.name,
				status: status
			},
			callback: function(r) {
				frm.reload_doc();
			}
		});
	},

	after_cancel: function(frm) {
		frappe.prompt([
			{
				fieldname: 'reason_for_cancellation',
				label: __('Reason for Cancellation'),
				fieldtype: 'Select',
				options: ['Revoked', 'Replaced', 'Entered in Error', 'Unknown'],
				reqd: 1
			}
		],
		function(data) {
			frm.events.set_status(frm, data.reason_for_cancellation);
		}, __('Reason for Cancellation'), __('Submit'));
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
