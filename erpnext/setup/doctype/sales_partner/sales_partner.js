// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

{% include 'setup/doctype/contact_control/contact_control.js' %};

cur_frm.cscript.onload = function(doc,dt,dn){

}

cur_frm.cscript.refresh = function(doc,dt,dn){

	if(doc.__islocal){
		hide_field(['address_html', 'contact_html']);
	}
	else{
		unhide_field(['address_html', 'contact_html']);
		// make lists
		cur_frm.cscript.make_address(doc,dt,dn);
		cur_frm.cscript.make_contact(doc,dt,dn);

		if (doc.show_in_website) {
			cur_frm.set_intro(__("Published on website at: {0}",
				[repl('<a href="/%(website_route)s" target="_blank">/%(website_route)s</a>', doc.__onload)]));
		}
	}
}


cur_frm.cscript.make_address = function() {
	if(!cur_frm.address_list) {
		cur_frm.address_list = new frappe.ui.Listing({
			parent: cur_frm.fields_dict['address_html'].wrapper,
			page_length: 2,
			new_doctype: "Address",
			custom_new_doc: function(doctype) {
				var address = frappe.model.make_new_doc_and_get_name('Address');
				address = locals['Address'][address];
				address.sales_partner = cur_frm.doc.name;
				address.address_title = cur_frm.doc.name;
				address.address_type = "Office";
				frappe.set_route("Form", "Address", address.name);
			},
			get_query: function() {
				return "select name, address_type, address_line1, address_line2, city, state, country, pincode, fax, email_id, phone, is_primary_address, is_shipping_address from tabAddress where sales_partner='" +
					cur_frm.doc.name.replace(/'/g, "\\'") + "' and docstatus != 2 order by is_primary_address desc"
			},
			as_dict: 1,
			no_results_message: __('No addresses created'),
			render_row: cur_frm.cscript.render_address_row,
		});
	}
	cur_frm.address_list.run();
}

cur_frm.cscript.make_contact = function() {
	if(!cur_frm.contact_list) {
		cur_frm.contact_list = new frappe.ui.Listing({
			parent: cur_frm.fields_dict['contact_html'].wrapper,
			page_length: 2,
			new_doctype: "Contact",
			custom_new_doc: function(doctype) {
				var contact = frappe.model.make_new_doc_and_get_name('Contact');
				contact = locals['Contact'][contact];
				contact.sales_partner = cur_frm.doc.name;
				frappe.set_route("Form", "Contact", contact.name);
			},
			get_query: function() {
				return "select name, first_name, last_name, email_id, phone, mobile_no, department, designation, is_primary_contact from tabContact where sales_partner='" +
					cur_frm.doc.name.replace(/'/g, "\\'") + "' and docstatus != 2 order by is_primary_contact desc"
			},
			as_dict: 1,
			no_results_message: __('No contacts created'),
			render_row: cur_frm.cscript.render_contact_row,
		});
	}
	cur_frm.contact_list.run();
}

cur_frm.fields_dict['partner_target_details'].grid.get_field("item_group").get_query = function(doc, dt, dn) {
  return{
  	filters:{ 'is_group': "No" }
  }
}
