// Copyright (c) 2016, ESS LLP and contributors
// For license information, please see license.txt

frappe.ui.form.on('Patient Admission', {
	refresh: function(frm) {
		frm.enable_save();
		if(frm.doc.patient && frappe.user.has_role("IP Physician")){
			frm.add_custom_button(__('History'), function() {
				frappe.route_options = {"patient": frm.doc.patient}
				frappe.set_route("medical_record");
			 } );
		}
		if(frm.doc.status== 'Scheduled' && !frm.doc.__islocal){
			//Allocate bed removed Temperarly....!
			/*if(!frm.doc.facility_alloc[0]){
				frm.add_custom_button(__("Allocate Bed"),function(){
					allocate_patient(frm);
				});
			}*/
			frm.add_custom_button(__("Cancel Schedule"),function(){
				cancel_schedule(frm);
			});
			frm.add_custom_button(__("Admit Patient"),function(){
				admit_patient(frm);
			});
		}
		if(frm.doc.status== 'Admitted'){
			frm.add_custom_button(__('Transfer'), function() {
				facility_transfer_allocate(frm);
			} );
			frm.add_custom_button(__("Consultation"),function(){
				btn_create_consultation(frm);
			},"Create");
			/*frm.add_custom_button(__("View All Consultations"), function() {
				frappe.route_options = {"Admission": frm.doc.name }
				frappe.set_route("List", "Consultation");
			});*/
			frm.add_custom_button(__('Pending Invoices'), function() {
				//Seles invoice - custom field - patient
				frappe.route_options = {"patient": frm.doc.patient, "status":['in',["Unpaid","Overdue"]]}
				frappe.set_route("List", "Sales Invoice");
			} );
			frm.add_custom_button(__("Discharge"),function(){
				queue_discharge_patient(frm);
			});
		}
		if(frm.doc.status== 'Queued'){
			/*frm.add_custom_button(__("Discharge"),function(){
				discharge_patient(frm);
			});*/
			if(frm.doc.created_ds == '1'){
				frm.page.set_primary_action(__("Discharge"),function(){
					discharge_patient(frm)
					cur_frm.reload_doc()
				});
				frm.add_custom_button(__('View Summary'), function() {
					frappe.set_route("Form", "Discharge Summary", frm.doc.name);
				} );
			}
			else{
				frm.add_custom_button(__("Create Discharge Summary"),function(){
					btn_discharge_summary(frm);
				});
			}
			cur_frm.fields.forEach(function(l){ cur_frm.set_df_property(l.df.fieldname, "read_only", 1); })
		}
		if(frm.doc.status== 'Discharged'){
			frm.disable_save();
			frm.add_custom_button(__('View Summary'), function() {
				frappe.set_route("Form", "Discharge Summary", frm.doc.name);
			} );
			//cur_frm.fields.forEach(function(l){ cur_frm.set_df_property(l.df.fieldname, "read_only", 1); })
		}
		if(frm.doc.status== 'Cancelled'){
			frm.disable_save();
		}
		if(!frm.doc.__islocal) {
			cur_frm.set_df_property("sb_facility_and_scheduling", "hidden", 0);
			frm.set_df_property("patient", "read_only", 1);
			frm.set_df_property("patient_id", "read_only", 1);
			frm.set_df_property("physician", "read_only", 1);
			frm.set_df_property("visit_department", "read_only", 1);
			frm.set_df_property("patient_age", "read_only", 1);
			frm.set_df_property("patient_sex", "read_only", 1);
			frm.set_df_property("op_consultation_id", "read_only", 1);
		}
		if(frm.doc.__islocal) {
			cur_frm.set_df_property("sb_facility_and_scheduling", "hidden", 1);
		}
		if(frm.doc.status != 'Scheduled' && frm.doc.status != 'Cancelled' && !frm.doc.__islocal ){
			if(frm.doc.facility_alloc){
				frm.add_custom_button(__("Invoice for Facility Used"),function(){
					btn_create_inv_for_facility_used(frm);
				},"Create");
			}
		}
	}
});

