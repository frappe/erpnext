// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.accounts");
{% include 'erpnext/public/js/controllers/buying.js' %};

erpnext.accounts.PurchaseInvoice = erpnext.buying.BuyingController.extend({
	setup: function(doc) {
		this.setup_posting_date_time_check();
		this._super(doc);

		// formatter for material request item
		this.frm.set_indicator_formatter('item_code',
			function(doc) { return (doc.qty<=doc.received_qty) ? "green" : "orange" })
	},
	onload: function() {
		this._super();

		if(!this.frm.doc.__islocal) {
			// show credit_to in print format
			if(!this.frm.doc.supplier && this.frm.doc.credit_to) {
				this.frm.set_df_property("credit_to", "print_hide", 0);
			}
		}
	},

	refresh: function(doc) {
		const me = this;
		this._super();

		hide_fields(this.frm.doc);
		// Show / Hide button
		this.show_general_ledger();

		if(doc.update_stock==1 && doc.docstatus==1) {
			this.show_stock_ledger();
		}

		if(!doc.is_return && doc.docstatus == 1 && doc.outstanding_amount != 0){
			if(doc.on_hold) {
				this.frm.add_custom_button(
					__('Change Release Date'),
					function() {me.change_release_date()},
					__('Hold Invoice')
				);
				this.frm.add_custom_button(
					__('Unblock Invoice'),
					function() {me.unblock_invoice()},
					__('Make')
				);
			} else if (!doc.on_hold) {
				this.frm.add_custom_button(
					__('Block Invoice'),
					function() {me.block_invoice()},
					__('Make')
				);
			}
		}

		if(doc.docstatus == 1 && doc.outstanding_amount != 0
			&& !(doc.is_return && doc.return_against)) {
			this.frm.add_custom_button(__('Payment'), this.make_payment_entry, __("Make"));
			cur_frm.page.set_inner_btn_group_as_primary(__("Make"));
		}

		if(!doc.is_return && doc.docstatus==1) {
			if(doc.outstanding_amount >= 0 || Math.abs(flt(doc.outstanding_amount)) < flt(doc.grand_total)) {
				cur_frm.add_custom_button(__('Return / Debit Note'),
					this.make_debit_note, __("Make"));
			}

			if(!doc.auto_repeat) {
				cur_frm.add_custom_button(__('Subscription'), function() {
					erpnext.utils.make_subscription(doc.doctype, doc.name)
				}, __("Make"))
			}
		}

		if (doc.outstanding_amount > 0 && !cint(doc.is_return)) {
			cur_frm.add_custom_button(__('Payment Request'),
				this.make_payment_request, __("Make"));
		}

		if(doc.docstatus===0) {
			this.frm.add_custom_button(__('Purchase Order'), function() {
				erpnext.utils.map_current_doc({
					method: "erpnext.buying.doctype.purchase_order.purchase_order.make_purchase_invoice",
					source_doctype: "Purchase Order",
					target: me.frm,
					setters: {
						supplier: me.frm.doc.supplier || undefined,
					},
					get_query_filters: {
						docstatus: 1,
						status: ["!=", "Closed"],
						per_billed: ["<", 99.99],
						company: me.frm.doc.company
					}
				})
			}, __("Get items from"));

			this.frm.add_custom_button(__('Purchase Receipt'), function() {
				erpnext.utils.map_current_doc({
					method: "erpnext.stock.doctype.purchase_receipt.purchase_receipt.make_purchase_invoice",
					source_doctype: "Purchase Receipt",
					target: me.frm,
					date_field: "posting_date",
					setters: {
						supplier: me.frm.doc.supplier || undefined,
					},
					get_query_filters: {
						docstatus: 1,
						status: ["not in", ["Closed", "Completed"]],
						company: me.frm.doc.company,
						is_return: 0
					}
				})
			}, __("Get items from"));
		}
		this.frm.toggle_reqd("supplier_warehouse", this.frm.doc.is_subcontracted==="Yes");

		if (doc.docstatus == 1 && !doc.inter_company_invoice_reference) {
			frappe.model.with_doc("Supplier", me.frm.doc.supplier, function() {
				var supplier = frappe.model.get_doc("Supplier", me.frm.doc.supplier);
				var internal = supplier.is_internal_supplier;
				var disabled = supplier.disabled;
				if (internal == 1 && disabled == 0) {
					me.frm.add_custom_button("Inter Company Invoice", function() {
						me.make_inter_company_invoice(me.frm);
					}, __("Make"));
				}
			});
		}

		// sales order
		if (doc.docstatus == 1 && !doc.is_return) {
			this.frm.add_custom_button(__('Sales Order'), function() { me.make_sales_order() }, __("Make"));
		}
	},

	unblock_invoice: function() {
		const me = this;
		frappe.call({
			'method': 'erpnext.accounts.doctype.purchase_invoice.purchase_invoice.unblock_invoice',
			'args': {'name': me.frm.doc.name},
			'callback': (r) => me.frm.reload_doc()
		});
	},

	block_invoice: function() {
		this.make_comment_dialog_and_block_invoice();
	},

	change_release_date: function() {
		this.make_dialog_and_set_release_date();
	},

	can_change_release_date: function(date) {
		const diff = frappe.datetime.get_diff(date, frappe.datetime.nowdate());
		if (diff < 0) {
			frappe.throw('New release date should be in the future');
			return false;
		} else {
			return true;
		}
	},

	make_sales_order: function(){
		var me = this;
		var dialog = new frappe.ui.Dialog({
			title: __("Customer"),
			fields: [
				{"fieldtype": "Link", "label": __("Customer"), "fieldname": "customer", "options":"Customer", "mandatory":true},
				{"fieldtype": "Button", "label": __("Make Sales Order"), "fieldname": "make_sales_order", "cssClass": "btn-primary"},
			]
		});

		dialog.fields_dict.make_sales_order.$input.click(function() {
			var args = dialog.get_values();
			dialog.hide();
			return frappe.call({
				type: "GET",
				method: "erpnext.accounts.doctype.purchase_invoice.purchase_invoice.make_sales_order",
				args: {
					"customer": args.customer,
					"source_name": me.frm.doc.name
				},
				freeze: true,
				callback: function(r) {
					if(!r.exc) {
						var doc = frappe.model.sync(r.message);
						frappe.set_route("Form", r.message.doctype, r.message.name);
					}
				}
			})
		});
		dialog.show();
	},

	make_comment_dialog_and_block_invoice: function(){
		const me = this;

		const title = __('Add Comment');
		const fields = [
			{
				fieldname: 'hold_comment',
				read_only: 0,
				fieldtype:'Small Text',
				label: __('Reason For Putting On Hold'),
				default: ""
			},
		];

		this.dialog = new frappe.ui.Dialog({
			title: title,
			fields: fields
		});

		this.dialog.set_primary_action(__('Save'), function() {
			const dialog_data = me.dialog.get_values();
			frappe.call({
				'method': 'erpnext.accounts.doctype.purchase_invoice.purchase_invoice.block_invoice',
				'args': {'name': me.frm.doc.name, 'hold_comment': dialog_data.hold_comment},
				'callback': (r) => me.frm.reload_doc()
			});
			me.dialog.hide();
		});

		this.dialog.show();
	},

	make_dialog_and_set_release_date: function() {
		const me = this;

		const title = __('Set New Release Date');
		const fields = [
			{
				fieldname: 'release_date',
				read_only: 0,
				fieldtype:'Date',
				label: __('Release Date'),
				default: me.frm.doc.release_date
			},
		];

		this.dialog = new frappe.ui.Dialog({
			title: title,
			fields: fields
		});

		this.dialog.set_primary_action(__('Save'), function() {
			me.dialog_data = me.dialog.get_values();
			if(me.can_change_release_date(me.dialog_data.release_date)) {
				me.dialog_data.name = me.frm.doc.name;
				me.set_release_date(me.dialog_data);
				me.dialog.hide();
			}
		});

		this.dialog.show();
	},

	set_release_date: function(data) {
		return frappe.call({
			'method': 'erpnext.accounts.doctype.purchase_invoice.purchase_invoice.change_release_date',
			'args': data,
			'callback': (r) => this.frm.reload_doc()
		});
	},

	supplier: function() {
		var me = this;
		if(this.frm.updating_party_details)
			return;
		erpnext.utils.get_party_details(this.frm, "erpnext.accounts.party.get_party_details",
			{
				posting_date: this.frm.doc.posting_date,
				bill_date: this.frm.doc.bill_date,
				party: this.frm.doc.supplier,
				party_type: "Supplier",
				account: this.frm.doc.credit_to,
				price_list: this.frm.doc.buying_price_list
			}, function() {
				me.apply_pricing_rule();

				me.frm.doc.apply_tds = me.frm.supplier_tds ? 1 : 0;
				me.frm.set_df_property("apply_tds", "read_only", me.frm.supplier_tds ? 0 : 1);
			})
	},

	credit_to: function() {
		var me = this;
		if(this.frm.doc.credit_to) {
			me.frm.call({
				method: "frappe.client.get_value",
				args: {
					doctype: "Account",
					fieldname: "account_currency",
					filters: { name: me.frm.doc.credit_to },
				},
				callback: function(r, rt) {
					if(r.message) {
						me.frm.set_value("party_account_currency", r.message.account_currency);
						me.set_dynamic_labels();
					}
				}
			});
		}
	},

	make_inter_company_invoice: function(frm) {
		frappe.model.open_mapped_doc({
			method: "erpnext.accounts.doctype.purchase_invoice.purchase_invoice.make_inter_company_sales_invoice",
			frm: frm
		});
	},

	is_paid: function() {
		hide_fields(this.frm.doc);
		if(cint(this.frm.doc.is_paid)) {
			if(!this.frm.doc.company) {
				this.frm.set_value("is_paid", 0)
				frappe.msgprint(__("Please specify Company to proceed"));
			}
		}
		this.calculate_outstanding_amount();
		this.frm.refresh_fields();
	},

	write_off_amount: function() {
		this.set_in_company_currency(this.frm.doc, ["write_off_amount"]);
		this.calculate_outstanding_amount();
		this.frm.refresh_fields();
	},

	paid_amount: function() {
		this.set_in_company_currency(this.frm.doc, ["paid_amount"]);
		this.write_off_amount();
		this.frm.refresh_fields();
	},

	allocated_amount: function() {
		this.calculate_total_advance();
		this.frm.refresh_fields();
	},

	items_add: function(doc, cdt, cdn) {
		var row = frappe.get_doc(cdt, cdn);
		this.frm.script_manager.copy_from_first_row("items", row,
			["expense_account", "cost_center", "project"]);
	},

	on_submit: function() {
		$.each(this.frm.doc["items"] || [], function(i, row) {
			if(row.purchase_receipt) frappe.model.clear_doc("Purchase Receipt", row.purchase_receipt)
		})
	},

	make_debit_note: function() {
		frappe.model.open_mapped_doc({
			method: "erpnext.accounts.doctype.purchase_invoice.purchase_invoice.make_debit_note",
			frm: cur_frm
		})
	},

	asset: function(frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		if(row.asset) {
			frappe.call({
				method: "erpnext.assets.doctype.asset_category.asset_category.get_asset_category_account",
				args: {
					"asset": row.asset,
					"fieldname": "fixed_asset_account",
					"account": row.expense_account
				},
				callback: function(r, rt) {
					frappe.model.set_value(cdt, cdn, "expense_account", r.message);
				}
			})
		}
	}
});

