// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.crm");

erpnext.crm.LeadController = frappe.ui.form.Controller.extend({
	setup: function () {
		this.frm.custom_make_buttons = {
			'Customer': 'Customer',
			'Quotation': 'Quotation',
			'Opportunity': 'Opportunity',
			'Vehicle Quotation': 'Vehicle Quotation',
		}

		this.frm.email_field = 'email_id';
	},

	refresh: function () {
		erpnext.toggle_naming_series();
		erpnext.hide_company();

		this.set_dynamic_link();
		this.set_sales_person_from_user();
		this.setup_buttons();

		this.frm.toggle_reqd("lead_name", !this.frm.doc.organization_lead);

		if (!this.frm.doc.__islocal) {
			frappe.contacts.render_address_and_contact(this.frm);
		} else {
			frappe.contacts.clear_address_and_contact(this.frm);
		}
	},

	validate: function() {
		erpnext.utils.format_ntn(this.frm, "tax_id");
		erpnext.utils.format_cnic(this.frm, "tax_cnic");
		erpnext.utils.format_strn(this.frm, "tax_strn");

		erpnext.utils.format_mobile_pakistan(this.frm, "mobile_no");
		erpnext.utils.format_mobile_pakistan(this.frm, "mobile_no_2");
	},

	set_dynamic_link: function() {
		frappe.dynamic_link = {doc: this.frm.doc, fieldname: 'name', doctype: 'Lead'}
	},

	set_sales_person_from_user: function() {
		if (!this.frm.get_field('sales_person') || this.frm.doc.sales_person || !this.frm.doc.__islocal) {
			return;
		}

		erpnext.utils.get_sales_person_from_user(sales_person => {
			if (sales_person) {
				this.frm.set_value('sales_person', sales_person);
			}
		});
	},

	setup_buttons: function () {
		if (!this.frm.doc.__islocal) {
			if (!this.frm.doc.customer) {
				this.frm.add_custom_button(__("Customer"), () => this.make_or_set_customer(),
					__('Create'));
				this.frm.add_custom_button(__("Opportunity"), () => this.create_opportunity(),
					__('Create'));

				if (frappe.boot.active_domains.includes("Vehicles")) {
					this.frm.add_custom_button(__("Vehicle Quotation"), () => this.make_vehicle_quotation(),
						__('Create'));
				}

				this.frm.add_custom_button(__("Quotation"), () => this.make_quotation(),
					__('Create'));
			} else {
				this.frm.add_custom_button(__("Customer"), () => this.make_or_set_customer(),
					__("Change"));
			}
		}
	},

	make_or_set_customer: function () {
		erpnext.utils.make_customer_from_lead(this.frm, this.frm.doc.name);
	},

	create_opportunity: function () {
		frappe.model.open_mapped_doc({
			method: "erpnext.crm.doctype.lead.lead.make_opportunity",
			frm: this.frm
		})
	},

	make_quotation: function () {
		frappe.model.open_mapped_doc({
			method: "erpnext.crm.doctype.lead.lead.make_quotation",
			frm: this.frm
		})
	},

	make_vehicle_quotation: function () {
		frappe.model.open_mapped_doc({
			method: "erpnext.crm.doctype.lead.lead.make_vehicle_quotation",
			frm: this.frm
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

$.extend(cur_frm.cscript, new erpnext.crm.LeadController({ frm: cur_frm }));
