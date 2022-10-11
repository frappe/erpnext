// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

{% include 'erpnext/public/js/controllers/buying.js' %};

frappe.provide("erpnext.stock");

frappe.ui.form.on("Purchase Receipt", {
	setup: (frm) => {
		frm.make_methods = {
			'Landed Cost Voucher': () => {
				let lcv = frappe.model.get_new_doc('Landed Cost Voucher');
				lcv.company = frm.doc.company;

				let lcv_receipt = frappe.model.get_new_doc('Landed Cost Purchase Receipt');
				lcv_receipt.receipt_document_type = 'Purchase Receipt';
				lcv_receipt.receipt_document = frm.doc.name;
				lcv_receipt.supplier = frm.doc.supplier;
				lcv_receipt.grand_total = frm.doc.grand_total;
				lcv.purchase_receipts = [lcv_receipt];

				frappe.set_route("Form", lcv.doctype, lcv.name);
			},
		}

		frm.custom_make_buttons = {
			'Stock Entry': 'Return',
			'Purchase Invoice': 'Purchase Invoice'
		};

		frm.set_query("expense_account", "items", function() {
			return {
				query: "erpnext.controllers.queries.get_expense_account",
				filters: {'company': frm.doc.company }
			}
		});

		frm.set_query("taxes_and_charges", function() {
			return {
				filters: {'company': frm.doc.company }
			}
		});

	},
	onload: function(frm) {
		erpnext.queries.setup_queries(frm, "Warehouse", function() {
			return erpnext.queries.warehouse(frm.doc);
		});
	},

	refresh: function(frm) {
		if(frm.doc.company) {
			frm.trigger("toggle_display_account_head");
		}
		//------Remove Add Row button in child table in logistic notice
		frm.set_df_property('items', 'cannot_add_rows', true);

		/* if (frm.doc.docstatus === 1 && frm.doc.is_return === 1 && frm.doc.per_billed !== 100) {
			frm.add_custom_button(__('Debit Note'), function() {
				frappe.model.open_mapped_doc({
					method: "erpnext.stock.doctype.purchase_receipt.purchase_receipt.make_purchase_invoice",
					frm: cur_frm,
				})
			}, __('Create'));
			frm.page.set_inner_btn_group_as_primary(__('Create'));
		} */

		/* if (frm.doc.docstatus === 1 && frm.doc.is_internal_supplier && !frm.doc.inter_company_reference) {
			frm.add_custom_button(__('Delivery Note'), function() {
				frappe.model.open_mapped_doc({
					method: 'erpnext.stock.doctype.purchase_receipt.purchase_receipt.make_inter_company_delivery_note',
					frm: cur_frm,
				})
			}, __('Create'));
		} */

		// frm.events.add_custom_buttons(frm);
	},

	/* add_custom_buttons: function(frm) {
		if (frm.doc.docstatus == 0) {
			frm.add_custom_button(__('Purchase Invoice'), function () {
				if (!frm.doc.supplier) {
					frappe.throw({
						title: __("Mandatory"),
						message: __("Please Select a Supplier")
					});
				}
				erpnext.utils.map_current_doc({
					method: "erpnext.accounts.doctype.purchase_invoice.purchase_invoice.make_purchase_receipt",
					source_doctype: "Purchase Invoice",
					target: frm,
					setters: {
						supplier: frm.doc.supplier,
					},
					get_query_filters: {
						docstatus: 1,
						per_received: ["<", 100],
						company: frm.doc.company
					}
				})
			}, __("Get Items From"));
		}
	}, */

	company: function(frm) {
		frm.trigger("toggle_display_account_head");
		erpnext.accounts.dimensions.update_dimension(frm, frm.doctype);
	},

	toggle_display_account_head: function(frm) {
		var enabled = erpnext.is_perpetual_inventory_enabled(frm.doc.company)
		frm.fields_dict["items"].grid.set_column_disp(["cost_center"], enabled);
	},
	/////////////delete items total and total_qty update
	set_total_allocated_amount: function (frm) {
		var total = 0.0;
		var base_total = 0.0;
		$.each(frm.doc.items || [], function (i, row) {
			if (row.amount) {
				total += flt(row.amount);
				base_total += flt(flt(row.amount) * flt(row.exchange_rate));
			}
		});
		frm.set_value("total", Math.abs(total));	
	},
	set_total_quantity: function (frm) {
		var total_qty = 0.0;
		$.each(frm.doc.items || [], function (i, row) {
			if (row.qty) {
				total_qty += flt(row.qty);
			}
			row.total_qty = flt(row.qty) - flt(row.total_qty);
			frm.refresh_field("total_qty", total_qty);
		});
		frm.set_value("total_qty", Math.abs(total_qty));
	}
});

