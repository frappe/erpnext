// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.cscript.refresh = function(doc, cdt, cdn) {
	if(doc.abbr && !doc.__islocal) {
		cur_frm.set_df_property("abbr", "read_only", 1);
	}

	if(!doc.__islocal) {
		cur_frm.toggle_enable("default_currency", (cur_frm.doc.__onload &&
			!cur_frm.doc.__onload.transactions_exist));
	}
}

cur_frm.cscript.change_abbr = function() {
	var dialog = new frappe.ui.Dialog({
		title: "Replace Abbr",
		fields: [
			{"fieldtype": "Data", "label": "New Abbreviation", "fieldname": "new_abbr",
				"reqd": 1 },
			{"fieldtype": "Button", "label": "Update", "fieldname": "update"},
		]
	});

	dialog.fields_dict.update.$input.click(function() {
		args = dialog.get_values();
		if(!args) return;
		return frappe.call({
			method: "erpnext.setup.doctype.company.company.replace_abbr",
			args: {
				"company": cur_frm.doc.name,
				"old": cur_frm.doc.abbr,
				"new": args.new_abbr
			},
			callback: function(r) {
				if(r.exc) {
					msgprint(__("There were errors."));
					return;
				} else {
					cur_frm.set_value("abbr", args.new_abbr);
				}
				dialog.hide();
				cur_frm.refresh();
			},
			btn: this
		})
	});
	dialog.show();
}

cur_frm.fields_dict.default_bank_account.get_query = function(doc) {
	return{
		filters: [
			['Account', 'account_type', 'in', 'Bank, Cash'],
			['Account', 'group_or_ledger', '=', 'Ledger'],
			['Account', 'company', '=', doc.name]
		]
	}
}

cur_frm.fields_dict.default_cash_account.get_query = cur_frm.fields_dict.default_bank_account.get_query;

cur_frm.fields_dict.receivables_group.get_query = function(doc) {
	return{
		filters:{
			'company': doc.name,
			'group_or_ledger': "Group"
		}
	}
}

cur_frm.get_field("chart_of_accounts").get_query = function(doc) {
	return {
		filters: {
			"country": doc.country
		}
	}
}

cur_frm.fields_dict.payables_group.get_query = cur_frm.fields_dict.receivables_group.get_query;


cur_frm.fields_dict.default_expense_account.get_query = function(doc) {
	return{
		filters:{
			'company': doc.name,
			'group_or_ledger': "Ledger",
			"report_type": "Profit and Loss"
		}
	}
}

cur_frm.fields_dict.default_income_account.get_query = function(doc) {
	return{
		filters:{
			'company': doc.name,
			'group_or_ledger': "Ledger",
			"report_type": "Profit and Loss"
		}
	}
}

cur_frm.fields_dict.cost_center.get_query = function(doc) {
	return{
		filters:{
			'company': doc.name,
			'group_or_ledger': "Ledger",
		}
	}
}

if (sys_defaults.auto_accounting_for_stock) {
	cur_frm.fields_dict["stock_adjustment_account"].get_query = function(doc) {
		return {
			"filters": {
				"report_type": "Profit and Loss",
				"company": doc.name,
				'group_or_ledger': "Ledger"
			}
		}
	}

	cur_frm.fields_dict["expenses_included_in_valuation"].get_query =
		cur_frm.fields_dict["stock_adjustment_account"].get_query;

	cur_frm.fields_dict["stock_received_but_not_billed"].get_query = function(doc) {
		return {
			"filters": {
				"report_type": "Balance Sheet",
				"company": doc.name,
				'group_or_ledger': "Ledger"
			}
		}
	}
}
