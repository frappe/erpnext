// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt


//========================== On Load =================================================
cur_frm.cscript.onload = function(doc, cdt, cdn) {
	if (!doc.transaction_date) doc.transaction_date = dateutil.obj_to_str(new Date());
}


// ***************** Get Account Head *****************
cur_frm.fields_dict['closing_account_head'].get_query = function(doc, cdt, cdn) {
	return{
		filters:{
			'is_pl_account': "No",
			"debit_or_credit": "Credit",
			"company": doc.company,
			"freeze_account": "No",
			"group_or_ledger": "Ledger"
		}
	}	
}