frappe.ui.form.on("Purchase Receipt Item", {
	item_code: function (frm, cdt, cdn) {
		var item = locals[cdt][cdn];
		if (!item.item_code && (item.qty || item.rate || item.amount)) {
			cur_frm.fields_dict["items"].grid.grid_rows[item.idx - 1].remove();
			cur_frm.refresh_fields();
		}
	},
	items_remove: function (frm) {
		frm.events.set_total_allocated_amount(frm);
		frm.events.set_total_quantity(frm);
	},
});

erpnext.stock.PurchaseReceiptController = erpnext.buying.BuyingController.extend({
	setup: function(doc) {
		this.setup_posting_date_time_check();
		this._super(doc);
	},

	refresh: function() {
		var me = this;
		this._super();
		if(this.frm.doc.docstatus > 0) {
			// this.show_stock_ledger();
			//removed for temporary
			// this.show_general_ledger();

			/* this.frm.add_custom_button(__('Asset'), function() {
				frappe.route_options = {
					purchase_receipt: me.frm.doc.name,
				};
				frappe.set_route("List", "Asset");
			}, __("View")); */

			/* this.frm.add_custom_button(__('Asset Movement'), function() {
				frappe.route_options = {
					reference_name: me.frm.doc.name,
				};
				frappe.set_route("List", "Asset Movement");
			}, __("View")); */
		}

		if(!this.frm.doc.is_return && this.frm.doc.status!="Closed") {
			/* if (this.frm.doc.docstatus == 0) {
				this.frm.add_custom_button(__('Purchase Order'),
					function () {
						if (!me.frm.doc.supplier) {
							frappe.throw({
								title: __("Mandatory"),
								message: __("Please Select a Supplier")
							});
						}
						erpnext.utils.map_current_doc({
							method: "erpnext.buying.doctype.purchase_order.purchase_order.make_purchase_receipt",
							source_doctype: "Purchase Order",
							target: me.frm,
							setters: {
								supplier: me.frm.doc.supplier,
								schedule_date: undefined
							},
							get_query_filters: {
								docstatus: 1,
								status: ["not in", ["Closed", "On Hold"]],
								per_received: ["<", 99.99],
								company: me.frm.doc.company
							}
						})
					}, __("Get Items From"));
			} */

			if(this.frm.doc.docstatus == 1 && this.frm.doc.status!="Closed") {
				/* if (this.frm.has_perm("submit")) {
					cur_frm.add_custom_button(__("Close"), this.close_purchase_receipt, __("Status"))
				} */

				// cur_frm.add_custom_button(__('Purchase Return'), this.make_purchase_return, __('Create'));

				// cur_frm.add_custom_button(__('Make Stock Entry'), cur_frm.cscript['Make Stock Entry'], __('Create'));

				/* if(flt(this.frm.doc.per_billed) < 100) {
					cur_frm.add_custom_button(__('Purchase Invoice'), this.make_purchase_invoice, __('Create'));
				} */
				// cur_frm.add_custom_button(__('Retention Stock Entry'), this.make_retention_stock_entry, __('Create'));

				/* if(!this.frm.doc.auto_repeat) {
					cur_frm.add_custom_button(__('Subscription'), function() {
						erpnext.utils.make_subscription(me.frm.doc.doctype, me.frm.doc.name)
					}, __('Create'))
				} */

				cur_frm.page.set_inner_btn_group_as_primary(__('Create'));

				// ***** MAKE LOGISITIC NOTICE BUTTON ***** //
				// if(flt(this.frm.doc.per_received) < 100 && allow_receipt) {// ** need to add condition**//
				// }
				cur_frm.add_custom_button(__('Logistic Notice'), this.make_logistic_notice, __('Create'));
			}
		}


		/* if(this.frm.doc.docstatus==1 && this.frm.doc.status === "Closed" && this.frm.has_perm("submit")) {
			cur_frm.add_custom_button(__('Reopen'), this.reopen_purchase_receipt, __("Status"))
		} */

		this.frm.toggle_reqd("supplier_warehouse", this.frm.doc.is_subcontracted==="Yes");
	},

	make_logistic_notice: function() {
		frappe.model.open_mapped_doc({
			method: "erpnext.stock.doctype.purchase_receipt.purchase_receipt.make_logistic_notice",
			frm: cur_frm,
			// freeze_message: __("Creating Logistic Notice ...")
		})
	},

	make_purchase_invoice: function() {
		frappe.model.open_mapped_doc({
			method: "erpnext.stock.doctype.purchase_receipt.purchase_receipt.make_purchase_invoice",
			frm: cur_frm
		})
	},

	make_purchase_return: function() {
		frappe.model.open_mapped_doc({
			method: "erpnext.stock.doctype.purchase_receipt.purchase_receipt.make_purchase_return",
			frm: cur_frm
		})
	},

	close_purchase_receipt: function() {
		cur_frm.cscript.update_status("Closed");
	},

	reopen_purchase_receipt: function() {
		cur_frm.cscript.update_status("Submitted");
	},

	make_retention_stock_entry: function() {
		frappe.call({
			method: "erpnext.stock.doctype.stock_entry.stock_entry.move_sample_to_retention_warehouse",
			args:{
				"company": cur_frm.doc.company,
				"items": cur_frm.doc.items
			},
			callback: function (r) {
				if (r.message) {
					var doc = frappe.model.sync(r.message)[0];
					frappe.set_route("Form", doc.doctype, doc.name);
				}
				else {
					frappe.msgprint(__("Purchase Receipt doesn't have any Item for which Retain Sample is enabled."));
				}
			}
		});
	},

	apply_putaway_rule: function() {
		if (this.frm.doc.apply_putaway_rule) erpnext.apply_putaway_rule(this.frm);
	}

});

