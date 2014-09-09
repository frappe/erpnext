// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

{% include 'setup/doctype/contact_control/contact_control.js' %};

cur_frm.cscript.onload = function(doc, dt, dn) {
	cur_frm.cscript.load_defaults(doc, dt, dn);
}

cur_frm.cscript.load_defaults = function(doc, dt, dn) {
	doc = locals[doc.doctype][doc.name];
	if(!(doc.__islocal && doc.lead_name)) { return; }

	var fields_to_refresh = frappe.model.set_default_values(doc);
	if(fields_to_refresh) { refresh_many(fields_to_refresh); }
}

cur_frm.add_fetch('lead_name', 'company_name', 'customer_name');
cur_frm.add_fetch('default_sales_partner','commission_rate','default_commission_rate');

cur_frm.cscript.refresh = function(doc, dt, dn) {
	cur_frm.cscript.setup_dashboard(doc);

	if(frappe.defaults.get_default("cust_master_name")!="Naming Series") {
		cur_frm.toggle_display("naming_series", false);
	} else {
		erpnext.toggle_naming_series();
	}

	if(doc.__islocal){
		hide_field(['address_html','contact_html']);
	}else{
		unhide_field(['address_html','contact_html']);
		// make lists
		cur_frm.cscript.make_address(doc, dt, dn);
		cur_frm.cscript.make_contact(doc, dt, dn);

		cur_frm.communication_view = new frappe.views.CommunicationList({
			parent: cur_frm.fields_dict.communication_html.wrapper,
			doc: doc,
		});
	}
}

cur_frm.cscript.validate = function(doc, dt, dn) {
	if(doc.lead_name) frappe.model.clear_doc("Lead", doc.lead_name);
}

cur_frm.cscript.setup_dashboard = function(doc) {
	cur_frm.dashboard.reset(doc);
	if(doc.__islocal)
		return;
	if (in_list(user_roles, "Accounts User") || in_list(user_roles, "Accounts Manager"))
		cur_frm.dashboard.set_headline('<span class="text-muted">'+ __('Loading...')+ '</span>')

	cur_frm.dashboard.add_doctype_badge("Opportunity", "customer");
	cur_frm.dashboard.add_doctype_badge("Quotation", "customer");
	cur_frm.dashboard.add_doctype_badge("Sales Order", "customer");
	cur_frm.dashboard.add_doctype_badge("Delivery Note", "customer");
	cur_frm.dashboard.add_doctype_badge("Sales Invoice", "customer");

	return frappe.call({
		type: "GET",
		method: "erpnext.selling.doctype.customer.customer.get_dashboard_info",
		args: {
			customer: cur_frm.doc.name
		},
		callback: function(r) {
			if (in_list(user_roles, "Accounts User") || in_list(user_roles, "Accounts Manager")) {
				cur_frm.dashboard.set_headline(
					__("Total Billing This Year: ") + "<b>"
					+ format_currency(r.message.total_billing, erpnext.get_currency(cur_frm.doc.company))
					+ '</b> / <span class="text-muted">' + __("Unpaid") + ": <b>"
					+ format_currency(r.message.total_unpaid, erpnext.get_currency(cur_frm.doc.company))
					+ '</b></span>');
			}
			cur_frm.dashboard.set_badge_count(r.message);
		}
	});
}

cur_frm.cscript.make_address = function() {
	if(!cur_frm.address_list) {
		cur_frm.address_list = new frappe.ui.Listing({
			parent: cur_frm.fields_dict['address_html'].wrapper,
			page_length: 5,
			new_doctype: "Address",
			get_query: function() {
				return "select name, address_type, address_line1, address_line2, city, state, country, pincode, fax, email_id, phone, is_primary_address, is_shipping_address from tabAddress where customer='" +
					cur_frm.doc.name.replace(/'/g, "\\'") + "' and docstatus != 2 order by is_primary_address desc"
			},
			as_dict: 1,
			no_results_message: __('No addresses created'),
			render_row: cur_frm.cscript.render_address_row,
		});
		// note: render_address_row is defined in contact_control.js
	}
	cur_frm.address_list.run();
}

cur_frm.cscript.make_contact = function() {
	if(!cur_frm.contact_list) {
		cur_frm.contact_list = new frappe.ui.Listing({
			parent: cur_frm.fields_dict['contact_html'].wrapper,
			page_length: 5,
			new_doctype: "Contact",
			get_query: function() {
				return "select name, first_name, last_name, email_id, phone, mobile_no, department, designation, is_primary_contact from tabContact where customer='" +
					cur_frm.doc.name.replace(/'/g, "\\'") + "' and docstatus != 2 order by is_primary_contact desc"
			},
			as_dict: 1,
			no_results_message: __('No contacts created'),
			render_row: cur_frm.cscript.render_contact_row,
		});
		// note: render_contact_row is defined in contact_control.js
	}
	cur_frm.contact_list.run();
}

cur_frm.fields_dict['customer_group'].get_query = function(doc, dt, dn) {
	return{
		filters:{'is_group': 'No'}
	}
}

cur_frm.fields_dict.lead_name.get_query = function(doc, cdt, cdn) {
	return{
		query: "erpnext.controllers.queries.lead_query"
	}
}

cur_frm.fields_dict['default_price_list'].get_query = function(doc, cdt, cdn) {
	return{
		filters:{'selling': 1}
	}
}
