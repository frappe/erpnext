// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Payment Entry', {
	onload: function(frm) {
		frm.set_value("paid_from_account_currency", null);
		frm.set_value("paid_from_account_currency", null);
	},
	
	setup: function(frm) {
		frm.get_field('references').grid.editable_fields = [
			{fieldname: 'reference_doctype', columns: 2},
			{fieldname: 'reference_name', columns: 3},
			{fieldname: 'outstanding_amount', columns: 3},
			{fieldname: 'allocated_amount', columns: 3}
		];
				
		var party_account_type = frm.doc.party_type=="Customer" ? "Receivable" : "Payable";
				
		frm.set_query("paid_from", function() {
			var account_types = in_list(["Pay", "Internal Transfer"], frm.doc.payment_type) ? 
				["Bank", "Cash"] : party_account_type;

			return {
				filters: {
					"account_type": ["in", account_types],
					"is_group": 0,
					"company": frm.doc.company
				}
			}
		});
		
		frm.set_query("paid_to", function() {
			var account_types = in_list(["Receive", "Internal Transfer"], frm.doc.payment_type) ? 
	 			["Bank", "Cash"] : party_account_type;
			
			return {
				filters: {
					"account_type": ["in", account_types],
					"is_group": 0,
					"company": frm.doc.company
				}
			}
		});
		
		frm.set_query("account", "deductions", function() {
			return {
				filters: {
					"is_group": 0,
					"company": frm.doc.company
				}
			}
		});
		
		frm.set_query("cost_center", "deductions", function() {
			return {
				filters: {
					"is_group": 0,
					"company": frm.doc.company
				}
			}
		});
		
		frm.set_query("reference_doctype", "references", function() {
			if (frm.doc.party_type=="Customer") {
				var doctypes = ["Sales Order", "Sales Invoice", "Journal Entry"];
			} else if (frm.doc.party_type=="Supplier") {
				var doctypes = ["Purchase Order", "Purchase Invoice", "Journal Entry"];
			} else {
				var doctypes = ["Journal Entry"];
			}
			
			return {
				filters: { "name": ["in", doctypes] }
			};
		});
	},
	
	refresh: function(frm) {
		frm.events.hide_unhide_fields(frm);
		frm.events.set_dynamic_labels(frm);
	},
	
	hide_unhide_fields: function(frm) {
		var company_currency = frappe.get_doc(":Company", frm.doc.company).default_currency;
		
		frm.toggle_display(["source_exchange_rate", "base_paid_amount"], 
			(frm.doc.paid_from && frm.doc.paid_from_account_currency != company_currency));
		
		frm.toggle_display(["target_exchange_rate", "base_received_amount"], 
			(frm.doc.paid_to && frm.doc.paid_to_account_currency != company_currency));
		
		frm.toggle_display(["base_total_allocated_amount"], 
			((frm.doc.payment_type=="Receive" && frm.doc.paid_from_account_currency != company_currency) || 
				(frm.doc.payment_type=="Pay" && frm.doc.paid_to_account_currency != company_currency)));
				
		frm.toggle_display(["received_amount"], 
			frm.doc.paid_from_account_currency != frm.doc.paid_to_account_currency)
	},
	
	set_dynamic_labels: function(frm) {
		var company_currency = frappe.get_doc(":Company", frm.doc.company).default_currency;
		
		var field_label_map = {};
		var grid_field_label_map = {};

		var setup_field_label_map = function(fields_list, currency, parentfield) {
			var doctype = parentfield ? frm.fields_dict[parentfield].grid.doctype : frm.doc.doctype;
			$.each(fields_list, function(i, fname) {
				var docfield = frappe.meta.docfield_map[doctype][fname];
				if(docfield) {
					var label = __(docfield.label || "").replace(/\([^\)]*\)/g, "");
					if(parentfield) {
						grid_field_label_map[doctype + "-" + fname] = 
							label.trim() + " (" + __(currency) + ")";
					} else {
						field_label_map[fname] = label.trim() + " (" + currency + ")";
					}
				}
			});
		}
		
		setup_field_label_map(["base_paid_amount", "base_received_amount", "base_total_allocated_amount", 
			"difference_amount"], company_currency);
		
		setup_field_label_map(["paid_amount"], frm.doc.paid_from_account_currency);
		setup_field_label_map(["received_amount"], frm.doc.paid_to_account_currency);
		
		var party_account_currency = frm.doc.payment_type=="Receive" ? 
			frm.doc.paid_from_account_currency : frm.doc.paid_to_account_currency;
			
		setup_field_label_map(["total_allocated_amount"], party_account_currency);
		
		$.each(field_label_map, function(fname, label) {
			me.frm.fields_dict[fname].set_label(label);
		});
		
		setup_field_label_map(["total_amount"], company_currency, "references");
		setup_field_label_map(["outstanding_amount", "allocated_amount"], 
			party_account_currency, "references");
		
		$.each(grid_field_label_map, function(fname, label) {
			fname = fname.split("-");
			var df = frappe.meta.get_docfield(fname[0], fname[1], me.frm.doc.name);
			if(df) df.label = label;
		});
		
		cur_frm.set_df_property("source_exchange_rate", "description", 
			("1 " + frm.doc.paid_from_account_currency + " = [?] " + company_currency));
		
		cur_frm.set_df_property("target_exchange_rate", "description", 
			("1 " + frm.doc.paid_to_account_currency + " = [?] " + company_currency));		
	},
		
	"party": function(frm) {
		if(frm.doc.payment_type && frm.doc.party_type && frm.doc.party) {
			frm.set_party_account_based_on_party = true;
			
			return frappe.call({
				method: "erpnext.accounts.doctype.payment_entry.payment_entry.get_party_details",
				args: {
					company: frm.doc.company,
					party_type: frm.doc.party_type,
					party: frm.doc.party, 
					date: frm.doc.posting_date
				},
				callback: function(r, rt) {
					if(r.message) {
						if(frm.doc.payment_type == "Receive") {
							frm.set_value("paid_from", r.message.party_account);
							frm.set_value("paid_from_account_currency", r.message.party_account_currency);
							frm.set_value("paid_from_account_balance", r.message.account_balance);
						} else if (frm.doc.payment_type == "Pay"){
							frm.set_value("paid_to", r.message.party_account);
							frm.set_value("paid_to_account_currency", r.message.party_account_currency);
							frm.set_value("paid_to_account_balance", r.message.account_balance);
						}
						frm.set_value("party_balance", r.message.party_balance);
						frm.events.get_outstanding_documents(frm);
						frm.events.hide_unhide_fields(frm);
						frm.events.set_dynamic_labels(frm);
						frm.set_party_account_based_on_party = false;
					}
				}
			});
		}
	},
	
	payment_type: function(frm) {
		if(frm.doc.payment_type == "Internal Transfer") {
			$.each(["party", "party_balance", "paid_from", "paid_to", 
				"references", "total_allocated_amount"], function(i, field) {
					frm.set_value(field, "");
			})
		} else {
			frm.events.party(frm);
		}
	},
		
	"mode_of_payment": function(frm) {
		return  frappe.call({
			method: "erpnext.accounts.doctype.sales_invoice.sales_invoice.get_bank_cash_account",
			args: {
				"mode_of_payment": frm.doc.mode_of_payment,
				"company": frm.doc.company
			},
			callback: function(r, rt) {
				if(r.message) {
					var payment_account_field = frm.doc.payment_type == "Receive" ? "paid_to" : "paid_from";
					frm.set_value(payment_account_field, r.message['account']);
				}
			}
		});
	},
	
	paid_from: function(frm) {
		if(frm.set_party_account_based_on_party) return;
		
		frm.events.set_account_currency_and_balance(frm, frm.doc.paid_from, 
			"paid_from_account_currency", "paid_from_account_balance", function() {
				if(frm.doc.payment_type == "Receive") frm.events.get_outstanding_documents(frm);
			}
		);
	},	
	
	paid_to: function(frm) {
		if(frm.set_party_account_based_on_party) return;
		
		frm.events.set_account_currency_and_balance(frm, frm.doc.paid_to, 
			"paid_to_account_currency", "paid_to_account_balance", function() {
				if(frm.doc.payment_type == "Pay") frm.events.get_outstanding_documents(frm);
			}
		);
	},
	
	set_account_currency_and_balance: function(frm, account, currency_field, 
			balance_field, callback_function) {
		frappe.call({
			method: "erpnext.accounts.doctype.payment_entry.payment_entry.get_account_currency_and_balance",
			args: {
				"account": account,
				"date": frm.doc.posting_date
			},
			callback: function(r, rt) {
				if(r.message) {
					frm.set_value(currency_field, r.message['account_currency']);
					frm.set_value(balance_field, r.message['account_balance']);
					
					if(callback_function) callback_function()
						
					frm.events.hide_unhide_fields(frm);
					frm.events.set_dynamic_labels(frm);
				}
			}
		});
	},
	
	paid_from_account_currency: function(frm) {
		var company_currency = frappe.get_doc(":Company", frm.doc.company).default_currency;
		
		if (frm.doc.paid_from_account_currency == company_currency) {
			frm.set_value("source_exchange_rate", 1);
		} else if (frm.doc.paid_from){
			if (in_list(["Internal Transfer", "Pay"], frm.doc.payment_type)) {
				frappe.call({
					method: "erpnext.accounts.doctype.journal_entry.journal_entry.get_average_exchange_rate",
					args: {
						account: frm.doc.paid_from
					},
					callback: function(r, rt) {
						frm.set_value("source_exchange_rate", r.message);
					}
				})
			} else {
				frm.events.set_current_exchange_rate(frm, "source_exchange_rate", 
					frm.doc.paid_from_account_currency, company_currency);
			}
		}
	},
	
	paid_to_account_currency: function(frm) {
		var company_currency = frappe.get_doc(":Company", frm.doc.company).default_currency;
		
		frm.events.set_current_exchange_rate(frm, "target_exchange_rate", 
			frm.doc.paid_to_account_currency, company_currency);
	},
	
	set_current_exchange_rate: function(frm, exchange_rate_field, from_currency, to_currency) {
		frappe.call({
			method: "erpnext.setup.utils.get_exchange_rate",
			args: {
				from_currency: from_currency,
				to_currency: to_currency
			},
			callback: function(r, rt) {
				frm.set_value(exchange_rate_field, r.message);
			}
		})
	},
	
	source_exchange_rate: function(frm) {
		if (frm.doc.paid_amount) {
			frm.set_value("base_paid_amount", flt(frm.doc.paid_amount) * flt(frm.doc.source_exchange_rate));
		}
	},
	
	target_exchange_rate: function(frm) {
		if (frm.doc.received_amount) {
			frm.set_value("base_received_amount", 
				flt(frm.doc.received_amount) * flt(frm.doc.target_exchange_rate));
		}
	},
	
	paid_amount: function(frm) {
		frm.set_value("base_paid_amount", flt(frm.doc.paid_amount) * flt(frm.doc.source_exchange_rate));
		
		if(frm.doc.paid_from_account_currency == frm.doc.paid_to_account_currency) {
			frm.set_value("received_amount", frm.doc.paid_amount);
			frm.set_value("target_exchange_rate", frm.doc.source_exchange_rate);
			frm.set_value("base_received_amount", frm.doc.base_paid_amount);
		}
		
		frm.events.set_difference_amount(frm);
	},
	
	received_amount: function(frm) {
		frm.set_value("base_received_amount", 
			flt(frm.doc.received_amount) * flt(frm.doc.target_exchange_rate));
		frm.events.set_difference_amount(frm);
	},
	
	get_outstanding_documents: function(frm) {
		frm.events.check_mandatory_to_fetch(frm);
		var company_currency = frappe.get_doc(":Company", frm.doc.company).default_currency;
		
		frm.clear_table("references");

		return  frappe.call({
			method: 'erpnext.accounts.doctype.payment_entry.payment_entry.get_outstanding_reference_documents',
			args: {
				args: {
					"company": frm.doc.company,
					"party_type": frm.doc.party_type,
					"payment_type": frm.doc.payment_type,
					"party": frm.doc.party,
					"party_account": frm.doc.payment_type=="Receive" ? frm.doc.paid_from : frm.doc.paid_to
				}
			},
			callback: function(r, rt) {
				if(r.message) {
					$.each(r.message, function(i, d) {
						var c = frm.add_child("references");
						c.reference_doctype = d.voucher_type;
						c.reference_name = d.voucher_no;
						c.total_amount = d.invoice_amount;
						c.outstanding_amount = d.outstanding_amount;

						if(frm.doc.party_account_currency != company_currency) {
							c.exchange_rate = d.exchange_rate;
						} else {
							c.exchange_rate = 1;
						}
						
						if (in_list(['Sales Invoice', 'Purchase Invoice'], d.reference_doctype)){
							c.due_date = d.due_date
						}
					});
				}
				frm.events.set_total_allocated_amount(frm);
				frm.refresh_fields()
			}
		});
	},
	
	set_total_allocated_amount: function(frm) {
		var total_allocated_amount = base_total_allocated_amount = 0.0;
		$.each(frm.doc.references || [], function(i, row) {
			if (row.allocated_amount) {
				if (flt(row.allocated_amount) <= row.outstanding_amount) {
					total_allocated_amount += flt(row.allocated_amount);
					base_total_allocated_amount += flt(flt(row.allocated_amount)*flt(row.exchange_rate), 
						precision("base_paid_amount"));
				} else {
					if(flt(row.allocated_amount) < 0)
						frappe.throw(__("Row {0}: Allocated amount can not be negative", [row.idx]));
					else if(flt(row.allocated_amount) > flt(row.outstanding_amount))
						frappe.throw(__("Row {0}: Allocated Amount cannot be greater than Outstanding Amount",
							 [__(row.idx)]));
				
					frappe.model.set_value(row.doctype, row.name, "allocated_amount", 0.0);
				}
			}
		});
		frm.set_value("total_allocated_amount", total_allocated_amount);
		frm.set_value("base_total_allocated_amount", base_total_allocated_amount);
					
		frm.events.set_difference_amount(frm);
	},
	
	set_difference_amount: function(frm) {
		var unallocated_amount = 0;
		var party_amount = frm.doc.payment_type=="Receive" ? frm.doc.paid_amount : frm.doc.received_amount;
		
		if(frm.doc.total_allocated_amount < party_amount)
			unallocated_amount = party_amount - frm.doc.total_allocated_amount;
		
		frm.set_value("unallocated_amount", unallocated_amount)
		
		var difference_amount = 0;
		var base_unallocated_amount = flt(frm.doc.unallocated_amount) *	
			(frm.doc.payment_type=="Receive" ? frm.doc.source_exchange_rate : frm.doc.target_exchange_rate);
			
		var base_party_amount = flt(frm.doc.base_total_allocated_amount) + base_unallocated_amount;
		
		if(frm.doc.payment_type == "Receive") {
			difference_amount = base_party_amount - flt(frm.doc.base_received_amount);
		} else if (frm.doc.payment_type == "Pay") {
			difference_amount = flt(frm.doc.base_paid_amount) - base_party_amount;
		} else {
			difference_amount = flt(frm.doc.base_paid_amount) - flt(frm.doc.base_received_amount);
		}
		
		$.each(frm.doc.deductions || [], function(i, d) {
			if(d.amount) difference_amount -= flt(d.amount);
		})
		
		frm.set_value("difference_amount", difference_amount);
		
		frm.toggle_display("write_off_difference_amount", 
			(frm.doc.difference_amount && frm.doc.total_allocated_amount > party_amount));
	},
	
	check_mandatory_to_fetch: function(frm) {
		$.each(["Company", "Party Type", "Party", "payment_type"], function(i, field) {
			if(!frm.doc[frappe.model.scrub(field)]) frappe.throw(__("Please select {0} first", [field]));
		});
	},
		
	validate_reference_document: function(frm, row) {
		var _validate = function(i, row) {
			if (!row.reference_doctype) {
				return;
			}

			if(frm.doc.party_type=="Customer"
				&& !in_list(["Sales Order", "Sales Invoice", "Journal Entry"], row.reference_doctype)) {
					frappe.model.set_value(row.doctype, row.name, "reference_doctype", null);
					frappe.msgprint(__("Row #{0}: Reference Document Type must be one of Sales Order, Sales Invoice or Journal Entry", [row.idx]));
					return false;
				}

			if(frm.doc.party_type=="Supplier" && !in_list(["Purchase Order", 
				"Purchase Invoice", "Journal Entry"], row.reference_doctype)) {
					frappe.model.set_value(row.doctype, row.name, "against_voucher_type", null);
					frappe.msgprint(__("Row #{0}: Reference Document Type must be one of Purchase Order, Purchase Invoice or Journal Entry", [row.idx]));
					return false;
				}

		}

		if (row) {
			_validate(0, row);
		} else {
			$.each(frm.doc.vouchers || [], _validate);
		}
	},
	
	write_off_difference_amount: function(frm) {
		if(frm.doc.difference_amount) {
			frappe.call({
				method: "erpnext.accounts.doctype.payment_entry.payment_entry.get_write_off_account_and_cost_center",
				args: {
					company: frm.doc.company
				},
				callback: function(r, rt) {
					if(r.message) {
						var write_off_row = $.map(frm.doc["deductions"] || [], function(t) { 
							return t.account==r.message["write_off_account"] ? t : null; });
						
						if (!write_off_row.length) {
							var row = frm.add_child("deductions");
							row.account = r.message["write_off_account"];
							row.cost_center = r.message["cost_center"];
						} else {
							var row = write_off_row[0];
						}
						
						row.amount = flt(row.amount) + flt(frm.doc.difference_amount);
						refresh_field("deductions");
						
						frm.events.set_difference_amount(frm);
					}
				}
			})
		}
	}
});


frappe.ui.form.on('Payment Entry Reference', {
	reference_doctype: function(frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		frm.events.validate_reference_document(frm, row);
	},
	
	allocated_amount: function(frm) {
		frm.events.set_total_allocated_amount(frm);
	},
	
	references_remove: function(frm) {
		frm.events.set_total_allocated_amount(frm);
	}
})

frappe.ui.form.on('Payment Entry Deduction', {
	amount: function(frm) {
		frm.events.set_difference_amount(frm);
	},
	
	deductions_remove: function(frm) {
		frm.events.set_difference_amount(frm);
	}
})