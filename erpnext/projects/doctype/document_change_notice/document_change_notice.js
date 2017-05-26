// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide("erpnext.document_change_notice");

frappe.ui.form.on('Document Change Notice', {
	onload: function(frm) {
		if (!frm.doc.start_date) {
			frm.set_value("start_date", get_today());
		}
	
		//frm.set_query("employee", erpnext.queries.employee);
		frm.add_fetch("employee", "department", "emp_department");
		erpnext.document_change_notice.protect_approval(frm);
	},
	validate: function(frm) {
		erpnext.document_change_notice.validate_duplicate_docs(frm.doc);
		erpnext.document_change_notice.validate_duplicate_approvals(frm.doc);
		erpnext.document_change_notice.protect_approval(frm);
	},
	
});

frappe.ui.form.on('Document Change Notice Item', {
	new_name: function(frm, cdt, cdn){
		var me = this;
		var item = frappe.get_doc(cdt, cdn);
		if(item.new_name && item.ref_type)
		{
			return frappe.call({
				method: "erpnext.projects.doctype.document_change_notice.document_change_notice.get_amended_from",
				args: {
					'doctype': item.ref_type,
					'name': item.new_name
				},
				callback: function(r) {
					debugger;
					if (!r.exc) {
						
						if(r.message.amended_from)
						{
							frappe.model.set_value(cdt, cdn, "old_name", r.message.amended_from);
						}
					}
				}
			});
			
		}
	},
	old_name: function(frm, cdt, cdn){
		debugger;
		var me = this;
		var item = frappe.get_doc(cdt, cdn);
		if(item.new_name && item.old_name && (item.new_name == item.old_name))
		{
			frappe.throw(__("Old Document can not be the same as New Document"));
		}
	}
});

frappe.ui.form.on('Document Change Notice Department', {
	form_render:function(frm, cdt, cdn){
		erpnext.document_change_notice.protect_approval_gridform(frm, cdt, cdn);
	},
	
	department: function(frm, cdt, cdn){
		var me = this;
		var dep = frappe.get_doc(cdt, cdn);
		debugger;
		if(dep.department)
		{
			frappe.model.get_value("Department", dep.department, "manager", function(value) {
				frappe.model.set_value(cdt, cdn, "manager", value.manager);
			});
		} else {
			frappe.model.set_value(cdt, cdn, "manager", "");
		}
	},
	manager: function(frm, cdt, cdn){
		var me = this;
		debugger;
		var dep = frappe.get_doc(cdt, cdn);
		if(dep.manager)
		{
			frappe.model.get_value("Employee", dep.manager, "user_id", function(value) {
				frappe.model.set_value(cdt, cdn, "manager_id", value.user_id);
			});
		} else {
			frappe.model.set_value(cdt, cdn, "manager_id", "");
		}
	}
});


erpnext.document_change_notice.validate_duplicate_docs = function(doc) {
		var doc_list = doc.items || [];
		for(var i=0; i<doc_list.length; i++) {
			for(var j=0; j<doc_list.length; j++) {
				if(i!=j && doc_list[i].department && doc_list[i].department==doc_list[j].department) {
					msgprint(__("You have entered duplicate documents. Please rectify and try again."));
					validated = false;
					return;
				}
			}
		}
	};
	
erpnext.document_change_notice.validate_duplicate_approvals = function(doc) {
		var dep_list = doc.approvals || [];
		for(var i=0; i<dep_list.length; i++) {
			for(var j=0; j<dep_list.length; j++) {
				if(i!=j && dep_list[i].new_doc && dep_list[i].new_doc==dep_list[j].new_doc) {
					msgprint(__("You have entered duplicate approving departments. Please rectify and try again."));
					validated = false;
					return;
				}
			}
		}
	}
	
erpnext.document_change_notice.protect_approval = function(frm)  {
	debugger;
	if(frm.doc.docstatus == 0)
	{
		frm.get_field("approvals").grid.toggle_enable("department", true);
		frm.get_field("approvals").grid.toggle_enable("manager", true);
		frm.get_field("approvals").grid.toggle_enable("manager_id", true);
		frm.get_field("approvals").grid.toggle_enable("status", false);
	
	}else if(frm.doc.docstatus == 1)
	{
		frm.get_field("approvals").grid.toggle_enable("department", false);
		frm.get_field("approvals").grid.toggle_enable("manager", false);
		frm.get_field("approvals").grid.toggle_enable("manager_id", false);
		frm.get_field("approvals").grid.toggle_enable("status", true);
	}
}
erpnext.document_change_notice.protect_approval_gridform = function(frm, cdt, cdn)  {
	debugger;
	if(frm.doc.docstatus == 1)
	{
		//frm.get_field("approvals").grid.toggle_enable("status", false);
		dep_list = frm.doc.approvals || [];
		
		var apps = frm.get_field("approvals");
		//grid = apps.grid.get_grid(frm.docname);
		var grid_row = apps.grid.get_grid_row(cdn);

		var docfield = grid_row.docfields;
		var dep = frappe.get_doc(cdt, cdn);
		for(var i = 0; i < docfield.length; i++) {
			if(docfield[i].allow_on_submit && dep.manager_id == frappe.user.name && frm.doc.status == 'Under Review')
			{
				docfield[i].read_only = 0;
			}
			else{
				docfield[i].read_only = 1;
			}
		}
		grid_row.refresh();
	}
}