// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.cscript.tname = "Sales Invoice Item";
cur_frm.cscript.fname = "entries";
cur_frm.cscript.other_fname = "other_charges";
cur_frm.cscript.sales_team_fname = "sales_team";

// print heading
cur_frm.pformat.print_heading = 'Invoice';

wn.require('app/accounts/doctype/sales_taxes_and_charges_master/sales_taxes_and_charges_master.js');
wn.require('app/utilities/doctype/sms_control/sms_control.js');
wn.require('app/selling/sales_common.js');
wn.require('app/accounts/doctype/sales_invoice/pos.js');

wn.provide("erpnext.accounts");
erpnext.accounts.SalesInvoiceController = erpnext.selling.SellingController.extend({
	onload: function() {
		this._super();

		if(!this.frm.doc.__islocal && !this.frm.doc.customer && this.frm.doc.debit_to) {
			// show debit_to in print format
			this.frm.set_df_property("debit_to", "print_hide", 0);
		}
		
		// toggle to pos view if is_pos is 1 in user_defaults
		if ((cint(wn.defaults.get_user_defaults("is_pos"))===1 || cur_frm.doc.is_pos)) {
			if(this.frm.doc.__islocal && !this.frm.doc.amended_from && !this.frm.doc.customer) {
				this.frm.set_value("is_pos", 1);
				this.is_pos(function() {
					if (cint(wn.defaults.get_user_defaults("fs_pos_view"))===1)
						cur_frm.cscript.toggle_pos(true);
				});
			}
		}
		
		// if document is POS then change default print format to "POS Invoice"
		if(cur_frm.doc.is_pos && cur_frm.doc.docstatus===1) {
			locals.DocType[cur_frm.doctype].default_print_format = "POS Invoice";
			cur_frm.setup_print();
		}
	},
	
	refresh: function(doc, dt, dn) {
		this._super();

		cur_frm.cscript.is_opening(doc, dt, dn);
		cur_frm.dashboard.reset();

		if(doc.docstatus==1) {
			cur_frm.appframe.add_button('View Ledger', function() {
				wn.route_options = {
					"voucher_no": doc.name,
					"from_date": doc.posting_date,
					"to_date": doc.posting_date,
				};
				wn.set_route("general-ledger");
			}, "icon-table");
			
			var percent_paid = cint(flt(doc.grand_total - doc.outstanding_amount) / flt(doc.grand_total) * 100);
			cur_frm.dashboard.add_progress(percent_paid + "% Paid", percent_paid);

			cur_frm.appframe.add_button(wn._('Send SMS'), cur_frm.cscript.send_sms, 'icon-mobile-phone');

			if(cint(doc.update_stock)!=1) {
				// show Make Delivery Note button only if Sales Invoice is not created from Delivery Note
				var from_delivery_note = false;
				from_delivery_note = cur_frm.get_doclist({parentfield: "entries"})
					.some(function(item) { 
						return item.delivery_note ? true : false; 
					});
				
				if(!from_delivery_note)
					cur_frm.appframe.add_primary_action(wn._('Make Delivery'), cur_frm.cscript['Make Delivery Note'])
			}

			if(doc.outstanding_amount!=0)
				cur_frm.appframe.add_primary_action(wn._('Make Payment Entry'), cur_frm.cscript.make_bank_voucher);
		}

		// Show buttons only when pos view is active
		if (doc.docstatus===0 && !this.pos_active) {
			cur_frm.cscript.sales_order_btn();
			cur_frm.cscript.delivery_note_btn();
		}
	},

	sales_order_btn: function() {
		this.$sales_order_btn = cur_frm.appframe.add_primary_action(wn._('From Sales Order'), 
			function() {
				wn.model.map_current_doc({
					method: "selling.doctype.sales_order.sales_order.make_sales_invoice",
					source_doctype: "Sales Order",
					get_query_filters: {
						docstatus: 1,
						status: ["!=", "Stopped"],
						per_billed: ["<", 99.99],
						customer: cur_frm.doc.customer || undefined,
						company: cur_frm.doc.company
					}
				})
			});
	},

	delivery_note_btn: function() {
		this.$delivery_note_btn = cur_frm.appframe.add_primary_action(wn._('From Delivery Note'), 
			function() {
				wn.model.map_current_doc({
					method: "stock.doctype.delivery_note.delivery_note.make_sales_invoice",
					source_doctype: "Delivery Note",
					get_query: function() {
						var filters = {
							company: cur_frm.doc.company
						};
						if(cur_frm.doc.customer) filters["customer"] = cur_frm.doc.customer;
						return {
							query: "controllers.queries.get_delivery_notes_to_be_billed",
							filters: filters
						};
					}
				});
			});
	},
	
	tc_name: function() {
		this.get_terms();
	},
	
	is_pos: function(callback_fn) {
		cur_frm.cscript.hide_fields(this.frm.doc);
		if(cint(this.frm.doc.is_pos)) {
			if(!this.frm.doc.company) {
				this.frm.set_value("is_pos", 0);
				msgprint(wn._("Please specify Company to proceed"));
			} else {
				var me = this;
				return this.frm.call({
					doc: me.frm.doc,
					method: "set_missing_values",
					callback: function(r) {
						if(!r.exc) {
							me.frm.script_manager.trigger("update_stock");
							me.set_default_values();
							me.set_dynamic_labels();
							me.calculate_taxes_and_totals();

							if(callback_fn) callback_fn()
						}
					}
				});
			}
		}
	},
	
	debit_to: function() {
		this.customer();
	},
	
	allocated_amount: function() {
		this.calculate_total_advance("Sales Invoice", "advance_adjustment_details");
		this.frm.refresh_fields();
	},
	
	write_off_outstanding_amount_automatically: function() {
		if(cint(this.frm.doc.write_off_outstanding_amount_automatically)) {
			wn.model.round_floats_in(this.frm.doc, ["grand_total", "paid_amount"]);
			// this will make outstanding amount 0
			this.frm.set_value("write_off_amount", 
				flt(this.frm.doc.grand_total - this.frm.doc.paid_amount), precision("write_off_amount"));
		}
		
		this.frm.script_manager.trigger("write_off_amount");
	},
	
	write_off_amount: function() {
		this.calculate_outstanding_amount();
		this.frm.refresh_fields();
	},
	
	paid_amount: function() {
		this.write_off_outstanding_amount_automatically();
	},
	
	entries_add: function(doc, cdt, cdn) {
		var row = wn.model.get_doc(cdt, cdn);
		this.frm.script_manager.copy_from_first_row("entries", row, ["income_account", "cost_center"]);
	},
	
	set_dynamic_labels: function() {
		this._super();
		this.hide_fields(this.frm.doc);
	},

	entries_on_form_rendered: function(doc, grid_row) {
		erpnext.setup_serial_no(grid_row)
	}

});

