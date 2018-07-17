// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Inpatient Record', {
	refresh: function(frm) {
		if(!frm.doc.__islocal && frm.doc.inpatient == "Admission Scheduled"){
			frm.add_custom_button(__('Admit'), function() {
				admit_patient_dialog(frm);
			} );
			frm.set_df_property("btn_transfer", "hidden", 1);
		}
		if(!frm.doc.__islocal && frm.doc.inpatient == "Discharge Scheduled"){
			frm.add_custom_button(__('Discharge'), function() {
				discharge_patient(frm);
			} );
			frm.set_df_property("btn_transfer", "hidden", 0);
		}
		if(!frm.doc.__islocal && (frm.doc.inpatient == "Discharged" || frm.doc.inpatient == "Discharge Scheduled")){
			frm.disable_save();
			frm.set_df_property("btn_transfer", "hidden", 1);
		}
	},
	btn_transfer: function(frm) {
		transfer_patient_dialog(frm);
	}
});

var discharge_patient = function(frm) {
	frappe.call({
		doc: frm.doc,
		method: "discharge",
		callback: function(data) {
			if(!data.exc){
				frm.reload_doc();
			}
		},
		freeze: true,
		freeze_message: "Process Discharge"
	});
};

var admit_patient_dialog = function(frm){
	var dialog = new frappe.ui.Dialog({
		title: 'Admit Patient',
		width: 100,
		fields: [
				{fieldtype: "Link", label: "Service Unit Type", fieldname: "service_unit_type", options: "Healthcare Service Unit Type"},
				{fieldtype: "Link", label: "Service Unit", fieldname: "service_unit", options: "Healthcare Service Unit", reqd: 1},
				{fieldtype: "Datetime", label: "Date and Time In", fieldname: "datetime_in", reqd: 1},
				{fieldtype: "Date", label: "Expected Discharge", fieldname: "expected_discharge"}
		],
		primary_action_label: __("Admit"),
		primary_action : function(){
				var service_unit = dialog.get_value('service_unit');
				var datetime_in = dialog.get_value('datetime_in');
				var expected_discharge = null;
				if(dialog.get_value('expected_discharge')){
					expected_discharge = dialog.get_value('expected_discharge');
				}
				if(!service_unit && !datetime_in){
					return;
				}
				frappe.call({
					doc: frm.doc,
					method: 'admit',
					args:{
						'bed_location': service_unit,
						'datetime_in': datetime_in,
						'expected_discharge': expected_discharge
					},
					callback: function(data) {
						if(!data.exc){
							frm.reload_doc();
						}
					},
					freeze: true,
					freeze_message: "Process Admission"
				});
				frm.refresh_fields();
				dialog.hide();
			}
	})

	dialog.fields_dict["service_unit_type"].get_query = function(txt){
		return {
			filters: {
				"inpatient_occupancy": 1,
				"allow_appointments": 0
			}
		}
	};
	dialog.fields_dict["service_unit"].get_query = function(txt){
		return {
		filters: {
			"is_group": 0,
			"service_unit_type": dialog.get_value("service_unit_type"),
			"occupied" : 0
			}
		}
	};

	dialog.show();
};

var transfer_patient_dialog = function(frm){
	var dialog = new frappe.ui.Dialog({
		title: 'Transfer Patient',
		width: 100,
		fields: [
				{fieldtype: "Link", label: "From", fieldname: "leave_from", options: "Healthcare Service Unit", reqd: 1},
				{fieldtype: "Link", label: "Service Unit Type", fieldname: "service_unit_type", options: "Healthcare Service Unit Type"},
				{fieldtype: "Link", label: "To", fieldname: "service_unit", options: "Healthcare Service Unit", reqd: 1},
				{fieldtype: "Datetime", label: "Date and Time", fieldname: "datetime_in", reqd: 1}
		],
		primary_action_label: __("Transfer"),
		primary_action : function(){
				var service_unit = null;
				var datetime_in = dialog.get_value('datetime_in');
				var leave_from = null;
				if(dialog.get_value('leave_from')){
					leave_from = dialog.get_value('leave_from');
				}
				if(dialog.get_value('service_unit')){
					service_unit = dialog.get_value('service_unit');
				}
				if(!datetime_in){
					return;
				}
				frappe.call({
					doc: frm.doc,
					method: 'transfer',
					args:{
						'bed_location': service_unit,
						'datetime_in': datetime_in,
						'leave_from': leave_from
					},
					callback: function(data) {
						if(!data.exc){
							frm.reload_doc();
						}
					},
					freeze: true,
					freeze_message: "Process Transfer"
				});
				frm.refresh_fields();
				dialog.hide();
			}
	})

	dialog.fields_dict["service_unit_type"].get_query = function(txt){
		return {
			filters: {
				"inpatient_occupancy": 1,
				"allow_appointments": 0
			}
		}
	};
	dialog.fields_dict["service_unit"].get_query = function(txt){
		return {
		filters: {
			"is_group": 0,
			"service_unit_type": dialog.get_value("service_unit_type"),
			"occupied" : 0
			}
		}
	};

	dialog.show();

	var not_left_bed_location = null;
	for(let bed_location in frm.doc.bed_locations){
		if(frm.doc.bed_locations[bed_location].left != 1){
			not_left_bed_location = frm.doc.bed_locations[bed_location].bed_location
		}
	}
	dialog.set_values({
		'leave_from': not_left_bed_location
	});
};
