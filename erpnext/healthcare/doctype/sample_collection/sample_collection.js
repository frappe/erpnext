// Copyright (c) 2016, ESS and contributors
// For license information, please see license.txt

frappe.ui.form.on('Sample Collection', {
	refresh: function(frm) {
		if(frappe.defaults.get_default("require_sample_collection")){
			frm.add_custom_button(__("View Lab Tests"), function() {
				frappe.route_options = {"sample": frm.doc.name};
				frappe.set_route("List", "Lab Test");
			});
		}
	}
});

frappe.ui.form.on("Sample Collection", "patient", function(frm) {
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
				frappe.model.set_value(frm.doctype,frm.docname, "patient_sex", data.message.sex);
			}
		});
	}
});

var calculate_age = function(birth) {
	var	ageMS = Date.parse(Date()) - Date.parse(birth);
	var	age = new Date();
	age.setTime(ageMS);
	var	years =  age.getFullYear() - 1970;
	return  years + " Year(s) " + age.getMonth() + " Month(s) " + age.getDate() + " Day(s)";
};
