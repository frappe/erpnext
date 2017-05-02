// Copyright (c) 2017, ESS LLP and contributors
// For license information, please see license.txt

frappe.ui.form.on('Procedure', {
	refresh: function(frm) {
		frm.set_query("patient", function () {
			return {
				filters: {"disabled": 0}
			}
		});
		if (!frm.doc.complete_procedure && !frm.doc.__islocal){

			if(frm.doc.maintain_stock){
				btn_label = 'Complete and Consume'
				msg = 'Are you sure to Complete and Consume Stock?'
			}else{
				btn_label = 'Complete'
				msg = 'Are you sure to Complete?'
			}

			frm.add_custom_button(__(btn_label), function () {
				frappe.confirm(
				    msg,
				    function(){
							frappe.call({
							 doc: frm.doc,
							 method: "complete",
							 callback: function(r) {
								 if(!r.exc) cur_frm.reload_doc();
							 }
						 });
				    }
				)

			})
		};
		if (frm.doc.__islocal){
			frm.set_df_property("stock_items", "hidden", 1);
			frm.set_df_property("sb_stages", "hidden", 1);
		}else{
			frm.set_df_property("stock_items", "hidden", 0);
			frm.set_df_property("sb_stages", "hidden", 0);
		}
	},
	onload: function(frm){
		if(frm.doc.complete_procedure){
			frm.set_df_property("items", "read_only", 1);
			frm.set_df_property("stages", "read_only", 1);
		}
	},
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

frappe.ui.form.on("Procedure", "procedure_template", function(frm) {
	if(frm.doc.procedure_template){
		frappe.call({
		    "method": "frappe.client.get",
		    args: {
		        doctype: "Procedure Template",
		        name: frm.doc.procedure_template
		    },
		    callback: function (data) {
					frappe.model.set_value(frm.doctype,frm.docname, "service_type", data.message.service_type)
					frappe.model.set_value(frm.doctype,frm.docname, "maintain_stock", data.message.maintain_stock)
					frappe.model.set_value(frm.doctype,frm.docname, "is_staged", data.message.is_staged)
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
