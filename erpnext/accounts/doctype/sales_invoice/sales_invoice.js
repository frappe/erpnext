// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

// print heading
cur_frm.pformat.print_heading = 'Invoice';

{% include 'selling/sales_common.js' %};

frappe.provide("erpnext.accounts");
erpnext.accounts.SalesInvoiceController = erpnext.selling.SellingController.extend({
	onload: function() {
		var me = this;
		this._super();

		if(!this.frm.doc.__islocal && !this.frm.doc.customer && this.frm.doc.debit_to) {
			// show debit_to in print format
			this.frm.set_df_property("debit_to", "print_hide", 0);
		}

		// toggle to pos view if is_pos is 1 in user_defaults
		if ((is_null(this.frm.doc.is_pos) && cint(frappe.defaults.get_user_default("is_pos"))===1) || this.frm.doc.is_pos) {
			if(this.frm.doc.__islocal && !this.frm.doc.amended_from && !this.frm.doc.customer) {
				this.frm.set_value("is_pos", 1);
				this.is_pos(function() {
					if (cint(frappe.defaults.get_user_defaults("fs_pos_view"))===1)
						erpnext.pos.toggle(me.frm, true);
				});
			}
		}

		// if document is POS then change default print format to "POS Invoice" if no default is specified
		if(cur_frm.doc.is_pos && cur_frm.doc.docstatus===1 && cint(frappe.defaults.get_user_defaults("fs_pos_view"))===1
			&& !locals.DocType[cur_frm.doctype].default_print_format) {
			locals.DocType[cur_frm.doctype].default_print_format = "POS Invoice";
			cur_frm.setup_print_layout();
		}
	},

	refresh: function(doc, dt, dn) {
		this._super();

		cur_frm.dashboard.reset();
		
		this.frm.toggle_reqd("due_date", !this.frm.doc.is_return);
		
		if(doc.docstatus==1) {
			cur_frm.add_custom_button('View Ledger', function() {
				frappe.route_options = {
					"voucher_no": doc.name,
					"from_date": doc.posting_date,
					"to_date": doc.posting_date,
					"company": doc.company,
					group_by_voucher: 0
				};
				frappe.set_route("query-report", "General Ledger");
			});

			if(cint(doc.update_stock)!=1) {
				// show Make Delivery Note button only if Sales Invoice is not created from Delivery Note
				var from_delivery_note = false;
				from_delivery_note = cur_frm.doc.items
					.some(function(item) {
						return item.delivery_note ? true : false;
					});

				if(!from_delivery_note) {
					cur_frm.add_custom_button(__('Make Delivery'), cur_frm.cscript['Make Delivery Note'])
				}
			}

			if(doc.outstanding_amount!=0 && !cint(doc.is_return)) {
				cur_frm.add_custom_button(__('Make Payment Entry'), cur_frm.cscript.make_bank_entry);
			}
			
			cur_frm.add_custom_button(__('Make Sales Return'), this.make_sales_return);
		}

		// Show buttons only when pos view is active
		if (cint(doc.docstatus==0) && cur_frm.page.current_view_name!=="pos") {
			cur_frm.cscript.sales_order_btn();
			cur_frm.cscript.delivery_note_btn();
		}
	},

	sales_order_btn: function() {
		this.$sales_order_btn = cur_frm.add_custom_button(__('From Sales Order'),
			function() {
				frappe.model.map_current_doc({
					method: "erpnext.selling.doctype.sales_order.sales_order.make_sales_invoice",
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
		this.$delivery_note_btn = cur_frm.add_custom_button(__('From Delivery Note'),
			function() {
				frappe.model.map_current_doc({
					method: "erpnext.stock.doctype.delivery_note.delivery_note.make_sales_invoice",
					source_doctype: "Delivery Note",
					get_query: function() {
						var filters = {
							company: cur_frm.doc.company
						};
						if(cur_frm.doc.customer) filters["customer"] = cur_frm.doc.customer;
						return {
							query: "erpnext.controllers.queries.get_delivery_notes_to_be_billed",
							filters: filters
						};
					}
				});
			});
	},

	tc_name: function() {
		this.get_terms();
	},

	is_pos: function(doc, dt, dn, callback_fn) {
		cur_frm.cscript.hide_fields(this.frm.doc);
		if(cint(this.frm.doc.is_pos)) {
			if(!this.frm.doc.company) {
				this.frm.set_value("is_pos", 0);
				msgprint(__("Please specify Company to proceed"));
			} else {
				var me = this;
				return this.frm.call({
					doc: me.frm.doc,
					method: "set_missing_values",
					callback: function(r) {
						if(!r.exc) {
							me.frm.script_manager.trigger("update_stock");
							frappe.model.set_default_values(me.frm.doc);
							me.set_dynamic_labels();
							me.calculate_taxes_and_totals();
							if(callback_fn) callback_fn();
						}
					}
				});
			}
		}
	},

	customer: function() {
		var me = this;
		if(this.frm.updating_party_details) return;

		erpnext.utils.get_party_details(this.frm,
			"erpnext.accounts.party.get_party_details", {
				posting_date: this.frm.doc.posting_date,
				party: this.frm.doc.customer,
				party_type: "Customer",
				account: this.frm.doc.debit_to,
				price_list: this.frm.doc.selling_price_list,
			}, function() {
			me.apply_pricing_rule();
		})
	},

	allocated_amount: function() {
		this.calculate_total_advance();
		this.frm.refresh_fields();
	},

	write_off_outstanding_amount_automatically: function() {
		if(cint(this.frm.doc.write_off_outstanding_amount_automatically)) {
			frappe.model.round_floats_in(this.frm.doc, ["base_grand_total", "paid_amount"]);
			// this will make outstanding amount 0
			this.frm.set_value("write_off_amount",
				flt(this.frm.doc.base_grand_total - this.frm.doc.paid_amount - this.frm.doc.total_advance, precision("write_off_amount"))
			);
			this.frm.toggle_enable("write_off_amount", false);

		} else {
			this.frm.toggle_enable("write_off_amount", true);
		}

		this.calculate_outstanding_amount(false);
		this.frm.refresh_fields();
	},

	write_off_amount: function() {
		this.write_off_outstanding_amount_automatically();
	},

	paid_amount: function() {
		this.write_off_outstanding_amount_automatically();
	},

	items_add: function(doc, cdt, cdn) {
		var row = frappe.get_doc(cdt, cdn);
		this.frm.script_manager.copy_from_first_row("items", row, ["income_account", "cost_center"]);
	},

	set_dynamic_labels: function() {
		this._super();
		this.hide_fields(this.frm.doc);
	},

	items_on_form_rendered: function() {
		erpnext.setup_serial_no();
	},
	
	make_sales_return: function() {
		frappe.model.open_mapped_doc({
			method: "erpnext.accounts.doctype.sales_invoice.sales_invoice.make_sales_return",
			frm: cur_frm
		})
	}
});

// for backward compatibility: combine new and previous states
$.extend(cur_frm.cscript, new erpnext.accounts.SalesInvoiceController({frm: cur_frm}));

// Hide Fields
// ------------
cur_frm.cscript.hide_fields = function(doc) {
	par_flds = ['project_name', 'due_date', 'is_opening', 'source', 'total_advance', 'get_advances_received',
		'advances', 'sales_partner', 'commission_rate', 'total_commission', 'advances', 'from_date', 'to_date'];

	if(cint(doc.is_pos) == 1) {
		hide_field(par_flds);
	} else {
		for (i in par_flds) {
			var docfield = frappe.meta.docfield_map[doc.doctype][par_flds[i]];
			if(!docfield.hidden) unhide_field(par_flds[i]);
		}
	}

	item_flds_stock = ['serial_no', 'batch_no', 'actual_qty', 'expense_account', 'warehouse', 'expense_account', 'warehouse']
	cur_frm.fields_dict['items'].grid.set_column_disp(item_flds_stock,
		(cint(doc.update_stock)==1 ? true : false));

	// India related fields
	if (frappe.boot.sysdefaults.country == 'India') unhide_field(['c_form_applicable', 'c_form_no']);
	else hide_field(['c_form_applicable', 'c_form_no']);

	this.frm.toggle_enable("write_off_amount", !!!cint(doc.write_off_outstanding_amount_automatically));

	cur_frm.refresh_fields();
}


cur_frm.cscript.mode_of_payment = function(doc) {
	if(doc.is_pos) {
		return cur_frm.call({
			method: "erpnext.accounts.doctype.sales_invoice.sales_invoice.get_bank_cash_account",
			args: {
				"mode_of_payment": doc.mode_of_payment,
				"company": doc.company
			 },
			 callback: function(r, rt) {
				if(r.message) {
					cur_frm.set_value("cash_bank_account", r.message["account"]);
				}

			 }
		});
	 }
}

cur_frm.cscript.update_stock = function(doc, dt, dn) {
	cur_frm.cscript.hide_fields(doc, dt, dn);
}

cur_frm.cscript['Make Delivery Note'] = function() {
	frappe.model.open_mapped_doc({
		method: "erpnext.accounts.doctype.sales_invoice.sales_invoice.make_delivery_note",
		frm: cur_frm
	})
}

cur_frm.cscript.make_bank_entry = function() {
	return frappe.call({
		method: "erpnext.accounts.doctype.journal_entry.journal_entry.get_payment_entry_from_sales_invoice",
		args: {
			"sales_invoice": cur_frm.doc.name
		},
		callback: function(r) {
			var doclist = frappe.model.sync(r.message);
			frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
		}
	});
}

cur_frm.fields_dict.cash_bank_account.get_query = function(doc) {
	return {
		filters: [
			["Account", "account_type", "in", ["Cash", "Bank"]],
			["Account", "root_type", "=", "Asset"],
			["Account", "is_group", "=",0],
			["Account", "company", "=", doc.company]
		]
	}
}

cur_frm.fields_dict.write_off_account.get_query = function(doc) {
	return{
		filters:{
			'report_type': 'Profit and Loss',
			'is_group': 0,
			'company': doc.company
		}
	}
}

// Write off cost center
//-----------------------
cur_frm.fields_dict.write_off_cost_center.get_query = function(doc) {
	return{
		filters:{
			'is_group': 0,
			'company': doc.company
		}
	}
}

//project name
//--------------------------
cur_frm.fields_dict['project_name'].get_query = function(doc, cdt, cdn) {
	return{
		query: "erpnext.controllers.queries.get_project_name",
		filters: {'customer': doc.customer}
	}
}

// Income Account in Details Table
// --------------------------------
cur_frm.set_query("income_account", "items", function(doc) {
	return{
		query: "erpnext.accounts.doctype.sales_invoice.sales_invoice.get_income_account",
		filters: {'company': doc.company}
	}
});

// expense account
if (sys_defaults.auto_accounting_for_stock) {
	cur_frm.fields_dict['items'].grid.get_field('expense_account').get_query = function(doc) {
		return {
			filters: {
				'report_type': 'Profit and Loss',
				'company': doc.company,
				"is_group": 0
			}
		}
	}
}


// Cost Center in Details Table
// -----------------------------
cur_frm.fields_dict["items"].grid.get_field("cost_center").get_query = function(doc) {
	return {
		filters: {
			'company': doc.company,
			"is_group": 0
		}
	}
}

cur_frm.cscript.income_account = function(doc, cdt, cdn) {
	erpnext.utils.copy_value_in_all_row(doc, cdt, cdn, "items", "income_account");
}

cur_frm.cscript.expense_account = function(doc, cdt, cdn) {
	erpnext.utils.copy_value_in_all_row(doc, cdt, cdn, "items", "expense_account");
}

cur_frm.cscript.cost_center = function(doc, cdt, cdn) {
	erpnext.utils.copy_value_in_all_row(doc, cdt, cdn, "items", "cost_center");
}

cur_frm.cscript.on_submit = function(doc, cdt, cdn) {
	$.each(doc["items"], function(i, row) {
		if(row.delivery_note) frappe.model.clear_doc("Delivery Note", row.delivery_note)
	})

	if(cint(frappe.boot.notification_settings.sales_invoice)) {
		cur_frm.email_doc(frappe.boot.notification_settings.sales_invoice_message);
	} else if(cur_frm.doc.is_pos) {
		new_doc("Sales Invoice");
	}
}

cur_frm.set_query("debit_to", function(doc) {
	return{
		filters: [
			['Account', 'root_type', '=', 'Asset'],
			['Account', 'account_type', '=', 'Receivable']
		]
	}
});