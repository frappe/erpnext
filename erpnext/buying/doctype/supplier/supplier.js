// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.cscript.refresh = function(doc, dt, dn) {
	cur_frm.cscript.make_dashboard(doc);

	if(frappe.defaults.get_default("supp_master_name")!="Naming Series") {
		cur_frm.toggle_display("naming_series", false);
	} else {
		erpnext.toggle_naming_series();
	}

	if(doc.__islocal){
    	hide_field(['address_html','contact_html']);
	}
	else{
	  	unhide_field(['address_html','contact_html']);

		erpnext.utils.render_address_and_contact(cur_frm)

		cur_frm.communication_view = new frappe.views.CommunicationList({
			parent: cur_frm.fields_dict.communication_html.wrapper,
			doc: doc
		});
  }
}

cur_frm.cscript.make_dashboard = function(doc) {
	cur_frm.dashboard.reset();
	if(doc.__islocal)
		return;
	if (in_list(user_roles, "Accounts User") || in_list(user_roles, "Accounts Manager"))
		cur_frm.dashboard.set_headline('<span class="text-muted">Loading...</span>')

	cur_frm.dashboard.add_doctype_badge("Supplier Quotation", "supplier");
	cur_frm.dashboard.add_doctype_badge("Purchase Order", "supplier");
	cur_frm.dashboard.add_doctype_badge("Purchase Receipt", "supplier");
	cur_frm.dashboard.add_doctype_badge("Purchase Invoice", "supplier");

	return frappe.call({
		type: "GET",
		method: "erpnext.buying.doctype.supplier.supplier.get_dashboard_info",
		args: {
			supplier: cur_frm.doc.name
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
	})
}

cur_frm.fields_dict['default_price_list'].get_query = function(doc, cdt, cdn) {
	return{
		filters:{'buying': 1}
	}
}
