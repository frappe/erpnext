// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Customer", "refresh", function(frm) {
	cur_frm.cscript.setup_dashboard(frm.doc);

	if(frappe.defaults.get_default("cust_master_name")!="Naming Series") {
		frm.toggle_display("naming_series", false);
	} else {
		erpnext.toggle_naming_series();
	}

	frm.toggle_display(['address_html','contact_html'], !frm.doc.__islocal);

	if(!frm.doc.__islocal) erpnext.utils.render_address_and_contact(frm);
})

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
				if(r.message["company_currency"].length == 1) {
					cur_frm.dashboard.set_headline(
						__("Total Billing This Year: ") + "<b>"
						+ format_currency(r.message.total_billing, r.message["company_currency"][0])
						+ '</b> / <span class="text-muted">' + __("Unpaid") + ": <b>"
						+ format_currency(r.message.total_unpaid, r.message["company_currency"][0])
						+ '</b></span>');
				}
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

cur_frm.fields_dict['accounts'].grid.get_field('account').get_query = function(doc, cdt, cdn) {
	var d  = locals[cdt][cdn];
	return {
		filters: {
			'account_type': 'Receivable',
			'company': d.company,
			'group_or_ledger': 'Ledger'
		}
	}
}
