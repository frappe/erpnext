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

//--------- ONLOAD -------------
cur_frm.cscript.onload = function(doc, cdt, cdn) {
	if(doc.customer) cur_frm.add_fetch('customer', 'customer_name', 'customer_name');
	if(doc.supplier) cur_frm.add_fetch('supplier', 'supplier_name', 'supplier_name');
}

/*
//---------- on refresh ----------------------
cur_frm.cscript.refresh = function(doc,cdt,cdn){
	
}


//------------- Trigger on customer ---------------------
cur_frm.cscript.is_customer = function(doc,cdt,cdn){
	if(!doc.is_customer){
		doc.customer = doc.customer_name = doc.customer_address = doc.customer_group = '';
		refresh_many(['customer','customer_name','customer_address','customer_group']);
	}
}

//------------- Trigger on supplier -----------------------
cur_frm.cscript.is_supplier = function(doc,cdt,cdn){
	if(!doc.is_supplier){
		doc.supplier = doc.supplier_name = doc.supplier_address = doc.supplier_type = ''; 
		refresh_many(['supplier','supplier_address','supplier_name','supplier_type']);
	}
}
	
//--------------- Trigger on sales partner ---------------------
cur_frm.cscript.is_sales_partner = function(doc,cdt,cdn){
	if(!doc.is_sales_partner){
		doc.sales_partner = doc.sales_partner_address = doc.partner_type = '';
		refresh_many(['sales_partner','sales_partner_address','partner_type']);
	}
}

//----------- Trigger on supplier name ------------------------
cur_frm.cscript.supplier = function(doc,cdt,cdn){
	arg = {'dt':'Supplier','dn':doc.supplier,'nm':'supplier_name','fld':'supplier_address','type':'supplier_type'};
	get_server_fields('get_address',docstring(arg),'',doc,cdt,cdn,1);
}

//------------ Trigger on customer name ------------------------
cur_frm.cscript.customer = function(doc,cdt,cdn){
	arg = {'dt':'Customer','dn':doc.customer,'nm':'customer_name','fld':'customer_address','type':'customer_group'};
	get_server_fields('get_address',docstring(arg),'',doc,cdt,cdn,1);
}

//------------ Trigger on sales partner ------------------------
cur_frm.cscript.sales_partner = function(doc,cdt,cdn){
	arg = {'dt':'Sales Partner','dn':doc.sales_partner,'nm':'partner_name','fld':'sales_partner_address','type':'partner_type'};
	get_server_fields('get_address',docstring(arg),'',doc,cdt,cdn,1);
}
*/
