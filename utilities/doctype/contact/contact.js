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
	cur_frm.add_fetch('customer', 'customer_name', 'customer_name');
	cur_frm.add_fetch('supplier', 'supplier_name', 'supplier_name');
	
	cur_frm.fields_dict.customer.get_query = erpnext.utils.customer_query;
	cur_frm.fields_dict.supplier.get_query = erpnext.utils.supplier_query;
}

cur_frm.cscript.refresh = function(doc) {
	cur_frm.communication_view = new wn.views.CommunicationList({
		list: wn.model.get("Communication", {"contact": doc.name}),
		parent: cur_frm.fields_dict.communication_html.wrapper,
		doc: doc,
		recipients: doc.email_id
	})	
}

cur_frm.cscript.hide_dialog = function() {
	if(cur_frm.contact_list)
		cur_frm.contact_list.run();
}