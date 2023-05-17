// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt


frappe.ui.form.on("Travel Request", {
	grade_details: function(frm) {
		$.each(frm.doc.travel_requisition || [], function (i, row) {
			frappe.call({
				method: "erpnext.hr.doctype.travel_request.travel_request.get_grade_child_details",
				async:false,
				args: {grade:frm.doc.employee_grade,
					mode: row.mode},
				callback: function(r) {
					var options = r.message
					var field = frappe.meta.get_docfield("Travel Requisition","class", row.name);
					field.options = [""].concat(options);
					cur_frm.refresh_field("class");
				}
			})
		})
	},
	before_save :function(frm){
		if (frm.doc.__islocal)
		{	frm.set_value("status", "Draft");
		}
	},
	refresh: function (frm) {
		if (frm.doc.employee_grade){
			frm.events.grade_details(frm);
		}

		let doc = frm.doc;
		if (!frm.doc.__islocal) {
			if (frappe.session.user === frm.doc.prepared_by){
				if (doc.status === "Draft") {
					cur_frm.add_custom_button(__('Approved Request'), () => cur_frm.events.approved_request(), __("Status"));
				}
				if (doc.status == "To Be Approved") {
					cur_frm.disable_save();				
				}				
			}
		}

		if (frappe.session.user === frm.doc.approving_officer) {
	
			if (doc.status == "To Be Approved" || doc.status=== "Check"){
				cur_frm.add_custom_button(__('Draft'), () => cur_frm.events.draft(), __("Status"));
			}
			if (doc.status=== "To Be Approved") {
				if (doc.status != "Approved") {
					cur_frm.add_custom_button(__('Approved'), () => cur_frm.events.approved(), __("Status"));
				}		
			}
		}
	},
	draft: function(){
		cur_frm.set_value("status","Draft");
		cur_frm.save();
	},
	approved: function(){
		let d = new frappe.ui.Dialog({
			title: 'Approved By HOD',
			fields: [
				{
					label: 'Remark',
					fieldname: 'remark',
					fieldtype: 'Small Text'
				},
			],
			primary_action_label: 'Submit',
			primary_action(values) {
				console.log(values);
				d.hide();
				cur_frm.set_value("status","Approved");
				cur_frm.set_value('remark', (values["remark"]));
				cur_frm.save();
			}
		});
		d.show();
	},
	approved_request: function(){
		frappe.call({                        
			method: "erpnext.hr.doctype.travel_request.travel_request.report_to_person_view_travel_request_form", 
			async:false,
			args: { 
					name:cur_frm.doc.name,
					approving_officer : cur_frm.doc.approving_officer,				},	 
		 });
		 cur_frm.set_value("status","To Be Approved");
		 cur_frm.save();
	},
});
frappe.ui.form.on("Travel Requisition", {
	mode:function(frm,cdt,cdn) {
		var d = locals[cdt][cdn];
		frappe.call({
			method: "erpnext.hr.doctype.travel_request.travel_request.get_grade_child_details",
			async:false,
			args: {grade:frm.doc.employee_grade,
				mode: d.mode},
			callback: function(r) {
				var options = r.message
				var field = frappe.meta.get_docfield(cdt, "class", cdn);
				field.options = [""].concat(options);
				frappe.model.set_value(cdt, cdn, "class", "");
				cur_frm.refresh_field("class");				
				// frm.save();
			}
		})
	},
	
});
