// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.support");

frappe.ui.form.on_change("Maintenance Visit", "customer", function(frm) {
	erpnext.utils.get_party_details(frm) });
frappe.ui.form.on_change("Maintenance Visit", "customer_address",
	erpnext.utils.get_address_display);
frappe.ui.form.on_change("Maintenance Visit", "contact_person",
	erpnext.utils.get_contact_details);

// TODO commonify this code
erpnext.support.MaintenanceVisit = frappe.ui.form.Controller.extend({
	refresh: function() {
		if (this.frm.doc.docstatus===0) {
			cur_frm.add_custom_button(__('From Maintenance Schedule'),
				function() {
					frappe.model.map_current_doc({
						method: "erpnext.support.doctype.maintenance_schedule.maintenance_schedule.make_maintenance_visit",
						source_doctype: "Maintenance Schedule",
						get_query_filters: {
							docstatus: 1,
							customer: cur_frm.doc.customer || undefined,
							company: cur_frm.doc.company
						}
					})
				}, "icon-download", "btn-default");
			cur_frm.add_custom_button(__('From Customer Issue'),
				function() {
					frappe.model.map_current_doc({
						method: "erpnext.support.doctype.customer_issue.customer_issue.make_maintenance_visit",
						source_doctype: "Customer Issue",
						get_query_filters: {
							status: ["in", "Open, Work in Progress"],
							customer: cur_frm.doc.customer || undefined,
							company: cur_frm.doc.company
						}
					})
				}, "icon-download", "btn-default");
			cur_frm.add_custom_button(__('From Sales Order'),
				function() {
					frappe.model.map_current_doc({
						method: "erpnext.selling.doctype.sales_order.sales_order.make_maintenance_visit",
						source_doctype: "Sales Order",
						get_query_filters: {
							docstatus: 1,
							order_type: cur_frm.doc.order_type,
							customer: cur_frm.doc.customer || undefined,
							company: cur_frm.doc.company
						}
					})
				}, "icon-download", "btn-default");
		}
	},
});

$.extend(cur_frm.cscript, new erpnext.support.MaintenanceVisit({frm: cur_frm}));

cur_frm.cscript.onload = function(doc, dt, dn) {
	if(!doc.status) set_multiple(dt,dn,{status:'Draft'});
	if(doc.__islocal) set_multiple(dt,dn,{mntc_date:get_today()});
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
	return {query: "erpnext.controllers.queries.customer_query" }
}
