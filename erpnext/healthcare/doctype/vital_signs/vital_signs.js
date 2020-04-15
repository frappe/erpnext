// Copyright (c) 2016, ESS LLP and contributors
// For license information, please see license.txt

frappe.ui.form.on('Vital Signs', {
	height: function(frm) {
		if (frm.doc.height && frm.doc.weight) {
			calculate_bmi(frm);
		}
	},

	weight: function(frm) {
		if (frm.doc.height && frm.doc.weight) {
			calculate_bmi(frm);
		}
	},

	bp_systolic: function(frm) {
		if (frm.doc.bp_systolic && frm.doc.bp_diastolic) {
			set_bp(frm);
		}
	},

	bp_diastolic: function(frm) {
		if (frm.doc.bp_systolic && frm.doc.bp_diastolic) {
			set_bp(frm);
		}
	}
});

let calculate_bmi = function(frm){
	// Reference https://en.wikipedia.org/wiki/Body_mass_index
	// bmi = weight (in Kg) / height * height (in Meter)
	let bmi = (frm.doc.weight / (frm.doc.height * frm.doc.height)).toFixed(2);
	let bmi_note = null;

	if (bmi<18.5) {
		bmi_note = 'Underweight';
	} else if (bmi>=18.5 && bmi<25) {
		bmi_note = 'Normal';
	} else if (bmi>=25 && bmi<30) {
		bmi_note = 'Overweight';
	} else if (bmi>=30) {
		bmi_note = 'Obese';
	}
	frappe.model.set_value(frm.doctype,frm.docname, 'bmi', bmi);
	frappe.model.set_value(frm.doctype,frm.docname, 'nutrition_note', bmi_note);
};

let set_bp = function(frm){
	let bp = frm.doc.bp_systolic+ '/' + frm.doc.bp_diastolic + ' mmHg';
	frappe.model.set_value(frm.doctype,frm.docname, 'bp', bp);
};