cur_frm.script_manager.make(erpnext.accounts.PurchaseInvoice);

// Hide Fields
// ------------
function hide_fields(doc) {
	var parent_fields = ['due_date', 'is_opening', 'advances_section', 'from_date', 'to_date'];

	if(cint(doc.is_paid) == 1) {
		hide_field(parent_fields);
	} else {
		for (var i in parent_fields) {
			var docfield = frappe.meta.docfield_map[doc.doctype][parent_fields[i]];
			if(!docfield.hidden) unhide_field(parent_fields[i]);
		}

	}

	var item_fields_stock = ['warehouse_section', 'received_qty', 'rejected_qty'];

	cur_frm.fields_dict['items'].grid.set_column_disp(item_fields_stock,
		(cint(doc.update_stock)==1 || cint(doc.is_return)==1 ? true : false));

	cur_frm.refresh_fields();
}

cur_frm.cscript.update_stock = function(doc, dt, dn) {
	hide_fields(doc, dt, dn);
	this.frm.fields_dict.items.grid.toggle_reqd("item_code", doc.update_stock? true: false)
}

cur_frm.fields_dict.cash_bank_account.get_query = function(doc) {
	return {
		filters: [
			["Account", "account_type", "in", ["Cash", "Bank"]],
			["Account", "is_group", "=",0],
			["Account", "company", "=", doc.company],
			["Account", "report_type", "=", "Balance Sheet"]
		]
	}
}

