// Copyright (c) 2016, ESS LLP and contributors
// For license information, please see license.txt

frappe.ui.form.on('Consultation', {
	setup: function(frm) {
		frm.get_field('drug_prescription').grid.editable_fields = [
			{fieldname: 'drug_code', columns: 2},
			{fieldname: 'drug_name', columns: 2},
			{fieldname: 'dosage', columns: 2},
			{fieldname: 'period', columns: 2}
		];
		frm.get_field('test_prescription').grid.editable_fields = [
			{fieldname: 'test_code', columns: 2},
			{fieldname: 'test_name', columns: 4},
			{fieldname: 'test_comment', columns: 4}
		];
	},
	onload: function(frm){
		if(frm.doc.patient){
			frappe.call({
				"method": "erpnext.healthcare.doctype.patient.patient.get_patient_detail",
				args: {
					patient: frm.doc.patient
				},
				callback: function (data) {
					var age = null;
					if(data.message.dob){
						age = calculate_age(data.message.dob);
					}
					frappe.model.set_value(frm.doctype,frm.docname, "patient_age", age);
					show_details(data.message);
				}
			});
		}
	},
	refresh: function(frm) {
		refresh_field('drug_prescription');
		refresh_field('test_prescription');

		frm.add_custom_button(__('Medical Record'), function() {
			if (frm.doc.patient) {
				frappe.route_options = {"patient": frm.doc.patient};
				frappe.set_route("medical_record");
			} else {
				frappe.msgprint("Please select Patient");
			}
		},"View");
		frm.add_custom_button(__('Vital Signs'), function() {
			btn_create_vital_signs(frm);
		},"Create");
		frm.add_custom_button(__('Medical Record'), function() {
			create_medical_record(frm);
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
		frm.set_query("test_code", "test_prescription", function() {
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
		if(!frm.doc.__islocal && !frm.doc.invoice && (frappe.user.has_role("Accounts User"))){
			frm.add_custom_button(__('Invoice'), function() {
				btn_invoice_consultation(frm);
			},__("Create"));
		}
		frm.set_df_property("appointment", "read_only", frm.doc.__islocal ? 0:1);
		frm.set_df_property("patient", "read_only", frm.doc.__islocal ? 0:1);
		frm.set_df_property("patient_age", "read_only", frm.doc.__islocal ? 0:1);
		frm.set_df_property("patient_sex", "read_only", frm.doc.__islocal ? 0:1);
		frm.set_df_property("type", "read_only", frm.doc.__islocal ? 0:1);
		frm.set_df_property("physician", "read_only", frm.doc.__islocal ? 0:1);
		frm.set_df_property("visit_department", "read_only", frm.doc.__islocal ? 0:1);
		frm.set_df_property("consultation_date", "read_only", frm.doc.__islocal ? 0:1);
		frm.set_df_property("consultation_time", "read_only", frm.doc.__islocal ? 0:1);
	}
});

var btn_invoice_consultation = function(frm){
	var doc = frm.doc;
	frappe.call({
		method:
		"erpnext.healthcare.doctype.consultation.consultation.create_invoice",
		args: {company: doc.company, patient: doc.patient, physician: doc.physician, consultation_id: doc.name },
		callback: function(data){
			if(!data.exc){
				if(data.message){
					frappe.set_route("Form", "Sales Invoice", data.message);
				}
				cur_frm.reload_doc();
			}
		}
	});
};

var create_medical_record = function (frm) {
	if(!frm.doc.patient){
		frappe.throw("Please select patient");
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
		frappe.throw("Please select patient");
	}
	frappe.route_options = {
		"patient": frm.doc.patient,
	};
	frappe.new_doc("Vital Signs");
};

var show_details = function(data){
	var personal_details = "";
	var age = null;
	if(data.dob){
		age = calculate_age(data.dob);
		personal_details += "<br><b>Age :</b> " + age;
	}
	if(data.sex) personal_details += "<br><b>Gender :</b> " + data.sex;
	if(data.blood_group) personal_details += "<br><b>Blood group : </b> " + data.blood_group;
	if(data.occupation) personal_details += "<br><b>Occupation :</b> " + data.occupation;
	if(data.email) personal_details += "<br><b>Email :</b> " + data.email;
	if(data.mobile) personal_details += "<br><b>Mobile :</b> " + data.mobile;

	if(personal_details){
		personal_details = "<div style='padding-left:10px; font-size:13px;' align='left'></br><b class='text-muted'>Personal Details</b>" + personal_details + "</div>";
	}

	var details = "";
	if(data.allergies) details +=  "<br><br><b>Allergies : </b> "+  data.allergies;
	if(data.medication) details +=  "<br><b>Medication : </b> "+  data.medication;
	if(data.alcohol_current_use) details +=  "<br><br><b>Alcohol use : </b> "+  data.alcohol_current_use;
	if(data.alcohol_past_use) details +=  "<br><b>Alcohol past use : </b> "+  data.alcohol_past_use;
	if(data.tobacco_current_use) details +=  "<br><b>Tobacco use : </b> "+  data.tobacco_current_use;
	if(data.tobacco_past_use) details +=  "<br><b>Tobacco past use : </b> "+  data.tobacco_past_use;
	if(data.medical_history) details +=  "<br><br><b>Medical history : </b> "+  data.medical_history;
	if(data.surgical_history) details +=  "<br><b>Surgical history : </b> "+  data.surgical_history;
	if(data.surrounding_factors) details +=  "<br><br><b>Occupational hazards : </b> "+  data.surrounding_factors;
	if(data.other_risk_factors) details += "<br><b>Other risk factors : </b> " + data.other_risk_factors;
	if(data.patient_details) details += "<br><br><b>More info : </b> " + data.patient_details;

	if(details){
		details = "<div style='padding-left:10px; font-size:13px;' align='left'></br><b class='text-muted'>Patient Details</b>" + details + "</div>";
	}

	var vitals = "";
	if(data.temperature) vitals += "<br><b>Temperature :</b> " + data.temperature;
	if(data.pulse) vitals += ", <b>Pulse :</b> " + data.pulse;
	if(data.respiratory_rate) vitals += ", <b>Respiratory Rate :</b> " + data.respiratory_rate;
	if(data.bp) vitals += ", <b>BP :</b> " + data.bp;
	if(data.bmi) vitals += "<br><b>BMI :</b> " + data.bmi;
	if(data.nutrition_note) vitals += " (" + data.nutrition_note + ")";
	if(data.height) vitals += ", <b>Height :</b> " + data.height;
	if(data.weight) vitals += ", <b>Weight :</b> " + data.weight;
	if(data.signs_date) vitals += "<br><b>Date :</b> " + data.signs_date;

	if(vitals){
		vitals = "<div style='padding-left:10px; font-size:13px;' align='left'></br><b class='text-muted'>Vital Signs</b>" + vitals + "<br></div>";
	}
	details = personal_details + vitals + details;
	cur_frm.fields_dict.patient_details_html.$wrapper.html(details);
};

frappe.ui.form.on("Consultation", "appointment", function(frm){
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
				frappe.model.set_value(frm.doctype,frm.docname, "physician", data.message.physician);
				frappe.model.set_value(frm.doctype,frm.docname, "invoice", data.message.sales_invoice);
			}
		});
	}
});

frappe.ui.form.on("Consultation", "physician", function(frm) {
	if(frm.doc.physician){
		frappe.call({
			"method": "frappe.client.get",
			args: {
				doctype: "Physician",
				name: frm.doc.physician
			},
			callback: function (data) {
				frappe.model.set_value(frm.doctype,frm.docname, "visit_department",data.message.department);
			}
		});
	}
});

frappe.ui.form.on("Consultation", "symptoms_select", function(frm) {
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
frappe.ui.form.on("Consultation", "diagnosis_select", function(frm) {
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

frappe.ui.form.on("Consultation", "patient", function(frm) {
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
				if(frm.doc.__islocal) show_details(data.message);
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


var calculate_age = function(birth) {
	var ageMS = Date.parse(Date()) - Date.parse(birth);
	var age = new Date();
	age.setTime(ageMS);
	var years =  age.getFullYear() - 1970;
	return  years + " Year(s) " + age.getMonth() + " Month(s) " + age.getDate() + " Day(s)";
};
