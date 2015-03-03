// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors // License: GNU General Public License v3. See license.txt

frappe.require("assets/erpnext/js/controllers/stock_controller.js");
frappe.require("assets/erpnext/js/utils.js");
frappe.provide("erpnext.stock");

erpnext.stock.StockEntry = erpnext.stock.StockController.extend({
	setup: function() {
		var me = this;

		this.frm.fields_dict.delivery_note_no.get_query = function() {
			return { query: "erpnext.stock.doctype.stock_entry.stock_entry.query_sales_return_doc" };
		};

		this.frm.fields_dict.sales_invoice_no.get_query =
			this.frm.fields_dict.delivery_note_no.get_query;

		this.frm.fields_dict.purchase_receipt_no.get_query = function() {
			return {
				filters:{ 'docstatus': 1 }
			};
		};

		this.frm.fields_dict.bom_no.get_query = function() {
			return {
				filters:{ 'docstatus': 1 }
			};
		};

		this.frm.fields_dict.items.grid.get_field('item_code').get_query = function() {
			if(in_list(["Sales Return", "Purchase Return"], me.frm.doc.purpose) &&
				me.get_doctype_docname()) {
					return {
						query: "erpnext.stock.doctype.stock_entry.stock_entry.query_return_item",
						filters: {
							purpose: me.frm.doc.purpose,
							delivery_note_no: me.frm.doc.delivery_note_no,
							sales_invoice_no: me.frm.doc.sales_invoice_no,
							purchase_receipt_no: me.frm.doc.purchase_receipt_no
						}
					};
			} else {
				return erpnext.queries.item({is_stock_item: "Yes"});
			}
		};

		if(cint(frappe.defaults.get_default("auto_accounting_for_stock"))) {
			this.frm.add_fetch("company", "stock_adjustment_account", "expense_account");
			this.frm.fields_dict.items.grid.get_field('expense_account').get_query =
					function() {
				return {
					filters: {
						"company": me.frm.doc.company,
						"group_or_ledger": "Ledger"
					}
				}
			}
		}
	},

	onload_post_render: function() {
		cur_frm.get_field("items").grid.set_multiple_add("item_code", "qty");
		this.set_default_account();
	},

	refresh: function() {
		var me = this;
		erpnext.toggle_naming_series();
		this.toggle_related_fields(this.frm.doc);
		this.toggle_enable_bom();
		this.show_stock_ledger();
		this.show_general_ledger();

		if(this.frm.doc.docstatus === 1 && frappe.boot.user.can_create.indexOf("Journal Entry")!==-1
			&& this.frm.doc.__onload.credit_debit_note_exists == 0 ) {
			if(this.frm.doc.purpose === "Sales Return") {
				this.frm.add_custom_button(__("Make Credit Note"),
					function() { me.make_return_jv(); }, frappe.boot.doctype_icons["Journal Entry"]);
				this.add_excise_button();
			} else if(this.frm.doc.purpose === "Purchase Return") {
				this.frm.add_custom_button(__("Make Debit Note"),
					function() { me.make_return_jv(); }, frappe.boot.doctype_icons["Journal Entry"]);
				this.add_excise_button();
			}
		}
	},

	on_submit: function() {
		this.clean_up();
	},

	after_cancel: function() {
		this.clean_up();
	},

	set_default_account: function() {
		var me = this;

		if(cint(frappe.defaults.get_default("auto_accounting_for_stock")) && this.frm.doc.company) {
			var account_for = "stock_adjustment_account";

			if (this.frm.doc.purpose == "Purchase Return")
				account_for = "stock_received_but_not_billed";

			return this.frm.call({
				method: "erpnext.accounts.utils.get_company_default",
				args: {
					"fieldname": account_for,
					"company": this.frm.doc.company
				},
				callback: function(r) {
					if (!r.exc) {
						$.each(me.frm.doc.items || [], function(i, d) {
							if(!d.expense_account) d.expense_account = r.message;
						});
					}
				}
			});
		}
	},

	clean_up: function() {
		// Clear Production Order record from locals, because it is updated via Stock Entry
		if(this.frm.doc.production_order &&
				in_list(["Manufacture", "Material Transfer for Manufacture"], this.frm.doc.purpose)) {
			frappe.model.remove_from_locals("Production Order",
				this.frm.doc.production_order);
		}
	},

	get_items: function() {
		var me = this;
		if(!this.frm.doc.fg_completed_qty || !this.frm.doc.bom_no)
			frappe.throw(__("BOM and Manufacturing Quantity are required"));
		
		if(this.frm.doc.production_order || this.frm.doc.bom_no) {
			// if production order / bom is mentioned, get items
			return this.frm.call({
				doc: me.frm.doc,
				method: "get_items",
				callback: function(r) {
					if(!r.exc) refresh_field("items");
				}
			});
		}
	},

	qty: function(doc, cdt, cdn) {
		var d = locals[cdt][cdn];
		d.transfer_qty = flt(d.qty) * flt(d.conversion_factor);
		refresh_field('items');
		calculate_total(doc, cdt, cdn);
	},

	incoming_rate: function(doc, cdt, cdn) {
		calculate_total(doc, cdt, cdn);
	},

	production_order: function() {
		var me = this;
		this.toggle_enable_bom();

		return this.frm.call({
			method: "get_production_order_details",
			args: {production_order: this.frm.doc.production_order},
			callback: function(r) {
				if (!r.exc) {
					if (me.frm.doc.purpose == "Material Transfer for Manufacture" && !me.frm.doc.to_warehouse)
						me.frm.set_value("to_warehouse", r.message["wip_warehouse"]);
					me.frm.set_value("from_bom", 1);
				}
			}
		});
	},

	toggle_enable_bom: function() {
		this.frm.toggle_enable("bom_no", !in_list(["Manufacture", "Material Transfer for Manufacture"], this.frm.doc.purpose));
	},

	get_doctype_docname: function() {
		if(this.frm.doc.purpose === "Sales Return") {
			if(this.frm.doc.delivery_note_no && this.frm.doc.sales_invoice_no) {
				// both specified
				msgprint(__("You can not enter both Delivery Note No and Sales Invoice No. Please enter any one."));

			} else if(!(this.frm.doc.delivery_note_no || this.frm.doc.sales_invoice_no)) {
				// none specified
				msgprint(__("Please enter Delivery Note No or Sales Invoice No to proceed"));

			} else if(this.frm.doc.delivery_note_no) {
				return {doctype: "Delivery Note", docname: this.frm.doc.delivery_note_no};

			} else if(this.frm.doc.sales_invoice_no) {
				return {doctype: "Sales Invoice", docname: this.frm.doc.sales_invoice_no};

			}
		} else if(this.frm.doc.purpose === "Purchase Return") {
			if(this.frm.doc.purchase_receipt_no) {
				return {doctype: "Purchase Receipt", docname: this.frm.doc.purchase_receipt_no};

			} else {
				// not specified
				msgprint(__("Please enter Purchase Receipt No to proceed"));

			}
		}
	},

	add_excise_button: function() {
		if(frappe.boot.sysdefaults.country === "India")
			this.frm.add_custom_button(__("Make Excise Invoice"), function() {
				var excise = frappe.model.make_new_doc_and_get_name('Journal Entry');
				excise = locals['Journal Entry'][excise];
				excise.voucher_type = 'Excise Entry';
				loaddoc('Journal Entry', excise.name);
			}, frappe.boot.doctype_icons["Journal Entry"], "btn-default");
	},

	make_return_jv: function() {
		if(this.get_doctype_docname()) {
			return this.frm.call({
				method: "make_return_jv",
				args: {
					stock_entry: this.frm.doc.name
				},
				callback: function(r) {
					if(!r.exc) {
						var doclist = frappe.model.sync(r.message);
						frappe.set_route("Form", doclist[0].doctype, doclist[0].name);

					}
				}
			});
		}
	},

	items_add: function(doc, cdt, cdn) {
		var row = frappe.get_doc(cdt, cdn);
		this.frm.script_manager.copy_from_first_row("items", row,
			["expense_account", "cost_center"]);

		if(!row.s_warehouse) row.s_warehouse = this.frm.doc.from_warehouse;
		if(!row.t_warehouse) row.t_warehouse = this.frm.doc.to_warehouse;
	},

	source_mandatory: ["Material Issue", "Material Transfer", "Purchase Return", "Subcontract",
		"Material Transfer for Manufacture"],
	target_mandatory: ["Material Receipt", "Material Transfer", "Sales Return", "Subcontract",
		"Material Transfer for Manufacture"],

	from_warehouse: function(doc) {
		var me = this;
		this.set_warehouse_if_different("s_warehouse", doc.from_warehouse, function(row) {
			return me.source_mandatory.indexOf(me.frm.doc.purpose)!==-1;
		});
	},

	to_warehouse: function(doc) {
		var me = this;
		this.set_warehouse_if_different("t_warehouse", doc.to_warehouse, function(row) {
			return me.target_mandatory.indexOf(me.frm.doc.purpose)!==-1;
		});
	},

	set_warehouse_if_different: function(fieldname, value, condition) {
		var changed = false;
		for (var i=0, l=(this.frm.doc.items || []).length; i<l; i++) {
			var row = this.frm.doc.items[i];
			if (row[fieldname] != value) {
				if (condition && !condition(row)) {
					continue;
				}

				frappe.model.set_value(row.doctype, row.name, fieldname, value, "Link");
				changed = true;
			}
		}
		refresh_field("items");
	},

	items_on_form_rendered: function(doc, grid_row) {
		erpnext.setup_serial_no();
	},

	customer: function() {
		this.get_party_details({
			party: this.frm.doc.customer,
			party_type:"Customer",
			doctype: this.frm.doc.doctype
		});
	},

	supplier: function() {
		this.get_party_details({
			party: this.frm.doc.supplier,
			party_type:"Supplier",
			doctype: this.frm.doc.doctype
		});
	},

	get_party_details: function(args) {
		var me = this;
		frappe.call({
			method: "erpnext.accounts.party.get_party_details",
			args: args,
			callback: function(r) {
				if(r.message) {
					me.frm.set_value({
						"customer_name": r.message["customer_name"],
						"customer_address": r.message["address_display"]
					});
				}
			}
		});
	},

	delivery_note_no: function() {
		this.get_party_details_from_against_voucher({
			ref_dt: "Delivery Note",
			ref_dn: this.frm.doc.delivery_note_no
		})
	},

	sales_invoice_no: function() {
		this.get_party_details_from_against_voucher({
			ref_dt: "Sales Invoice",
			ref_dn: this.frm.doc.sales_invoice_no
		})
	},

	purchase_receipt_no: function() {
		this.get_party_details_from_against_voucher({
			ref_dt: "Purchase Receipt",
			ref_dn: this.frm.doc.purchase_receipt_no
		})
	},

	get_party_details_from_against_voucher: function(args) {
		return this.frm.call({
			method: "erpnext.stock.doctype.stock_entry.stock_entry.get_party_details",
			args: args,
		})
	}

});

