// Copyright (c) 2016, ESS LLP and contributors
// For license information, please see license.txt

frappe.ui.form.on('Patient', {
	refresh: function (frm) {
		frm.set_query("patient", "patient_relation", function () {
			return {
				filters: [
					["Patient", "name", "!=", frm.doc.name]
				]
			};
		});
		if (frappe.defaults.get_default("patient_master_name") != "Naming Series") {
			frm.toggle_display("naming_series", false);
		} else {
			erpnext.toggle_naming_series();
		}
		if (frappe.defaults.get_default("collect_registration_fee") && frm.doc.disabled == 1) {
			frm.add_custom_button(__('Invoice Patient Registration'), function () {
				btn_invoice_registration(frm);
			});
		}
		if (frm.doc.patient_name && frappe.user.has_role("Physician")) {
			frm.add_custom_button(__('Medical Record'), function () {
				frappe.route_options = { "patient": frm.doc.name };
				frappe.set_route("medical_record");
			},"View");
		}
		if (!frm.doc.__islocal && (frappe.user.has_role("Nursing User") || frappe.user.has_role("Physician"))) {
			frm.add_custom_button(__('Vital Signs'), function () {
				btn_create_vital_signs(frm);
			}, "Create");
			frm.add_custom_button(__('Medical Record'), function () {
				create_medical_record(frm);
			}, "Create");
			frm.add_custom_button(__('Consultation'), function () {
				btn_create_consultation(frm);
			}, "Create");
		}
	},
	onload: function (frm) {
		if(!frm.doc.dob){
			$(frm.fields_dict['age_html'].wrapper).html("Age not specified");
		}
		if(frm.doc.dob){
			$(frm.fields_dict['age_html'].wrapper).html("AGE : " + get_age(frm.doc.dob));
		}
	}
});

frappe.ui.form.on("Patient", "dob", function(frm) {
	if(frm.doc.dob){
		var today = new Date();
		var birthDate = new Date(frm.doc.dob);
		if(today < birthDate){
			frappe.msgprint("Please select a valid Date");
			frappe.model.set_value(frm.doctype,frm.docname, "dob", "");
		}
		else{
			var age_str = get_age(frm.doc.dob);
			$(frm.fields_dict['age_html'].wrapper).html("AGE : " + age_str);
		}
	}
});

var create_medical_record = function (frm) {
	frappe.route_options = {
		"patient": frm.doc.name,
		"status": "Open",
		"reference_doctype": "Patient Medical Record",
		"reference_owner": frm.doc.owner
	};
	frappe.new_doc("Patient Medical Record");
};

var get_age = function (birth) {
	var ageMS = Date.parse(Date()) - Date.parse(birth);
	var age = new Date();
	age.setTime(ageMS);
	var years = age.getFullYear() - 1970;
	return years + " Year(s) " + age.getMonth() + " Month(s) " + age.getDate() + " Day(s)";
};

var btn_create_vital_signs = function (frm) {
	if (!frm.doc.name) {
		frappe.throw("Please save the patient first");
	}
	frappe.route_options = {
		"patient": frm.doc.name,
	};
	frappe.new_doc("Vital Signs");
};

var btn_create_consultation = function (frm) {
	if (!frm.doc.name) {
		frappe.throw("Please save the patient first");
	}
	frappe.route_options = {
		"patient": frm.doc.name,
	};
	frappe.new_doc("Consultation");
};

var btn_invoice_registration = function (frm) {
	frappe.call({
		doc: frm.doc,
		method: "invoice_patient_registration",
		callback: function(data){
			if(!data.exc){
				if(data.message.invoice){
					/* frappe.show_alert(__('Sales Invoice {0} created',
					['<a href="#Form/Sales Invoice/'+data.message.invoice+'">' + data.message.invoice+ '</a>'])); */
					frappe.set_route("Form", "Sales Invoice", data.message.invoice);
				}
				cur_frm.reload_doc();
			}
		}
	});
};