cur_frm.fields_dict['items'].grid.get_field("item_code").get_query = function(doc, cdt, cdn) {
	return {
		query: "erpnext.controllers.queries.item_query",
		filters: {'is_purchase_item': 1}
	}
}

cur_frm.fields_dict['credit_to'].get_query = function(doc) {
	// filter on Account
	if (doc.supplier) {
		return {
			filters: {
				'account_type': 'Payable',
				'is_group': 0,
				'company': doc.company
			}
		}
	} else {
		return {
			filters: {
				'report_type': 'Balance Sheet',
				'is_group': 0,
				'company': doc.company
			}
		}
	}
}

// Get Print Heading
cur_frm.fields_dict['select_print_heading'].get_query = function(doc, cdt, cdn) {
	return {
		filters:[
			['Print Heading', 'docstatus', '!=', 2]
		]
	}
}

cur_frm.set_query("expense_account", "items", function(doc) {
	return {
		query: "erpnext.controllers.queries.get_expense_account",
		filters: {'company': doc.company}
	}
});

cur_frm.set_query("asset", "items", function(doc, cdt, cdn) {
	var d = locals[cdt][cdn];
	return {
		filters: {
			'item_code': d.item_code,
			'docstatus': 1,
			'company': doc.company,
			'status': 'Submitted'
		}
	}
});

