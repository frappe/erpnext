// Copyright (c) 2016, ESS LLP and contributors
// For license information, please see license.txt

frappe.ui.form.on('Patient', {
  refresh: function(frm) {
    if(frappe.defaults.get_default("patient_master_name")!="Naming Series") {
			frm.toggle_display("naming_series", false);
    } else {
			erpnext.toggle_naming_series();
    }
    if(frappe.defaults.get_default("collect_registration_fee") && frm.doc.disabled == 1){
      frm.add_custom_button(__('Invoice Patient Registration'), function() {
				btn_invoice_registration(frm);
			 });
    }
 		if(frm.doc.patient_name && (frappe.user.has_role("IP Physician")||frappe.user.has_role("OP Physician"))){
 			frm.add_custom_button(__('Medical Record'), function() {
 				frappe.route_options = {"patient": frm.doc.name}
 				frappe.set_route("medical_record");
 			 });
		};
    if(!frm.doc.__islocal && (frappe.user.has_role("Nursing User")||frappe.user.has_role("IP Physician")||frappe.user.has_role("OP Physician"))){
			frm.add_custom_button(__('Vital Signs'), function() {
				btn_create_vital_signs(frm);
			 },"Create");
       frm.add_custom_button(__('Medical Record'), function() {
        create_medical_record(frm);
       },"Create");
       frm.add_custom_button(__('Consultation'), function() {
        btn_create_consultation(frm);
       },"Create");
		}
  },
  onload: function (frm) {
    if(!frm.doc.dob && !frm.doc.age){
      $(frm.fields_dict['age_html'].wrapper).html("Age not specified");
    }
    if(frm.doc.dob){
      $(frm.fields_dict['age_html'].wrapper).html("AGE : " + get_age(frm.doc.dob));
      frm.set_df_property("age", "hidden", 1);
    }else if (frm.doc.age) {
      $(frm.fields_dict['age_html'].wrapper).html("AGE : "+ frm.doc.age + " as on " + frm.doc.age_as_on);
      frm.set_df_property("dob", "hidden", 1);
    }
  }
});

frappe.ui.form.on("Patient", "dob", function(frm) {
  if(frm.doc.dob){
    today = new Date();
    birthDate = new Date(frm.doc.dob);
    if(today < birthDate){
      msgprint("Please select a valid Date");
      frappe.model.set_value(frm.doctype,frm.docname, "dob", "");
      }
    else{
      age_str = get_age(frm.doc.dob);
      frappe.model.set_value(frm.doctype, frm.docname, "age", "");
      frappe.model.set_value(frm.doctype, frm.docname, "age_as_on", "");
      frm.set_df_property("age", "hidden", 1);
      $(frm.fields_dict['age_html'].wrapper).html("AGE : " + age_str);
      }
  }else{
    frm.set_df_property("age", "hidden", 0);
    $(frm.fields_dict['age_html'].wrapper).html("")
  }
});

frappe.ui.form.on("Patient", "age", function(frm) {
  if(frm.doc.age){
    frm.set_df_property("dob", "hidden", 1);
    frappe.model.set_value(frm.doctype, frm.docname, "dob", "");
    frappe.model.set_value(frm.doctype, frm.docname, "age_as_on", frappe.datetime.get_today());
    $(frm.fields_dict['age_html'].wrapper).html("AGE : "+ frm.doc.age + " as on " + frappe.datetime.get_today());
  }else{
    frappe.model.set_value(frm.doctype, frm.docname, "age_as_on", "");
    frm.set_df_property("dob", "hidden", 0);
    $(frm.fields_dict['age_html'].wrapper).html("")
  }
});

var create_medical_record = function (frm) {
	frappe.route_options = {
		"patient": frm.doc.name,
		"status": "Open",
		"reference_doctype": "Patient Medical Record",
		"reference_owner": frm.doc.owner
	}
	frappe.new_doc("Patient Medical Record")
}

var get_age = function (birth) {
  ageMS = Date.parse(Date()) - Date.parse(birth);
  age = new Date();
  age.setTime(ageMS);
  years =  age.getFullYear() - 1970
  return  years + " Year(s) " + age.getMonth() + " Month(s) " + age.getDate() + " Day(s)"
}

var btn_create_vital_signs = function (frm) {
	if(!frm.doc.name){
		frappe.throw("Please save the patient first")
	}
	frappe.route_options = {
		"patient": frm.doc.name,
	}
	frappe.new_doc("Vital Signs")
}

var btn_create_consultation = function (frm) {
	if(!frm.doc.name){
		frappe.throw("Please save the patient first")
	}
	frappe.route_options = {
		"patient": frm.doc.name,
	}
	frappe.new_doc("Consultation")
}

var btn_invoice_registration= function(frm){
	frappe.call({
		doc: frm.doc,
    method: "invoice_patient_registration",
		callback: function(data){
			if(!data.exc){
        if(data.message.invoice){
          /*frappe.show_alert(__('Sales Invoice {0} created',
  					['<a href="#Form/Sales Invoice/'+data.message.invoice+'">' + data.message.invoice+ '</a>']));*/
            frappe.set_route("Form", "Sales Invoice", data.message.invoice);
        }
        cur_frm.reload_doc();
			}
		}
	});
}
me.frm.set_query("patient", "patient_relation", function(doc, cdt, cdn) {
  	return {
			filters: [
        ["Patient", "name", "!=", me.frm.doc.name]
			]
		};
	});
