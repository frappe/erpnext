// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.stock");

frappe.ui.form.on("Stock Reconciliation", {
	onload: function(frm) {
		frm.add_fetch("item_code", "item_name", "item_name");

		// end of life
		frm.set_query("item_code", "items", function(doc, cdt, cdn) {
			return {
				query: "erpnext.controllers.queries.item_query",
				filters:{
					"is_stock_item": 1
				}
			}
		});

		var me = this;

		frm.set_query("batch_no", "items", function(doc, cdt, cdn) {
			var item = frappe.get_doc(cdt, cdn);
			let filters = {
				'item_code': item.item_code,
				'posting_date': doc.posting_date || frappe.datetime.nowdate(),
				'posting_time': doc.posting_time,
				'show_negative': 1
			};
			if (item.warehouse) filters["warehouse"] = item.warehouse;
			return {
				query : "erpnext.controllers.queries.get_batch_no",
				filters: filters
			}
		});

		frm.set_query("default_warehouse", function() {
			return {
				filters: ["Warehouse", "company", "in", ["", cstr(frm.doc.company)]]
			}
		});

		if (!frm.doc.expense_account) {
			frm.trigger("set_expense_account");
		}

		if (!frm.doc.__islocal) {
			frm.events.update_item_details(frm);
		}
	},

	refresh: function(frm) {
		erpnext.toggle_naming_series();
		erpnext.hide_company();

		if(frm.doc.company) {
			frm.trigger("toggle_display_account_head");
		}
	},

	reset_rate: function (frm) {
		frm.events.update_item_details(frm);
	},

	// loose_uom: function (frm) {
	// 	frm.events.update_conversion_factor(frm);
	// },
	//
	// update_conversion_factor: function(frm) {
	// 	frappe.call({
	// 		method: "update_conversion_factor",
	// 		doc: frm.doc,
	// 		freeze: true,
	// 		callback: function (r) {
	// 			frm.dirty();
	// 			frm.refresh_fields();
	// 		}
	// 	});
	// },

	get_items: function(frm) {
		frappe.call({
			method:"erpnext.stock.doctype.stock_reconciliation.stock_reconciliation.get_items",
			args: {
				args: {
					posting_date: frm.doc.posting_date,
					posting_time: frm.doc.posting_time,
					company: frm.doc.company,
					warehouse: frm.doc.default_warehouse,
					item_group: frm.doc.selected_item_group,
					brand: frm.doc.selected_brand,
					item_code: frm.doc.selected_item_code,
					get_batches: cint(frm.doc.get_batches),
					sort_by: frm.doc.sort_by,
					positive_or_negative: frm.doc.positive_or_negative,
					reset_rate: frm.doc.reset_rate,
					loose_uom: frm.doc.loose_uom
				}
			},
			callback: function(r) {
				frm.clear_table("items");
				for(var i=0; i < r.message.length; i++) {
					var d = frm.add_child("items");
					$.extend(d, r.message[i]);
					if(!d.qty) d.qty = null;
					if(!d.valuation_rate) d.valuation_rate = null;
				}
				frm.refresh_field("items");
			},
			freeze: 1,
			freeze_message: "Loading items. Please Wait...",
		});
	},

	get_item_details: function(frm, cdt, cdn) {
		var d = frappe.model.get_doc(cdt, cdn);
		if(d.item_code) {
			frappe.call({
				method: "erpnext.stock.doctype.stock_reconciliation.stock_reconciliation.get_item_details",
				args: {
					args: {
						name: frm.doc.name,
						company: frm.doc.company,
						posting_date: frm.doc.posting_date,
						posting_time: frm.doc.posting_time,
						item_code: d.item_code,
						warehouse: d.warehouse,
						batch_no: d.batch_no,
						cost_center: d.cost_center,
						valuation_rate: d.valuation_rate,
						reset_rate: frm.doc.reset_rate,
						loose_uom: frm.doc.loose_uom,
						default_warehouse: frm.doc.default_warehouse,
					}
				},
				callback: function(r) {
					if (r.message) {
						Object.assign(d, r.message);
						frm.refresh_field('items');
					}
				}
			});
		}
	},

	update_item_details: function(frm) {
		if (frm.doc.docstatus == 0) {
			frappe.call({
				method: "update_item_details",
				doc: frm.doc,
				freeze: true,
				callback: function (r) {
					frm.dirty();
					frm.refresh_fields();
				}
			});
		}
	},

	set_item_code: function(doc, cdt, cdn) {
		var d = frappe.model.get_doc(cdt, cdn);
		if (d.barcode) {
			frappe.call({
				method: "erpnext.stock.get_item_details.get_item_code",
				args: {"barcode": d.barcode },
				callback: function(r) {
					if (!r.exc){
						frappe.model.set_value(cdt, cdn, "item_code", r.message);
					}
				}
			});
		}
	},
	set_amount_quantity: function(doc, cdt, cdn) {
		var d = frappe.model.get_doc(cdt, cdn);
		if (d.qty || d.loose_qty || d.valuation_rate) {
			frappe.model.set_value(cdt, cdn, "amount", flt(d.qty) * flt(d.valuation_rate));
			frappe.model.set_value(cdt, cdn, "quantity_difference", flt(d.qty) - flt(d.current_qty));
			frappe.model.set_value(cdt, cdn, "amount_difference", flt(d.amount) - flt(d.current_amount));
			frappe.model.set_value(cdt, cdn, "stock_loose_qty", flt(d.loose_qty) * flt(d.conversion_factor));
			frappe.model.set_value(cdt, cdn, "total_qty", flt(d.qty) + flt(d.stock_loose_qty));
		}
	},
	company: function(frm) {
		frm.trigger("toggle_display_account_head");
	},
	toggle_display_account_head: function(frm) {
		frm.toggle_display(['expense_account', 'cost_center'],
			erpnext.is_perpetual_inventory_enabled(frm.doc.company));
	},
	purpose: function(frm) {
		frm.trigger("set_expense_account");
	},
	set_expense_account: function(frm) {
		if (frm.doc.company && erpnext.is_perpetual_inventory_enabled(frm.doc.company)) {
			return frm.call({
				method: "erpnext.stock.doctype.stock_reconciliation.stock_reconciliation.get_difference_account",
				args: {
					"purpose": frm.doc.purpose,
					"company": frm.doc.company
				},
				callback: function(r) {
					if (!r.exc) {
						frm.set_value("expense_account", r.message);
					}
				}
			});
		}
	}
});

