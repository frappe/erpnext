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
		if (!frm.doc.__islocal){
			frappe.call({
				method: 'frappe.client.get_value',
				args: {
					doctype: 'Patient',
					fieldname: 'inpatient_status',
					filters: {name: frm.doc.patient}
				},
				callback: function(data) {
					if(data.message && data.message.inpatient_status == "Admission Scheduled" || data.message.inpatient_status == "Admitted"){
						frm.add_custom_button(__('Schedule Discharge'), function() {
							schedule_discharge(frm);
						});
					}
					else if(data.message.inpatient_status != "Discharge Scheduled"){
						frm.add_custom_button(__('Schedule Admission'), function() {
							schedule_inpatient(frm);
						});
					}
				}
			});
		}
		frm.add_custom_button(__('Medical Record'), function() {
			if (frm.doc.patient) {
				frappe.route_options = {"patient": frm.doc.patient};
				frappe.set_route("medical_record");
			} else {
				frappe.msgprint(__("Please select Patient"));
			}
		},"View");
		frm.add_custom_button(__('Vital Signs'), function() {
			btn_create_vital_signs(frm);
		},"Create");
		frm.add_custom_button(__('Medical Record'), function() {
			create_medical_record(frm);
		},"Create");

		frm.add_custom_button(__("Procedure"),function(){
			btn_create_procedure(frm);
		},"Create");

		frm.set_query("patient", function () {
			return {
				filters: {"disabled": 0}
			};
		});
		frm.set_query("drug_code", "drug_prescription", function() {
			return {
				filters: {
					is_stock_item:'1'
				}
			};
		});
		frm.set_query("lab_test_code", "lab_test_prescription", function() {
			return {
				filters: {
					is_billable:'1'
				}
			};
		});
		frm.set_query("medical_code", "codification_table", function() {
			return {
				filters: {
					medical_code_standard: frappe.defaults.get_default("default_medical_code_standard")
				}
			};
		});
		frm.set_query("appointment", function() {
			return {
				filters: {
					//	Scheduled filter for demo ...
					status:['in',["Open","Scheduled"]]
				}
			};
		});
		frm.set_df_property("appointment", "read_only", frm.doc.__islocal ? 0:1);
		frm.set_df_property("patient", "read_only", frm.doc.__islocal ? 0:1);
		frm.set_df_property("patient_age", "read_only", frm.doc.__islocal ? 0:1);
		frm.set_df_property("patient_sex", "read_only", frm.doc.__islocal ? 0:1);
		frm.set_df_property("type", "read_only", frm.doc.__islocal ? 0:1);
		frm.set_df_property("practitioner", "read_only", frm.doc.__islocal ? 0:1);
		frm.set_df_property("visit_department", "read_only", frm.doc.__islocal ? 0:1);
		frm.set_df_property("encounter_date", "read_only", frm.doc.__islocal ? 0:1);
		frm.set_df_property("encounter_time", "read_only", frm.doc.__islocal ? 0:1);
	}
});

var schedule_inpatient = function(frm) {
	frappe.call({
		method: "erpnext.healthcare.doctype.inpatient_record.inpatient_record.schedule_inpatient",
		args: {patient: frm.doc.patient, encounter_id: frm.doc.name, practitioner: frm.doc.practitioner},
		callback: function(data) {
			if(!data.exc){
				frm.reload_doc();
			}
		},
		freeze: true,
		freeze_message: "Process Inpatient Scheduling"
	});
};

var schedule_discharge = function(frm) {
	frappe.call({
		method: "erpnext.healthcare.doctype.inpatient_record.inpatient_record.schedule_discharge",
		args: {patient: frm.doc.patient, encounter_id: frm.doc.name, practitioner: frm.doc.practitioner},
		callback: function(data) {
			if(!data.exc){
				frm.reload_doc();
			}
		},
		freeze: true,
		freeze_message: "Process Discharge"
	});
};

var create_medical_record = function (frm) {
	if(!frm.doc.patient){
		frappe.throw(__("Please select patient"));
	}
	frappe.route_options = {
		"patient": frm.doc.patient,
		"status": "Open",
		"reference_doctype": "Patient Medical Record",
		"reference_owner": frm.doc.owner
	};
	frappe.new_doc("Patient Medical Record");
};

var btn_create_vital_signs = function (frm) {
	if(!frm.doc.patient){
		frappe.throw(__("Please select patient"));
	}
	frappe.route_options = {
		"patient": frm.doc.patient,
		"appointment": frm.doc.appointment
	};
	frappe.new_doc("Vital Signs");
};

var btn_create_procedure = function (frm) {
	if(!frm.doc.patient){
		frappe.throw("Please select patient");
	}
	frappe.route_options = {
		"patient": frm.doc.patient,
		"medical_department": frm.doc.visit_department
	};
	frappe.new_doc("Clinical Procedure");
};

