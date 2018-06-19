// Copyright (c) 2016, ESS LLP and contributors
// For license information, please see license.txt
frappe.provide("erpnext.queries");
frappe.ui.form.on('Patient Appointment', {
	setup: function(frm) {
		frm.custom_make_buttons = {
			'Sales Invoice': 'Invoice',
			'Vital Signs': 'Vital Signs',
			'Consultation': 'Consultation'
		};
	},
	refresh: function(frm) {
		frm.set_query("patient", function () {
			return {
				filters: {"disabled": 0}
			};
		});
		frm.set_query("physician", function() {
			return {
				filters: {
					'department': frm.doc.department
				}
			};
		});
		frm.set_query("service_unit", function(){
			return {
				filters: {
					"is_group": false,
					"allow_appointments": true
				}
			};
		});
		if(frm.doc.patient){
			frm.add_custom_button(__('Medical Record'), function() {
				frappe.route_options = {"patient": frm.doc.patient};
				frappe.set_route("medical_record");
			},__("View"));
		}
		if(frm.doc.status == "Open"){
			frm.add_custom_button(__('Cancel'), function() {
				btn_update_status(frm, "Cancelled");
			});

			if(frm.doc.procedure_template){
				frm.add_custom_button(__("Procedure"),function(){
					btn_create_procedure(frm);
				},"Create");
			}
			else{
				frm.add_custom_button(__("Consultation"),function(){
					btn_create_consultation(frm);
				},"Create");
			}

			frm.add_custom_button(__('Vital Signs'), function() {
				btn_create_vital_signs(frm);
			},"Create");
		}
		if(frm.doc.status == "Scheduled" && !frm.doc.__islocal){
			frm.add_custom_button(__('Cancel'), function() {
				btn_update_status(frm, "Cancelled");
			});

			if(frm.doc.procedure_template){
				frm.add_custom_button(__("Procedure"),function(){
					btn_create_procedure(frm);
				},"Create");
			}
			else{
				frm.add_custom_button(__("Consultation"),function(){
					btn_create_consultation(frm);
				},"Create");
			}

			frm.add_custom_button(__('Vital Signs'), function() {
				btn_create_vital_signs(frm);
			},"Create");
		}
		if(frm.doc.status == "Pending"){
			frm.add_custom_button(__('Set Open'), function() {
				btn_update_status(frm, "Open");
			});
			frm.add_custom_button(__('Cancel'), function() {
				btn_update_status(frm, "Cancelled");
			});
		}

		if(!frm.doc.__islocal){
			if(frm.doc.sales_invoice && frappe.user.has_role("Accounts User")){
				frm.add_custom_button(__('Invoice'), function() {
					frappe.set_route("Form", "Sales Invoice", frm.doc.sales_invoice);
				},__("View") );
			}
			else if(frm.doc.status != "Cancelled" && frappe.user.has_role("Accounts User")){
				frm.add_custom_button(__('Invoice'), function() {
					btn_invoice_consultation(frm);
				},__("Create"));
			}
		}
	},
	check_availability: function(frm) {
		var { physician, appointment_date } = frm.doc;
		if(!(physician && appointment_date)) {
			frappe.throw(__("Please select Physician and Date"));
		}

		// show booking modal
		frm.call({
			method: 'get_availability_data',
			args: {
				physician: physician,
				date: appointment_date
			},
			callback: (r) => {
				var data = r.message;
				if(data.slot_details.length > 0){
					show_availability(data);
				}else{
					show_empty_state();
				}
			}
		});

		function show_empty_state() {
			frappe.msgprint({
				title: __('Not Available'),
				message: __("Physician {0} not available on {1}", [physician.bold(), appointment_date.bold()]),
				indicator: 'red'
			});
		}

		function show_availability(data) {
			var d = new frappe.ui.Dialog({
				title: __("Available slots"),
				fields: [{ fieldtype: 'HTML', fieldname: 'available_slots'}],
				primary_action_label: __("Book"),
				primary_action: function() {
					// book slot
					var btn_selected = $wrapper.find('button.btn-selected-slot');
					frm.set_value('appointment_time', btn_selected.attr('data-name'));
					frm.set_value('service_unit', btn_selected.attr('data-service-unit') || '');
					frm.set_value('duration', btn_selected.attr('data-duration'));
					d.hide();
					frm.save();
					frm.enable_save();
				}
			});
			var $wrapper = d.fields_dict.available_slots.$wrapper;

			// disable dialog action initially
			d.get_primary_btn().attr('disabled', true);

			var slot_details = data.slot_details;
			var slot_html = "";
			var duration = frm.doc.duration | 0;
			$.each(slot_details, function(i, slot_detail){
				slot_html = slot_html + `<label>${slot_detail['slot_name']}</label>`;
				slot_html = slot_html + `<br/>` + slot_detail['avail_slot'].map(slot => {
					let disabled = '';
					let start_str = slot.from_time;
					let start_time = moment(slot.from_time, 'HH:mm:ss');
					let to_time = moment(slot.to_time, 'HH:mm:ss');
					let interval = (to_time - start_time)/60000 | 0;
					// iterate in all booked appointments, update the start time and duration
					slot_detail['appointments'].forEach(function(booked) {
						let booked_moment = moment(booked.appointment_time, 'HH:mm:ss');
						if(booked_moment.isSame(start_time) || booked_moment.isBetween(start_time, to_time)){
							if(booked.duration == 0){
								disabled = 'disabled="disabled"';
								return false;
							}
							start_time = booked_moment;
							let end_time = booked_moment.add(booked.duration, 'minutes');
							if(end_time.isSameOrAfter(to_time) || end_time.add(duration).isAfter(to_time)){
								disabled = 'disabled="disabled"';
								return false;
							}else{
								start_str = end_time.format('HH:mm:ss');
							}
						}
					});

					return `<button class="btn btn-default"
						data-name=${start_str}
						data-duration=${duration || interval}
						data-service-unit="${slot_detail['service_unit'] || ''}"
						style="margin: 0 10px 10px 0; width: 72px;" ${disabled}>
						${start_str.substring(0, start_str.length - 3)}
					</button>`;
				}).join("");
				slot_html = slot_html + `<br/>`;
			});

			$wrapper
				.css('margin-bottom', 0)
				.addClass('text-center')
				.html(slot_html);

			// blue button when clicked
			$wrapper.on('click', 'button', function() {
				var $btn = $(this);
				$wrapper.find('button').removeClass('btn-primary');
				$wrapper.find('button').removeClass('btn-selected-slot');
				$btn.addClass('btn-primary');
				$btn.addClass('btn-selected-slot');
				// enable dialog action
				d.get_primary_btn().attr('disabled', null);
			});

			d.show();
		}
	},
	onload:function(frm){
		if(frm.is_new()) {
			frm.set_value("appointment_time", null);
			frm.disable_save();
		}
	},
	get_procedure_from_consultation: function(frm) {
		get_procedure_prescribed(frm);
	}
});

