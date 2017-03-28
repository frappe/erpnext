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
		if(frm.doc.__islocal && frm.doc.patient){
			frappe.call({
					"method": "erpnext.medical.doctype.patient.patient.get_patient_detail",
					args: {
							patient: frm.doc.patient
					},
					callback: function (data) {
						age = ""
						if(data.message.dob){
							age = calculate_age(data.message.dob)
						}else if (data.message.age){
							age = data.message.age
							if(data.message.age_as_on){
								age = age+" as on "+data.message.age_as_on
							}
						}
						frappe.model.set_value(frm.doctype,frm.docname, "patient_age", age)
						show_details(data.message);
					}
				});
		}
	},
	refresh: function(frm) {
		refresh_field('drug_prescription');
		refresh_field('test_prescription');
		if((frappe.user.has_role("IP Physician")) || (frappe.user.has_role("OP Physician"))){
			frm.add_custom_button(__('View History'), function() {
				if(frm.doc.patient){
					frappe.route_options = {"patient": frm.doc.patient}
					frappe.set_route("medical_record");
				}else{
					frappe.msgprint("Please select Patient");
				}
			} );
		}
		frm.set_query("patient", function () {
			return {
				filters: {"disabled": 0}
			}
		});
		frm.set_df_property("appointment", "read_only", frm.doc.__islocal ? 0:1);
		frm.set_df_property("patient", "read_only", frm.doc.__islocal ? 0:1);
		frm.set_df_property("patient_age", "read_only", frm.doc.__islocal ? 0:1);
		frm.set_df_property("patient_sex", "read_only", frm.doc.__islocal ? 0:1);
		frm.set_df_property("type", "read_only", frm.doc.__islocal ? 0:1);
		frm.set_df_property("physician", "read_only", frm.doc.__islocal ? 0:1);
		frm.set_df_property("ref_physician", "read_only", frm.doc.__islocal ? 0:1);
		frm.set_df_property("visit_department", "read_only", frm.doc.__islocal ? 0:1);
		frm.set_df_property("consultation_date", "read_only", frm.doc.__islocal ? 0:1);
		frm.set_df_property("consultation_time", "read_only", frm.doc.__islocal ? 0:1);
		if(frm.doc.admitted){
			frm.set_df_property("appointment", "hidden", 1);
		}else{
			frm.set_df_property("appointment", "hidden", 0);
		}
		if(!frm.doc.__islocal){
			if(!frm.doc.admitted && !frm.doc.admit_scheduled){
				frm.add_custom_button(__('Admit Patient'), function() {
					btn_admit_patient(frm);
				 });
			}
			if(frappe.user.has_role("Nursing User")||frappe.user.has_role("IP Physician")||frappe.user.has_role("OP Physician")){
				frm.add_custom_button(__('Vital Signs'), function() {
					btn_create_vital_signs(frm);
				 },"Create");
			}
		}

	}
});

var show_details = function(data){
	var details = "";
	if(data.email) details += "<br><b>Email :</b> " + data.email;
	if(data.mobile) details += "<br><b>Mobile :</b> " + data.mobile;
	if(data.occupation) details += "<br><b>Occupation :</b> " + data.occupation;
	if(data.blood_group) details += "<br><b>Blood group : </b> " + data.blood_group;
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
		details = "<div style='padding-left:10px; font-size:13px;' align='center'></br><b class='text-muted'>Patient Details</b>" + details + "</div>"
	}

	var vitals = ""
	if(data.temperature) vitals += "<br><b>Temperature :</b> " + data.temperature;
	if(data.pulse) vitals += "<br><b>Pulse :</b> " + data.pulse;
	if(data.respiratory_rate) vitals += "<br><b>Respiratory Rate :</b> " + data.respiratory_rate;
	if(data.bp) vitals += "<br><b>BP :</b> " + data.bp;
	if(data.bmi) vitals += "<br><b>BMI :</b> " + data.bmi;
	if(data.height) vitals += "<br><b>Height :</b> " + data.height;
	if(data.weight) vitals += "<br><b>Weight :</b> " + data.weight;
	if(data.signs_date) vitals += "<br><b>Date :</b> " + data.signs_date;

	if(vitals){
		vitals = "<div style='padding-left:10px; font-size:13px;' align='center'></br><b class='text-muted'>Vital Signs</b>" + vitals + "<br></div>"
		details = vitals + details
	}
	$('#page-Form\\/Consultation').find('.layout-side-section').html(details);
	$('#page-Form\\/Consultation').find('.layout-side-section').show();
}

frappe.ui.form.on("Consultation", "appointment",
    function(frm) {
	if(frm.doc.appointment){
		frappe.call({
		    "method": "frappe.client.get",
		    args: {
		        doctype: "Appointment",
		        name: frm.doc.appointment
		    },
		    callback: function (data) {
				frappe.model.set_value(frm.doctype,frm.docname, "patient", data.message.patient)
				frappe.model.set_value(frm.doctype,frm.docname, "type", data.message.appointment_type)
				frappe.model.set_value(frm.doctype,frm.docname, "physician", data.message.physician)
		    }
		})
	}
});

frappe.ui.form.on("Consultation", "physician",
    function(frm) {
	if(frm.doc.physician){
		frappe.call({
		    "method": "frappe.client.get",
		    args: {
		        doctype: "Physician",
		        name: frm.doc.physician
		    },
		    callback: function (data) {
				frappe.model.set_value(frm.doctype,frm.docname, "visit_department",data.message.department)
		    }
		})
	}
});

