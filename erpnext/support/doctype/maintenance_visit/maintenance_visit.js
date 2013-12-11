// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

wn.provide("erpnext.support");
// TODO commonify this code
erpnext.support.MaintenanceVisit = wn.ui.form.Controller.extend({
	refresh: function() {
		if (this.frm.doc.docstatus===0) {
			cur_frm.add_custom_button(wn._('From Maintenance Schedule'), 
				function() {
					wn.model.map_current_doc({
						method: "support.doctype.maintenance_schedule.maintenance_schedule.make_maintenance_visit",
						source_doctype: "Maintenance Schedule",
						get_query_filters: {
							docstatus: 1,
							customer: cur_frm.doc.customer || undefined,
							company: cur_frm.doc.company
						}
					})
				});
			cur_frm.add_custom_button(wn._('From Customer Issue'), 
				function() {
					wn.model.map_current_doc({
						method: "support.doctype.customer_issue.customer_issue.make_maintenance_visit",
						source_doctype: "Customer Issue",
						get_query_filters: {
							status: ["in", "Open, Work in Progress"],
							customer: cur_frm.doc.customer || undefined,
							company: cur_frm.doc.company
						}
					})
				});
			cur_frm.add_custom_button(wn._('From Sales Order'), 
				function() {
					wn.model.map_current_doc({
						method: "selling.doctype.sales_order.sales_order.make_maintenance_visit",
						source_doctype: "Sales Order",
						get_query_filters: {
							docstatus: 1,
							order_type: cur_frm.doc.order_type,
							customer: cur_frm.doc.customer || undefined,
							company: cur_frm.doc.company
						}
					})
				});
		}
		cur_frm.cscript.hide_contact_info();			
	},
	customer: function() {
		var me = this;
		if(this.frm.doc.customer) {
			// TODO shift this to depends_on
			cur_frm.cscript.hide_contact_info();
			
			return this.frm.call({
				doc: this.frm.doc,
				method: "set_customer_defaults",
			});
		}
	}, 
});

$.extend(cur_frm.cscript, new erpnext.support.MaintenanceVisit({frm: cur_frm}));

cur_frm.cscript.onload = function(doc, dt, dn) {
	if(!doc.status) set_multiple(dt,dn,{status:'Draft'});
	if(doc.__islocal) set_multiple(dt,dn,{mntc_date:get_today()});
	cur_frm.cscript.hide_contact_info();			
}

cur_frm.cscript.hide_contact_info = function() {
	cur_frm.toggle_display("contact_info_section", cur_frm.doc.customer ? true : false);
}

cur_frm.cscript.customer_address = cur_frm.cscript.contact_person = function(doc,dt,dn) {		
	if(doc.customer) return get_server_fields('get_customer_address', JSON.stringify({customer: doc.customer, address: doc.customer_address, contact: doc.contact_person}),'', doc, dt, dn, 1);
}

cur_frm.fields_dict['customer_address'].get_query = function(doc, cdt, cdn) {
	return{
    	filters:{'customer': doc.customer}
  	}
}

cur_frm.fields_dict['contact_person'].get_query = function(doc, cdt, cdn) {
  	return{
    	filters:{'customer': doc.customer}
  	}
}

cur_frm.fields_dict['maintenance_visit_details'].grid.get_field('item_code').get_query = function(doc, cdt, cdn) {
	return{
    	filters:{ 'is_service_item': "Yes"}
  	}
}

cur_frm.cscript.item_code = function(doc, cdt, cdn) {
	var fname = cur_frm.cscript.fname;
	var d = locals[cdt][cdn];
	if (d.item_code) {
		return get_server_fields('get_item_details',d.item_code, 'maintenance_visit_details',doc,cdt,cdn,1);
	}
}


cur_frm.fields_dict.customer.get_query = function(doc,cdt,cdn) {
	return {query: "controllers.queries.customer_query" }
}