cur_frm.script_manager.make(erpnext.stock.StockEntry);

cur_frm.cscript.toggle_related_fields = function(doc) {
	disable_from_warehouse = inList(["Material Receipt", "Sales Return"], doc.purpose);
	disable_to_warehouse = inList(["Material Issue", "Purchase Return"], doc.purpose);

	cur_frm.toggle_enable("from_warehouse", !disable_from_warehouse);
	cur_frm.toggle_enable("to_warehouse", !disable_to_warehouse);

	cur_frm.fields_dict["items"].grid.set_column_disp("s_warehouse", !disable_from_warehouse);
	cur_frm.fields_dict["items"].grid.set_column_disp("t_warehouse", !disable_to_warehouse);

	cur_frm.cscript.toggle_enable_bom();

	if(doc.purpose == 'Purchase Return') {
		doc.customer = doc.customer_name = doc.customer_address =
			doc.delivery_note_no = doc.sales_invoice_no = null;
		doc.bom_no = doc.production_order = doc.fg_completed_qty = null;
	} else if(doc.purpose == 'Sales Return') {
		doc.supplier=doc.supplier_name = doc.supplier_address = doc.purchase_receipt_no=null;
		doc.bom_no = doc.production_order = doc.fg_completed_qty = null;
	} else if (doc.purpose == 'Subcontract') {
		doc.customer = doc.customer_name = doc.customer_address =
			doc.delivery_note_no = doc.sales_invoice_no = null;
	} else {
		doc.customer = doc.customer_name = doc.customer_address =
			doc.delivery_note_no = doc.sales_invoice_no = doc.supplier =
			doc.supplier_name = doc.supplier_address = doc.purchase_receipt_no = null;
	}
	if(in_list(["Material Receipt", "Sales Return", "Purchase Return"], doc.purpose)) {
		cur_frm.set_value("from_bom", 0);
	}
}

