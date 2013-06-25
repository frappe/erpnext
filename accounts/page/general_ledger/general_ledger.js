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

wn.pages['general-ledger'].onload = function(wrapper) { 
	wn.ui.make_app_page({
		parent: wrapper,
		title: 'General Ledger',
		single_column: true
	});
	
	erpnext.general_ledger = new erpnext.GeneralLedger(wrapper);
	
	wrapper.appframe.add_home_breadcrumb()
	wrapper.appframe.add_module_breadcrumb("Accounts")
	wrapper.appframe.add_breadcrumb("icon-bar-chart")

}

erpnext.GeneralLedger = wn.views.GridReport.extend({
	init: function(wrapper) {
		this._super({
			title: "General Ledger",
			page: wrapper,
			parent: $(wrapper).find('.layout-main'),
			appframe: wrapper.appframe,
			doctypes: ["Company", "Account", "GL Entry", "Cost Center"],
		});
	},
	setup_columns: function() {
		this.columns = [
			{id: "posting_date", name: "Posting Date", field: "posting_date", width: 100,
				formatter: this.date_formatter},
			{id: "account", name: "Account", field: "account", width: 240, 	
				link_formatter: {
					filter_input: "account",
					open_btn: true,
					doctype: "'Account'"
				}},
			{id: "against_account", name: "Against Account", field: "against_account", 
				width: 240, hidden: !this.account},

			{id: "debit", name: "Debit", field: "debit", width: 100,
				formatter: this.currency_formatter},
			{id: "credit", name: "Credit", field: "credit", width: 100,
				formatter: this.currency_formatter},
			{id: "voucher_type", name: "Voucher Type", field: "voucher_type", width: 120},
			{id: "voucher_no", name: "Voucher No", field: "voucher_no", width: 160,
				link_formatter: {
					filter_input: "voucher_no",
					open_btn: true,
					doctype: "dataContext.voucher_type"
				}},
			{id: "remarks", name: "Remarks", field: "remarks", width: 200,
				formatter: this.text_formatter},
				
		];
	},
	
	filters: [
		{fieldtype:"Select", label: "Company", link:"Company", default_value: "Select Company...",
			filter: function(val, item, opts) {
				return item.company == val || val == opts.default_value;
			}},
		{fieldtype:"Link", label: "Account", link:"Account",
			filter: function(val, item, opts, me) {
				if(!val) {
					return true;
				} else {
					// true if GL Entry belongs to selected
					// account ledger or group
					return me.is_child_account(val, item.account);
				}
			}},
		{fieldtype:"Data", label: "Voucher No",
			filter: function(val, item, opts) {
				if(!val) return true;
				return (item.voucher_no && item.voucher_no.indexOf(val)!=-1);
			}},
		{fieldtype:"Date", label: "From Date", filter: function(val, item) {
			return dateutil.str_to_obj(val) <= dateutil.str_to_obj(item.posting_date);
		}},
		{fieldtype:"Label", label: "To"},
		{fieldtype:"Date", label: "To Date", filter: function(val, item) {
			return dateutil.str_to_obj(val) >= dateutil.str_to_obj(item.posting_date);
		}},
		{fieldtype: "Check", label: "Group by Ledger"},
		{fieldtype: "Check", label: "Group by Voucher"},
		{fieldtype:"Button", label: "Refresh", icon:"icon-refresh icon-white", cssClass:"btn-info"},
		{fieldtype:"Button", label: "Reset Filters"}
	],
	setup_filters: function() {
		this._super();
		var me = this;
		
		this.accounts_by_company = this.make_accounts_by_company();
		
		// filter accounts options by company
		this.filter_inputs.company.change(function() {
			me.setup_account_filter(this);
			me.set_route()
		});
		
		this.filter_inputs.account.change(function() {
			me.make_account_by_name();
			me.filter_inputs.group_by_ledger
				.parent().toggle(!!(me.account_by_name[$(this).val()] 
					&& me.account_by_name[$(this).val()].group_or_ledger==="Group"));
					
			me.filter_inputs.group_by_voucher
				.parent().toggle(!!(me.account_by_name[$(this).val()] 
					&& me.account_by_name[$(this).val()].group_or_ledger==="Ledger"));
		});
		
		this.trigger_refresh_on_change(["group_by_ledger"]);
		this.trigger_refresh_on_change(["group_by_voucher"]);
	},
	setup_account_filter: function(company_filter) {
		var me = this;
		
		var $account = me.filter_inputs.account;
		var company = $(company_filter).val();
		var default_company = this.filter_inputs.company.get(0).opts.default_value;
		var opts = $account.get(0).opts;
		opts.list = $.map(wn.report_dump.data["Account"], function(ac) {
				return (company===default_company || 
					me.accounts_by_company[company].indexOf(ac.name)!=-1) ? 
					ac.name : null;
			});
		
		this.set_autocomplete($account, opts.list);
		
	},
	init_filter_values: function() {
		this._super();
		this.filter_inputs.group_by_ledger.parent().toggle(false);
		this.filter_inputs.group_by_voucher.parent().toggle(false);
		this.filter_inputs.company.change();
		this.filter_inputs.account.change();
	},
	apply_filters_from_route: function() {
		this._super();
		this.filter_inputs.group_by_ledger.parent().toggle(false);
		this.filter_inputs.group_by_voucher.parent().toggle(false);
		this.filter_inputs.company.change();
		this.filter_inputs.account.change();
	},
	make_accounts_by_company: function() {
		var accounts_by_company = {};
		var me = this;
		$.each(wn.report_dump.data["Account"], function(i, ac) {
			if(!accounts_by_company[ac.company]) accounts_by_company[ac.company] = [];
			accounts_by_company[ac.company].push(ac.name);
		});
		return accounts_by_company;
	},
	is_child_account: function(account, item_account) {
		var opts = [account, item_account];
		account = this.account_by_name[account];
		item_account = this.account_by_name[item_account];
		
		return ((item_account.lft >= account.lft) && (item_account.rgt <= account.rgt));
	},
	prepare_data: function() {
		// add Opening, Closing, Totals rows
		// if filtered by account and / or voucher
		var data = wn.report_dump.data["GL Entry"];
		var out = [];
		
		this.make_account_by_name();
		
		var me = this;
		
		var from_date = dateutil.str_to_obj(this.from_date);
		var to_date = dateutil.str_to_obj(this.to_date);
		
		if(to_date < from_date) {
			msgprint("From Date must be before To Date");
			return;
		}
		
		var opening = this.make_summary_row("Opening", this.account);
		var totals = this.make_summary_row("Totals", this.account);

		var grouped_ledgers = {};
		$.each(data, function(i, item) {
			if((me.is_default("company") ? true : me.apply_filter(item, "company")) &&
				(me.account ? me.is_child_account(me.account, item.account) 
				: true) && (me.voucher_no ? item.voucher_no==me.voucher_no : true)) {
				var date = dateutil.str_to_obj(item.posting_date);

				// create grouping by ledger
				if(!grouped_ledgers[item.account]) {
					grouped_ledgers[item.account] = {
						entries: [],
						entries_group_by_voucher: {},
						opening: me.make_summary_row("Opening", item.account),
						totals: me.make_summary_row("Totals", item.account),
						closing: me.make_summary_row("Closing (Opening + Totals)",
							item.account)
					};
				}
				
				if(!grouped_ledgers[item.account].entries_group_by_voucher[item.voucher_no]) {
					grouped_ledgers[item.account].entries_group_by_voucher[item.voucher_no] = {
						row: {},
						totals: {"debit": 0, "credit": 0}
					}
				}
				
				if(date < from_date || item.is_opening=="Yes") {
					opening.debit += item.debit;
					opening.credit += item.credit;

					grouped_ledgers[item.account].opening.debit += item.debit;
					grouped_ledgers[item.account].opening.credit += item.credit;
				} else if(date <= to_date) {
					totals.debit += item.debit;
					totals.credit += item.credit;

					grouped_ledgers[item.account].totals.debit += item.debit;
					grouped_ledgers[item.account].totals.credit += item.credit;
					grouped_ledgers[item.account].entries_group_by_voucher[item.voucher_no]
						.totals.debit += item.debit;
					grouped_ledgers[item.account].entries_group_by_voucher[item.voucher_no]
						.totals.credit += item.credit;
				}
				if(item.account) {
					item.against_account = me.voucher_accounts[item.voucher_type + ":"
						+ item.voucher_no][(item.debit > 0 ? "credits" : "debits")].join(", ");
				}

				if(me.apply_filters(item) && item.is_opening=="No") {
					out.push(item);
					grouped_ledgers[item.account].entries.push(item);
					
					if(grouped_ledgers[item.account].entries_group_by_voucher[item.voucher_no].row){
						grouped_ledgers[item.account].entries_group_by_voucher[item.voucher_no]
							.row = jQuery.extend({}, item);
					}
				}
			}
		});

		var closing = this.make_summary_row("Closing (Opening + Totals)", this.account);
		closing.debit = opening.debit + totals.debit;
		closing.credit = opening.credit + totals.credit;

		if(me.account) {
			me.appframe.set_title("General Ledger: " + me.account);

			// group by ledgers
			if(this.account_by_name[this.account].group_or_ledger==="Group"
				&& this.group_by_ledger) {
					out = this.group_data_by_ledger(grouped_ledgers);
			}
			
			if(this.account_by_name[this.account].group_or_ledger==="Ledger"
				&& this.group_by_voucher) {
					out = this.group_data_by_voucher(grouped_ledgers);
			}
			
			opening = me.get_balance(me.account_by_name[me.account].debit_or_credit, opening)
			closing = me.get_balance(me.account_by_name[me.account].debit_or_credit, closing)
			
			out = [opening].concat(out).concat([totals, closing]);
		} else {
			me.appframe.set_title("General Ledger");
			out = out.concat([totals]);
		}

		this.data = out;
	},

	group_data_by_ledger: function(grouped_ledgers) {
		var me = this;
		var out = []
		$.each(Object.keys(grouped_ledgers).sort(), function(i, account) {
			if(grouped_ledgers[account].entries.length) {
				grouped_ledgers[account].closing.debit = 
					grouped_ledgers[account].opening.debit
					+ grouped_ledgers[account].totals.debit;

				grouped_ledgers[account].closing.credit = 
					grouped_ledgers[account].opening.credit
					+ grouped_ledgers[account].totals.credit;
			
				grouped_ledgers[account].opening = 
					me.get_balance(me.account_by_name[me.account].debit_or_credit,
					grouped_ledgers[account].opening)
				grouped_ledgers[account].closing = 
					me.get_balance(me.account_by_name[me.account].debit_or_credit, 
					grouped_ledgers[account].closing)
				
				out = out.concat([grouped_ledgers[account].opening])
					.concat(grouped_ledgers[account].entries)
					.concat([grouped_ledgers[account].totals, 
						grouped_ledgers[account].closing,
						{id: "_blank" + i, _no_format: true, debit: "", credit: ""}]);
			}
		});
		return [{id: "_blank_first", _no_format: true, debit: "", credit: ""}].concat(out);
	},
	
	group_data_by_voucher: function(grouped_ledgers) {
		var me = this;
		var out = []
		$.each(Object.keys(grouped_ledgers).sort(), function(i, account) {
			if(grouped_ledgers[account].entries.length) {
				$.each(Object.keys(grouped_ledgers[account].entries_group_by_voucher),
				 	function(j, voucher) {						
						voucher_dict = grouped_ledgers[account].entries_group_by_voucher[voucher];
						if(voucher_dict && 
								(voucher_dict.totals.debit || voucher_dict.totals.credit)) {
							voucher_dict.row.debit = voucher_dict.totals.debit;
							voucher_dict.row.credit = voucher_dict.totals.credit;
							voucher_dict.row.id = "entry_grouped_by_" + voucher
							out = out.concat(voucher_dict.row);
						}
				});
			}
		});
		return [{id: "_blank_first", _no_format: true, debit: "", credit: ""}].concat(out);
	},
	
	get_balance: function(debit_or_credit, balance) {
		if(debit_or_credit == "Debit") {
			balance.debit -= balance.credit; balance.credit = 0;
		} else {
			balance.credit -= balance.debit; balance.debit = 0;
		}
		return balance
	},

	make_summary_row: function(label, item_account) {
		return {
			account: label,
			debit: 0.0,
			credit: 0.0,
			id: ["", label, item_account].join("_").replace(" ", "_").toLowerCase(),
			_show: true,
			_style: "font-weight: bold"
		}
	},

	make_account_by_name: function() {
		this.account_by_name = this.make_name_map(wn.report_dump.data["Account"]);
		this.make_voucher_accounts_map();
	},
	
	make_voucher_accounts_map: function() {
		this.voucher_accounts = {};
		var data = wn.report_dump.data["GL Entry"];
		for(var i=0, j=data.length; i<j; i++) {
			var gl = data[i];
			
			if(!this.voucher_accounts[gl.voucher_type + ":" + gl.voucher_no])
				this.voucher_accounts[gl.voucher_type + ":" + gl.voucher_no] = {
					debits: [],
					credits: []
				}
				
			var va = this.voucher_accounts[gl.voucher_type + ":" + gl.voucher_no];
			if(gl.debit > 0) {
				va.debits.push(gl.account);
			} else {
				va.credits.push(gl.account);
			}
		}
	},
	
	get_plot_data: function() {
		var data = [];
		var me = this;
		if(!me.account || me.voucher_no) return false;
		var debit_or_credit = me.account_by_name[me.account].debit_or_credit;
		var balance = debit_or_credit=="Debit" ? me.data[0].debit : me.data[0].credit;
		data.push({
			label: me.account,
			data: [[dateutil.str_to_obj(me.from_date).getTime(), balance]]
				.concat($.map(me.data, function(col, idx) {
					if (col.posting_date) {
						var diff = (debit_or_credit == "Debit" ? 1 : -1) * (flt(col.debit) - flt(col.credit));
						balance += diff;
						return [[dateutil.str_to_obj(col.posting_date).getTime(), balance - diff],
								[dateutil.str_to_obj(col.posting_date).getTime(), balance]]
					}
					return null;
				})).concat([
					// closing
					[dateutil.str_to_obj(me.to_date).getTime(), balance]
				]),
			points: {show: true},
			lines: {show: true, fill: true},
		});
		return data;
	},
	get_plot_options: function() {
		return {
			grid: { hoverable: true, clickable: true },
			xaxis: { mode: "time", 
				min: dateutil.str_to_obj(this.from_date).getTime(),
				max: dateutil.str_to_obj(this.to_date).getTime() }
		}
	},
});