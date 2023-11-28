// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.support");

frappe.ui.form.on("Warranty Claim", {
	setup: (frm) => {
		frm.set_query('contact_person', erpnext.queries.contact_query);
		frm.set_query('customer_address', erpnext.queries.address_query);
		frm.set_query('customer', erpnext.queries.customer);
	},

	onload: (frm) => {
		if(!frm.doc.status) {
			frm.set_value('status', 'Open');
		}
	},

	customer: (frm) => {
		erpnext.utils.get_party_details(frm);
	},

	customer_address: (frm) => {
		erpnext.utils.get_address_display(frm);
	},

	contact_person: (frm) => {
		erpnext.utils.get_contact_details(frm);
	}
});

erpnext.support.WarrantyClaim = class WarrantyClaim extends frappe.ui.form.Controller {
	refresh() {
		frappe.dynamic_link = {doc: this.frm.doc, fieldname: 'customer', doctype: 'Customer'}

		if(!cur_frm.doc.__islocal &&
			(cur_frm.doc.status=='Open' || cur_frm.doc.status == 'Work In Progress')) {
			cur_frm.add_custom_button(__('Maintenance Visit'),
				this.make_maintenance_visit);
		}
	}

	make_maintenance_visit() {
		frappe.model.open_mapped_doc({
			method: "erpnext.support.doctype.warranty_claim.warranty_claim.make_maintenance_visit",
			frm: cur_frm
		})
	}
};

extend_cscript(cur_frm.cscript, new erpnext.support.WarrantyClaim({frm: cur_frm}));

cur_frm.fields_dict['serial_no'].get_query = (doc, cdt, cdn) => {
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

cur_frm.fields_dict['item_code'].get_query = (doc, cdt, cdn) => {
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
};
