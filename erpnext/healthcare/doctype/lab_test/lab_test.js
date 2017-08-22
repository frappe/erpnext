// Copyright (c) 2016, ESS and contributors
// For license information, please see license.txt

cur_frm.cscript.custom_refresh = function(doc) {
	cur_frm.toggle_display("sb_sensitivity", doc.sensitivity_toggle=="1");
	cur_frm.toggle_display("sb_special", doc.special_toggle=="1");
	cur_frm.toggle_display("sb_normal", doc.normal_toggle=="1");
};

frappe.ui.form.on('Lab Test', {
	setup: function(frm) {
		frm.get_field('normal_test_items').grid.editable_fields = [
			{fieldname: 'test_name', columns: 3},
			{fieldname: 'test_event', columns: 2},
			{fieldname: 'result_value', columns: 2},
			{fieldname: 'test_uom', columns: 1},
			{fieldname: 'normal_range', columns: 2}
		];
		frm.get_field('special_test_items').grid.editable_fields = [
			{fieldname: 'test_particulars', columns: 3},
			{fieldname: 'result_value', columns: 7}
		];
	},
	refresh :  function(frm){
		refresh_field('normal_test_items');
		refresh_field('special_test_items');
		if(!frm.doc.__islocal && !frm.doc.invoice && frappe.user.has_role("Accounts User")){
			frm.add_custom_button(__('Make Invoice'), function() {
				make_invoice(frm);
			});
		}
		if(frm.doc.__islocal){
			frm.add_custom_button(__('Get from Consultation'), function () {
				get_lab_test_prescribed(frm);
			});
		}
		if(frm.doc.docstatus==1	&&	frm.doc.status!='Approved'	&&	frm.doc.status!='Rejected'	&&	frappe.defaults.get_default("require_test_result_approval")	&&	frappe.user.has_role("LabTest Approver")){
			frm.add_custom_button(__('Approve'), function() {
				status_update(1,frm);
			});
			frm.add_custom_button(__('Reject'), function() {
				status_update(0,frm);
			});
		}
		if(frm.doc.docstatus==1 && frm.doc.sms_sent==0){
			frm.add_custom_button(__('Send SMS'), function() {
				frappe.call({
					method: "erpnext.healthcare.doctype.healthcare_settings.healthcare_settings.get_sms_text",
					args:{doc: frm.doc.name},
					callback: function(r) {
						if(!r.exc) {
							var emailed = r.message.emailed;
							var printed = r.message.printed;
							make_dialog(frm, emailed, printed);
						}
					}
				});
			});
		}

	},
	onload: function (frm) {
		frm.add_fetch("physician", "department", "department");
		if(frm.doc.employee){
			frappe.call({
				method: "frappe.client.get",
				args:{
					doctype: "Employee",
					name: frm.doc.employee
				},
				callback: function(arg){
					frappe.model.set_value(frm.doctype,frm.docname,"employee_name", arg.message.employee_name);
					frappe.model.set_value(frm.doctype,frm.docname,"employee_designation", arg.message.designation);
				}
			});
		}
	}
});

frappe.ui.form.on("Lab Test", "patient", function(frm) {
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
				frappe.model.set_value(frm.doctype,frm.docname, "email", data.message.email);
				frappe.model.set_value(frm.doctype,frm.docname, "mobile", data.message.mobile);
				frappe.model.set_value(frm.doctype,frm.docname, "report_preference", data.message.report_preference);
			}
		});
	}
});

frappe.ui.form.on('Normal Test Items', {
	normal_test_items_remove: function() {
		frappe.msgprint("Not permitted, configure Lab Test Template as required");
		cur_frm.reload_doc();
	}
});

frappe.ui.form.on('Special Test Items', {
	special_test_items_remove: function() {
		frappe.msgprint("Not permitted, configure Lab Test Template as required");
		cur_frm.reload_doc();
	}
});

var status_update = function(approve,frm){
	var doc = frm.doc;
	var status = null;
	if(approve == 1){
		status = "Approved";
	}
	else {
		status = "Rejected";
	}
	frappe.call({
		method: "erpnext.healthcare.doctype.lab_test.lab_test.update_status",
		args: {status: status, name: doc.name},
		callback: function(){
			cur_frm.reload_doc();
		}
	});
};

var get_lab_test_prescribed = function(frm){
	if(frm.doc.patient){
		frappe.call({
			method:	"erpnext.healthcare.doctype.lab_test.lab_test.get_lab_test_prescribed",
			args:	{patient: frm.doc.patient},
			callback: function(r){
				show_lab_tests(frm, r.message);
			}
		});
	}
	else{
		frappe.msgprint("Please select Patient to get Lab Tests");
	}
};