cur_frm.cscript.expense_account = function(doc, cdt, cdn){
	var d = locals[cdt][cdn];
	if(d.idx == 1 && d.expense_account){
		var cl = doc.items || [];
		for(var i = 0; i < cl.length; i++){
			if(!cl[i].expense_account) cl[i].expense_account = d.expense_account;
		}
	}
	refresh_field('items');
}

cur_frm.fields_dict["items"].grid.get_field("cost_center").get_query = function(doc) {
	return {
		filters: {
			'company': doc.company,
			'is_group': 0
		}

	}
}

cur_frm.cscript.cost_center = function(doc, cdt, cdn){
	var d = locals[cdt][cdn];
	if(d.idx == 1 && d.cost_center){
		var cl = doc.items || [];
		for(var i = 0; i < cl.length; i++){
			if(!cl[i].cost_center) cl[i].cost_center = d.cost_center;
		}
	}
	refresh_field('items');
}

cur_frm.fields_dict['items'].grid.get_field('project').get_query = function(doc, cdt, cdn) {
	return{
		filters:[
			['Project', 'status', 'not in', 'Completed, Cancelled']
		]
	}
}

cur_frm.cscript.select_print_heading = function(doc,cdt,cdn){
	if(doc.select_print_heading){
		// print heading
		cur_frm.pformat.print_heading = doc.select_print_heading;
	}
	else
		cur_frm.pformat.print_heading = __("Purchase Invoice");
}

frappe.ui.form.on("Purchase Invoice", {
	setup: function(frm) {
		frm.custom_make_buttons = {
			'Purchase Invoice': 'Debit Note',
			'Payment Entry': 'Payment',
			'Sales Order': 'Sales Order'
		}

		frm.fields_dict['items'].grid.get_field('deferred_expense_account').get_query = function(doc) {
			return {
				filters: {
					'root_type': 'Asset',
					'company': doc.company,
					"is_group": 0
				}
			}
		}
	},

	onload: function(frm) {
		if(frm.doc.__onload && !frm.doc.__onload.supplier_tds) {
			me.frm.set_df_property("apply_tds", "read_only", 1);
		}

		$.each(["warehouse", "rejected_warehouse"], function(i, field) {
			frm.set_query(field, "items", function() {
				return {
					filters: [
						["Warehouse", "company", "in", ["", cstr(frm.doc.company)]],
						["Warehouse", "is_group", "=", 0]
					]
				}
			})
		})

		frm.set_query("supplier_warehouse", function() {
			return {
				filters: [
					["Warehouse", "company", "in", ["", cstr(frm.doc.company)]],
					["Warehouse", "is_group", "=", 0]
				]
			}
		})
	},

	is_subcontracted: function(frm) {
		if (frm.doc.is_subcontracted === "Yes") {
			erpnext.buying.get_default_bom(frm);
		}
		frm.toggle_reqd("supplier_warehouse", frm.doc.is_subcontracted==="Yes");
	}
})
