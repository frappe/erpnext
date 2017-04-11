// Copyright (c) 2017, ESS LLP and contributors
// For license information, please see license.txt

frappe.ui.form.on('Procedure', {
	refresh: function(frm) {
		frm.set_query("patient", function () {
			return {
				filters: {"disabled": 0}
			}
		});
	},
	onload: function(frm){
		if(frm.doc.__islocal){
			frm.add_fetch("procedure_template", "service_type", "service_type")
		}
	}
});

frappe.ui.form.on("Procedure", "patient",
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
		    }
		})
	}
});

frappe.ui.form.on("Procedure", "appointment",
    function(frm) {
	if(frm.doc.appointment){
		frappe.call({
		    "method": "frappe.client.get",
		    args: {
		        doctype: "Procedure Appointment",
		        name: frm.doc.appointment
		    },
		    callback: function (data) {
				frappe.model.set_value(frm.doctype,frm.docname, "patient", data.message.patient)
				frappe.model.set_value(frm.doctype,frm.docname, "procedure_template", data.message.procedure_template)
				frappe.model.set_value(frm.doctype,frm.docname, "service_type", data.message.service_type)
				frappe.model.set_value(frm.doctype,frm.docname, "service_unit", data.message.service_unit)
				frappe.model.set_value(frm.doctype,frm.docname, "start_dt", data.message.start_dt)
				frappe.model.set_value(frm.doctype,frm.docname, "end_dt", data.message.end_dt)
				frappe.model.set_value(frm.doctype,frm.docname, "token", data.message.token)
		    }
		})
	}
});

me.frm.set_query("appointment", function(doc, cdt, cdn) {
	return {
		filters: {
			status:['in',["Open"]]
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
