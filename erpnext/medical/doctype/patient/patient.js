// Copyright (c) 2016, ESS LLP and contributors
// For license information, please see license.txt

frappe.ui.form.on('Patient', {
  setup: function(frm) {
		frm.set_query('account', 'accounts', function(doc, cdt, cdn) {
			var d  = locals[cdt][cdn];
			return {
				filters: {
					'account_type': 'Receivable',
					'company': d.company,
				}
			}
		});
	},
 	refresh: function(frm) {
    if(frappe.defaults.get_default("register_patient") && frm.doc.disabled == 1){
      frm.add_custom_button(__('Register Patient'), function() {
				btn_register_patient(frm);
			 });
    }
 		if(frm.doc.patient_name && (frappe.user.has_role("IP Physician")||frappe.user.has_role("OP Physician"))){
 			frm.add_custom_button(__('View History'), function() {
 				frappe.route_options = {"patient": frm.doc.name}
 				frappe.set_route("medical_record");
 			 });
		};
    if(!frm.doc.__islocal && (frappe.user.has_role("Nursing User")||frappe.user.has_role("IP Physician")||frappe.user.has_role("OP Physician"))){
			frm.add_custom_button(__('Vital Signs'), function() {
				btn_create_vital_signs(frm);
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

var get_age = function (birth) {
  ageMS = Date.parse(Date()) - Date.parse(birth);
  age = new Date();
  age.setTime(ageMS);
  years =  age.getFullYear() - 1970
  return  years + " Year(s) " + age.getMonth() + " Month(s) " + age.getDate() + " Day(s)"
}

var btn_create_vital_signs = function(frm){
	var doc = frm.doc;
	frappe.call({
		method:"erpnext.medical.doctype.vital_signs.vital_signs.create_vital_signs",
		args: {patient: doc.name},
		callback: function(data){
			if(!data.exc){
				var doclist = frappe.model.sync(data.message);
				frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
			}
		}
	});
}

var btn_register_patient= function(frm){
	frappe.call({
		method:"erpnext.medical.doctype.patient.patient.register_patient",
		args: {patient: frm.doc.name, company: frappe.defaults.get_user_default("company")},
		callback: function(data){
			if(!data.exc){
				cur_frm.reload_doc();
        if(data.message.invoice){
          msgprint(__("Sales Invoice  <a href='#Form/Sales Invoice/{0}'> {0} </a> created", [data.message.invoice]))
        }
			}
		}
	});
}
