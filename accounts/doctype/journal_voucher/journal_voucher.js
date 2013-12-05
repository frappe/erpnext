// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

wn.provide("erpnext.accounts");

erpnext.accounts.JournalVoucher = wn.ui.form.Controller.extend({
	onload: function() {
		this.load_defaults();
		this.setup_queries();
	},
	
	load_defaults: function() {
		if(this.frm.doc.__islocal && this.frm.doc.company) {
			wn.model.set_default_values(this.frm.doc);
			$.each(wn.model.get_doclist(this.frm.doc.doctype, 
				this.frm.doc.name, {parentfield: "entries"}), function(i, jvd) {
					wn.model.set_default_values(jvd);
				}
			);
			
			if(!this.frm.doc.amended_from) this.frm.doc.posting_date = get_today();
		}
	},
	
	setup_queries: function() {
		var me = this;
		
		$.each(["account", "cost_center"], function(i, fieldname) {
			me.frm.set_query(fieldname, "entries", function() {
				wn.model.validate_missing(me.frm.doc, "company");
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
					var jvd = wn.model.get_doc(cdt, cdn);
					wn.model.validate_missing(jvd, "account");
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
			var jvd = wn.model.get_doc(cdt, cdn);
			wn.model.validate_missing(jvd, "account");
			
			return {
				query: "accounts.doctype.journal_voucher.journal_voucher.get_against_jv",
				filters: { account: jvd.account }
			};
		});
	},
	
	against_voucher: function(doc, cdt, cdn) {
		var d = wn.model.get_doc(cdt, cdn);
		if (d.against_voucher && !flt(d.debit)) {
			this.get_outstanding({
				'doctype': 'Purchase Invoice', 
				'docname': d.against_voucher
			}, d)
		}
	},
	
	against_invoice: function(doc, cdt, cdn) {
		var d = wn.model.get_doc(cdt, cdn);
		if (d.against_invoice && !flt(d.credit)) {
			this.get_outstanding({
				'doctype': 'Sales Invoice', 
				'docname': d.against_invoice
			}, d)
		}
	},
	
	against_jv: function(doc, cdt, cdn) {
		var d = wn.model.get_doc(cdt, cdn);
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
	erpnext.hide_naming_series();
	cur_frm.cscript.voucher_type(doc);
	if(doc.docstatus==1) { 
		cur_frm.appframe.add_button(wn._('View Ledger'), function() {
			wn.route_options = {
				"voucher_no": doc.name,
				"from_date": doc.posting_date,
				"to_date": doc.posting_date,
			};
			wn.set_route("general-ledger");
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
	var el = getchildren('Journal Voucher Detail', doc.name, 'entries');
	for(var i in el) {
		td += flt(el[i].debit, 2);
		tc += flt(el[i].credit, 2);
	}
	var doc = locals[doc.doctype][doc.name];
	doc.total_debit = td;
	doc.total_credit = tc;
	doc.difference = flt((td - tc), 2);
	refresh_many(['total_debit','total_credit','difference']);
}

cur_frm.cscript.debit = function(doc,dt,dn) { cur_frm.cscript.update_totals(doc); }
cur_frm.cscript.credit = function(doc,dt,dn) { cur_frm.cscript.update_totals(doc); }

cur_frm.cscript.get_balance = function(doc,dt,dn) {
	cur_frm.cscript.update_totals(doc); 
	return $c_obj(make_doclist(dt,dn), 'get_balance', '', function(r, rt){
	cur_frm.refresh();
	});
}
// Get balance
// -----------

cur_frm.cscript.account = function(doc,dt,dn) {
	var d = locals[dt][dn];
	if(d.account) {
		return wn.call({
			method: "accounts.utils.get_balance_on",
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
		cur_frm.pformat.print_heading = wn._("Journal Voucher");
}

cur_frm.cscript.voucher_type = function(doc, cdt, cdn) {
	cur_frm.set_df_property("cheque_no", "reqd", doc.voucher_type=="Bank Voucher");
	cur_frm.set_df_property("cheque_date", "reqd", doc.voucher_type=="Bank Voucher");

	if(wn.model.get("Journal Voucher Detail", {"parent":doc.name}).length!==0 // too late
		|| !doc.company) // too early
		return;
	
	var update_jv_details = function(doc, r) {
		$.each(r.message, function(i, d) {
			var jvdetail = wn.model.add_child(doc, "Journal Voucher Detail", "entries");
			jvdetail.account = d.account;
			jvdetail.balance = d.balance;
		});
		refresh_field("entries");
	}
	
	if(in_list(["Bank Voucher", "Cash Voucher"], doc.voucher_type)) {
		return wn.call({
			type: "GET",
			method: "accounts.doctype.journal_voucher.journal_voucher.get_default_bank_cash_account",
			args: {
				"voucher_type": doc.voucher_type,
				"company": doc.company
			},
			callback: function(r) {
				if(r.message) {
					update_jv_details(doc, r);
				}
			}
		})
	} else if(doc.voucher_type=="Opening Entry") {
		return wn.call({
			type:"GET",
			method: "accounts.doctype.journal_voucher.journal_voucher.get_opening_accounts",
			args: {
				"company": doc.company
			},
			callback: function(r) {
				wn.model.clear_table("Journal Voucher Detail", "Journal Voucher", 
					doc.name, "entries");
				if(r.message) {
					update_jv_details(doc, r);
				}
				cur_frm.set_value("is_opening", "Yes")
			}
		})
	}
}