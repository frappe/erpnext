// Copyright (c) 2016, ESS LLP and contributors
// For license information, please see license.txt

frappe.ui.form.on('Procedure', {
	refresh: function(frm) {
		if(frm.doc.__islocal){
			frm.add_custom_button(__('Check Availability'), function() {
				check_availability(frm);
			 });
	 		frm.add_custom_button(__('Get from Consultation'), function() {
 				get_procedures(frm);
			});
		//  frm.add_custom_button(__('From Invoice'), function() {
		// 		 get_from_invoice(frm);
		// 	},"Get Procedure");
		}else if (!frm.doc.invoiced){
			frm.add_custom_button(__('Invoice Procedure'), function(){
				invoice_procedure(frm);
			});
		}
		frm.set_df_property("patient", "read_only", frm.doc.__islocal ? 0:1);
		frm.set_df_property("token", "read_only", frm.doc.__islocal ? 0:1);
		frm.set_df_property("patient_age", "read_only", frm.doc.__islocal ? 0:1);
		frm.set_df_property("patient_sex", "read_only", frm.doc.__islocal ? 0:1);
		frm.set_df_property("procedure_template", "read_only", frm.doc.__islocal ? 0:1);
		frm.set_df_property("service_type", "read_only", frm.doc.__islocal ? 0:1);
		frm.set_df_property("date", "read_only", frm.doc.__islocal ? 0:1);
		frm.set_df_property("time", "read_only", frm.doc.__islocal ? 0:1);
		frm.set_df_property("status", "read_only", frm.doc.__islocal ? 0:1);
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
	},
	procedure_template: function (frm) {
		frm.add_fetch("procedure_template", "service_type", "service_type")
	}
});

var invoice_procedure = function (frm){
	var doc = frm.doc;
	frappe.call({
		method:"erpnext.medical.doctype.procedure.procedure.create_invoice",
		args: {company:doc.company, patient:doc.patient, procedures: [doc.name], prescriptions:[]},
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

var check_availability = function(frm){
	if(frm.doc.service_type && frm.doc.date){
		frappe.call({
			method:
			"erpnext.medical.doctype.procedure.procedure.btn_check_availability",
			args: {service_type: frm.doc.service_type, date: frm.doc.date, time: frm.doc.time, end_dt: frm.doc.end_dt},
			callback: function(r){
				if(r.message){
					show_availability(frm, r.message)
				}
			}
		});
	}else{
		msgprint("Please select Procedure and Date");
	}
}

var get_procedures = function(frm){
	if(frm.doc.patient){
		frappe.call({
			method:
			"erpnext.medical.doctype.procedure.procedure.get_procedures",
			args: {patient: frm.doc.patient},
			callback: function(r){
				show_procedures(frm, r.message)
			}
		});
	}
	else{
			msgprint("Please select Patient to get procedures");
	}
}

var get_procedures_by_sales_invoice = function(invoice){
		frappe.call({
			method:
			"erpnext.medical.doctype.procedure.procedure.get_procedures_by_sales_invoice",
			args: {invoice: invoice},
			callback: function(r){
				show_procedures_invoiced(cur_frm, invoice, r.message)
			}
		});
}

var get_from_invoice = function(frm){
	var d = new frappe.ui.Dialog({
		title: __("Select Invoice"),
		fields: [
			{
					"fieldtype": "Link",
					"fieldname": "invoice",
					"options": "Sales Invoice",
					"reqd": 1
			}
		],
		primary_action_label: __("Get Procedures"),
		primary_action : function(){
				var values = d.get_values();
				if(!values)
					return;
				get_procedures_by_sales_invoice(values["invoice"])
				d.hide();
			}
	})
	d.fields_dict["invoice"].get_query = function(txt){
		return {
		filters: {
			"docstatus": 1
			}
		}
	};
	d.show();
}

var show_procedures_invoiced = function(frm, invoice, result){
	var d = new frappe.ui.Dialog({
		title: __("Procedures"),
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
		<div class="col-xs-4"> %(procedure)s </div>\
		<div class="col-xs-4"> %(service_type)s </div>\
		<div class="col-xs-4">\
		<a data-procedure="%(procedure)s" data-service_type="%(service_type)s" href="#"><button class="btn btn-default btn-xs">Get Procedure</button></a></div></div>', {procedure:y[0], service_type: y[1]})).appendTo(html_field);
		row.find("a").click(function() {
			frm.doc.procedure_template = $(this).attr("data-procedure");
			frm.doc.service_type = $(this).attr("data-service_type");
			frm.doc.invoiced = 1;
			frm.doc.invoice = invoice
			refresh_field("procedure_template");
			refresh_field("service_type");
			refresh_field("invoiced");
			refresh_field("invoice");
			d.hide();
			return false;
		});
	})
	if(!result){
		var msg = "There are no procedure(s) for "+frm.doc.patient
		$(repl('<div class="col-xs-12" style="padding-top:20px;" >%(msg)s</div></div>', {msg: msg})).appendTo(html_field);
	}
	d.show();
}

var show_procedures = function(frm, result){
	var d = new frappe.ui.Dialog({
		title: __("Procedures"),
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
		<div class="col-xs-3"> %(procedure)s </div>\
		<div class="col-xs-3"> %(consultation)s </div>\
		<div class="col-xs-3"> %(service_type)s </div>\
		<div class="col-xs-3">\
		<a data-name="%(name)s" data-procedure="%(procedure)s" data-consultation="%(consultation)s" data-service_type="%(service_type)s" data-invoice="%(invoice)s" href="#"><button class="btn btn-default btn-xs">Get Procedure</button></a></div></div>', {name:y[0], procedure: y[1], consultation:y[2], service_type: y[3], invoice:y[4]})).appendTo(html_field);
		row.find("a").click(function() {
			frm.doc.procedure_template = $(this).attr("data-procedure");
			frm.doc.service_type = $(this).attr("data-service_type");
			frm.doc.prescription = $(this).attr("data-name");

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
		var msg = "There are no procedure(s) for "+frm.doc.patient
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