var cancel_schedule = function(frm){
	var doc = frm.doc;

	var d = new frappe.ui.Dialog({
		fields: [
			{fieldname:'confirmation_messages', fieldtype:'HTML'},
		],
		primary_action_label : __("Cancel Admission"),
		primary_action : function(){
			frappe.call({
				"method": "erpnext.medical.doctype.patient_admission.patient_admission.cancel_scheduled_admission",
				"args": {admission:doc.name},
				callback: function(r){
					cur_frm.reload_doc();
				}
			});
			d.hide();
		}
	})
	d.fields_dict.confirmation_messages.html("Are You Sure to Proceed ? Click 'Cancel Admission'".bold())
	d.show();
}

var admit_patient = function(frm){
	var doc = frm.doc;
	var d = new frappe.ui.Dialog({
		title: __("Facility Schedule"),
		fields: [
				{
				"fieldtype": "Date",
				"label": "Date In",
				"fieldname": "date_in",
				"reqd": 1,
				},
				{
				"fieldtype": "Time",
				"label": "Time In",
				"fieldname": "time_in",
				},
				{
				"fieldtype": "Link",
				"label": "Facility Type",
				"fieldname": "facility_type",
				"options": "Facility Type"
				},
				{
				"fieldtype": "Link",
				"label": "Facility",
				"fieldname": "facility_name",
				"options": "Facility",
				},
				{
				"fieldtype": "Link",
				"label": "Bed",
				"fieldname": "bed_number",
				"options": "Bed",
				"reqd": 1,
				},
				{
				"fieldtype": "Date",
				"label": "Expected Discharge",
				"fieldname": "expected_discharge"
				}
		],
		primary_action_label: __("Admit"),
		primary_action : function(){
			var values = d.get_values();
			if(!values)
				return;
			if(!values["time_in"]){
				time_in = null
			}else{
				time_in = values["time_in"]
			}
			if(!values["expected_discharge"]){
				expected_discharge = null
			}else{
				expected_discharge = values["expected_discharge"]
			}
			admit_and_allocate(values["date_in"],time_in,values["bed_number"],values["facility_type"],values["facility_name"],expected_discharge);
			d.hide();
		}
	});

	d.fields_dict["facility_name"].get_query = function(txt){
		return {
		filters: {
			"type": d.get_value("facility_type"),
			"occupied" : 0
			}
		}
	};
	d.fields_dict["bed_number"].get_query = function(txt){
		return {
		filters: {
			"parent": d.get_value("facility_name"),
			"occupied" : 0
			}
		}
	};

	if(frm.doc.facility_alloc[0]){
		d.set_values({
			"date_in":frm.doc.facility_alloc[0].date_in,
			"time_in":frm.doc.facility_alloc[0].time_in,
			"facility_type":frm.doc.facility_alloc[0].facility_type,
			"facility_name":frm.doc.facility_alloc[0].facility,
			"bed_number":frm.doc.facility_alloc[0].bed,
			"expected_discharge":frm.doc.facility_alloc[0].date_discharge
		})
	}
	d.show();

	var admit_and_allocate = function(date_in,time_in,bed_number,facility_type,facility_name,expected_discharge){
		frappe.call({
			"method": "erpnext.medical.doctype.patient_admission.patient_admission.admit_and_allocate_patient",
			"args": {patient: doc.patient, admission: doc.name,
				date_in:date_in, time_in:time_in, bed: bed_number,
				facility_type: facility_type, facility: facility_name,
				expected_discharge: expected_discharge},
			callback: function(r){
				cur_frm.reload_doc();
			}
		});
	}
}