var get_procedure_prescribed = function(frm){
	if(frm.doc.patient){
		frappe.call({
			method:"erpnext.healthcare.doctype.patient_appointment.patient_appointment.get_procedure_prescribed",
			args: {patient: frm.doc.patient},
			callback: function(r){
				show_procedure_templates(frm, r.message);
			}
		});
	}
	else{
		frappe.msgprint("Please select Patient to get prescribed procedure");
	}
};

var show_procedure_templates = function(frm, result){
	var d = new frappe.ui.Dialog({
		title: __("Prescribed Procedures"),
		fields: [
			{
				fieldtype: "HTML", fieldname: "procedure_template"
			}
		]
	});
	var html_field = d.fields_dict.procedure_template.$wrapper;
	html_field.empty();
	$.each(result, function(x, y){
		var row = $(repl('<div class="col-xs-12" style="padding-top:12px; text-align:center;" >\
		<div class="col-xs-5"> %(consultation)s <br> %(consulting_physician)s <br> %(consultation_date)s </div>\
		<div class="col-xs-5"> %(procedure_template)s <br>%(physician)s  <br> %(date)s</div>\
		<div class="col-xs-2">\
		<a data-name="%(name)s" data-procedure-template="%(procedure_template)s"\
		data-consultation="%(consultation)s" data-physician="%(physician)s"\
		data-date="%(date)s"  data-department="%(department)s">\
		<button class="btn btn-default btn-xs">Add\
		</button></a></div></div><div class="col-xs-12"><hr/><div/>', {name:y[0], procedure_template: y[1],
				consultation:y[2], consulting_physician:y[3], consultation_date:y[4],
				physician:y[5]? y[5]:'', date: y[6]? y[6]:'', department: y[7]? y[7]:''})).appendTo(html_field);
		row.find("a").click(function() {
			frm.doc.procedure_template = $(this).attr("data-procedure-template");
			frm.doc.procedure_prescription = $(this).attr("data-name");
			frm.doc.physician = $(this).attr("data-physician");
			frm.doc.appointment_date = $(this).attr("data-date");
			frm.doc.department = $(this).attr("data-department");
			refresh_field("procedure_template");
			refresh_field("procedure_prescription");
			refresh_field("appointment_date");
			refresh_field("physician");
			refresh_field("department");
			d.hide();
			return false;
		});
	});
	if(!result){
		var msg = "There are no procedure prescribed for "+frm.doc.patient;
		$(repl('<div class="col-xs-12" style="padding-top:20px;" >%(msg)s</div></div>', {msg: msg})).appendTo(html_field);
	}
	d.show();
};

