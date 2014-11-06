// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.accounts");

erpnext.accounts.JournalVoucher = frappe.ui.form.Controller.extend({
	onload: function() {
		this.load_defaults();
		this.setup_queries();
		this.setup_balance_formatter();
	},

	onload_post_render: function() {
		cur_frm.get_field("entries").grid.set_multiple_add("account");
	},

	load_defaults: function() {
		if(this.frm.doc.__islocal && this.frm.doc.company) {
			frappe.model.set_default_values(this.frm.doc);
			$.each(this.frm.doc.entries || [], function(i, jvd) {
					frappe.model.set_default_values(jvd);
				}
			);

			if(!this.frm.doc.amended_from) this.frm.doc.posting_date = get_today();
		}
	},

	setup_queries: function() {
		var me = this;

		$.each(["account", "cost_center"], function(i, fieldname) {
			me.frm.set_query(fieldname, "entries", function() {
				frappe.model.validate_missing(me.frm.doc, "company");
				return {
					filters: {
						company: me.frm.doc.company,
						group_or_ledger: "Ledger"
					}
				};
			});
		});

		$.each([["against_voucher", "Purchase Invoice", "credit_to"],
			["against_invoice", "Sales Invoice", "debit_to"]], function(i, opts) {
				me.frm.set_query(opts[0], "entries", function(doc, cdt, cdn) {
					var jvd = frappe.get_doc(cdt, cdn);
					frappe.model.validate_missing(jvd, "account");
					return {
						filters: [
							[opts[1], opts[2], "=", jvd.account],
							[opts[1], "docstatus", "=", 1],
							[opts[1], "outstanding_amount", ">", 0]
						]
					};
				});
		});

		this.frm.set_query("against_jv", "entries", function(doc, cdt, cdn) {
			var jvd = frappe.get_doc(cdt, cdn);
			frappe.model.validate_missing(jvd, "account");

			return {
				query: "erpnext.accounts.doctype.journal_voucher.journal_voucher.get_against_jv",
				filters: { account: jvd.account }
			};
		});
	},

	setup_balance_formatter: function() {
		var df = frappe.meta.get_docfield("Journal Voucher Detail", "balance", this.frm.doc.name);
		df.formatter = function(value, df, options, doc) {
			var currency = frappe.meta.get_field_currency(df, doc);
			var dr_or_cr = value ? ('<label>' + (value > 0.0 ? __("Dr") : __("Cr")) + '</label>') : "";
			return "<div style='text-align: right'>"
				+ ((value==null || value==="") ? "" : format_currency(Math.abs(value), currency))
				+ " " + dr_or_cr
				+ "</div>";
		}
	},

	against_voucher: function(doc, cdt, cdn) {
		var d = frappe.get_doc(cdt, cdn);
		if (d.against_voucher && !flt(d.debit)) {
			this.get_outstanding({
				'doctype': 'Purchase Invoice',
				'docname': d.against_voucher
			}, d)
		}
	},

	against_invoice: function(doc, cdt, cdn) {
		var d = frappe.get_doc(cdt, cdn);
		if (d.against_invoice && !flt(d.credit)) {
			this.get_outstanding({
				'doctype': 'Sales Invoice',
				'docname': d.against_invoice
			}, d)
		}
	},

	against_jv: function(doc, cdt, cdn) {
		var d = frappe.get_doc(cdt, cdn);
		if (d.against_jv && !flt(d.credit) && !flt(d.debit)) {
			this.get_outstanding({
				'doctype': 'Journal Voucher',
				'docname': d.against_jv,
				'account': d.account
			}, d)
		}
	},

	get_outstanding: function(args, child) {
		var me = this;
		return this.frm.call({
			child: child,
			method: "get_outstanding",
			args: { args: args},
			callback: function(r) {
				cur_frm.cscript.update_totals(me.frm.doc);
			}
		});
	}
});

cur_frm.script_manager.make(erpnext.accounts.JournalVoucher);

cur_frm.cscript.refresh = function(doc) {
	cur_frm.cscript.is_opening(doc)
	erpnext.toggle_naming_series();
	cur_frm.cscript.voucher_type(doc);
	if(doc.docstatus==1) {
		cur_frm.appframe.add_button(__('View Ledger'), function() {
			frappe.route_options = {
				"voucher_no": doc.name,
				"from_date": doc.posting_date,
				"to_date": doc.posting_date,
				"company": doc.company,
				group_by_voucher: 0
			};
			frappe.set_route("query-report", "General Ledger");
		}, "icon-table");
	}
}

cur_frm.cscript.company = function(doc, cdt, cdn) {
	cur_frm.refresh_fields();
}

cur_frm.cscript.is_opening = function(doc, cdt, cdn) {
	hide_field('aging_date');
	if (doc.is_opening == 'Yes') unhide_field('aging_date');
}

cur_frm.cscript.update_totals = function(doc) {
	var td=0.0; var tc =0.0;
	var el = doc.entries || [];
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
			method: "erpnext.accounts.utils.get_balance_on",
			args: {account: d.account, date: doc.posting_date},
			callback: function(r) {
				d.balance = r.message;
				refresh_field('balance', d.name, 'entries');
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
		cur_frm.pformat.print_heading = __("Journal Voucher");
}

cur_frm.cscript.voucher_type = function(doc, cdt, cdn) {
	cur_frm.set_df_property("cheque_no", "reqd", doc.voucher_type=="Bank Voucher");
	cur_frm.set_df_property("cheque_date", "reqd", doc.voucher_type=="Bank Voucher");

	if((doc.entries || []).length!==0 || !doc.company) // too early
		return;

	var update_jv_details = function(doc, r) {
		var jvdetail = frappe.model.add_child(doc, "Journal Voucher Detail", "entries");
		$.each(r, function(i, d) {
			var row = frappe.model.add_child(doc, "Journal Voucher Detail", "entries");
			row.account = d.account;
			row.balance = d.balance;
		});
		refresh_field("entries");
	}

	if(in_list(["Bank Voucher", "Cash Voucher"], doc.voucher_type)) {
		return frappe.call({
			type: "GET",
			method: "erpnext.accounts.doctype.journal_voucher.journal_voucher.get_default_bank_cash_account",
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
			method: "erpnext.accounts.doctype.journal_voucher.journal_voucher.get_opening_accounts",
			args: {
				"company": doc.company
			},
			callback: function(r) {
				frappe.model.clear_table(doc, "entries");
				if(r.message) {
					update_jv_details(doc, r.message);
				}
				cur_frm.set_value("is_opening", "Yes")
			}
		})
	}
}
