// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.cscript.refresh = function(doc,dt,dn){

	if(doc.__islocal){
		hide_field(['address_html', 'contact_html']);
	}
	else{
		unhide_field(['address_html', 'contact_html']);
		// make lists

		erpnext.utils.render_address_and_contact(cur_frm)

		if (doc.show_in_website) {
			cur_frm.set_intro(__("Published on website at: {0}",
				[repl('<a href="/%(website_route)s" target="_blank">/%(website_route)s</a>', doc.__onload)]));
		}
	}
}

cur_frm.fields_dict['partner_target_details'].grid.get_field("item_group").get_query = function(doc, dt, dn) {
  return{
  	filters:{ 'is_group': "No" }
  }
}
