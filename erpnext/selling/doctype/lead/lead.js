// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

{% include 'setup/doctype/contact_control/contact_control.js' %};

frappe.provide("erpnext");
erpnext.LeadController = frappe.ui.form.Controller.extend({
	setup: function() {
		this.frm.fields_dict.customer.get_query = function(doc, cdt, cdn) {
				return { query: "erpnext.controllers.queries.customer_query" } }
	},

	onload: function() {
		if(cur_frm.fields_dict.lead_owner.df.options.match(/^User/)) {
			cur_frm.fields_dict.lead_owner.get_query = function(doc, cdt, cdn) {
				return { query:"frappe.core.doctype.user.user.user_query" } }
		}

		if(cur_frm.fields_dict.contact_by.df.options.match(/^User/)) {
			cur_frm.fields_dict.contact_by.get_query = function(doc, cdt, cdn) {
				return { query:"frappe.core.doctype.user.user.user_query" } }
		}
	},

	refresh: function() {
		var doc = this.frm.doc;
		erpnext.toggle_naming_series();

		if(!this.frm.doc.__islocal && this.frm.doc.__onload && !this.frm.doc.__onload.is_customer) {
			this.frm.add_custom_button(__("Create Customer"), this.create_customer,
				frappe.boot.doctype_icons["Customer"], "btn-default");
			this.frm.add_custom_button(__("Create Opportunity"), this.create_opportunity,
				frappe.boot.doctype_icons["Opportunity"], "btn-default");
			this.frm.appframe.add_button(__("Send SMS"), this.frm.cscript.send_sms, "icon-mobile-phone");
		}

		cur_frm.communication_view = new frappe.views.CommunicationList({
			list: frappe.get_list("Communication", {"parenttype": "Lead", "parent":this.frm.doc.name}),
			parent: this.frm.fields_dict.communication_html.wrapper,
			doc: this.frm.doc,
			recipients: this.frm.doc.email_id
		});

		if(!this.frm.doc.__islocal) {
			this.make_address_list();
		}
	},

	make_address_list: function() {
		var me = this;
		if(!this.frm.address_list) {
			this.frm.address_list = new frappe.ui.Listing({
				parent: this.frm.fields_dict['address_html'].wrapper,
				page_length: 5,
				new_doctype: "Address",
				get_query: function() {
					return 'select name, address_type, address_line1, address_line2, \
					city, state, country, pincode, fax, email_id, phone, \
					is_primary_address, is_shipping_address from tabAddress \
					where lead="'+me.frm.doc.name+'" and docstatus != 2 \
					order by is_primary_address, is_shipping_address desc'
				},
				as_dict: 1,
				no_results_message: __('No addresses created'),
				render_row: this.render_address_row,
			});
			// note: render_address_row is defined in contact_control.js
		}
		this.frm.address_list.run();
	},

	create_customer: function() {
		frappe.model.open_mapped_doc({
			method: "erpnext.selling.doctype.lead.lead.make_customer",
			frm: cur_frm
		})
	},

	create_opportunity: function() {
		frappe.model.open_mapped_doc({
			method: "erpnext.selling.doctype.lead.lead.make_opportunity",
			frm: cur_frm
		})
	}
});

$.extend(cur_frm.cscript, new erpnext.LeadController({frm: cur_frm}));

cur_frm.cscript.send_sms = function() {
	frappe.require("assets/erpnext/js/sms_manager.js");
	var sms_man = new SMSManager(cur_frm.doc);
}

