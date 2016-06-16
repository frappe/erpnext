// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.support");
frappe.require("assets/erpnext/js/utils.js");

frappe.ui.form.on_change("Maintenance Visit", "customer", function(frm) {
	erpnext.utils.get_party_details(frm) });
frappe.ui.form.on_change("Maintenance Visit", "customer_address", function(frm){
	erpnext.utils.get_address_display(frm, 'customer_address', 'address_display')
});
frappe.ui.form.on_change("Maintenance Visit", "contact_person", function(frm){
	erpnext.utils.get_contact_details(frm)
});

// TODO commonify this code
erpnext.support.MaintenanceVisit = frappe.ui.form.Controller.extend({
	refresh: function() {
		if (this.frm.doc.docstatus===0) {
			cur_frm.add_custom_button(__('Maintenance Schedule'),
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
				}, __("Get items from"));
			cur_frm.add_custom_button(__('Warranty Claim'),
				function() {
					frappe.model.map_current_doc({
						method: "erpnext.support.doctype.warranty_claim.warranty_claim.make_maintenance_visit",
						source_doctype: "Warranty Claim",
						get_query_filters: {
							status: ["in", "Open, Work in Progress"],
							customer: cur_frm.doc.customer || undefined,
							company: cur_frm.doc.company
						}
					})
				}, __("Get items from"));
			cur_frm.add_custom_button(__('Sales Order'),
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
				}, __("Get items from"));
		}
	},
});

$.extend(cur_frm.cscript, new erpnext.support.MaintenanceVisit({frm: cur_frm}));

cur_frm.cscript.onload = function(doc, dt, dn) {
	if(!doc.status) set_multiple(dt,dn,{status:'Draft'});
	if(doc.__islocal) set_multiple(dt,dn,{mntc_date:get_today()});

	// set add fetch for item_code's item_name and description
	cur_frm.add_fetch('item_code', 'item_name', 'item_name');
	cur_frm.add_fetch('item_code', 'description', 'description');
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

cur_frm.fields_dict['purposes'].grid.get_field('item_code').get_query = function(doc, cdt, cdn) {
	return{
    	filters:{ 'is_sales_item': 1}
  	}
}

cur_frm.fields_dict.customer.get_query = function(doc,cdt,cdn) {
	return {query: "erpnext.controllers.queries.customer_query" }
}
