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
		}
		if(frm.doc.status == "Scheduled" && !frm.doc.__islocal){
			frm.add_custom_button(__('Cancel'), function() {
				btn_update_status(frm, "Cancelled");
			});
		}
		if(frm.doc.status == "Pending"){
			frm.add_custom_button(__('Set Open'), function() {
				btn_update_status(frm, "Open");
			});
			frm.add_custom_button(__('Cancel'), function() {
				btn_update_status(frm, "Cancelled");
			});
		}

		frm.add_custom_button(__("Consultation"),function(){
			btn_create_consultation(frm);
		},"Create");

		frm.add_custom_button(__('Vital Signs'), function() {
			btn_create_vital_signs(frm);
		},"Create");

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
				// console.log(r);
				var data = r.message;
				if(data.available_slots.length > 0) {
					show_availability(data);
				} else {
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
					frm.set_value('appointment_time', selected_slot);
					frm.set_value('duration', data.time_per_appointment);
					d.hide();
					frm.save();
				}
			});
			var $wrapper = d.fields_dict.available_slots.$wrapper;
			var selected_slot = null;

			// disable dialog action initially
			d.get_primary_btn().attr('disabled', true);

			// make buttons for each slot
			var slot_html = data.available_slots.map(slot => {
				return `<button class="btn btn-default"
					data-name=${slot.from_time}
					style="margin: 0 10px 10px 0; width: 72px">
					${slot.from_time.substring(0, slot.from_time.length - 3)}
				</button>`;
			}).join("");

			$wrapper
				.css('margin-bottom', 0)
				.addClass('text-center')
				.html(slot_html);

			// disable buttons for which appointments are booked
			data.appointments.map(slot => {
				if(slot.status == "Scheduled" || slot.status == "Open" || slot.status == "Closed"){
					$wrapper
						.find(`button[data-name="${slot.appointment_time}"]`)
						.attr('disabled', true);
				}
			});

			// blue button when clicked
			$wrapper.on('click', 'button', function() {
				var $btn = $(this);
				$wrapper.find('button').removeClass('btn-primary');
				$btn.addClass('btn-primary');
				selected_slot = $btn.attr('data-name');

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
});

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
		frappe.throw("Please select patient");
	}
	frappe.route_options = {
		"patient": frm.doc.patient,
	};
	frappe.new_doc("Vital Signs");
};

var btn_update_status = function(frm, status){
	var doc = frm.doc;
	frappe.call({
		method:
		"erpnext.healthcare.doctype.patient_appointment.patient_appointment.update_status",
		args: {appointmentId: doc.name, status:status},
		callback: function(data){
			if(!data.exc){
				cur_frm.reload_doc();
			}
		}
	});
};

var btn_invoice_consultation = function(frm){
	var doc = frm.doc;
	frappe.call({
		method:
		"erpnext.healthcare.doctype.patient_appointment.patient_appointment.create_invoice",
		args: {company: doc.company, physician:doc.physician, patient: doc.patient,
			appointment_id: doc.name, appointment_date:doc.appointment_date },
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

var calculate_age = function(birth) {
	var ageMS = Date.parse(Date()) - Date.parse(birth);
	var age = new Date();
	age.setTime(ageMS);
	var years =  age.getFullYear() - 1970;
	return  years + " Year(s) " + age.getMonth() + " Month(s) " + age.getDate() + " Day(s)";
};