var allocate_patient = function(frm){
	var doc = frm.doc;
	var d = new frappe.ui.Dialog({
		title: __("Facility Schedule"),
		fields: [
				{
				"fieldtype": "Date",
				"label": "Date In",
				"fieldname": "date_in",
				"reqd": 1,
				},
				{
				"fieldtype": "Time",
				"label": "Time In",
				"fieldname": "time_in"
				},
				{
				"fieldtype": "Link",
				"label": "Facility Type",
				"fieldname": "facility_type",
				"options": "Facility Type"
				},
				{
				"fieldtype": "Link",
				"label": "Facility",
				"fieldname": "facility_name",
				"options": "Facility",
				"get_query": {'occupied' : 0},
				},
				{
				"fieldtype": "Link",
				"label": "Bed",
				"fieldname": "bed_number",
				"options": "Bed",
				"reqd": 1,
				"get_query": {'occupied' : 0},
				},
				{
				"fieldtype": "Date",
				"label": "Expected Discharge",
				"fieldname": "expected_discharge"
				}
		],
		primary_action_label: __("Allocate Facility"),
		primary_action : function(){
			var values = d.get_values();
			if(!values)
				return;
			if(!values["time_in"]){
				time_in = null
			}else{
				time_in = values["time_in"]
			}
			if(!values["expected_discharge"]){
				expected_discharge = null
			}else{
				expected_discharge = values["expected_discharge"]
			}
			allocate(values["date_in"],time_in,values["bed_number"],values["facility_type"],values["facility_name"],expected_discharge);
			d.hide();
		}
	});

	d.fields_dict["facility_name"].get_query = function(txt){
		return {
		filters: {
			"type": d.get_value("facility_type"),
			"occupied" : 0
			}
		}
	};
	d.fields_dict["bed_number"].get_query = function(txt){
		return {
		filters: {
			"parent": d.get_value("facility_name"),
			"occupied" : 0
			}
		}
	};

	d.show();

	var allocate = function(date_in,time_in,bed_number,facility_type,facility_name,expected_discharge){
		frappe.call({
			"method": "erpnext.medical.doctype.patient_admission.patient_admission.allocate_facility",
			"args": {patient: doc.patient, admission: doc.name,
				date_in:date_in, time_in:time_in, bed: bed_number,
				 facility_type: facility_type, facility: facility_name,
				 expected_discharge: expected_discharge, status:"Scheduled", occupied:false},
			callback: function(r){
				cur_frm.reload_doc();
			}
		});
	}
}

var facility_transfer_allocate = function(frm){
	var doc = frm.doc;
	var d = new frappe.ui.Dialog({
		title: __("Transfer/Allocate"),
		fields: [
				{
				"fieldtype": "Link",
				"label": "Facility Type",
				"fieldname": "facility_type",
				"options": "Facility Type"
				},
				{
				"fieldtype": "Link",
				"label": "Facility",
				"fieldname": "facility_name",
				"options": "Facility",
				"get_query": {'occupied' : 0},
				},
				{
				"fieldtype": "Link",
				"label": "Bed",
				"fieldname": "bed_number",
				"options": "Bed",
				"reqd": 1,
				"get_query": {'occupied' : 0},
				},
				{
				"fieldtype": "Date",
				"label": "Expected Discharge",
				"fieldname": "expected_discharge"
				}
		],
		primary_action_label: __("Transfer/Allocate"),
		primary_action : function(){
			var values = d.get_values();
			if(!values)
				return;
			if(!values["expected_discharge"]){
				expected_discharge = null
			}else{
				expected_discharge = values["expected_discharge"]
			}
			transfer_and_allocate(values["bed_number"],values["facility_type"],values["facility_name"],expected_discharge);
			d.hide();
		}
	});

	d.fields_dict["facility_name"].get_query = function(txt){
		return {
		filters: {
			"type": d.get_value("facility_type"),
			"occupied" : 0
			}
		}
	};
	d.fields_dict["bed_number"].get_query = function(txt){
		return {
		filters: {
			"parent": d.get_value("facility_name"),
			"occupied" : 0
			}
		}
	};

	d.show();

	var transfer_and_allocate = function(bed_number,facility_type,facility_name,expected_discharge){
		frappe.call({
			"method": "erpnext.medical.doctype.patient_admission.patient_admission.facility_transfer_allocation",
			"args": {patient: doc.patient, admission: doc.name, bed_number: bed_number,
				facility_type: facility_type, facility_name: facility_name,
				expected_discharge: expected_discharge, old_facility_name: frm.doc.current_facility},
			callback: function(r){
				cur_frm.reload_doc();
			}
		});
	}
}


var queue_discharge_patient = function(frm){
	var doc = frm.doc;

	var d = new frappe.ui.Dialog({
		fields: [
			{fieldname:'confirmation_messages', fieldtype:'HTML'},
		],
		primary_action_label : __("Queue Discharge"),
		primary_action : function(){
			frappe.call({
				"method": "erpnext.medical.doctype.patient_admission.patient_admission.queue_discharge_patient",
				"args": {patient: doc.patient, admission: doc.name},
				callback: function(r){
					cur_frm.reload_doc();
				}
			});
			d.hide();
		}
	})
	d.fields_dict.confirmation_messages.html("Are You Sure to Proceed ? Click 'Queue Discharge'".bold())
	d.show();
}

