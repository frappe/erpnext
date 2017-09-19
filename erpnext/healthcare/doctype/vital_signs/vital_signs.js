// Copyright (c) 2016, ESS LLP and contributors
// For license information, please see license.txt

frappe.ui.form.on("Vital Signs", "height", function(frm) {
	if(frm.doc.height && frm.doc.weight){
		calculate_bmi(frm);
	}
});

frappe.ui.form.on("Vital Signs", "weight", function(frm) {
	if(frm.doc.height && frm.doc.weight){
		calculate_bmi(frm);
	}
});

var calculate_bmi = function(frm){
	// Reference https://en.wikipedia.org/wiki/Body_mass_index
	// bmi = weight (in Kg) / height * height (in Meter)
	var bmi = (frm.doc.weight/(frm.doc.height*frm.doc.height)).toFixed(2);
	var bmi_note = null;
	if(bmi<18.5){
		bmi_note = "Underweight";
	}else if(bmi>=18.5 && bmi<25){
		bmi_note = "Normal";
	}else if(bmi>=25 && bmi<30){
		bmi_note = "Overweight";
	}else if(bmi>=30){
		bmi_note = "Obese";
	}
	frappe.model.set_value(frm.doctype,frm.docname, "bmi", bmi);
	frappe.model.set_value(frm.doctype,frm.docname, "nutrition_note", bmi_note);
};

frappe.ui.form.on("Vital Signs", "bp_systolic", function(frm) {
	if(frm.doc.bp_systolic && frm.doc.bp_diastolic){
		set_bp(frm);
	}
});

frappe.ui.form.on("Vital Signs", "bp_diastolic", function(frm) {
	if(frm.doc.bp_systolic && frm.doc.bp_diastolic){
		set_bp(frm);
	}
});

var set_bp = function(frm){
	var bp = frm.doc.bp_systolic+"/"+frm.doc.bp_diastolic+" mmHg";
	frappe.model.set_value(frm.doctype,frm.docname, "bp", bp);
};
