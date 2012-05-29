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

cur_frm.cscript.onload = function(doc, cdt, cdn) {
	if(doc.customer) cur_frm.add_fetch('customer', 'customer_name', 'customer_name');
	if(doc.supplier) cur_frm.add_fetch('supplier', 'supplier_name', 'supplier_name');
	
	var route = wn.get_route();
	if(route[1]=='Supplier') {
		var supplier = wn.container.page.frm.doc;
		doc.supplier = supplier.name;
		doc.supplier_name = supplier.supplier_name;
		doc.address_type = 'Office';
	} else if(route[1]=='Customer') {
		var customer = wn.container.page.frm.doc;
		doc.customer = customer.name;
		doc.customer_name = customer.customer_name;
		doc.address_type = 'Office';
	} else if(route[1]=='Sales Partner') {
		var sp = wn.container.page.frm.doc;
		doc.sales_partner = sp.name;
		doc.address_type = 'Office';				
	}
}

cur_frm.cscript.hide_dialog = function() {
	if(cur_frm.address_list)
		cur_frm.address_list.run();
}