var discharge_patient = function(frm){
	var doc = frm.doc;

	var d = new frappe.ui.Dialog({
		fields: [
			{fieldname:'confirmation_messages', fieldtype:'HTML'},
		],
		primary_action_label : __("Discharge"),
		primary_action : function(){
			frappe.call({
				"method": "erpnext.medical.doctype.patient_admission.patient_admission.discharge_patient",
				"args": {patient: doc.patient, admission: doc.name},
				callback: function(r){
					cur_frm.reload_doc();
				}
			});
			d.hide();
		}
	})
	d.fields_dict.confirmation_messages.html("Are You Sure to Proceed ? Click 'Discharge'".bold())
	d.show();
}

var btn_create_consultation = function(frm){
	var doc = frm.doc;
	frappe.call({
		method:"erpnext.medical.doctype.patient_admission.patient_admission.create_consultation",
		args: {admission:doc.name},
		callback: function(data){
			if(!data.exc){
				var doclist = frappe.model.sync(data.message);
				frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
			}
		}
	});
}

var btn_create_inv_for_facility_used = function(frm){
	var doc = frm.doc;
	frappe.call({
		method:"erpnext.medical.doctype.patient_admission.patient_admission.create_inv_for_facility_used",
		args: {admission:doc.name},
		callback: function(data){
			if(!data.exc){
				var doclist = frappe.model.sync(data.message);
				frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
			}
		}
	});
}

var btn_discharge_summary = function(frm){
	var doc = frm.doc;
	frappe.call({
		method:"erpnext.medical.doctype.patient_admission.patient_admission.create_discharge_summary",
		args: {admission:doc.name},
		callback: function(data){
			if(!data.exc){
				frappe.set_route("Form", "Discharge Summary", doc.name);
				cur_frm.reload_doc();
			}
		}
	});
}

frappe.ui.form.on("Patient Admission", "op_consultation_id",
    function(frm) {
	if(frm.doc.op_consultation_id){
		frappe.call({
		    "method": "frappe.client.get",
		    args: {
		        doctype: "Consultation",
		        name: frm.doc.op_consultation_id
		    },
		    callback: function (data) {
				frappe.model.set_value(frm.doctype,frm.docname, "patient", data.message.patient)
				frappe.model.set_value(frm.doctype,frm.docname, "physician", data.message.physician)
			}
		})
	}
});


frappe.ui.form.on("Patient Admission", "patient",
    function(frm) {
	if(frm.doc.patient){
		frappe.call({
		    "method": "frappe.client.get",
		    args: {
		        doctype: "Patient",
		        name: frm.doc.patient
		    },
		    callback: function (data) {
					age = null
					if(data.message.dob){
						age = calculate_age(data.message.dob)
					}else if (data.message.age_int){
						age = data.message.age_int
						if(data.message.age_as_on){
							age = age+" as on "+data.message.age_as_on
						}
					}
					frappe.model.set_value(frm.doctype,frm.docname, "patient_age", age)
		    	frappe.model.set_value(frm.doctype,frm.docname, "patient_id", data.message.patient_id)
					frappe.model.set_value(frm.doctype,frm.docname, "patient_sex", data.message.sex)
		    }
		})
	}
});

frappe.ui.form.on("Patient Admission", "physician",
    function(frm) {
	if(frm.doc.physician){
		frappe.call({
		    "method": "frappe.client.get",
		    args: {
		        doctype: "Physician",
		        name: frm.doc.physician
		    },
		    callback: function (data) {
				frappe.model.set_value(frm.doctype,frm.docname, "visit_department",data.message.department)
		    }
		})
	}
});

var calculate_age = function(dob){
	today = new Date();
	birthDate = new Date(dob);
	age_yr = today.getFullYear() - birthDate.getFullYear();
	today_m = today.getMonth()+1 //Month jan = 0
	birth_m = birthDate.getMonth()+1 //Month jan = 0
	m = today_m - birth_m;
	d = today.getDate() - birthDate.getDate()

	if (m < 0 || (m === 0 && today.getDate() < birthDate.getDate())) {
		age_yr--;
	}
	if (m < 0) {
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
	return age_str
}