frappe.ui.form.on("Consultation", "symptoms_select", function(frm) {
	if(frm.doc.symptoms_select){
		if(frm.doc.symptoms)
			symptoms = frm.doc.symptoms + "\n" +frm.doc.symptoms_select
		else
			symptoms = frm.doc.symptoms_select
		frappe.model.set_value(frm.doctype,frm.docname, "symptoms", symptoms)
		frappe.model.set_value(frm.doctype,frm.docname, "symptoms_select", null)
	}
});
frappe.ui.form.on("Consultation", "diagnosis_select", function(frm) {
	if(frm.doc.diagnosis_select){
		if(frm.doc.diagnosis)
			diagnosis = frm.doc.diagnosis + "\n" +frm.doc.diagnosis_select
		else
			diagnosis = frm.doc.diagnosis_select
		frappe.model.set_value(frm.doctype,frm.docname, "diagnosis", diagnosis)
		frappe.model.set_value(frm.doctype,frm.docname, "diagnosis_select", null)
	}
});

frappe.ui.form.on("Consultation", "patient",
    function(frm) {
        if(frm.doc.patient){
		frappe.call({
				"method": "erpnext.medical.doctype.patient.patient.get_patient_detail",
		    args: {
		        patient: frm.doc.patient
		    },
		    callback: function (data) {
					age = ""
					if(data.message.dob){
						age = calculate_age(data.message.dob)
					}else if (data.message.age){
						age = data.message.age
						if(data.message.age_as_on){
							age = age+" as on "+data.message.age_as_on
						}
					}
					frappe.model.set_value(frm.doctype,frm.docname, "patient_age", age)
					frappe.model.set_value(frm.doctype,frm.docname, "patient_sex", data.message.sex)
					frappe.model.set_value(frm.doctype,frm.docname, "admitted", data.message.admitted)
					if(data.message.admitted){
						frappe.model.set_value(frm.doctype,frm.docname, "admission", data.message.admission)
					}
					if(frm.doc.__islocal) show_details(data.message);
		    }
		})
	}
});

me.frm.set_query("drug_code", "drug_prescription", function(doc, cdt, cdn) {
		return {
			filters: {
				is_stock_item:'1'
			}
		};
	});

me.frm.set_query("test_code", "test_prescription", function(doc, cdt, cdn) {
		return {
			filters: {
				is_billable:'1'
			}
		};
	});

frappe.ui.form.on("Drug Prescription", {
	drug_code:  function(frm, cdt, cdn) {
		var child = locals[cdt][cdn]
		if(child.drug_code){
			frappe.call({
				"method": "frappe.client.get",
				args: {
				    doctype: "Item",
				    name: child.drug_code,
				},
				callback: function (data) {
				frappe.model.set_value(cdt, cdn, 'drug_name',data.message.item_name)
				}
			})
		}
	},
	dosage: function(frm, cdt, cdn){
		frappe.model.set_value(cdt, cdn, 'update_schedule', 1)
		var child = locals[cdt][cdn]
		if(child.dosage){
			frappe.model.set_value(cdt, cdn, 'in_every', 'Day')
			frappe.model.set_value(cdt, cdn, 'interval', 1)
		}
	},
	period: function(frm, cdt, cdn){
		frappe.model.set_value(cdt, cdn, 'update_schedule', 1)
	},
	in_every: function(frm, cdt, cdn){
		frappe.model.set_value(cdt, cdn, 'update_schedule', 1)
		var child = locals[cdt][cdn]
		if(child.in_every == "Hour"){
			frappe.model.set_value(cdt, cdn, 'dosage', null)
		}
	}
});

frappe.ui.form.on("IP Routine Observation", {
	number: function(frm, cdt, cdn){
		frappe.model.set_value(cdt, cdn, 'update_schedule', 1)
	},
	observe: function(frm, cdt, cdn){
		frappe.model.set_value(cdt, cdn, 'update_schedule', 1)
	},
	period: function(frm, cdt, cdn){
		frappe.model.set_value(cdt, cdn, 'update_schedule', 1)
	}
});

frappe.ui.form.on("Procedure Prescription", {
	procedure_template: function(frm, cdt, cdn){
		frappe.model.set_value(cdt, cdn, 'patient', frm.doc.patient)
	},
});

var btn_create_vital_signs = function(frm){
	var doc = frm.doc;
	frappe.call({
		method:"erpnext.medical.doctype.vital_signs.vital_signs.create_vital_signs",
		args: {patient: doc.patient},
		callback: function(data){
			if(!data.exc){
				var doclist = frappe.model.sync(data.message);
				frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
			}
		}
	});
}

var btn_admit_patient = function(frm){
	var doc = frm.doc;
	frappe.call({
		method:"erpnext.medical.doctype.consultation.consultation.admit_patient",
		args: {consultationId: doc.name},
		callback: function(data){
			if(!data.exc){
				frappe.msgprint("Patient scheduled for admission");
				cur_frm.reload_doc()
			}
		}
	});
}

me.frm.set_query("appointment", function(doc, cdt, cdn) {
		return {
			filters: {
				//Scheduled filter for demo ...
				status:['in',["Open","Scheduled"]],
				//Commented for demo ..
				//physician: doc.physician
			}
		};
	});


var calculate_age = function(birth) {
  ageMS = Date.parse(Date()) - Date.parse(birth);
  age = new Date();
  age.setTime(ageMS);
  years =  age.getFullYear() - 1970
  return  years + " Year(s) " + age.getMonth() + " Month(s) " + age.getDate() + " Day(s)"
}
