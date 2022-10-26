// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext");
cur_frm.email_field = "email_id";

erpnext.LeadController = frappe.ui.form.Controller.extend({
	setup: function () {
		this.frm.custom_make_buttons = {
			'Customer': 'Customer',
			'Quotation': 'Quotation',
			'Opportunity': 'Opportunity',
			'Vehicle Quotation': 'Vehicle Quotation',
		}

		this.frm.fields_dict.customer.get_query = function (doc, cdt, cdn) {
			return { query: "erpnext.controllers.queries.customer_query" }
		}

		this.frm.toggle_reqd("lead_name", !this.frm.doc.organization_lead);
	},

	onload: function () {
	},

	refresh: function () {
		var doc = this.frm.doc;
		erpnext.toggle_naming_series();
		erpnext.hide_company();
		frappe.dynamic_link = { doc: doc, fieldname: 'name', doctype: 'Lead' }

		if(!doc.__islocal && doc.__onload && !doc.__onload.is_customer) {
			this.frm.add_custom_button(__("Customer"), this.create_customer, __('Create'));
			this.frm.add_custom_button(__("Opportunity"), this.create_opportunity, __('Create'));
			this.frm.add_custom_button(__("Quotation"), this.make_quotation, __('Create'));

			if (frappe.boot.active_domains.includes("Vehicles")) {
				this.frm.add_custom_button(__("Vehicle Quotation"), this.make_vehicle_quotation, __('Create'));
			}
		}

		if (!this.frm.doc.__islocal) {
			frappe.contacts.render_address_and_contact(cur_frm);
		} else {
			frappe.contacts.clear_address_and_contact(cur_frm);
		}
	},

	create_customer: function () {
		frappe.model.open_mapped_doc({
			method: "erpnext.crm.doctype.lead.lead.make_customer",
			frm: cur_frm
		})
	},

	create_opportunity: function () {
		frappe.model.open_mapped_doc({
			method: "erpnext.crm.doctype.lead.lead.make_opportunity",
			frm: cur_frm
		})
	},

	make_quotation: function () {
		frappe.model.open_mapped_doc({
			method: "erpnext.crm.doctype.lead.lead.make_quotation",
			frm: cur_frm
		})
	},

	make_vehicle_quotation: function () {
		frappe.model.open_mapped_doc({
			method: "erpnext.crm.doctype.lead.lead.make_vehicle_quotation",
			frm: cur_frm
		})
	},

	organization_lead: function () {
		this.frm.toggle_reqd("lead_name", !this.frm.doc.organization_lead);
		this.frm.toggle_reqd("company_name", this.frm.doc.organization_lead);
	},

	company_name: function () {
		if (this.frm.doc.organization_lead == 1) {
			this.frm.set_value("lead_name", this.frm.doc.company_name);
		}
	},

	contact_date: function () {
		if (this.frm.doc.contact_date) {
			let d = moment(this.frm.doc.contact_date);
			d.add(1, "hours");
			this.frm.set_value("ends_on", d.format(frappe.defaultDatetimeFormat));
		}
	},

	validate: function() {
		erpnext.utils.format_ntn(this.frm, "tax_id");
		erpnext.utils.format_cnic(this.frm, "tax_cnic");
		erpnext.utils.format_strn(this.frm, "tax_strn");

		erpnext.utils.format_mobile_pakistan(this.frm, "mobile_no");
		erpnext.utils.format_mobile_pakistan(this.frm, "mobile_no_2");
	},

	tax_id: function() {
		erpnext.utils.format_ntn(this.frm, "tax_id");
		erpnext.utils.validate_duplicate_tax_id(this.frm.doc, "tax_id");
	},
	tax_cnic: function() {
		erpnext.utils.format_cnic(this.frm, "tax_cnic");
		erpnext.utils.validate_duplicate_tax_id(this.frm.doc, "tax_cnic");
	},
	tax_strn: function() {
		erpnext.utils.format_strn(this.frm, "tax_strn");
		erpnext.utils.validate_duplicate_tax_id(this.frm.doc, "tax_strn");
	},

	mobile_no: function () {
		erpnext.utils.format_mobile_pakistan(this.frm, "mobile_no");
	},
	mobile_no_2: function () {
		erpnext.utils.format_mobile_pakistan(this.frm, "mobile_no_2");
	}
});

$.extend(cur_frm.cscript, new erpnext.LeadController({ frm: cur_frm }));
