// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.accounts");
frappe.provide("erpnext.journal_entry");
frappe.require("assets/erpnext/js/utils.js");

cur_frm.add_fetch("account", "currency", "currency");

frappe.ui.form.on("Journal Entry", {
	refresh: function(frm) {
		erpnext.toggle_naming_series();
		cur_frm.cscript.voucher_type(frm.doc);

		if(frm.doc.docstatus==1) {
			cur_frm.add_custom_button(__('View Ledger'), function() {
				frappe.route_options = {
					"voucher_no": frm.doc.name,
					"from_date": frm.doc.posting_date,
					"to_date": frm.doc.posting_date,
					"company": frm.doc.company,
					group_by_voucher: 0
				};
				frappe.set_route("query-report", "General Ledger");
			}, "icon-table");
		}
		
		// hide /unhide fields based on currency
		erpnext.journal_entry.toggle_fields_based_on_currency(frm);
	}
})

erpnext.journal_entry.toggle_fields_based_on_currency = function(frm) {
	var fields = ["balance_in_account_currency", "party_balance_in_account_currency", 
		"debit_in_account_currency", "credit_in_account_currency"];
		
	var company_currency = erpnext.get_currency(frm.doc.company);
		
	var grid = frm.get_field("accounts").grid;
	grid.set_column_disp(fields, grid.currency!=company_currency);
}

erpnext.accounts.JournalEntry = frappe.ui.form.Controller.extend({
	onload: function() {
		this.load_defaults();
		this.setup_queries();
		this.setup_balance_formatter();
	},

	onload_post_render: function() {
		cur_frm.get_field("accounts").grid.set_multiple_add("account");
	},

	load_defaults: function() {
		if(this.frm.doc.__islocal && this.frm.doc.company) {
			frappe.model.set_default_values(this.frm.doc);
			$.each(this.frm.doc.accounts || [], function(i, jvd) {
					frappe.model.set_default_values(jvd);
				}
			);

			if(!this.frm.doc.amended_from) this.frm.doc.posting_date = get_today();
		}
	},

	setup_queries: function() {
		var me = this;

		$.each(["account", "cost_center"], function(i, fieldname) {
			me.frm.set_query(fieldname, "accounts", function() {
				frappe.model.validate_missing(me.frm.doc, "company");
				return {
					filters: {
						company: me.frm.doc.company,
						is_group: 0
					}
				};
			});
		});

		me.frm.set_query("party_type", "accounts", function(doc, cdt, cdn) {
			return {
				filters: {"name": ["in", ["Customer", "Supplier"]]}
			}
		});

		me.frm.set_query("reference_name", "accounts", function(doc, cdt, cdn) {
			var jvd = frappe.get_doc(cdt, cdn);

			// expense claim
			if(jvd.reference_type==="Expense Claim") {
				return {};
			}

			// journal entry
			if(jvd.reference_type==="Journal Entry") {
				frappe.model.validate_missing(jvd, "account");

				return {
					query: "erpnext.accounts.doctype.journal_entry.journal_entry.get_against_jv",
					filters: {
						account: jvd.account,
						party: jvd.party
					}
				};
			}

			// against party

			frappe.model.validate_missing(jvd, "party_type");
			frappe.model.validate_missing(jvd, "party");

			var out = {
				filters: [
					[jvd.reference_type, jvd.reference_type.indexOf("Sales")===0 ? "customer" : "supplier", "=", jvd.party],
					[jvd.reference_type, "docstatus", "=", 1],
				]
			};

			if(in_list(["Sales Invoice", "Purchase Invoice"], jvd.reference_type)) {
				out.filters.push([jvd.reference_type, "outstanding_amount", "!=", 0]);
			} else {
				out.filters.push([jvd.reference_type, "per_billed", "<", 100]);
			}

			return out;
		});


	},

	setup_balance_formatter: function() {
		var me = this;
		$.each(["balance", "party_balance"], function(i, field) {
			var df = frappe.meta.get_docfield("Journal Entry Account", field, me.frm.doc.name);
			df.formatter = function(value, df, options, doc) {
				var currency = frappe.meta.get_field_currency(df, doc);
				var dr_or_cr = value ? ('<label>' + (value > 0.0 ? __("Dr") : __("Cr")) + '</label>') : "";
				return "<div style='text-align: right'>"
					+ ((value==null || value==="") ? "" : format_currency(Math.abs(value), currency))
					+ " " + dr_or_cr
					+ "</div>";
			}
		})
	},

	reference_name: function(doc, cdt, cdn) {
		var d = frappe.get_doc(cdt, cdn);
		if (d.reference_type==="Purchase Invoice" && !flt(d.debit)) {
			this.get_outstanding('Purchase Invoice', d.reference_name, d);
		}
		if (d.reference_type==="Sales Invoice" && !flt(d.credit)) {
			this.get_outstanding('Sales Invoice', d.reference_name, d);
		}
		if (d.reference_type==="Journal Entry" && !flt(d.credit) && !flt(d.debit)) {
			this.get_outstanding('Journal Entry', d.reference_name, d);
		}
	},

	get_outstanding: function(doctype, docname, child) {
		var me = this;
		var args = {
			"doctype": doctype,
			"docname": docname,
			"party": child.party,
			"account": child.account
		}

		return this.frm.call({
			child: child,
			method: "get_outstanding",
			args: { args: args},
			callback: function(r) {
				cur_frm.cscript.update_totals(me.frm.doc);
			}
		});
	},

	accounts_add: function(doc, cdt, cdn) {
		var row = frappe.get_doc(cdt, cdn);
		$.each(doc.accounts, function(i, d) {
			if(d.account && d.party && d.party_type) {
				row.account = d.account;
				row.party = d.party;
				row.party_type = d.party_type;
			}
		});

		// set difference
		if(doc.difference) {
			if(doc.difference > 0) {
				row.credit = doc.difference;
			} else {
				row.debit = -doc.difference;
			}
		}
	},

});

