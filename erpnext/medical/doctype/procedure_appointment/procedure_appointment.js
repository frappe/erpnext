// Copyright (c) 2017, ESS LLP and contributors
// For license information, please see license.txt

frappe.ui.form.on('Procedure Appointment', {
	refresh: function(frm) {
		frm.set_query("patient", function () {
			return {
				filters: {"disabled": 0}
			}
		});
		if(frappe.user.has_role("Nursing User")){
			if(frm.doc.patient){
				frm.add_custom_button(__('Medical Record'), function() {
					frappe.route_options = {"patient": frm.doc.patient}
					frappe.set_route("medical_record");
				 },__("View") );
			};

			if(frm.doc.status == "Scheduled" && !frm.doc.__islocal){
				 frm.add_custom_button(__('Cancel'), function() {
	 				btn_update_status(frm, "Cancelled");
	 			 } );
			};
			if(frm.doc.status == "Pending"){
				frm.add_custom_button(__('Set Open'), function() {
					btn_update_status(frm, "Open");
				 } );
				 frm.add_custom_button(__('Cancel'), function() {
	 				btn_update_status(frm, "Cancelled");
	 			 } );
			};

			if(frm.doc.__islocal){
				frm.add_custom_button(__('Check Availability'), function() {
					check_availability(frm);
				 });
		 		frm.add_custom_button(__('Get from Consultation'), function() {
	 				get_procedures_rx(frm);
				});
			}

			if(!frm.doc.__islocal){
				if(frm.doc.invoiced == '1'){
					frm.add_custom_button(__('Invoice'), function() {
						frappe.set_route("Form", "Sales Invoice", frm.doc.invoice);
					 },__("View") );
				}
				else if(frm.doc.status != "Cancelled"){
					frm.add_custom_button(__('Invoice'), function() {
						invoice_procedure_appointment(frm);
					 },__("Create") );
				}
				if(frm.doc.status == "Open"){
					 frm.add_custom_button(__('Cancel'), function() {
		 				btn_update_status(frm, "Cancelled");
		 			 } );
					 frm.add_custom_button(__("Procedure"),function(){
		 				btn_create_procedure(frm);
		 				},"Create");
				};
			};
		}
	},
	onload: function(frm){
		if(frm.doc.__islocal){
			frappe.model.set_value(frm.doctype,frm.docname,"time", null);
			frm.add_fetch("procedure_template", "service_type", "service_type")
		}
	},
	date: function(frm){
		frappe.model.set_value(frm.doctype,frm.docname, 'start_dt', new Date(frm.doc.date + ' ' + frm.doc.time))
	},
	time: function(frm){
		frappe.model.set_value(frm.doctype,frm.docname, 'start_dt', new Date(frm.doc.date + ' ' + frm.doc.time))
	}
});