// for backward compatibility: combine new and previous states
$.extend(cur_frm.cscript, new erpnext.stock.PurchaseReceiptController({frm: cur_frm}));

cur_frm.cscript.update_status = function(status) {
	frappe.ui.form.is_saving = true;
	frappe.call({
		method:"erpnext.stock.doctype.purchase_receipt.purchase_receipt.update_purchase_receipt_status",
		args: {docname: cur_frm.doc.name, status: status},
		callback: function(r){
			if(!r.exc)
				cur_frm.reload_doc();
		},
		always: function(){
			frappe.ui.form.is_saving = false;
		}
	})
}

cur_frm.fields_dict['items'].grid.get_field('project').get_query = function(doc, cdt, cdn) {
	return {
		filters: [
			['Project', 'status', 'not in', 'Completed, Cancelled']
		]
	}
}

cur_frm.fields_dict['select_print_heading'].get_query = function(doc, cdt, cdn) {
	return {
		filters: [
			['Print Heading', 'docstatus', '!=', '2']
		]
	}
}

cur_frm.fields_dict['items'].grid.get_field('bom').get_query = function(doc, cdt, cdn) {
	var d = locals[cdt][cdn]
	return {
		filters: [
			['BOM', 'item', '=', d.item_code],
			['BOM', 'is_active', '=', '1'],
			['BOM', 'docstatus', '=', '1']
		]
	}
}

frappe.provide("erpnext.buying");