var show_lab_tests = function(frm, result){
	var d = new frappe.ui.Dialog({
		title: __("Lab Test Prescriptions"),
		fields: [
			{
				fieldtype: "HTML", fieldname: "lab_test"
			}
		]
	});
	var html_field = d.fields_dict.lab_test.$wrapper;
	html_field.empty();
	$.each(result, function(x, y){
		var row = $(repl('<div class="col-xs-12" style="padding-top:12px; text-align:center;" >\
		<div class="col-xs-2"> %(lab_test)s </div>\
		<div class="col-xs-2"> %(consultation)s </div>\
		<div class="col-xs-3"> %(physician)s </div>\
		<div class="col-xs-3"> %(date)s </div>\
		<div class="col-xs-1">\
		<a data-name="%(name)s" data-lab-test="%(lab_test)s"\
		data-consultation="%(consultation)s" data-physician="%(physician)s"\
		data-invoice="%(invoice)s" href="#"><button class="btn btn-default btn-xs">Get Lab Test\
		</button></a></div></div>', {name:y[0], lab_test: y[1], consultation:y[2], invoice:y[3], physician:y[4], date:y[5]})).appendTo(html_field);
		row.find("a").click(function() {
			frm.doc.template = $(this).attr("data-lab-test");
			frm.doc.prescription = $(this).attr("data-name");
			frm.doc.physician = $(this).attr("data-physician");
			frm.set_df_property("template", "read_only", 1);
			frm.set_df_property("patient", "read_only", 1);
			frm.set_df_property("physician", "read_only", 1);
			if($(this).attr("data-invoice") != 'null'){
				frm.doc.invoice = $(this).attr("data-invoice");
				refresh_field("invoice");
			}else {
				frm.doc.invoice = "";
				refresh_field("invoice");
			}

			refresh_field("template");
			d.hide();
			return false;
		});
	});
	if(!result){
		var msg = "There are no Lab Test prescribed for "+frm.doc.patient;
		$(repl('<div class="col-xs-12" style="padding-top:20px;" >%(msg)s</div></div>', {msg: msg})).appendTo(html_field);
	}
	d.show();
};

var make_invoice = function(frm){
	var doc = frm.doc;
	frappe.call({
		method: "erpnext.healthcare.doctype.lab_test.lab_test.create_invoice",
		args: {company:doc.company, patient:doc.patient, lab_tests: [doc.name], prescriptions:[]},
		callback: function(r){
			if(!r.exc){
				if(r.message){
					/*	frappe.show_alert(__('Sales Invoice {0} created',
					['<a href="#Form/Sales Invoice/'+r.message+'">' + r.message+ '</a>']));	*/
					frappe.set_route("Form", "Sales Invoice", r.message);
				}
				cur_frm.reload_doc();
			}
		}
	});
};

cur_frm.cscript.custom_before_submit =  function(doc) {
	if(doc.normal_test_items){
		for(let result in doc.normal_test_items){
			if(!doc.normal_test_items[result].result_value	&&	doc.normal_test_items[result].require_result_value == 1){
				frappe.msgprint("Please input all required Result Value(s)");
				throw("Error");
			}
		}
	}
	if(doc.special_test_items){
		for(let result in doc.special_test_items){
			if(!doc.special_test_items[result].result_value	&&	doc.special_test_items[result].require_result_value == 1){
				frappe.msgprint("Please input all required Result Value(s)");
				throw("Error");
			}
		}
	}
};

var make_dialog = function(frm, emailed, printed) {
	var number = frm.doc.mobile;

	var dialog = new frappe.ui.Dialog({
		title: 'Send SMS',
		width: 400,
		fields: [
			{fieldname:'sms_type', fieldtype:'Select', label:'Type', options:
			['Emailed','Printed']},
			{fieldname:'number', fieldtype:'Data', label:'Mobile Number', reqd:1},
			{fieldname:'messages_label', fieldtype:'HTML'},
			{fieldname:'messages', fieldtype:'HTML', reqd:1}
		],
		primary_action_label: __("Send"),
		primary_action : function(){
			var values = dialog.fields_dict;
			if(!values){
				return;
			}
			send_sms(values,frm);
			dialog.hide();
		}
	});
	if(frm.doc.report_preference == "Email"){
		dialog.set_values({
			'sms_type': "Emailed",
			'number': number
		});
		dialog.fields_dict.messages_label.html("Message".bold());
		dialog.fields_dict.messages.html(emailed);
	}else{
		dialog.set_values({
			'sms_type': "Printed",
			'number': number
		});
		dialog.fields_dict.messages_label.html("Message".bold());
		dialog.fields_dict.messages.html(printed);
	}
	var fd = dialog.fields_dict;
	$(fd.sms_type.input).change(function(){
		if(dialog.get_value('sms_type') == 'Emailed'){
			dialog.set_values({
				'number': number
			});
			fd.messages_label.html("Message".bold());
			fd.messages.html(emailed);
		}else{
			dialog.set_values({
				'number': number
			});
			fd.messages_label.html("Message".bold());
			fd.messages.html(printed);
		}
	});
	dialog.show();
};

var send_sms = function(v,frm){
	var doc = frm.doc;
	var number = v.number.last_value;
	var messages = v.messages.wrapper.innerText;
	frappe.call({
		method: "frappe.core.doctype.sms_settings.sms_settings.send_sms",
		args: {
			receiver_list: [number],
			msg: messages
		},
		callback: function(r) {
			if(r.exc) {frappe.msgprint(r.exc); return; }
			else{
				frappe.call({
					method: "erpnext.healthcare.doctype.lab_test.lab_test.update_lab_test_print_sms_email_status",
					args: {print_sms_email: "sms_sent", name: doc.name},
					callback: function(){
						cur_frm.reload_doc();
					}
				});
			}
		}
	});
};

var calculate_age = function(birth) {
	var	ageMS = Date.parse(Date()) - Date.parse(birth);
	var	age = new Date();
	age.setTime(ageMS);
	var	years =  age.getFullYear() - 1970;
	return  years + " Year(s) " + age.getMonth() + " Month(s) " + age.getDate() + " Day(s)";
};
