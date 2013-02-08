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


// Onload
// -----------------------------------------
cur_frm.cscript.onload = function(doc, cdt, cdn) {
}

// Refresh
// -----------------------------------------
cur_frm.cscript.refresh = function(doc, cdt, cdn) {
	if(doc.__islocal) {
		msgprint("Please create new account from Chart of Accounts.");
		throw "cannot create";
	}

	cur_frm.toggle_display('account_name', doc.__islocal);
	
	// hide fields if group
	cur_frm.toggle_display(['account_type', 'master_type', 'master_name', 'freeze_account', 
		'credit_days', 'credit_limit', 'tax_rate'], doc.group_or_ledger=='Ledger')	
		
	// disable fields
	cur_frm.toggle_enable(['account_name', 'debit_or_credit', 'group_or_ledger', 
		'is_pl_account', 'company'], false);

	// read-only for root accounts
	if(!doc.parent_account) {
		cur_frm.perm = [[1,0,0], [1,0,0]];
		cur_frm.set_intro("This is a root account and cannot be edited.");
	} else {
		// credit days and type if customer or supplier
		cur_frm.set_intro(null);
		cur_frm.toggle_display(['credit_days', 'credit_limit', 'master_name'], 
			in_list(['Customer', 'Supplier'], doc.master_type));

		// hide tax_rate
		cur_frm.cscript.account_type(doc, cdt, cdn);

		// show / hide convert buttons
		cur_frm.cscript.add_toolbar_buttons(doc);
	}
}

cur_frm.cscript.master_type = function(doc, cdt, cdn) {
	cur_frm.toggle_display(['credit_days', 'credit_limit', 'master_name'], 
		in_list(['Customer', 'Supplier'], doc.master_type));
}


// Fetch parent details
// -----------------------------------------
cur_frm.add_fetch('parent_account', 'debit_or_credit', 'debit_or_credit');
cur_frm.add_fetch('parent_account', 'is_pl_account', 'is_pl_account');

// Hide tax rate based on account type
// -----------------------------------------
cur_frm.cscript.account_type = function(doc, cdt, cdn) {
	if(doc.group_or_ledger=='Ledger') {
		cur_frm.toggle_display(['tax_rate'], 
			doc.account_type == 'Tax');
		cur_frm.toggle_display(['master_type', 'master_name'], 
			cstr(doc.account_type)=='');		
	}
}

// Hide/unhide group or ledger
// -----------------------------------------
cur_frm.cscript.add_toolbar_buttons = function(doc) {
	cur_frm.add_custom_button('Chart of Accounts', 
		function() { wn.set_route("Accounts Browser", "Account"); }, 'icon-list')

	if (cstr(doc.group_or_ledger) == 'Group') {
		cur_frm.add_custom_button('Convert to Ledger', 
			function() { cur_frm.cscript.convert_to_ledger(); }, 'icon-retweet')
	} else if (cstr(doc.group_or_ledger) == 'Ledger') {
		cur_frm.add_custom_button('Convert to Group', 
			function() { cur_frm.cscript.convert_to_group(); }, 'icon-retweet')
			
		cur_frm.add_custom_button('View Ledger', function() {
			wn.set_route("general-ledger", "account=" + doc.name);
		});
	}
}
// Convert group to ledger
// -----------------------------------------
cur_frm.cscript.convert_to_ledger = function(doc, cdt, cdn) {
  $c_obj(cur_frm.get_doclist(),'convert_group_to_ledger','',function(r,rt) {
    if(r.message == 1) {  
	  cur_frm.refresh();
    }
  });
}

// Convert ledger to group
// -----------------------------------------
cur_frm.cscript.convert_to_group = function(doc, cdt, cdn) {
  $c_obj(cur_frm.get_doclist(),'convert_ledger_to_group','',function(r,rt) {
    if(r.message == 1) {
	  cur_frm.refresh();
    }
  });
}

cur_frm.fields_dict['master_name'].get_query = function(doc) {
	if (doc.master_type) {
		return {
			query: "accounts.doctype.account.account.get_master_name",
			args: {	"master_type": doc.master_type }
		}
	}
}

cur_frm.fields_dict['parent_account'].get_query = function(doc) {
	return {
		query: "accounts.doctype.account.account.get_parent_account",
		args: { "company": doc.company}
	}
}
