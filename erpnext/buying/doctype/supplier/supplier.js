// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

{% include 'setup/doctype/contact_control/contact_control.js' %};

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
		// make lists
		cur_frm.cscript.make_address(doc,dt,dn);
		cur_frm.cscript.make_contact(doc,dt,dn);

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


cur_frm.cscript.make_address = function() {
	if(!cur_frm.address_list) {
		cur_frm.address_list = new frappe.ui.Listing({
			parent: cur_frm.fields_dict['address_html'].wrapper,
			page_length: 5,
			new_doctype: "Address",
			get_query: function() {
				return "select name, address_type, address_line1, address_line2, city, state, country, pincode, fax, email_id, phone, is_primary_address, is_shipping_address from tabAddress where supplier='" +
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
				return "select name, first_name, last_name, email_id, phone, mobile_no, department, designation, is_primary_contact from tabContact where supplier='" +
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

cur_frm.fields_dict['default_price_list'].get_query = function(doc, cdt, cdn) {
	return{
		filters:{'buying': 1}
	}
}
