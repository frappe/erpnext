// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

//c-form js file
// -----------------------------
frappe.require("assets/erpnext/js/utils.js");

cur_frm.fields_dict.invoices.grid.get_field("invoice_no").get_query = function(doc) {
	return {
		filters: {
			"docstatus": 1, 
			"customer": doc.customer,
			"company": doc.company,
			"c_form_applicable": 'Yes',
			"c_form_no": ''
		}
	}
}

cur_frm.fields_dict.state.get_query = function(doc) {
	return {filters: { country: "India"}}
}

cur_frm.cscript.invoice_no = function(doc, cdt, cdn) {
	var d = locals[cdt][cdn];
	return get_server_fields('get_invoice_details', d.invoice_no, 'invoices', doc, cdt, cdn, 1);
}

cur_frm.cscript.company = function(doc, cdt, cdn) {
	erpnext.get_fiscal_year(doc.company, doc.received_date);
}

cur_frm.cscript.received_date = function(doc, cdt, cdn){
	erpnext.get_fiscal_year(doc.company, doc.received_date);
}