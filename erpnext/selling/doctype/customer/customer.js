// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

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

		erpnext.utils.render_address_and_contact(cur_frm)

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