frappe.ui.form.on("Stock Reconciliation Item", {
	barcode: function(frm, cdt, cdn) {
		frm.events.set_item_code(frm, cdt, cdn);
	},
	warehouse: function(frm, cdt, cdn) {
		var doc = frappe.get_doc(cdt, cdn);
		if (doc.warehouse) {
			frm.events.get_item_details(frm, cdt, cdn);
		}
	},
	batch_no: function(frm, cdt, cdn) {
		frm.events.get_item_details(frm, cdt, cdn);
	},
	item_code: function(frm, cdt, cdn) {
		frm.events.get_item_details(frm, cdt, cdn);
	},
	qty: function(frm, cdt, cdn) {
		frm.events.set_amount_quantity(frm, cdt, cdn);
	},
	loose_qty: function(frm, cdt, cdn) {
		frm.events.set_amount_quantity(frm, cdt, cdn);
	},
	valuation_rate: function(frm, cdt, cdn) {
		frm.events.set_amount_quantity(frm, cdt, cdn);
	},

	serial_no: function(frm, cdt, cdn) {
		var child = locals[cdt][cdn];

		if (child.serial_no) {
			const serial_nos = child.serial_no.trim().split('\n');
			frappe.model.set_value(cdt, cdn, "qty", serial_nos.length);
		}
	},

	loose_uom: function(frm, cdt, cdn) {
		var item = frappe.get_doc(cdt, cdn);
		if(item.item_code && item.loose_uom) {
			return frm.call({
				method: "erpnext.stock.get_item_details.get_conversion_factor",
				child: item,
				args: {
					item_code: item.item_code,
					uom: item.loose_uom
				},
				callback: function(r) {
					if(!r.exc) {
						frm.cscript.conversion_factor(frm.doc, cdt, cdn);
					}
				}
			});
		}
	},
});

erpnext.stock.StockReconciliation = class StockReconciliation extends erpnext.stock.StockController {
	setup() {
		var me = this;

		this.remove_sidebar();

		this.setup_posting_date_time_check();

		if (me.frm.doc.company && erpnext.is_perpetual_inventory_enabled(me.frm.doc.company)) {
			this.frm.add_fetch("company", "cost_center", "cost_center");
		}
		this.frm.fields_dict["expense_account"].get_query = function() {
			if(erpnext.is_perpetual_inventory_enabled(me.frm.doc.company)) {
				return {
					"filters": {
						'company': me.frm.doc.company,
						"is_group": 0
					}
				}
			}
		}
		this.frm.fields_dict["cost_center"].get_query = function() {
			if(erpnext.is_perpetual_inventory_enabled(me.frm.doc.company)) {
				return {
					"filters": {
						'company': me.frm.doc.company,
						"is_group": 0
					}
				}
			}
		}
	}

	refresh() {
		if(this.frm.doc.docstatus==1) {
			this.show_stock_ledger();
			if (erpnext.is_perpetual_inventory_enabled(this.frm.doc.company)) {
				this.show_general_ledger();
			}
		}
	}

	conversion_factor(doc, cdt, cdn) {
		this.frm.events.set_amount_quantity(doc, cdt, cdn);
	}

};

cur_frm.cscript = new erpnext.stock.StockReconciliation({frm: cur_frm});
