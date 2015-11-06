// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.cscript.refresh = function(doc,dt,dn){

	if(doc.__islocal){
		hide_field(['address_html', 'contact_html']);
		erpnext.utils.clear_address_and_contact(cur_frm);
	}
	else{
		unhide_field(['address_html', 'contact_html']);
		erpnext.utils.render_address_and_contact(cur_frm);
	}
}

cur_frm.fields_dict['targets'].grid.get_field("item_group").get_query = function(doc, dt, dn) {
  return{
  	filters:{ 'is_group': "No" }
  }
}
