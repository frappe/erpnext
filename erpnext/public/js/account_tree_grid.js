// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

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

erpnext.AccountTreeGrid = frappe.views.TreeGridReport.extend({
	init: function(wrapper, title) {
		this._super({
			title: title,
			page: wrapper,
			parent: $(wrapper).find('.layout-main'),
			page: wrapper.page,
			doctypes: ["Company", "Fiscal Year", "Account", "GL Entry", "Cost Center"],
			tree_grid: {
				show: true,
				parent_field: "parent_account",
				formatter: function(item) {
					return repl("<a \
						onclick='frappe.cur_grid_report.show_general_ledger(\"%(value)s\")'>\
						%(value)s</a>", {
							value: item.name,
						});
				}
			},
		});
	},
	setup_columns: function() {
		this.columns = [
			{id: "name", name: __("Account"), field: "name", width: 300, cssClass: "cell-title",
				formatter: this.tree_formatter},
			{id: "opening_dr", name: __("Opening (Dr)"), field: "opening_dr", width: 100,
				formatter: this.currency_formatter},
			{id: "opening_cr", name: __("Opening (Cr)"), field: "opening_cr", width: 100,
				formatter: this.currency_formatter},
			{id: "debit", name: __("Debit"), field: "debit", width: 100,
				formatter: this.currency_formatter},
			{id: "credit", name: __("Credit"), field: "credit", width: 100,
				formatter: this.currency_formatter},
			{id: "closing_dr", name: __("Closing (Dr)"), field: "closing_dr", width: 100,
				formatter: this.currency_formatter},
			{id: "closing_cr", name: __("Closing (Cr)"), field: "closing_cr", width: 100,
				formatter: this.currency_formatter}
		];

	},
	filters: [
		{fieldtype: "Select", label: __("Company"), link:"Company", fieldname: "company",
			default_value: __("Select Company..."),
			filter: function(val, item, opts, me) {
				if (item.company == val || val == opts.default_value) {
					return me.apply_zero_filter(val, item, opts, me);
				}
				return false;
			}},
		{fieldtype: "Select", label: "Fiscal Year", link:"Fiscal Year", fieldname: "fiscal_year",
			default_value: __("Select Fiscal Year...")},
		{fieldtype: "Date", label: __("From Date"), fieldname: "from_date"},
		{fieldtype: "Label", label: __("To")},
		{fieldtype: "Date", label: __("To Date"), fieldname: "to_date"}
	],
	setup_filters: function() {
		this._super();
		var me = this;
		// default filters
		this.filter_inputs.fiscal_year.change(function() {
			var fy = $(this).val();
			$.each(frappe.report_dump.data["Fiscal Year"], function(i, v) {
				if (v.name==fy) {
					me.filter_inputs.from_date.val(dateutil.str_to_user(v.year_start_date));
					me.filter_inputs.to_date.val(dateutil.str_to_user(v.year_end_date));
				}
			});
			me.refresh();
		});
		me.show_zero_check()
		if(me.ignore_closing_entry) me.ignore_closing_entry();
	},
	prepare_data: function() {
		var me = this;
		if(!this.primary_data) {
			// make accounts list
			me.data = [];
			me.parent_map = {};
			me.item_by_name = {};

			$.each(frappe.report_dump.data["Account"], function(i, v) {
				var d = copy_dict(v);

				me.data.push(d);
				me.item_by_name[d.name] = d;
				if(d.parent_account) {
					me.parent_map[d.name] = d.parent_account;
				}
			});

			me.primary_data = [].concat(me.data);
		}

		me.data = [].concat(me.primary_data);
		$.each(me.data, function(i, d) {
			me.init_account(d);
		});

		this.set_indent();
		this.prepare_balances();

	},
	init_account: function(d) {
		this.reset_item_values(d);
	},

	prepare_balances: function() {
		var gl = frappe.report_dump.data['GL Entry'];
		var me = this;

		this.opening_date = dateutil.user_to_obj(this.filter_inputs.from_date.val());
		this.closing_date = dateutil.user_to_obj(this.filter_inputs.to_date.val());
		this.set_fiscal_year();
		if (!this.fiscal_year) return;

		$.each(this.data, function(i, v) {
			v.opening_dr = v.opening_cr = v.debit
				= v.credit = v.closing_dr = v.closing_cr = 0;
		});

		$.each(gl, function(i, v) {
			var posting_date = dateutil.str_to_obj(v.posting_date);
			var account = me.item_by_name[v.account];
			me.update_balances(account, posting_date, v);
		});

		this.update_groups();
	},
	update_balances: function(account, posting_date, v) {
		// opening
		if (posting_date < this.opening_date || v.is_opening === "Yes") {
			if (account.report_type === "Profit and Loss" &&
				posting_date <= dateutil.str_to_obj(this.fiscal_year[1])) {
				// balance of previous fiscal_year should
				//	not be part of opening of pl account balance
			} else {
				var opening_bal = flt(account.opening_dr) - flt(account.opening_cr) +
					flt(v.debit) - flt(v.credit);
				this.set_debit_or_credit(account, "opening", opening_bal);
			}
		} else if (this.opening_date <= posting_date && posting_date <= this.closing_date) {
			// in between
			account.debit += flt(v.debit);
			account.credit += flt(v.credit);
		}
		// closing
		var closing_bal = flt(account.opening_dr) - flt(account.opening_cr) +
			flt(account.debit) - flt(account.credit);
		this.set_debit_or_credit(account, "closing", closing_bal);
	},
	set_debit_or_credit: function(account, field, balance) {
		if(balance > 0) {
			account[field+"_dr"] = balance;
			account[field+"_cr"] = 0;
		} else {
			account[field+"_cr"] = Math.abs(balance);
			account[field+"_dr"] = 0;
		}
	},
	update_groups: function() {
		// update groups
		var me= this;
		$.each(this.data, function(i, account) {
			// update groups
			if((account.is_group == 0) || (account.rgt - account.lft == 1)) {
				var parent = me.parent_map[account.name];
				while(parent) {
					var parent_account = me.item_by_name[parent];
					$.each(me.columns, function(c, col) {
						if (col.formatter == me.currency_formatter) {
							if(col.field=="opening_dr") {
								var bal = flt(parent_account.opening_dr) -
									flt(parent_account.opening_cr) +
									flt(account.opening_dr) - flt(account.opening_cr);
								me.set_debit_or_credit(parent_account, "opening", bal);
							} else if(col.field=="closing_dr") {
								var bal = flt(parent_account.closing_dr) -
									flt(parent_account.closing_cr) +
									flt(account.closing_dr) - flt(account.closing_cr);
								me.set_debit_or_credit(parent_account, "closing", bal);
							} else if(in_list(["debit", "credit"], col.field)) {
								parent_account[col.field] = flt(parent_account[col.field]) +
									flt(account[col.field]);
							}
						}
					});
					parent = me.parent_map[parent];
				}
			}
		});
	},

	set_fiscal_year: function() {
		if (this.opening_date > this.closing_date) {
			msgprint(__("Opening Date should be before Closing Date"));
			return;
		}

		this.fiscal_year = null;
		var me = this;
		$.each(frappe.report_dump.data["Fiscal Year"], function(i, v) {
			if (me.opening_date >= dateutil.str_to_obj(v.year_start_date) &&
				me.closing_date <= dateutil.str_to_obj(v.year_end_date)) {
					me.fiscal_year = v;
				}
		});

		if (!this.fiscal_year) {
			msgprint(__("Opening Date and Closing Date should be within same Fiscal Year"));
			return;
		}
	},

	show_general_ledger: function(account) {
		frappe.route_options = {
			account: account,
			company: this.company,
			from_date: this.from_date,
			to_date: this.to_date
		};
		frappe.set_route("query-report", "General Ledger");
	}
});
