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
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	See the
// GNU General Public License for more details.
// 
// You should have received a copy of the GNU General Public License
// along with this program.	If not, see <http://www.gnu.org/licenses/>.


//========================== On Load =================================================
cur_frm.cscript.onload = function(doc, cdt, cdn) {
	if (!doc.transaction_date) doc.transaction_date = dateutil.obj_to_str(new Date());
}


// ***************** Get Account Head *****************
cur_frm.fields_dict['closing_account_head'].get_query = function(doc, cdt, cdn) {
	return 'SELECT `tabAccount`.name FROM `tabAccount` WHERE `tabAccount`.is_pl_account = "No" AND `tabAccount`.debit_or_credit = "Credit" AND `tabAccount`.company = "'+ cstr(doc.company) +'" AND ifnull(`tabAccount`.freeze_account, "No") = "No" AND `tabAccount`.group_or_ledger = "Ledger" AND `tabAccount`.%(key)s LIKE "%s" ORDER BY `tabAccount`.name ASC LIMIT 50';
}
