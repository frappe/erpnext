// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

wn.require('app/setup/doctype/contact_control/contact_control.js');

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
	}
}


cur_frm.cscript.make_address = function() {
	if(!cur_frm.address_list) {
		cur_frm.address_list = new wn.ui.Listing({
			parent: cur_frm.fields_dict['address_html'].wrapper,
			page_length: 2,
			new_doctype: "Address",
			custom_new_doc: function(doctype) {
				var address = wn.model.make_new_doc_and_get_name('Address');
				address = locals['Address'][address];
				address.sales_partner = cur_frm.doc.name;
				address.address_title = cur_frm.doc.name;
				address.address_type = "Office";
				wn.set_route("Form", "Address", address.name);
			},			
			get_query: function() {
				return "select name, address_type, address_line1, address_line2, city, state, country, pincode, fax, email_id, phone, is_primary_address, is_shipping_address from tabAddress where sales_partner='"+cur_frm.docname+"' and docstatus != 2 order by is_primary_address desc"
			},
			as_dict: 1,
			no_results_message: wn._('No addresses created'),
			render_row: function(wrapper, data) {
				$(wrapper).css('padding','5px 0px');
				var link = $ln(wrapper,cstr(data.name), function() { loaddoc("Address", this.dn); }, {fontWeight:'bold'});
				link.dn = data.name
				
				$a(wrapper,'span','',{marginLeft:'5px', color: '#666'},(data.is_primary_address ? '[Primary]' : '') + (data.is_shipping_address ? '[Shipping]' : ''));				
				$a(wrapper,'div','',{marginTop:'5px', color:'#555'}, data.address_line1 + '<br />' + (data.address_line2 ? data.address_line2 + '<br />' : '') + data.city + '<br />' + (data.state ? data.state + ', ' : '') + data.country + '<br />' + (data.pincode ? 'Pincode: ' + data.pincode + '<br />' : '') + (data.phone ? 'Tel: ' + data.phone + '<br />' : '') + (data.fax ? 'Fax: ' + data.fax + '<br />' : '') + (data.email_id ? 'Email: ' + data.email_id + '<br />' : ''));
			}
		});
	}
	cur_frm.address_list.run();
}

cur_frm.cscript.make_contact = function() {
	if(!cur_frm.contact_list) {
		cur_frm.contact_list = new wn.ui.Listing({
			parent: cur_frm.fields_dict['contact_html'].wrapper,
			page_length: 2,
			new_doctype: "Contact",
			custom_new_doc: function(doctype) {
				var contact = wn.model.make_new_doc_and_get_name('Contact');
				contact = locals['Contact'][contact];
				contact.sales_partner = cur_frm.doc.name;
				wn.set_route("Form", "Contact", contact.name);
			},
			get_query: function() {
				return "select name, first_name, last_name, email_id, phone, mobile_no, department, designation, is_primary_contact from tabContact where sales_partner='"+cur_frm.docname+"' and docstatus != 2 order by is_primary_contact desc"
			},
			as_dict: 1,
			no_results_message: wn._('No contacts created'),
			render_row: function(wrapper, data) {
				$(wrapper).css('padding', '5px 0px');
				var link = $ln(wrapper, cstr(data.name), function() { loaddoc("Contact", this.dn); }, {fontWeight:'bold'});
				link.dn = data.name

				$a(wrapper,'span','',{marginLeft:'5px', color: '#666'},(data.is_primary_contact ? '[Primary]' : ''));
				$a(wrapper,'div', '',{marginTop:'5px', color:'#555'}, data.first_name + (data.last_name ? ' ' + data.last_name + '<br />' : '<br>') + (data.phone ? 'Tel: ' + data.phone + '<br />' : '') + (data.mobile_no ? 'Mobile: ' + data.mobile_no + '<br />' : '') + (data.email_id ? 'Email: ' + data.email_id + '<br />' : '') + (data.department ? 'Department: ' + data.department + '<br />' : '') + (data.designation ? 'Designation: ' + data.designation + '<br />' : ''));
			}
		});
	}
	cur_frm.contact_list.run();
}

cur_frm.fields_dict['partner_target_details'].grid.get_field("item_group").get_query = function(doc, dt, dn) {
  return{
  	filters:{ 'is_group': "No" }
  }
}