// Copyright (c) 2016, ESS LLP and contributors
// For license information, please see license.txt

frappe.ui.form.on('Discharge Summary', {
	refresh: function(frm) {
		frm.add_custom_button(__('View Admission'), function() {
			frappe.set_route("Form", "Patient Admission", frm.doc.admission);
		} );
	}
});

frappe.ui.form.on("Discharge Summary", "admission",
    function(frm) {
	if(frm.doc.admission){
		frappe.call({
		    "method": "frappe.client.get",
		    args: {
		        doctype: "Patient Admission",
		        name: frm.doc.admission
		    },
		    callback: function (data) {
				frappe.model.set_value(frm.doctype,frm.docname, "patient", data.message.patient)
				frappe.model.set_value(frm.doctype,frm.docname, "physician", data.message.physician)
				frappe.model.set_value(frm.doctype,frm.docname, "admit_date", data.message.admit_date)
				frappe.model.set_value(frm.doctype,frm.docname, "discharge_date", data.message.discharge_date)
		    }
		})
	}
});

frappe.ui.form.on("Discharge Summary", "physician",
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

frappe.ui.form.on("Discharge Summary", "patient",
    function(frm) {
        if(frm.doc.patient){
		frappe.call({
		    "method": "frappe.client.get",
		    args: {
		        doctype: "Patient",
		        name: frm.doc.patient
		    },
		    callback: function (data) {
					age = null
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
		    }
		})
	}
});

var calculate_age = function(birth) {
  ageMS = Date.parse(Date()) - Date.parse(birth);
  age = new Date();
  age.setTime(ageMS);
  years =  age.getFullYear() - 1970
  return  years + " Year(s) " + age.getMonth() + " Month(s) " + age.getDate() + " Day(s)"
}