cur_frm.script_manager.make(erpnext.accounts.JournalEntry);

cur_frm.cscript.company = function(doc, cdt, cdn) {
	cur_frm.refresh_fields();
	erpnext.get_fiscal_year(doc.company, doc.posting_date);
}

cur_frm.cscript.posting_date = function(doc, cdt, cdn){
	erpnext.get_fiscal_year(doc.company, doc.posting_date);
}

cur_frm.cscript.update_totals = function(doc) {
	var td=0.0; var tc =0.0;
	var el = doc.accounts || [];
	for(var i in el) {
		td += flt(el[i].debit, precision("debit", el[i]));
		tc += flt(el[i].credit, precision("credit", el[i]));
	}
	var doc = locals[doc.doctype][doc.name];
	doc.total_debit = td;
	doc.total_credit = tc;
	doc.difference = flt((td - tc), precision("difference"));
	refresh_many(['total_debit','total_credit','difference']);
}

cur_frm.cscript.debit = function(doc,dt,dn) { cur_frm.cscript.update_totals(doc); }
cur_frm.cscript.credit = function(doc,dt,dn) { cur_frm.cscript.update_totals(doc); }

cur_frm.cscript.get_balance = function(doc,dt,dn) {
	cur_frm.cscript.update_totals(doc);
	return $c_obj(cur_frm.doc, 'get_balance', '', function(r, rt){
	cur_frm.refresh();
	});
}
// Get balance
// -----------

cur_frm.cscript.account = function(doc,dt,dn) {
	var d = locals[dt][dn];
	if(d.account) {
		return frappe.call({
			method: "erpnext.accounts.doctype.journal_entry.journal_entry.get_account_balance_and_party_type",
			args: {account: d.account, date: doc.posting_date},
			callback: function(r) {
				$.extend(d, r.message);
				refresh_field('balance', d.name, 'accounts');
				refresh_field('party_type', d.name, 'accounts');
			}
		});
	}
}

cur_frm.cscript.validate = function(doc,cdt,cdn) {
	cur_frm.cscript.update_totals(doc);
}

cur_frm.cscript.select_print_heading = function(doc,cdt,cdn){
	if(doc.select_print_heading){
		// print heading
		cur_frm.pformat.print_heading = doc.select_print_heading;
	}
	else
		cur_frm.pformat.print_heading = __("Journal Entry");
}

cur_frm.cscript.voucher_type = function(doc, cdt, cdn) {
	cur_frm.set_df_property("cheque_no", "reqd", doc.voucher_type=="Bank Entry");
	cur_frm.set_df_property("cheque_date", "reqd", doc.voucher_type=="Bank Entry");

	if(!doc.company) return;

	var update_jv_details = function(doc, r) {
		var jvdetail = frappe.model.add_child(doc, "Journal Entry Account", "accounts");
		$.each(r, function(i, d) {
			var row = frappe.model.add_child(doc, "Journal Entry Account", "accounts");
			row.account = d.account;
			row.balance = d.balance;
		});
		refresh_field("accounts");
	}

	if(!(doc.accounts || []).length) {
		if(in_list(["Bank Entry", "Cash Entry"], doc.voucher_type)) {
			return frappe.call({
				type: "GET",
				method: "erpnext.accounts.doctype.journal_entry.journal_entry.get_default_bank_cash_account",
				args: {
					"voucher_type": doc.voucher_type,
					"company": doc.company
				},
				callback: function(r) {
					if(r.message) {
						update_jv_details(doc, [r.message]);
					}
				}
			})
		} else if(doc.voucher_type=="Opening Entry") {
			return frappe.call({
				type:"GET",
				method: "erpnext.accounts.doctype.journal_entry.journal_entry.get_opening_accounts",
				args: {
					"company": doc.company
				},
				callback: function(r) {
					frappe.model.clear_table(doc, "accounts");
					if(r.message) {
						update_jv_details(doc, r.message);
					}
					cur_frm.set_value("is_opening", "Yes")
				}
			})
		}
	}
}

frappe.ui.form.on("Journal Entry Account", "party", function(frm, cdt, cdn) {
	var d = frappe.get_doc(cdt, cdn);
	if(!d.account && d.party_type && d.party) {
		return frm.call({
			method: "erpnext.accounts.doctype.journal_entry.journal_entry.get_party_account_and_balance",
			child: d,
			args: {
				company: frm.doc.company,
				party_type: d.party_type,
				party: d.party
			}
		});
	}
})

frappe.ui.form.on("Journal Entry Account", "accounts_remove", function(frm) {
	cur_frm.cscript.update_totals(frm.doc);
});

