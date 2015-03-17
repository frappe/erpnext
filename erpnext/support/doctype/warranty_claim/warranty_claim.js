// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.support");
frappe.require("assets/erpnext/js/utils.js");

frappe.ui.form.on_change("Warranty Claim", "customer", function(frm) {
	erpnext.utils.get_party_details(frm) });
frappe.ui.form.on_change("Warranty Claim", "customer_address",
	erpnext.utils.get_address_display);
frappe.ui.form.on_change("Warranty Claim", "contact_person",
	erpnext.utils.get_contact_details);

erpnext.support.WarrantyClaim = frappe.ui.form.Controller.extend({
	refresh: function() {
		if(!cur_frm.doc.__islocal &&
			(cur_frm.doc.status=='Open' || cur_frm.doc.status == 'Work In Progress')) {
			cur_frm.add_custom_button(__('Make Maintenance Visit'),
				this.make_maintenance_visit, frappe.boot.doctype_icons["Maintenance Visit"], "btn-default")
		}
	},

	make_maintenance_visit: function() {
		frappe.model.open_mapped_doc({
			method: "erpnext.support.doctype.warranty_claim.warranty_claim.make_maintenance_visit",
			frm: cur_frm
		})
	}
});

$.extend(cur_frm.cscript, new erpnext.support.WarrantyClaim({frm: cur_frm}));

cur_frm.cscript.onload = function(doc,cdt,cdn){
	if(!doc.status)
		set_multiple(dt,dn,{status:'Open'});
}

cur_frm.fields_dict['customer_address'].get_query = function(doc, cdt, cdn) {
	return{
		filters:{ 'customer': doc.customer}
	}
}

cur_frm.fields_dict['contact_person'].get_query = function(doc, cdt, cdn) {
	return{
		filters:{ 'customer': doc.customer}
	}
}

cur_frm.fields_dict['serial_no'].get_query = function(doc, cdt, cdn) {
	var cond = [];
	var filter = [
		['Serial No', 'docstatus', '!=', 2],
		['Serial No', 'status', '=', "Delivered"]
	];
	if(doc.item_code) {
		cond = ['Serial No', 'item_code', '=', doc.item_code];
		filter.push(cond);
	}
	if(doc.customer) {
		cond = ['Serial No', 'customer', '=', doc.customer];
		filter.push(cond);
	}
	return{
		filters:filter
	}
}

cur_frm.add_fetch('serial_no', 'item_code', 'item_code');
cur_frm.add_fetch('serial_no', 'item_name', 'item_name');
cur_frm.add_fetch('serial_no', 'description', 'description');
cur_frm.add_fetch('serial_no', 'maintenance_status', 'warranty_amc_status');
cur_frm.add_fetch('serial_no', 'warranty_expiry_date', 'warranty_expiry_date');
cur_frm.add_fetch('serial_no', 'amc_expiry_date', 'amc_expiry_date');
cur_frm.add_fetch('serial_no', 'customer', 'customer');
cur_frm.add_fetch('serial_no', 'customer_name', 'customer_name');
cur_frm.add_fetch('item_code', 'item_name', 'item_name');
cur_frm.add_fetch('item_code', 'description', 'description');

cur_frm.fields_dict['item_code'].get_query = function(doc, cdt, cdn) {
	if(doc.serial_no) {
		return{
			filters:{ 'serial_no': doc.serial_no}
		}
	}
	else{
		return{
			filters:[
				['Item', 'docstatus', '!=', 2]
			]
		}
	}
}



cur_frm.fields_dict.customer.get_query = function(doc,cdt,cdn) {
	return{	query: "erpnext.controllers.queries.customer_query" } }

cur_frm.cscript.company = function(doc, cdt, cdn) {
	erpnext.get_fiscal_year(doc.company, doc.complaint_date);
}

cur_frm.cscript.complaint_date = function(doc, cdt, cdn){
	erpnext.get_fiscal_year(doc.company, doc.complaint_date);
}