var btn_create_procedure = function(frm){
	var doc = frm.doc;
	frappe.call({
		method:"erpnext.healthcare.doctype.clinical_procedure.clinical_procedure.create_procedure",
		args: {appointment: doc.name},
		callback: function(data){
			if(!data.exc){
				var doclist = frappe.model.sync(data.message);
				frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
			}
		}
	});
};

var btn_create_consultation = function(frm){
	var doc = frm.doc;
	frappe.call({
		method:"erpnext.healthcare.doctype.patient_appointment.patient_appointment.create_consultation",
		args: {appointment: doc.name},
		callback: function(data){
			if(!data.exc){
				var doclist = frappe.model.sync(data.message);
				frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
			}
		}
	});
};

var btn_create_vital_signs = function (frm) {
	if(!frm.doc.patient){
		frappe.throw(__("Please select patient"));
	}
	frappe.route_options = {
		"patient": frm.doc.patient,
		"appointment": frm.doc.name,
	};
	frappe.new_doc("Vital Signs");
};

var btn_update_status = function(frm, status){
	var doc = frm.doc;
	frappe.confirm(__('Are you sure you want to cancel this appointment?'),
		function() {
			frappe.call({
				method:
				"erpnext.healthcare.doctype.patient_appointment.patient_appointment.update_status",
				args: {appointment_id: doc.name, status:status},
				callback: function(data){
					if(!data.exc){
						frm.reload_doc();
					}
				}
			});
		}
	);
};

var btn_invoice_consultation = function(frm){
	frappe.call({
		doc: frm.doc,
		method:"create_invoice",
		callback: function(data){
			if(!data.exc){
				if(data.message){
					frappe.set_route("Form", "Sales Invoice", data.message);
				}
				cur_frm.reload_doc();
			}
		}
	});
};

frappe.ui.form.on("Patient Appointment", "physician", function(frm) {
	if(frm.doc.physician){
		frappe.call({
			"method": "frappe.client.get",
			args: {
				doctype: "Physician",
				name: frm.doc.physician
			},
			callback: function (data) {
				frappe.model.set_value(frm.doctype,frm.docname, "department",data.message.department);
			}
		});
	}
});

frappe.ui.form.on("Patient Appointment", "patient", function(frm) {
	if(frm.doc.patient){
		frappe.call({
			"method": "frappe.client.get",
			args: {
				doctype: "Patient",
				name: frm.doc.patient
			},
			callback: function (data) {
				var age = null;
				if(data.message.dob){
					age = calculate_age(data.message.dob);
				}
				frappe.model.set_value(frm.doctype,frm.docname, "patient_age", age);
			}
		});
	}
});

frappe.ui.form.on("Patient Appointment", "appointment_type", function(frm) {
	if(frm.doc.appointment_type) {
		frappe.call({
			"method": "frappe.client.get",
			args: {
				doctype: "Appointment Type",
				name: frm.doc.appointment_type
			},
			callback: function (data) {
				frappe.model.set_value(frm.doctype,frm.docname, "duration",data.message.default_duration);
			}
		});
	}
});

var calculate_age = function(birth) {
	var ageMS = Date.parse(Date()) - Date.parse(birth);
	var age = new Date();
	age.setTime(ageMS);
	var years =  age.getFullYear() - 1970;
	return  years + " Year(s) " + age.getMonth() + " Month(s) " + age.getDate() + " Day(s)";
};