frappe.ui.form.on("Purchase Receipt", "is_subcontracted", function(frm) {
	if (frm.doc.is_subcontracted === "Yes") {
		erpnext.buying.get_default_bom(frm);
	}
	frm.toggle_reqd("supplier_warehouse", frm.doc.is_subcontracted==="Yes");
});

frappe.ui.form.on('Purchase Receipt Item', {
	item_code: function(frm, cdt, cdn) {
		var d = locals[cdt][cdn];
		frappe.db.get_value('Item', {name: d.item_code}, 'sample_quantity', (r) => {
			frappe.model.set_value(cdt, cdn, "sample_quantity", r.sample_quantity);
			validate_sample_quantity(frm, cdt, cdn);
		});
	},
	qty: function(frm, cdt, cdn) {
		validate_sample_quantity(frm, cdt, cdn);
	},
	sample_quantity: function(frm, cdt, cdn) {
		validate_sample_quantity(frm, cdt, cdn);
	},
	batch_no: function(frm, cdt, cdn) {
		validate_sample_quantity(frm, cdt, cdn);
	},
});

cur_frm.cscript['Make Stock Entry'] = function() {
	frappe.model.open_mapped_doc({
		method: "erpnext.stock.doctype.purchase_receipt.purchase_receipt.make_stock_entry",
		frm: cur_frm,
	})
}

var validate_sample_quantity = function(frm, cdt, cdn) {
	var d = locals[cdt][cdn];
	if (d.sample_quantity && d.qty) {
		frappe.call({
			method: 'erpnext.stock.doctype.stock_entry.stock_entry.validate_sample_quantity',
			args: {
				batch_no: d.batch_no,
				item_code: d.item_code,
				sample_quantity: d.sample_quantity,
				qty: d.qty
			},
			callback: (r) => {
				frappe.model.set_value(cdt, cdn, "sample_quantity", r.message);
			}
		});
	}
};
frappe.ui.form.on("Purchase Receipt", "before_save", function (frm) {
	$.each(cur_frm.doc.items || [], function (i, v) {
		var manufacturing_date;
		var expiry_date;
		
		frappe.call({
			method: "frappe.client.get_list",
			args: {
				doctype: "Batch",
				filters: [
					["batch_id", "=", v.batch_number],
				],
				fields: [
					"manufacturing_date",
					"expiry_date",
					"name",
				]
			},
			callback: function (r) {
				manufacturing_date = (r.message[0].manufacturing_date);
				expiry_date = (r.message[0].expiry_date);
				var batch_id = r.message[0].name
				if (manufacturing_date != v.manufacturing_date) {
					frappe.db.set_value("Batch", batch_id, "manufacturing_date", v.manufacturing_date)	
				}else if (expiry_date != v.expiry_date) {
					frappe.db.set_value("Batch", batch_id, "expiry_date", v.expiry_date)
				}
			}
		});
	})
})
frappe.ui.form.on('Purchase Receipt',  {
   after_cancel : function(frm) {
        frappe.call({
            "method": "frappe.client.set_value",
            "args": {
                "doctype": "Purchase Order",
                "name": frm.doc.purchase_order,
                "fieldname": {"po_status" : "Open" },
            }
        });
		frappe.call({
            "method": "frappe.client.set_value",
            "args": {
                "doctype": "Account Payable",
                "name": frm.doc.purchase_order,
                "fieldname": "total_payable_after_revision",
                "value": frm.doc.po_total,
            }
        });
    }
});


frappe.ui.form.on("Purchase Receipt", "before_submit", function (frm) {
	$.each(frm.doc.items || [], function(i, d) {
		frappe.call({
			method:"erpnext.stock.doctype.purchase_receipt.purchase_receipt.pr_batch_details",
			async: false,
			args: {
				item_code: d.item_code,
				item_name: d.item_name, 
				qty: d.qty,
				name:d.purchase_order,
				batch_number:d.batch_number,
				manufacturing_date:d.manufacturing_date,
				expiry_date:d.expiry_date,
			},
		})
	});
})