cur_frm.fields_dict['production_order'].get_query = function(doc) {
	return {
		filters: [
			['Production Order', 'docstatus', '=', 1],
			['Production Order', 'qty', '>','`tabProduction Order`.produced_qty']
		]
	}
}

cur_frm.cscript.purpose = function(doc, cdt, cdn) {
	cur_frm.cscript.toggle_related_fields(doc);
}

// Overloaded query for link batch_no
cur_frm.fields_dict['items'].grid.get_field('batch_no').get_query = function(doc, cdt, cdn) {
	var d = locals[cdt][cdn];
	if(d.item_code) {
		return{
			query: "erpnext.stock.doctype.stock_entry.stock_entry.get_batch_no",
			filters:{
				'item_code'		: d.item_code,
				's_warehouse'	: d.s_warehouse,
				'posting_date'	: doc.posting_date
			}
		}
	} else {
		msgprint(__("Please enter Item Code to get batch no"));
	}
}

cur_frm.cscript.item_code = function(doc, cdt, cdn) {
	var d = locals[cdt][cdn];
	if(d.item_code) {
		args = {
			'item_code'			: d.item_code,
			'warehouse'			: cstr(d.s_warehouse) || cstr(d.t_warehouse),
			'transfer_qty'		: d.transfer_qty,
			'serial_no	'		: d.serial_no,
			'bom_no'			: d.bom_no,
			'expense_account'	: d.expense_account,
			'cost_center'		: d.cost_center,
			'company'			: cur_frm.doc.company
		};
		return frappe.call({
			doc: cur_frm.doc,
			method: "get_item_details",
			args: args,
			callback: function(r) {
				if(r.message) {
					$.each(r.message, function(k, v) {
						frappe.model.set_value(cdt, cdn, k, v);
					});
				refresh_field('image_view', d.name, 'items');
				}
			}
		});
	}
}

