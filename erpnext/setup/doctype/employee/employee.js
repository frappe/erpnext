// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.setup");
erpnext.setup.EmployeeController = class EmployeeController extends frappe.ui.form.Controller {
	setup() {
		this.frm.fields_dict.user_id.get_query = function (doc, cdt, cdn) {
			return {
				query: "frappe.core.doctype.user.user.user_query",
				filters: { ignore_user_type: 1 },
			};
		};
		this.frm.fields_dict.reports_to.get_query = function (doc, cdt, cdn) {
			return { query: "erpnext.controllers.queries.employee_query" };
		};
	}

	refresh() {
		erpnext.toggle_naming_series();
	}
};

frappe.ui.form.on("Employee", {
	onload: function (frm) {
		frm.set_query("department", function () {
			return {
				filters: {
					company: frm.doc.company,
				},
			};
		});
	},
	prefered_contact_email: function (frm) {
		frm.events.update_contact(frm);
	},

	personal_email: function (frm) {
		frm.events.update_contact(frm);
	},

	company_email: function (frm) {
		frm.events.update_contact(frm);
	},

	user_id: function (frm) {
		frm.events.update_contact(frm);
	},

	update_contact: function (frm) {
		var prefered_email_fieldname = frappe.model.scrub(frm.doc.prefered_contact_email) || "user_id";
		frm.set_value("prefered_email", frm.fields_dict[prefered_email_fieldname].value);
	},

	status: function (frm) {
		return frm.call({
			method: "deactivate_sales_person",
			args: {
				employee: frm.doc.employee,
				status: frm.doc.status,
			},
		});
	},

	create_user: function (frm) {
		if (!frm.doc.prefered_email) {
			frappe.throw(__("Please enter Preferred Contact Email"));
		}
		frappe.call({
			method: "erpnext.setup.doctype.employee.employee.create_user",
			args: {
				employee: frm.doc.name,
				email: frm.doc.prefered_email,
			},
			freeze: true,
			freeze_message: __("Creating User..."),
			callback: function (r) {
				frm.reload_doc();
			},
		});
	},
});

cur_frm.cscript = new erpnext.setup.EmployeeController({
	frm: cur_frm,
});

frappe.tour["Employee"] = [
	{
		fieldname: "first_name",
		title: "First Name",
		description: __(
			"Enter First and Last name of Employee, based on Which Full Name will be updated. IN transactions, it will be Full Name which will be fetched."
		),
	},
	{
		fieldname: "company",
		title: "Company",
		description: __("Select a Company this Employee belongs to."),
	},
	{
		fieldname: "date_of_birth",
		title: "Date of Birth",
		description: __(
			"Select Date of Birth. This will validate Employees age and prevent hiring of under-age staff."
		),
	},
	{
		fieldname: "date_of_joining",
		title: "Date of Joining",
		description: __(
			"Select Date of joining. It will have impact on the first salary calculation, Leave allocation on pro-rata bases."
		),
	},
	{
		fieldname: "reports_to",
		title: "Reports To",
		description: __(
			"Here, you can select a senior of this Employee. Based on this, Organization Chart will be populated."
		),
	},
];
