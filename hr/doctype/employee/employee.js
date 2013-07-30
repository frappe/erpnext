// ERPNext - web based ERP (http://erpnext.com)
// Copyright (C) 2012 Web Notes Technologies Pvt Ltd
// 
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
// 
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	See the
// GNU General Public License for more details.
// 
// You should have received a copy of the GNU General Public License
// along with this program.	If not, see <http://www.gnu.org/licenses/>.

wn.provide("erpnext.hr");
erpnext.hr.EmployeeController = wn.ui.form.Controller.extend({
	setup: function() {
		this.setup_leave_approver_select();
		this.frm.fields_dict.user_id.get_query = function(doc,cdt,cdn) {
				return { query:"controllers.queries.profile_query"} }
		this.frm.fields_dict.reports_to.get_query = function(doc,cdt,cdn) {	
			return{	query:"controllers.queries.employee_query"}	}
	},
	
	onload: function() {
		this.frm.toggle_display(["esic_card_no", "gratuity_lic_id", "pan_number", "pf_number"],
			wn.control_panel.country==="India");
	},
	
	refresh: function() {
		var me = this;
		erpnext.hide_naming_series();
		if(!this.frm.doc.__islocal) {			
			cur_frm.add_custom_button('Make Salary Structure', function() {
				me.make_salary_structure(this); });
		}
	},
	
	setup_leave_approver_select: function() {
		var me = this;
		return this.frm.call({
			method:"hr.utils.get_leave_approver_list",
			callback: function(r) {
				me.frm.fields_dict.employee_leave_approvers.grid
					.get_field("leave_approver").df.options =
					$.map(r.message, function(profile) { 
						return {value: profile, label: wn.user_info(profile).fullname}; 
					});
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
		var me = this;
		this.validate_salary_structure(btn, function(r) {
			if(r.message) {
				msgprint(wn._("Employee") + ' "' + me.frm.doc.name + '": ' 
					+ wn._("An active Salary Structure already exists. \
						If you want to create new one, please ensure that no active \
						Salary Structure exists for this Employee. \
						Go to the active Salary Structure and set \"Is Active\" = \"No\""));
			} else if(!r.exc) {
				wn.model.map({
					source: wn.model.get_doclist(me.frm.doc.doctype, me.frm.doc.name),
					target: "Salary Structure"
				});
			}
		});
	},
	
	validate_salary_structure: function(btn, callback) {
		var me = this;
		return this.frm.call({
			btn: btn,
			method: "webnotes.client.get_value",
			args: {
				doctype: "Salary Structure",
				fieldname: "name",
				filters: {
					employee: me.frm.doc.name,
					is_active: "Yes",
					docstatus: ["!=", 2]
				},
			},
			callback: callback
		});
	},
});
cur_frm.cscript = new erpnext.hr.EmployeeController({frm: cur_frm});