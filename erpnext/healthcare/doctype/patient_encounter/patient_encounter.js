// Copyright (c) 2016, ESS LLP and contributors
// For license information, please see license.txt

frappe.ui.form.on('Patient Encounter', {
	setup: function(frm) {
		frm.get_field('drug_prescription').grid.editable_fields = [
			{fieldname: 'drug_code', columns: 2},
			{fieldname: 'drug_name', columns: 2},
			{fieldname: 'dosage', columns: 2},
			{fieldname: 'period', columns: 2}
		];
		frm.get_field('lab_test_prescription').grid.editable_fields = [
			{fieldname: 'lab_test_code', columns: 2},
			{fieldname: 'lab_test_name', columns: 4},
			{fieldname: 'lab_test_comment', columns: 4}
		];
	},

	refresh: function(frm) {
		refresh_field('drug_prescription');
		refresh_field('lab_test_prescription');

		if (!frm.doc.__islocal) {

			if (frm.doc.inpatient_status == 'Admission Scheduled' || frm.doc.inpatient_status == 'Admitted') {
				frm.add_custom_button(__('Schedule Discharge'), function() {
					schedule_discharge(frm);
				});
			} else if (frm.doc.inpatient_status != 'Discharge Scheduled') {
				frm.add_custom_button(__('Schedule Admission'), function() {
					schedule_inpatient(frm);
				});
			}

			frm.add_custom_button(__('Patient History'), function() {
				if (frm.doc.patient) {
					frappe.route_options = {'patient': frm.doc.patient};
					frappe.set_route('patient_history');
				} else {
					frappe.msgprint(__('Please select Patient'));
				}
			},'View');

			frm.add_custom_button(__('Vital Signs'), function() {
				create_vital_signs(frm);
			},'Create');

			frm.add_custom_button(__('Medical Record'), function() {
				create_medical_record(frm);
			},'Create');

			frm.add_custom_button(__('Clinical Procedure'), function() {
				create_procedure(frm);
			},'Create');

		}

		frm.set_query('patient', function() {
			return {
				filters: {'status': 'Active'}
			};
		});

		frm.set_query('drug_code', 'drug_prescription', function() {
			return {
				filters: {
					is_stock_item: 1
				}
			};
		});

		frm.set_query('lab_test_code', 'lab_test_prescription', function() {
			return {
				filters: {
					is_billable: 1
				}
			};
		});

		frm.set_query('appointment', function() {
			return {
				filters: {
					//	Scheduled filter for demo ...
					status:['in',['Open','Scheduled']]
				}
			};
		});

		frm.set_df_property('patient', 'read_only', frm.doc.appointment ? 1 : 0);
	},

	appointment: function(frm) {
		frm.events.set_appointment_fields(frm);
	},

	patient: function(frm) {
		frm.events.set_patient_info(frm);
	},

	set_appointment_fields: function(frm) {
		if (frm.doc.appointment) {
			frappe.call({
				method: 'frappe.client.get',
				args: {
					doctype: 'Patient Appointment',
					name: frm.doc.appointment
				},
				callback: function(data) {
					let values = {
						'patient':data.message.patient,
						'type': data.message.appointment_type,
						'practitioner': data.message.practitioner,
						'invoiced': data.message.invoiced
					};
					frm.set_value(values);
				}
			});
		}
		else {
			let values = {
				'patient': '',
				'patient_name': '',
				'type': '',
				'practitioner': '',
				'invoiced': 0,
				'patient_sex': '',
				'patient_age': '',
				'inpatient_record': '',
				'inpatient_status': ''
			};
			frm.set_value(values);
		}
	},

	set_patient_info: function(frm) {
		if (frm.doc.patient) {
			frappe.call({
				method: 'erpnext.healthcare.doctype.patient.patient.get_patient_detail',
				args: {
					patient: frm.doc.patient
				},
				callback: function(data) {
					let age = '';
					if (data.message.dob) {
						age = calculate_age(data.message.dob);
					}
					frappe.model.set_value(frm.doctype, frm.docname, 'patient_age', age);
					frappe.model.set_value(frm.doctype, frm.docname, 'patient_sex', data.message.sex);
					if (data.message.inpatient_record) {
						frappe.model.set_value(frm.doctype, frm.docname, 'inpatient_record', data.message.inpatient_record);
						frappe.model.set_value(frm.doctype, frm.docname, 'inpatient_status', data.message.inpatient_status);
					}
				}
			});
		} else {
			frappe.model.set_value(frm.doctype, frm.docname, 'patient_sex', '');
			frappe.model.set_value(frm.doctype, frm.docname, 'patient_age', '');
			frappe.model.set_value(frm.doctype, frm.docname, 'inpatient_record', '');
			frappe.model.set_value(frm.doctype, frm.docname, 'inpatient_status', '');
		}
	}
});

