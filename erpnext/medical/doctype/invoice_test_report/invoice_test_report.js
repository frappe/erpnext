// Copyright (c) 2016, ESS and contributors
// For license information, please see license.txt

frappe.ui.form.on('Invoice Test Report', {
	setup: function(frm) {
		frm.get_field('lab_test_items').grid.editable_fields = [
			{fieldname: 'print_this', columns: 1},
			{fieldname: 'lab_test', columns: 6},
			{fieldname: 'workflow', columns: 3},
		];
	},
	refresh :  function(frm){
		refresh_field('lab_test_items');
		var doc = frm.doc;
		var approvable = false;
		var btn_send_sms_show = false;
		if(frappe.defaults.get_default("require_test_result_approval")){
			approvable = true;
		}
		for(result in doc.lab_test_items){
			if((doc.lab_test_items[result].workflow == "Submitted") && !approvable){
				if(doc.lab_test_items[result].sms_sent==0){
					btn_send_sms_show = true;
				}
			}
			else if((doc.lab_test_items[result].workflow == "Approved") && approvable){
				if(doc.lab_test_items[result].sms_sent==0){
					btn_send_sms_show = true;
				}
			}
		}
		if(btn_send_sms_show){
			frm.add_custom_button(__('Send SMS'), function() {
				make_dialog(frm);
			 } );
		}
		if(frm.doc.status == "In Progress"){
			frm.add_custom_button(__('Mark as Completed'), function() {
				mark_as_completed(frm);
			 } );
		}
		frm.add_custom_button(__("View Lab Tests"), function() {
			frappe.route_options = {"invoice": frm.doc.invoice}
			frappe.set_route("List", "Lab Test");
		});
		if(frappe.defaults.get_default("require_sample_collection")){
			frm.add_custom_button(__("View Sample Collections"), function() {
				frappe.route_options = {"invoice": frm.doc.invoice}
				frappe.set_route("List", "Sample Collection");
			});
		}
	},
	onload: function (frm) {
		frappe.call({
  			method:"frappe.client.get_value",
  			args: {
				doctype:"Sales Invoice",
				filters: { "name" : frm.doc.invoice },
				fieldname: "outstanding_amount"
			},
  			callback(r) {
				if(r.message.outstanding_amount == 0){
					frm.set_value("invoice_status", "Paid");
				}else{
					frm.set_value("invoice_status", "Unpaid");
				}
			}
		});
   	},
});


var mark_as_completed = function(frm){
	var doc = frm.doc;
	var approvable = false;
	if(frappe.defaults.get_default("require_test_result_approval")){
		approvable = true;
	}
	for(result in doc.lab_test_items){
		if(!(doc.lab_test_items[result].workflow == "Submitted") && !approvable && !(doc.lab_test_items[result].workflow == "Cancelled")){
			msgprint("All Lab Tests should be 'Submitted' or 'Cancelled' to complete")
			throw("Error");
		}
		else if(!(doc.lab_test_items[result].workflow == "Approved") && approvable && !(doc.lab_test_items[result].workflow == "Cancelled")){
			msgprint("All Lab Tests should be 'Approved' or 'Cancelled' to complete")
			throw("Error");
		}
	}
	frappe.call({
		method:"erpnext.medical.doctype.invoice_test_report.invoice_test_report.mark_as_completed",
		args: {status: "Completed", name: doc.name},
		callback: function(r){
			cur_frm.reload_doc();
		}
	});

}

var make_dialog = function(frm) {
	var number = frm.doc.mobile;
	var company  = frappe.defaults.get_user_default("company")
	var emailed = 	"Hello, "+ frm.doc.patient + "\nYour test result has been emailed to " + frm.doc.email + ".\nThank You, \n"+company ;
	var printed = 	"Hello, " + frm.doc.patient + "\nYour test result is ready with "+company+". \nThank You, Good Day";

	var dialog = new frappe.ui.Dialog({
		title: 'Send SMS',
		width: 400,
		fields: [
			{fieldname:'sms_type', fieldtype:'Select', label:'Type', options:
				['Emailed','Printed']},
			{fieldname:'number', fieldtype:'Data', label:'Mobile Number', reqd:1},
			{fieldname:'messages_label', fieldtype:'HTML',},
			{fieldname:'messages', fieldtype:'HTML', label:'Message', reqd:1}
		],
		primary_action_label: __("Send"),
		primary_action : function(){
				var values = dialog.fields_dict;
				if(!values)
					return;
				send_sms(values,frm);
				dialog.hide();
			}
	})
	if(frm.doc.report_preference == "Email"){
		dialog.set_values({
			'sms_type': "Emailed",
			'number': number
		})
		dialog.fields_dict.messages_label.html("Message".bold())
		dialog.fields_dict.messages.html(printed)
	}else{
		dialog.set_values({
			'sms_type': "Printed",
			'number': number
		})
		dialog.fields_dict.messages_label.html("Message".bold())
		dialog.fields_dict.messages.html(printed)
	}
	var fd = dialog.fields_dict;
	$(fd.sms_type.input).change(function(){
		if(dialog.get_value('sms_type') == 'Emailed'){
			dialog.set_values({
				'number': number
			});
			fd.messages_label.html("Message".bold())
			fd.messages.html(emailed)
		}else{
			dialog.set_values({
				'number': number
			})
			fd.messages_label.html("Message".bold())
			fd.messages.html(printed)
		}
	})
	dialog.show();
}

var send_sms = function(v,frm){
	var doc = frm.doc;
	number = v.number.last_value
	messages = v.messages.wrapper.innerText
	frappe.call({
		method: "erpnext.setup.doctype.sms_settings.sms_settings.send_sms",
		args: {
			receiver_list: [number],
			msg: messages
		},
		callback: function(r) {
			if(r.exc) {msgprint(r.exc); return; }
			else{
				for(result in doc.lab_test_items){
					if(doc.lab_test_items[result].sms_sent==0){
						frappe.call({
							method: 		"erpnext.medical.doctype.lab_test.lab_test.update_lab_test_print_sms_email_status",
							args: {
							print_sms_email: "sms_sent",
							name: doc.lab_test_items[result].lab_test
							},
							callback: function(r){
								cur_frm.reload_doc();
							}
						});
					}
				}
			}
		}
	});}
