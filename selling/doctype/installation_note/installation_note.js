// ERPNext - web based ERP (http://erpnext.com)
// Copyright (C) 2012 Web Notes Technologies Pvt Ltd
// 
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
// 
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	See the
// GNU General Public License for more details.
// 
// You should have received a copy of the GNU General Public License
// along with this program.	If not, see <http://www.gnu.org/licenses/>.

cur_frm.cscript.tname = "Installation Note Item";
cur_frm.cscript.fname = "installed_item_details";

wn.provide("erpnext.selling");
// TODO commonify this code
erpnext.selling.InstallationNote = wn.ui.form.Controller.extend({
	customer: function() {
		var me = this;
		if(this.frm.doc.customer) {
			this.frm.call({
				doc: this.frm.doc,
				method: "set_customer_defaults",
				callback: function(r) {
					if(!r.exc) me.frm.refresh_fields();
				}
			});
			
			// TODO shift this to depends_on
			unhide_field(['customer_address', 'contact_person', 'customer_name',
				'address_display', 'contact_display', 'contact_mobile', 'contact_email', 
				'territory', 'customer_group']);
		}
	}, 
	get_items: function() {
		wn.model.map_current_doc({
			method: "stock.doctype.delivery_note.delivery_note.make_installation_note",
			source_name: cur_frm.doc.delivery_note_no,
		})
		unhide_field(['customer_address', 'contact_person', 'customer_name', 'address_display', 
			'contact_display', 'contact_mobile', 'contact_email', 'territory', 'customer_group']);
	}
});

$.extend(cur_frm.cscript, new erpnext.selling.InstallationNote({frm: cur_frm}));

cur_frm.cscript.onload = function(doc, dt, dn) {
	if(!doc.status) set_multiple(dt,dn,{status:'Draft'});
	if(doc.__islocal){
		set_multiple(dt,dn,{inst_date:get_today()});
		hide_field(['customer_address','contact_person','customer_name','address_display','contact_display','contact_mobile','contact_email','territory','customer_group']);				
	}
	if (doc.customer) {
		 unhide_field(['customer_address','contact_person','customer_name','address_display','contact_display','contact_mobile','contact_email','territory','customer_group']);
	}	 
}

cur_frm.fields_dict['delivery_note_no'].get_query = function(doc) {
	doc = locals[this.doctype][this.docname];

	var filter = {
    	'company': doc.company,
    	'docstatus': 1,
    	'per_installed': 99.99
  	};
	if(doc.customer) filter['customer'] = doc.customer;
  	return { filters: filter }
}

cur_frm.fields_dict['territory'].get_query = function(doc,cdt,cdn) {
  	return{
 		filters: { 'is_group': "No" }
  	}	
}

cur_frm.cscript.customer_address = cur_frm.cscript.contact_person = function(doc,dt,dn) {		
	if(doc.customer) get_server_fields('get_customer_address', JSON.stringify({customer: doc.customer, address: doc.customer_address, contact: doc.contact_person}),'', doc, dt, dn, 1);
}

cur_frm.fields_dict['customer_address'].get_query = function(doc, cdt, cdn) {
  	return{
    	filters: { 'customer': doc.customer }
	}
}

cur_frm.fields_dict['contact_person'].get_query = function(doc, cdt, cdn) {
	return{
    	filters: { 'customer': doc.customer }
	}
}

cur_frm.fields_dict.customer.get_query = function(doc,cdt,cdn) {
	return{
		query:"controllers.queries.customer_query"
	}
}