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
    if(frappe.defaults.get_default("register_patient") && frm.doc.status != "Active"){
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
 }
});

frappe.ui.form.on("Patient", "dob", function(frm) {
  if(frm.doc.dob && !frm.doc.age){
    today = new Date();
    birthDate = new Date(frm.doc.dob);
    if(today < birthDate){
      msgprint("Please select a valid Date");
      frappe.model.set_value(frm.doctype,frm.docname, "dob", null)
    }else{
      age_yr = today.getFullYear() - birthDate.getFullYear();
      today_m = today.getMonth()+1 //Month jan = 0
      birth_m = birthDate.getMonth()+1 //Month jan = 0
      m = today_m - birth_m;
      d = today.getDate() - birthDate.getDate()

      if (m < 0 || (m === 0 && today.getDate() < birthDate.getDate())) {
        age_yr--;
      }
      if (m < 0 || m==0) {
       m = (12 + m);
      }
      if (d < 0) {
        m--;
        d = 31 + d;// 31 may varry with month Feb(28,29),Even Month(30) or Odd Month(31)
      }
      age_str = null
      if(age_yr > 0)
        age_str = age_yr+" Year(s), "
      if(m > 0)
        age_str = age_str+m+" Month(s), "
      if(d > 0)
        age_str = age_str+d+" Day(s)"
      frappe.model.set_value(frm.doctype,frm.docname, "age", age_str)
      frm.set_df_property("age_int", "hidden", 1);
      frm.set_df_property("age", "hidden", 0);
    }
  }
});

frappe.ui.form.on("Patient", "age_int", function(frm) {
  if(frm.doc.age_int){
    today = new Date()
    frm.set_df_property("dob", "hidden", 1);
    frm.set_df_property("age", "hidden", 1);
    frm.set_df_property("age_as_on", "hidden", 0);
    frm.set_df_property("age_int", "hidden", 0);
    d = today.getDate();m = today.getMonth();y = today.getFullYear();
    frappe.model.set_value(frm.doctype,frm.docname, "age_as_on", today)
    frappe.model.set_value(frm.doctype,frm.docname, "age", frm.doc.age_int+" as on "+d+"-"+m+"-"+y)
  }
});

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