// for backward compatibility: combine new and previous states
$.extend(cur_frm.cscript, new erpnext.accounts.SalesInvoiceController({frm: cur_frm}));

// Hide Fields
// ------------
cur_frm.cscript.hide_fields = function(doc) {
	par_flds = ['project_name', 'due_date', 'is_opening', 'source', 'total_advance', 'gross_profit',
	'gross_profit_percent', 'get_advances_received',
	'advance_adjustment_details', 'sales_partner', 'commission_rate',
	'total_commission', 'advances'];
	
	item_flds_normal = ['sales_order', 'delivery_note']
	
	if(cint(doc.is_pos) == 1) {
		hide_field(par_flds);
		unhide_field('payments_section');
		cur_frm.fields_dict['entries'].grid.set_column_disp(item_flds_normal, false);
	} else {
		hide_field('payments_section');
		for (i in par_flds) {
			var docfield = wn.meta.docfield_map[doc.doctype][par_flds[i]];
			if(!docfield.hidden) unhide_field(par_flds[i]);
		}
		cur_frm.fields_dict['entries'].grid.set_column_disp(item_flds_normal, true);
	}
	
	item_flds_stock = ['serial_no', 'batch_no', 'actual_qty', 'expense_account', 'warehouse']
	cur_frm.fields_dict['entries'].grid.set_column_disp(item_flds_stock,
		(cint(doc.update_stock)==1 ? true : false));
	
	// India related fields
	var cp = wn.control_panel;
	if (cp.country == 'India') unhide_field(['c_form_applicable', 'c_form_no']);
	else hide_field(['c_form_applicable', 'c_form_no']);
	
	cur_frm.refresh_fields();
}


cur_frm.cscript.mode_of_payment = function(doc) {
	return cur_frm.call({
		method: "get_bank_cash_account",
		args: { mode_of_payment: doc.mode_of_payment }
	});
}

cur_frm.cscript.update_stock = function(doc, dt, dn) {
	cur_frm.cscript.hide_fields(doc, dt, dn);
}

cur_frm.cscript.is_opening = function(doc, dt, dn) {
	hide_field('aging_date');
	if (doc.is_opening == 'Yes') unhide_field('aging_date');
}

//Make Delivery Note Button
//-----------------------------

cur_frm.cscript['Make Delivery Note'] = function() {
	wn.model.open_mapped_doc({
		method: "accounts.doctype.sales_invoice.sales_invoice.make_delivery_note",
		source_name: cur_frm.doc.name
	})
}

