// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt


// Onload
// -----------------------------------------
cur_frm.cscript.onload = function(doc, cdt, cdn) {
}

// Refresh
// -----------------------------------------
cur_frm.cscript.refresh = function(doc, cdt, cdn) {
	if(doc.__islocal) {
		msgprint(wn._("Please create new account from Chart of Accounts."));
		throw "cannot create";
	}

	cur_frm.toggle_display('account_name', doc.__islocal);
	
	// hide fields if group
	cur_frm.toggle_display(['account_type', 'master_type', 'master_name', 
		'credit_days', 'credit_limit', 'tax_rate'], doc.group_or_ledger=='Ledger')	
		
	// disable fields
	cur_frm.toggle_enable(['account_name', 'debit_or_credit', 'group_or_ledger', 
		'is_pl_account', 'company'], false);
	
	if(doc.group_or_ledger=='Ledger') {
		wn.model.with_doc("Accounts Settings", "Accounts Settings", function (name) {
			var accounts_settings = wn.model.get_doc("Accounts Settings", name);
			var display = accounts_settings["frozen_accounts_modifier"] 
				&& in_list(user_roles, accounts_settings["frozen_accounts_modifier"]);
			
			cur_frm.toggle_display('freeze_account', display);
		});
	}

	// read-only for root accounts
	if(!doc.parent_account) {
		cur_frm.perm = [[1,0,0], [1,0,0]];
		cur_frm.set_intro(wn._("This is a root account and cannot be edited."));
	} else {
		// credit days and type if customer or supplier
		cur_frm.set_intro(null);
		cur_frm.toggle_display(['credit_days', 'credit_limit'], in_list(['Customer', 'Supplier'], 
			doc.master_type));
		
		cur_frm.cscript.master_type(doc, cdt, cdn);
		cur_frm.cscript.account_type(doc, cdt, cdn);

		// show / hide convert buttons
		cur_frm.cscript.add_toolbar_buttons(doc);
	}
}

cur_frm.cscript.master_type = function(doc, cdt, cdn) {
	cur_frm.toggle_display(['credit_days', 'credit_limit'], in_list(['Customer', 'Supplier'], 
		doc.master_type));
		
	cur_frm.toggle_display('master_name', doc.account_type=='Warehouse' || 
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
		cur_frm.toggle_display(['tax_rate'], doc.account_type == 'Tax');
		cur_frm.toggle_display('master_type', cstr(doc.account_type)=='');
		cur_frm.toggle_display('master_name', doc.account_type=='Warehouse' || 
			in_list(['Customer', 'Supplier'], doc.master_type));
	}
}

// Hide/unhide group or ledger
// -----------------------------------------
cur_frm.cscript.add_toolbar_buttons = function(doc) {
	cur_frm.appframe.add_button(wn._('Chart of Accounts'), 
		function() { wn.set_route("Accounts Browser", "Account"); }, 'icon-sitemap')

	if (cstr(doc.group_or_ledger) == 'Group') {
		cur_frm.add_custom_button(wn._('Convert to Ledger'), 
			function() { cur_frm.cscript.convert_to_ledger(); }, 'icon-retweet')
	} else if (cstr(doc.group_or_ledger) == 'Ledger') {
		cur_frm.add_custom_button(wn._('Convert to Group'), 
			function() { cur_frm.cscript.convert_to_group(); }, 'icon-retweet')
			
		cur_frm.appframe.add_button(wn._('View Ledger'), function() {
			wn.route_options = {
				"account": doc.name,
				"from_date": sys_defaults.year_start_date,
				"to_date": sys_defaults.year_end_date
			};
			wn.set_route("general-ledger");
		}, "icon-table");
	}
}
// Convert group to ledger
// -----------------------------------------
cur_frm.cscript.convert_to_ledger = function(doc, cdt, cdn) {
  return $c_obj(cur_frm.get_doclist(),'convert_group_to_ledger','',function(r,rt) {
    if(r.message == 1) {  
	  cur_frm.refresh();
    }
  });
}

// Convert ledger to group
// -----------------------------------------
cur_frm.cscript.convert_to_group = function(doc, cdt, cdn) {
  return $c_obj(cur_frm.get_doclist(),'convert_ledger_to_group','',function(r,rt) {
    if(r.message == 1) {
	  cur_frm.refresh();
    }
  });
}

cur_frm.fields_dict['master_name'].get_query = function(doc) {
	if (doc.master_type || doc.account_type=="Warehouse") {
		var dt = doc.master_type || "Warehouse";
		return {
			doctype: dt,
			query: "accounts.doctype.account.account.get_master_name",
			filters: {
				"master_type": dt,
				"company": doc.company
			}
		}
	}
}

cur_frm.fields_dict['parent_account'].get_query = function(doc) {
	return {
		filters: {
			"group_or_ledger": "Group", 
			"company": doc.company
		}
	}
}