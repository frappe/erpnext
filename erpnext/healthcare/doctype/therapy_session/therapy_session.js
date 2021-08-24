// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Therapy Session', {
	setup: function(frm) {
		frm.get_field('exercises').grid.editable_fields = [
			{fieldname: 'exercise_type', columns: 7},
			{fieldname: 'counts_target', columns: 1},
			{fieldname: 'counts_completed', columns: 1},
			{fieldname: 'assistance_level', columns: 1}
		];

		frm.set_query('service_unit', function() {
			return {
				filters: {
					'is_group': false,
					'allow_appointments': true,
					'company': frm.doc.company
				}
			};
		});

		frm.set_query('appointment', function() {

			return {
				filters: {
					'status': ['in', ['Open', 'Scheduled']]
				}
			};
		});
	},

	refresh: function(frm) {
		if (frm.doc.therapy_plan) {
			frm.trigger('filter_therapy_types');
		}

		if (!frm.doc.__islocal) {
			frm.dashboard.add_indicator(__('Counts Targeted: {0}', [frm.doc.total_counts_targeted]), 'blue');
			frm.dashboard.add_indicator(__('Counts Completed: {0}', [frm.doc.total_counts_completed]),
				(frm.doc.total_counts_completed < frm.doc.total_counts_targeted) ? 'orange' : 'green');
		}

		if (frm.doc.docstatus === 1) {
			frm.add_custom_button(__('Patient Assessment'), function() {
				frappe.model.open_mapped_doc({
					method: 'erpnext.healthcare.doctype.patient_assessment.patient_assessment.create_patient_assessment',
					frm: frm,
				})
			}, 'Create');

			frappe.db.get_value('Therapy Plan', {'name': frm.doc.therapy_plan}, 'therapy_plan_template', (r) => {
				if (r && !r.therapy_plan_template) {
					frm.add_custom_button(__('Sales Invoice'), function() {
						frappe.model.open_mapped_doc({
							method: 'erpnext.healthcare.doctype.therapy_session.therapy_session.invoice_therapy_session',
							frm: frm,
						});
					}, 'Create');
				}
			});
		}
	},

	therapy_plan: function(frm) {
		if (frm.doc.therapy_plan) {
			frm.trigger('filter_therapy_types');
		}
	},

	filter_therapy_types: function(frm) {
		frappe.call({
			'method': 'frappe.client.get',
			args: {
				doctype: 'Therapy Plan',
				name: frm.doc.therapy_plan
			},
			callback: function(data) {
				let therapy_types = (data.message.therapy_plan_details || []).map(function(d){ return d.therapy_type; });
				frm.set_query('therapy_type', function() {
					return {
						filters: { 'therapy_type': ['in', therapy_types]}
					};
				});
			}
		});
	},

	patient: function(frm) {
		if (frm.doc.patient) {
			frappe.call({
				'method': 'erpnext.healthcare.doctype.patient.patient.get_patient_detail',
				args: {
					patient: frm.doc.patient
				},
				callback: function (data) {
					let age = '';
					if (data.message.dob) {
						age = calculate_age(data.message.dob);
					} else if (data.message.age) {
						age = data.message.age;
						if (data.message.age_as_on) {
							age = __('{0} as on {1}', [age, data.message.age_as_on]);
						}
					}
					frm.set_value('patient_age', age);
					frm.set_value('gender', data.message.sex);
					frm.set_value('patient_name', data.message.patient_name);
				}
			});
		} else {
			frm.set_value('patient_age', '');
			frm.set_value('gender', '');
			frm.set_value('patient_name', '');
		}
	},

	appointment: function(frm) {
		if (frm.doc.appointment) {
			frappe.call({
				'method': 'frappe.client.get',
				args: {
					doctype: 'Patient Appointment',
					name: frm.doc.appointment
				},
				callback: function(data) {
					let values = {
						'patient':data.message.patient,
						'therapy_type': data.message.therapy_type,
						'therapy_plan': data.message.therapy_plan,
						'practitioner': data.message.practitioner,
						'department': data.message.department,
						'start_date': data.message.appointment_date,
						'start_time': data.message.appointment_time,
						'service_unit': data.message.service_unit,
						'company': data.message.company,
						'duration': data.message.duration
					};
					frm.set_value(values);
				}
			});
		}
	},

	therapy_type: function(frm) {
		if (frm.doc.therapy_type) {
			frappe.call({
				'method': 'frappe.client.get',
				args: {
					doctype: 'Therapy Type',
					name: frm.doc.therapy_type
				},
				callback: function(data) {
					frm.set_value('duration', data.message.default_duration);
					frm.set_value('rate', data.message.rate);
					frm.set_value('service_unit', data.message.healthcare_service_unit);
					frm.set_value('department', data.message.medical_department);
					frm.doc.exercises = [];
					$.each(data.message.exercises, function(_i, e) {
						let exercise = frm.add_child('exercises');
						exercise.exercise_type = e.exercise_type;
						exercise.difficulty_level = e.difficulty_level;
						exercise.counts_target = e.counts_target;
						exercise.assistance_level = e.assistance_level;
					});
					refresh_field('exercises');
				}
			});
		}
	}
});