cur_frm.cscript.make_bank_voucher = function() {
	return wn.call({
		method: "accounts.doctype.journal_voucher.journal_voucher.get_payment_entry_from_sales_invoice",
		args: {
			"sales_invoice": cur_frm.doc.name
		},
		callback: function(r) {
			var doclist = wn.model.sync(r.message);
			wn.set_route("Form", doclist[0].doctype, doclist[0].name);
		}
	});
}

cur_frm.fields_dict.debit_to.get_query = function(doc) {
	return{
		filters: {
			'debit_or_credit': 'Debit',
			'is_pl_account': 'No',
			'group_or_ledger': 'Ledger',
			'company': doc.company
		}
	}
}

cur_frm.fields_dict.cash_bank_account.get_query = function(doc) {
	return{
		filters: {
			'debit_or_credit': 'Debit',
			'is_pl_account': 'No',
			'group_or_ledger': 'Ledger',
			'company': doc.company
		}
	}	
}

cur_frm.fields_dict.write_off_account.get_query = function(doc) {
	return{
		filters:{
			'debit_or_credit': 'Debit',
			'is_pl_account': 'Yes',
			'group_or_ledger': 'Ledger',
			'company': doc.company
		}
	}
}

// Write off cost center
//-----------------------
cur_frm.fields_dict.write_off_cost_center.get_query = function(doc) {
	return{
		filters:{
			'group_or_ledger': 'Ledger',
			'company': doc.company
		}
	}	
}

//project name
//--------------------------
cur_frm.fields_dict['project_name'].get_query = function(doc, cdt, cdn) {
	return{
		query: "controllers.queries.get_project_name",
		filters: {'customer': doc.customer}
	}	
}

// Income Account in Details Table
// --------------------------------
cur_frm.set_query("income_account", "entries", function(doc) {
	return{
		query: "accounts.doctype.sales_invoice.sales_invoice.get_income_account",
		filters: {'company': doc.company}
	}
});

// expense account
if (sys_defaults.auto_accounting_for_stock) {
	cur_frm.fields_dict['entries'].grid.get_field('expense_account').get_query = function(doc) {
		return {
			filters: {
				'is_pl_account': 'Yes',
				'debit_or_credit': 'Debit',
				'company': doc.company,
				'group_or_ledger': 'Ledger'
			}
		}
	}
}

// warehouse in detail table
//----------------------------
cur_frm.fields_dict['entries'].grid.get_field('warehouse').get_query = function(doc, cdt, cdn) {
	var d = locals[cdt][cdn];
	return{
		filters:[
			['Bin', 'item_code', '=', d.item_code],
			['Bin', 'actual_qty', '>', 0]
		]
	}	
}

// Cost Center in Details Table
// -----------------------------
cur_frm.fields_dict["entries"].grid.get_field("cost_center").get_query = function(doc) {
	return {
		filters: { 
			'company': doc.company,
			'group_or_ledger': 'Ledger'
		}	
	}
}

cur_frm.cscript.income_account = function(doc, cdt, cdn) {
	cur_frm.cscript.copy_account_in_all_row(doc, cdt, cdn, "income_account");
}

cur_frm.cscript.expense_account = function(doc, cdt, cdn) {
	cur_frm.cscript.copy_account_in_all_row(doc, cdt, cdn, "expense_account");
}

cur_frm.cscript.cost_center = function(doc, cdt, cdn) {
	cur_frm.cscript.copy_account_in_all_row(doc, cdt, cdn, "cost_center");
}

cur_frm.cscript.on_submit = function(doc, cdt, cdn) {
	if(cint(wn.boot.notification_settings.sales_invoice)) {
		cur_frm.email_doc(wn.boot.notification_settings.sales_invoice_message);
	}
}

cur_frm.cscript.convert_into_recurring_invoice = function(doc, dt, dn) {
	// set default values for recurring invoices
	if(doc.convert_into_recurring_invoice) {
		var owner_email = doc.owner=="Administrator"
			? wn.user_info("Administrator").email
			: doc.owner;
		
		doc.notification_email_address = $.map([cstr(owner_email),
			cstr(doc.contact_email)], function(v) { return v || null; }).join(", ");
		doc.repeat_on_day_of_month = wn.datetime.str_to_obj(doc.posting_date).getDate();
	}
		
	refresh_many(["notification_email_address", "repeat_on_day_of_month"]);
}

cur_frm.cscript.invoice_period_from_date = function(doc, dt, dn) {
	// set invoice_period_to_date
	if(doc.invoice_period_from_date) {
		var recurring_type_map = {'Monthly': 1, 'Quarterly': 3, 'Half-yearly': 6,
			'Yearly': 12};

		var months = recurring_type_map[doc.recurring_type];
		if(months) {
			var to_date = wn.datetime.add_months(doc.invoice_period_from_date,
				months);
			doc.invoice_period_to_date = wn.datetime.add_days(to_date, -1);
			refresh_field('invoice_period_to_date');
		}
	}
}