frappe.ui.form.on("Procedure Appointment", "patient",
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

var btn_update_status = function(frm, status){
	var doc = frm.doc;
	frappe.call({
		method:
		"erpnext.medical.doctype.procedure_appointment.procedure_appointment.update_status",
		args: {appointmentId: doc.name, status:status},
		callback: function(data){
			if(!data.exc){
				cur_frm.reload_doc();
			}
		}
	});
}

var invoice_procedure_appointment = function (frm){
	var doc = frm.doc;
	frappe.call({
		method:"erpnext.medical.doctype.procedure_appointment.procedure_appointment.create_invoice",
		args: {company:doc.company, patient:doc.patient, procedure_appointment: [doc.name], prescriptions:[]},
		callback: function(data){
			if(!data.exc){
				/*if(data.message){
					var doclist = frappe.model.sync(data.message);
					frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
				}*/
				cur_frm.reload_doc();
			}
		}
	});
}

var btn_create_procedure = function(frm){
	var doc = frm.doc;
	frappe.call({
		method:"erpnext.medical.doctype.procedure_appointment.procedure_appointment.create_procedure",
		args: {appointment: doc.name},
		callback: function(data){
			if(!data.exc){
				var doclist = frappe.model.sync(data.message);
				frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
			}
		}
	});
}

var check_availability = function(frm){
	if(frm.doc.service_type && frm.doc.date){
		frappe.call({
			method:
			"erpnext.medical.doctype.procedure_appointment.procedure_appointment.btn_check_availability",
			args: {service_type: frm.doc.service_type, date: frm.doc.date, time: frm.doc.time, end_dt: frm.doc.end_dt},
			callback: function(r){
				if(r.message){
					show_availability(frm, r.message)
				}
			}
		});
	}else{
		msgprint("Please select Service Type and Date");
	}
}

var get_procedures_rx = function(frm){
	if(frm.doc.patient){
		frappe.call({
			method:
			"erpnext.medical.doctype.procedure_appointment.procedure_appointment.get_procedures_rx",
			args: {patient: frm.doc.patient},
			callback: function(r){
				show_procedure_rx(frm, r.message)
			}
		});
	}
	else{
			msgprint("Please select Patient to get procedures");
	}
}

var show_procedure_rx = function(frm, result){
	var d = new frappe.ui.Dialog({
		title: __("Procedures Prescriptions"),
		fields: [
			{
				fieldtype: "HTML", fieldname: "procedure"
			}
		]
	});
	var html_field = d.fields_dict.procedure.$wrapper;
	html_field.empty();
	$.each(result, function(x, y){
		var row = $(repl('<div class="col-xs-12" style="padding-top:12px; text-align:center;" >\
		<div class="col-xs-2"> %(procedure)s </div>\
		<div class="col-xs-2"> %(consultation)s </div>\
		<div class="col-xs-2"> %(physician)s </div>\
		<div class="col-xs-3"> %(date)s </div>\
		<div class="col-xs-3">\
		<a data-name="%(name)s" data-procedure="%(procedure)s" data-consultation="%(consultation)s" data-service_type="%(service_type)s" data-invoice="%(invoice)s" href="#"><button class="btn btn-default btn-xs">Get Procedure</button></a></div></div>', {name:y[0], procedure: y[1], consultation:y[2], service_type: y[3], invoice:y[4], physician:y[5], date:y[6]})).appendTo(html_field);
		row.find("a").click(function() {
			frm.doc.procedure_template = $(this).attr("data-procedure");
			frm.doc.service_type = $(this).attr("data-service_type");
			frm.doc.prescription = $(this).attr("data-name");
			frm.set_df_property("procedure_template", "read_only", 1);
			frm.set_df_property("service_type", "read_only", 1);
			frm.set_df_property("patient", "read_only", 1);
			if($(this).attr("data-invoice") != 'null'){
				frm.doc.invoice = $(this).attr("data-invoice");
				frm.doc.invoiced = 1
				refresh_field("invoice");
				refresh_field("invoiced");
			}

			refresh_field("procedure_template");
			refresh_field("service_type");
			d.hide();
			return false;
		});
	})
	if(!result){
		var msg = "There are no procedure prescription(s) for "+frm.doc.patient
		$(repl('<div class="col-xs-12" style="padding-top:20px;" >%(msg)s</div></div>', {msg: msg})).appendTo(html_field);
	}
	d.show();
}

var show_availability = function(frm, result){
	var d = new frappe.ui.Dialog({
		title: __("Resource Availability (Time - Token)"),
		fields: [
			{
				fieldtype: "HTML", fieldname: "availability"
			}
		]
	});
	var html_field = d.fields_dict.availability.$wrapper;
	html_field.empty();

	var list = ''
	$.each(result, function(i, v) {
		if(v[0]["msg"]){
			var message = $(repl('<div class="col-xs-12" style="padding-top:20px;" >%(msg)s</div></div>', {msg: v[0]["msg"]})).appendTo(html_field);
			return
		}
		$(repl('<div class="col-xs-12" style="padding-top:20px;"><b> %(service_unit)s</b></div>', {service_unit: i})).appendTo(html_field);
		$.each(result[i], function(x, y){
			var row = $(repl('<div class="col-xs-12" style="padding-top:12px; text-align:center;" ><div class="col-xs-4"> %(start)s </div><div class="col-xs-4"> %(token)s </div><div class="col-xs-4"><a data-start="%(start)s" data-end="%(end)s" data-token="%(token)s" data-service_unit="%(service_unit)s"  href="#"><button class="btn btn-default btn-xs"> Book</button></a></div></div>', {start: y["start"], end: y["end"], token: y["token"], service_unit: i})).appendTo(html_field);
			row.find("a").click(function() {
				p_datetime = new Date($(this).attr("data-start"));
				frm.doc.time = p_datetime.toLocaleTimeString();
				frm.doc.start_dt = $(this).attr("data-start");
				frm.doc.end_dt = $(this).attr("data-end");
				frm.doc.token = $(this).attr("data-token");
				frm.doc.service_unit = $(this).attr("data-service_unit");
				frm.set_df_property("token", "read_only", 1);
				frm.set_df_property("procedure_template", "read_only", 1);
				frm.set_df_property("service_type", "read_only", 1);
				frm.set_df_property("service_unit", "read_only", 1);
				frm.set_df_property("date", "read_only", 1);
				frm.set_df_property("time", "read_only", 1);
				refresh_field("token");refresh_field("start_dt");
				refresh_field("time");refresh_field("end_dt");
				refresh_field("service_unit")
				d.hide();
				return false;
			});
		})

	});
	d.show();
}

var calculate_age = function(birth) {
  ageMS = Date.parse(Date()) - Date.parse(birth);
  age = new Date();
  age.setTime(ageMS);
  years =  age.getFullYear() - 1970
  return  years + " Year(s) " + age.getMonth() + " Month(s) " + age.getDate() + " Day(s)"
}