cur_frm.cscript.barcode = function(doc, cdt, cdn) {
	var d = locals[cdt][cdn];
	if (d.barcode) {
		frappe.call({
			method: "erpnext.stock.get_item_details.get_item_code",
			args: {"barcode": d.barcode },
			callback: function(r) {
				if (!r.exe){
					frappe.model.set_value(cdt, cdn, "item_code", r.message);
				}
			}
		});
	}
}

cur_frm.cscript.s_warehouse = function(doc, cdt, cdn) {
	var d = locals[cdt][cdn];
	if(!d.bom_no) {
		args = {
			'item_code'		: d.item_code,
			'warehouse'		: cstr(d.s_warehouse) || cstr(d.t_warehouse),
			'transfer_qty'	: d.transfer_qty,
			'serial_no'		: d.serial_no,
			'qty'			: d.s_warehouse ? -1* d.qty : d.qty
		}
		return get_server_fields('get_warehouse_details', JSON.stringify(args),
			'items', doc, cdt, cdn, 1);
	}
}

cur_frm.cscript.t_warehouse = cur_frm.cscript.s_warehouse;

cur_frm.cscript.uom = function(doc, cdt, cdn) {
	var d = locals[cdt][cdn];
	if(d.uom && d.item_code){
		var arg = {'item_code':d.item_code, 'uom':d.uom, 'qty':d.qty}
		return get_server_fields('get_uom_details', JSON.stringify(arg),
			'items', doc, cdt, cdn, 1);
	}
}

cur_frm.cscript.validate = function(doc, cdt, cdn) {
	cur_frm.cscript.validate_items(doc);
	if($.inArray(cur_frm.doc.purpose, ["Purchase Return", "Sales Return"])!==-1)
		validated = cur_frm.cscript.get_doctype_docname() ? true : false;
}

cur_frm.cscript.validate_items = function(doc) {
	cl = doc.items || [];
	if (!cl.length) {
		msgprint(__("Item table can not be blank"));
		validated = false;
	}
}

cur_frm.cscript.expense_account = function(doc, cdt, cdn) {
	cur_frm.cscript.copy_account_in_all_row(doc, cdt, cdn, "expense_account");
}

cur_frm.cscript.cost_center = function(doc, cdt, cdn) {
	cur_frm.cscript.copy_account_in_all_row(doc, cdt, cdn, "cost_center");
}

cur_frm.fields_dict.customer.get_query = function(doc, cdt, cdn) {
	return { query: "erpnext.controllers.queries.customer_query" }
}

cur_frm.fields_dict.supplier.get_query = function(doc, cdt, cdn) {
	return { query: "erpnext.controllers.queries.supplier_query" }
}

cur_frm.cscript.company = function(doc, cdt, cdn) {
	erpnext.get_fiscal_year(doc.company, doc.posting_date);
}

cur_frm.cscript.posting_date = function(doc, cdt, cdn){
	erpnext.get_fiscal_year(doc.company, doc.posting_date);
}

var calculate_total = function(doc, cdt, cdn){
	var d = locals[cdt][cdn];
	amount = flt(d.incoming_rate) * flt(d.transfer_qty)
	frappe.model.set_value(cdt, cdn, 'amount', amount);
	var total_amount = 0.0;
	var items = doc.items || [];
	for(var i=0;i<items.length;i++) {
		total_amount += flt(items[i].amount);
	}
	doc.total_amount = total_amount;
	refresh_field("total_amount");
}