let schedule_inpatient = function(frm) {
	frappe.call({
		method: 'erpnext.healthcare.doctype.inpatient_record.inpatient_record.schedule_inpatient',
		args: {patient: frm.doc.patient, encounter_id: frm.doc.name, practitioner: frm.doc.practitioner},
		callback: function(data) {
			if (!data.exc) {
				frm.reload_doc();
			}
		},
		freeze: true,
		freeze_message: __('Process Inpatient Scheduling')
	});
};

let schedule_discharge = function(frm) {
	frappe.call({
		method: 'erpnext.healthcare.doctype.inpatient_record.inpatient_record.schedule_discharge',
		args: {patient: frm.doc.patient, encounter_id: frm.doc.name, practitioner: frm.doc.practitioner},
		callback: function(data) {
			if (!data.exc) {
				frm.reload_doc();
			}
		},
		freeze: true,
		freeze_message: 'Process Discharge'
	});
};

let create_medical_record = function (frm) {
	if (!frm.doc.patient) {
		frappe.throw(__('Please select patient'));
	}
	frappe.route_options = {
		'patient': frm.doc.patient,
		'status': 'Open',
		'reference_doctype': 'Patient Medical Record',
		'reference_owner': frm.doc.owner
	};
	frappe.new_doc('Patient Medical Record');
};

let create_vital_signs = function (frm) {
	if (!frm.doc.patient) {
		frappe.throw(__('Please select patient'));
	}
	frappe.route_options = {
		'patient': frm.doc.patient,
		'appointment': frm.doc.appointment,
		'encounter': frm.doc.name
	};
	frappe.new_doc('Vital Signs');
};

let create_procedure = function (frm) {
	if (!frm.doc.patient) {
		frappe.throw(__('Please select patient'));
	}
	frappe.route_options = {
		'patient': frm.doc.patient,
		'medical_department': frm.doc.medical_department
	};
	frappe.new_doc('Clinical Procedure');
};

frappe.ui.form.on('Drug Prescription', {
	dosage: function(frm, cdt, cdn){
		frappe.model.set_value(cdt, cdn, 'update_schedule', 1);
		let child = locals[cdt][cdn];
		if (child.dosage) {
			frappe.model.set_value(cdt, cdn, 'interval_uom', 'Day');
			frappe.model.set_value(cdt, cdn, 'interval', 1);
		}
	},
	period: function(frm, cdt, cdn) {
		frappe.model.set_value(cdt, cdn, 'update_schedule', 1);
	},
	interval_uom: function(frm, cdt, cdn) {
		frappe.model.set_value(cdt, cdn, 'update_schedule', 1);
		let child = locals[cdt][cdn];
		if (child.interval_uom == 'Hour') {
			frappe.model.set_value(cdt, cdn, 'dosage', null);
		}
	}
});

let calculate_age = function(birth) {
	let ageMS = Date.parse(Date()) - Date.parse(birth);
	let age = new Date();
	age.setTime(ageMS);
	let years =  age.getFullYear() - 1970;
	return  years + ' Year(s) ' + age.getMonth() + ' Month(s) ' + age.getDate() + ' Day(s)';
};
