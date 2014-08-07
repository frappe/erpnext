// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.hr");
erpnext.hr.EmployeeController = frappe.ui.form.Controller.extend({
	setup: function() {
		this.frm.fields_dict.user_id.get_query = function(doc, cdt, cdn) {
			return { query:"frappe.core.doctype.user.user.user_query"} }
		this.frm.fields_dict.reports_to.get_query = function(doc, cdt, cdn) {
			return { query: "erpnext.controllers.queries.employee_query"} }
	},

	onload: function() {
		this.setup_leave_approver_select();
		if(this.frm.doc.__islocal) this.frm.set_value("employee_name", "");
	},

	refresh: function() {
		var me = this;
		erpnext.toggle_naming_series();
		if(!this.frm.doc.__islocal && this.frm.doc.__onload &&
			!this.frm.doc.__onload.salary_structure_exists) {
				cur_frm.add_custom_button(__('Make Salary Structure'), function() {
					me.make_salary_structure(this); }, frappe.boot.doctype_icons["Salary Structure"]);
		}
	},

	setup_leave_approver_select: function() {
		var me = this;
		return this.frm.call({
			method: "erpnext.hr.utils.get_leave_approver_list",
			callback: function(r) {
				var df = frappe.meta.get_docfield("Employee Leave Approver", "leave_approver",
					me.frm.doc.name);
				df.options = $.map(r.message, function(user) {
					return {value: user, label: frappe.user_info(user).fullname};
				});
				me.frm.fields_dict.employee_leave_approvers.refresh();
			}
		});
	},

	date_of_birth: function() {
		return cur_frm.call({
			method: "get_retirement_date",
			args: {date_of_birth: this.frm.doc.date_of_birth}
		});
	},

	salutation: function() {
		if(this.frm.doc.salutation) {
			this.frm.set_value("gender", {
				"Mr": "Male",
				"Ms": "Female"
			}[this.frm.doc.salutation]);
		}
	},

	make_salary_structure: function(btn) {
		frappe.model.open_mapped_doc({
			method: "erpnext.hr.doctype.employee.employee.make_salary_structure",
			frm: cur_frm
		});
	}
});
cur_frm.cscript = new erpnext.hr.EmployeeController({frm: cur_frm});