frappe.ui.form.on("Patient Encounter", "appointment", function(frm){
	if(frm.doc.appointment){
		frappe.call({
			"method": "frappe.client.get",
			args: {
				doctype: "Patient Appointment",
				name: frm.doc.appointment
			},
			callback: function (data) {
				frappe.model.set_value(frm.doctype,frm.docname, "patient", data.message.patient);
				frappe.model.set_value(frm.doctype,frm.docname, "type", data.message.appointment_type);
				frappe.model.set_value(frm.doctype,frm.docname, "practitioner", data.message.practitioner);
				frappe.model.set_value(frm.doctype,frm.docname, "invoiced", data.message.invoiced);
			}
		});
	}
	else{
		frappe.model.set_value(frm.doctype,frm.docname, "patient", "");
		frappe.model.set_value(frm.doctype,frm.docname, "type", "");
		frappe.model.set_value(frm.doctype,frm.docname, "practitioner", "");
		frappe.model.set_value(frm.doctype,frm.docname, "invoiced", 0);
	}
});

frappe.ui.form.on("Patient Encounter", "practitioner", function(frm) {
	if(frm.doc.practitioner){
		frappe.call({
			"method": "frappe.client.get",
			args: {
				doctype: "Healthcare Practitioner",
				name: frm.doc.practitioner
			},
			callback: function (data) {
				frappe.model.set_value(frm.doctype,frm.docname, "visit_department",data.message.department);
			}
		});
	}
});

frappe.ui.form.on("Patient Encounter", "symptoms_select", function(frm) {
	if(frm.doc.symptoms_select){
		var symptoms = null;
		if(frm.doc.symptoms)
			symptoms = frm.doc.symptoms + "\n" +frm.doc.symptoms_select;
		else
			symptoms = frm.doc.symptoms_select;
		frappe.model.set_value(frm.doctype,frm.docname, "symptoms", symptoms);
		frappe.model.set_value(frm.doctype,frm.docname, "symptoms_select", null);
	}
});
frappe.ui.form.on("Patient Encounter", "diagnosis_select", function(frm) {
	if(frm.doc.diagnosis_select){
		var diagnosis = null;
		if(frm.doc.diagnosis)
			diagnosis = frm.doc.diagnosis + "\n" +frm.doc.diagnosis_select;
		else
			diagnosis = frm.doc.diagnosis_select;
		frappe.model.set_value(frm.doctype,frm.docname, "diagnosis", diagnosis);
		frappe.model.set_value(frm.doctype,frm.docname, "diagnosis_select", null);
	}
});

frappe.ui.form.on("Patient Encounter", "patient", function(frm) {
	if(frm.doc.patient){
		frappe.call({
			"method": "erpnext.healthcare.doctype.patient.patient.get_patient_detail",
			args: {
				patient: frm.doc.patient
			},
			callback: function (data) {
				var age = "";
				if(data.message.dob){
					age = calculate_age(data.message.dob);
				}
				frappe.model.set_value(frm.doctype,frm.docname, "patient_age", age);
				frappe.model.set_value(frm.doctype,frm.docname, "patient_sex", data.message.sex);
			}
		});
	}
});

frappe.ui.form.on("Drug Prescription", {
	drug_code:  function(frm, cdt, cdn) {
		var child = locals[cdt][cdn];
		if(child.drug_code){
			frappe.call({
				"method": "frappe.client.get",
				args: {
					doctype: "Item",
					name: child.drug_code,
				},
				callback: function (data) {
					frappe.model.set_value(cdt, cdn, 'drug_name',data.message.item_name);
				}
			});
		}
	},
	dosage: function(frm, cdt, cdn){
		frappe.model.set_value(cdt, cdn, 'update_schedule', 1);
		var child = locals[cdt][cdn];
		if(child.dosage){
			frappe.model.set_value(cdt, cdn, 'in_every', 'Day');
			frappe.model.set_value(cdt, cdn, 'interval', 1);
		}
	},
	period: function(frm, cdt, cdn){
		frappe.model.set_value(cdt, cdn, 'update_schedule', 1);
	},
	in_every: function(frm, cdt, cdn){
		frappe.model.set_value(cdt, cdn, 'update_schedule', 1);
		var child = locals[cdt][cdn];
		if(child.in_every == "Hour"){
			frappe.model.set_value(cdt, cdn, 'dosage', null);
		}
	}
});

frappe.ui.form.on("Procedure Prescription", {
	procedure:  function(frm, cdt, cdn) {
		var child = locals[cdt][cdn];
		if(child.procedure){
			frappe.call({
				"method": "frappe.client.get_value",
				args: {
					doctype: "Clinical Procedure Template",
					fieldname: "medical_department",
					filters: {name: child.procedure}
				},
				callback: function (data) {
					frappe.model.set_value(cdt, cdn, 'department',data.message.medical_department);
				}
			});
		}
	}
});


var calculate_age = function(birth) {
	var ageMS = Date.parse(Date()) - Date.parse(birth);
	var age = new Date();
	age.setTime(ageMS);
	var years =  age.getFullYear() - 1970;
	return  years + " Year(s) " + age.getMonth() + " Month(s) " + age.getDate() + " Day(s)";
};
