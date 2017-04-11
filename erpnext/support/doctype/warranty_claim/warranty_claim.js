// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.support");

frappe.ui.form.on("Warranty Claim", {
	setup: function(frm) {
		frm.set_query('contact_person', erpnext.queries.contact_query);
		frm.set_query('customer_address', erpnext.queries.address_query);
	},
	customer: function(frm) {
		erpnext.utils.get_party_details(frm);
	},
	customer_address: function(frm) {
		erpnext.utils.get_address_display(frm);
	},
	contact_person: function(frm) {
		erpnext.utils.get_contact_details(frm);
	}
});

erpnext.support.WarrantyClaim = frappe.ui.form.Controller.extend({
	refresh: function() {
		frappe.dynamic_link = {doc: this.frm.doc, fieldname: 'customer', doctype: 'Customer'}

		if(!cur_frm.doc.__islocal &&
			(cur_frm.doc.status=='Open' || cur_frm.doc.status == 'Work In Progress')) {
			cur_frm.add_custom_button(__('Maintenance Visit'),
				this.make_maintenance_visit, __("Make"))
			cur_frm.page.set_inner_btn_group_as_primary(__("Make"));
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
		set_multiple(cdt,cdn,{status:'Open'});
}

cur_frm.fields_dict['serial_no'].get_query = function(doc, cdt, cdn) {
	var cond = [];
	var filter = [
		['Serial No', 'docstatus', '!=', 2]
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
			doctype: "Serial No",
			fields: "item_code",
			filters:{
				name: doc.serial_no
			}
		}
	}
	else{
		return{
			filters:[
				['Item', 'docstatus', '!=', 2],
				['Item', 'disabled', '=', 0]
			]
		}
	}
}



cur_frm.fields_dict.customer.get_query = function(doc,cdt,cdn) {
	return{	query: "erpnext.controllers.queries.customer_query" } }

