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
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
// 
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <http://www.gnu.org/licenses/>.

//c-form js file
// -----------------------------
cur_frm.fields_dict.invoice_details.grid.get_field("invoice_no").get_query = function(doc) {
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
	get_server_fields('get_invoice_details', d.invoice_no, 'invoice_details', doc, cdt, cdn, 1);
}