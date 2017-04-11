// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt


cur_frm.cscript.refresh = function(doc, cdt, cdn) {
	if(doc.__islocal) {
		msgprint(__("Please create new account from Chart of Accounts."));
		throw "cannot create";
	}

	cur_frm.toggle_display('account_name', doc.__islocal);

	// hide fields if group
	cur_frm.toggle_display(['account_type', 'tax_rate'], cint(doc.is_group)==0)

	// disable fields
	cur_frm.toggle_enable(['account_name', 'is_group', 'company'], false);

	if(cint(doc.is_group)==0) {
		cur_frm.toggle_display('freeze_account', doc.__onload && doc.__onload.can_freeze_account);
	}

	// read-only for root accounts
	if(!doc.parent_account) {
		cur_frm.set_read_only();
		cur_frm.set_intro(__("This is a root account and cannot be edited."));
	} else {
		// credit days and type if customer or supplier
		cur_frm.set_intro(null);

		cur_frm.cscript.account_type(doc, cdt, cdn);

		// show / hide convert buttons
		cur_frm.cscript.add_toolbar_buttons(doc);
	}
}

cur_frm.add_fetch('parent_account', 'report_type', 'report_type');
cur_frm.add_fetch('parent_account', 'root_type', 'root_type');

cur_frm.cscript.account_type = function(doc, cdt, cdn) {
	if(doc.is_group==0) {
		cur_frm.toggle_display(['tax_rate'], doc.account_type == 'Tax');
		cur_frm.toggle_display('warehouse', doc.account_type=='Stock');
	}
}

cur_frm.cscript.add_toolbar_buttons = function(doc) {
	cur_frm.add_custom_button(__('Chart of Accounts'),
		function() { frappe.set_route("Tree", "Account"); });

	if (doc.is_group == 1) {
		cur_frm.add_custom_button(__('Group to Non-Group'),
			function() { cur_frm.cscript.convert_to_ledger(); }, 'fa fa-retweet', 'btn-default');
	} else if (cint(doc.is_group) == 0) {
		cur_frm.add_custom_button(__('Ledger'), function() {
			frappe.route_options = {
				"account": doc.name,
				"from_date": sys_defaults.year_start_date,
				"to_date": sys_defaults.year_end_date,
				"company": doc.company
			};
			frappe.set_route("query-report", "General Ledger");
		});

		cur_frm.add_custom_button(__('Non-Group to Group'),
			function() { cur_frm.cscript.convert_to_group(); }, 'fa fa-retweet', 'btn-default')
	}
}

cur_frm.cscript.convert_to_ledger = function(doc, cdt, cdn) {
  return $c_obj(cur_frm.doc,'convert_group_to_ledger','',function(r,rt) {
    if(r.message == 1) {
	  cur_frm.refresh();
    }
  });
}

cur_frm.cscript.convert_to_group = function(doc, cdt, cdn) {
  return $c_obj(cur_frm.doc,'convert_ledger_to_group','',function(r,rt) {
    if(r.message == 1) {
	  cur_frm.refresh();
    }
  });
}

cur_frm.fields_dict['parent_account'].get_query = function(doc) {
	return {
		filters: {
			"is_group": 1,
			"company": doc.company
		}
	}
}
