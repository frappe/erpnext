// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
// License: GNU General Public License v3. See license.txt

cur_frm.cscript.onload = function(doc, cdt, cdn) {
if(!doc.currency){doc.currency = sys_defaults.currency;}
}


cur_frm.fields_dict['landed_cost_details'].grid.get_field("account_head").get_query = function(doc,cdt,cdn) {
return{
		filters:[
			['Account', 'group_or_ledger', '=', 'Ledger'],
			['Account', 'account_type', 'in', 'Tax, Chargeable'],
			['Account', 'is_pl_account', '=', 'Yes'],
			['Account', 'debit_or_credit', '=', 'Debit']
		]
	}
}
