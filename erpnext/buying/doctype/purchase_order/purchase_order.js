// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.buying");

{% include 'erpnext/public/js/controllers/buying.js' %};

frappe.ui.form.on("Purchase Order", {
	setup: function(frm) {
		frm.custom_make_buttons = {
			'Purchase Receipt': 'Receipt',
			'Purchase Invoice': 'Invoice',
			'Stock Entry': 'Material to Supplier'
		}

		frm.set_query("reserve_warehouse", "supplied_items", function() {
			return {
				filters: {
					"company": frm.doc.company,
					"is_group": 0
				}
			}
		});

		frm.set_indicator_formatter('item_code',
			function(doc) { return (doc.qty<=doc.received_qty) ? "green" : "orange" })

		frm.set_query("blanket_order", "items", function() {
			return {
				filters: {
					"company": frm.doc.company,
					"docstatus": 1
				}
			}
		});
	},

	refresh: function(frm) {
		if(frm.doc.docstatus == 1 && frm.doc.status == 'To Receive and Bill') {
			frm.add_custom_button(__('Update Items'), () => {
				erpnext.utils.update_child_items({
					frm: frm,
					child_docname: "items",
					child_doctype: "Purchase Order Detail",
				})
			});
		}
	},

	onload: function(frm) {
		set_schedule_date(frm);
		if (!frm.doc.transaction_date){
			frm.set_value('transaction_date', frappe.datetime.get_today())
		}

		erpnext.queries.setup_queries(frm, "Warehouse", function() {
			return erpnext.queries.warehouse(frm.doc);
		});
	}
});

frappe.ui.form.on("Purchase Order Item", {
	schedule_date: function(frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		if (row.schedule_date) {
			if(!frm.doc.schedule_date) {
				erpnext.utils.copy_value_in_all_rows(frm.doc, cdt, cdn, "items", "schedule_date");
			} else {
				set_schedule_date(frm);
			}
		}
	}
});

erpnext.buying.PurchaseOrderController = erpnext.buying.BuyingController.extend({
	refresh: function(doc, cdt, cdn) {
		var me = this;
		this._super();
		var allow_receipt = false;
		var is_drop_ship = false;

		for (var i in cur_frm.doc.items) {
			var item = cur_frm.doc.items[i];
			if(item.delivered_by_supplier !== 1) {
				allow_receipt = true;
			} else {
				is_drop_ship = true;
			}

			if(is_drop_ship && allow_receipt) {
				break;
			}
		}

		cur_frm.set_df_property("drop_ship", "hidden", !is_drop_ship);

		if(doc.docstatus == 1 && !in_list(["Closed", "Delivered"], doc.status)) {
			if (this.frm.has_perm("submit")) {
				if(flt(doc.per_billed, 2) < 100 || doc.per_received < 100) {
					cur_frm.add_custom_button(__('Close'), this.close_purchase_order, __("Status"));
				}
			}

			if(is_drop_ship && doc.status!="Delivered"){
				cur_frm.add_custom_button(__('Delivered'),
					this.delivered_by_supplier, __("Status"));

				cur_frm.page.set_inner_btn_group_as_primary(__("Status"));
			}
		} else if(doc.docstatus===0) {
			cur_frm.cscript.add_from_mappers();
		}

		if(doc.docstatus == 1 && in_list(["Closed", "Delivered"], doc.status)) {
			if (this.frm.has_perm("submit")) {
				cur_frm.add_custom_button(__('Re-open'), this.unclose_purchase_order, __("Status"));
			}
		}

		if(doc.docstatus == 1 && doc.status != "Closed") {
			if(flt(doc.per_received, 2) < 100 && allow_receipt) {
				cur_frm.add_custom_button(__('Receipt'), this.make_purchase_receipt, __("Make"));

				if(doc.is_subcontracted==="Yes") {
					cur_frm.add_custom_button(__('Material to Supplier'),
						function() { me.make_stock_entry(); }, __("Transfer"));
				}
			}

			if(flt(doc.per_billed, 2) < 100)
				cur_frm.add_custom_button(__('Invoice'),
					this.make_purchase_invoice, __("Make"));

			if(flt(doc.per_billed)==0 && doc.status != "Delivered") {
				cur_frm.add_custom_button(__('Payment'), cur_frm.cscript.make_payment_entry, __("Make"));
			}

			if(!doc.auto_repeat) {
				cur_frm.add_custom_button(__('Subscription'), function() {
					erpnext.utils.make_subscription(doc.doctype, doc.name)
				}, __("Make"))
			}

			if(flt(doc.per_billed)==0) {
				this.frm.add_custom_button(__('Payment Request'),
					function() { me.make_payment_request() }, __("Make"));
			}

			cur_frm.page.set_inner_btn_group_as_primary(__("Make"));
		}
	},

	get_items_from_open_material_requests: function() {
		erpnext.utils.map_current_doc({
			method: "erpnext.stock.doctype.material_request.material_request.make_purchase_order_based_on_supplier",
			source_name: this.frm.doc.supplier,
			get_query_filters: {
				docstatus: ["!=", 2],
			}
		});
	},

	validate: function() {
		set_schedule_date(this.frm);
	},

	make_stock_entry: function() {
		var items = $.map(cur_frm.doc.items, function(d) { return d.bom ? d.item_code : false; });
		var me = this;

		if(items.length >= 1){
			me.raw_material_data = [];
			me.show_dialog = 1;
			let title = "";
			let fields = [
			{fieldtype:'Section Break', label: __('Raw Materials')},
			{fieldname: 'sub_con_rm_items', fieldtype: 'Table',
				fields: [
					{
						fieldtype:'Data',
						fieldname:'item_code',
						label: __('Item'),
						read_only:1,
						in_list_view:1
					},
					{
						fieldtype:'Data',
						fieldname:'rm_item_code',
						label: __('Raw Material'),
						read_only:1,
						in_list_view:1
					},
					{
						fieldtype:'Float',
						read_only:1,
						fieldname:'qty',
						label: __('Quantity'),
						read_only:1,
						in_list_view:1
					},
					{
						fieldtype:'Data',
						read_only:1,
						fieldname:'warehouse',
						label: __('Reserve Warehouse'),
						in_list_view:1
					},
					{
						fieldtype:'Float',
						read_only:1,
						fieldname:'rate',
						label: __('Rate'),
						hidden:1
					},
					{
						fieldtype:'Float',
						read_only:1,
						fieldname:'amount',
						label: __('Amount'),
						hidden:1
					},
					{
						fieldtype:'Link',
						read_only:1,
						fieldname:'uom',
						label: __('UOM'),
						hidden:1
					}
				],
				data: me.raw_material_data,
				get_data: function() {
					return me.raw_material_data;
				}
			}
		]

		me.dialog = new frappe.ui.Dialog({
			title: title, fields: fields
		});

		if (me.frm.doc['supplied_items']) {
			me.frm.doc['supplied_items'].forEach((item, index) => {
			if (item.rm_item_code && item.main_item_code) {
					me.raw_material_data.push ({
						'name':item.name,
						'item_code': item.main_item_code,
						'rm_item_code': item.rm_item_code,
						'item_name': item.rm_item_code,
						'qty': item.required_qty,
						'warehouse':item.reserve_warehouse,
						'rate':item.rate,
						'amount':item.amount,
						'stock_uom':item.stock_uom
					});
					me.dialog.fields_dict.sub_con_rm_items.grid.refresh();
				}
			})
		}

		me.dialog.show()
		this.dialog.set_primary_action(__('Transfer'), function() {
			me.values = me.dialog.get_values();
			if(me.values) {
				me.values.sub_con_rm_items.map((row,i) => {
					if (!row.item_code || !row.rm_item_code || !row.warehouse || !row.qty || row.qty === 0) {
						frappe.throw(__("Item Code, warehouse, quantity are required on row" + (i+1)));
					}
				})
				me._make_rm_stock_entry(me.dialog.fields_dict.sub_con_rm_items.grid.get_selected_children())
				me.dialog.hide()
				}
			});
		}

		me.dialog.get_close_btn().on('click', () => {
			me.dialog.hide();
		});

	},

	_make_rm_stock_entry: function(rm_items) {
		frappe.call({
			method:"erpnext.buying.doctype.purchase_order.purchase_order.make_rm_stock_entry",
			args: {
				purchase_order: cur_frm.doc.name,
				rm_items: rm_items
			}
			,
			callback: function(r) {
				var doclist = frappe.model.sync(r.message);
				frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
			}
		});
	},

	make_purchase_receipt: function() {
		frappe.model.open_mapped_doc({
			method: "erpnext.buying.doctype.purchase_order.purchase_order.make_purchase_receipt",
			frm: cur_frm
		})
	},

	make_purchase_invoice: function() {
		frappe.model.open_mapped_doc({
			method: "erpnext.buying.doctype.purchase_order.purchase_order.make_purchase_invoice",
			frm: cur_frm
		})
	},

	add_from_mappers: function() {
		var me = this;
		this.frm.add_custom_button(__('Material Request'),
			function() {
				erpnext.utils.map_current_doc({
					method: "erpnext.stock.doctype.material_request.material_request.make_purchase_order",
					source_doctype: "Material Request",
					target: me.frm,
					setters: {
						company: me.frm.doc.company
					},
					get_query_filters: {
						material_request_type: "Purchase",
						docstatus: 1,
						status: ["!=", "Stopped"],
						per_ordered: ["<", 99.99],
					}
				})
			}, __("Get items from"));

		this.frm.add_custom_button(__('Supplier Quotation'),
			function() {
				erpnext.utils.map_current_doc({
					method: "erpnext.buying.doctype.supplier_quotation.supplier_quotation.make_purchase_order",
					source_doctype: "Supplier Quotation",
					target: me.frm,
					setters: {
						company: me.frm.doc.company
					},
					get_query_filters: {
						docstatus: 1,
						status: ["!=", "Stopped"],
					}
				})
			}, __("Get items from"));

		this.frm.add_custom_button(__('Update rate as per last purchase'),
			function() {
				frappe.call({
					"method": "get_last_purchase_rate",
					"doc": me.frm.doc,
					callback: function(r, rt) {
						me.frm.dirty();
						me.frm.cscript.calculate_taxes_and_totals();
					}
				})
			}, __("Tools"));

		this.frm.add_custom_button(__('Link to Material Request'),
		function() {
			var my_items = [];
			for (var i in me.frm.doc.items) {
				if(!me.frm.doc.items[i].material_request){
					my_items.push(me.frm.doc.items[i].item_code);
				}
			}
			frappe.call({
				method: "erpnext.buying.utils.get_linked_material_requests",
				args:{
					items: my_items
				},
				callback: function(r) {
					if(r.exc) return;

					var i = 0;
					var item_length = me.frm.doc.items.length;
					while (i < item_length) {
						var qty = me.frm.doc.items[i].qty;
						(r.message[0] || []).forEach(function(d) {
							if (d.qty > 0 && qty > 0 && me.frm.doc.items[i].item_code == d.item_code && !me.frm.doc.items[i].material_request_item)
							{
								me.frm.doc.items[i].material_request = d.mr_name;
								me.frm.doc.items[i].material_request_item = d.mr_item;
								var my_qty = Math.min(qty, d.qty);
								qty = qty - my_qty;
								d.qty = d.qty  - my_qty;
								me.frm.doc.items[i].stock_qty = my_qty * me.frm.doc.items[i].conversion_factor;
								me.frm.doc.items[i].qty = my_qty;

								frappe.msgprint("Assigning " + d.mr_name + " to " + d.item_code + " (row " + me.frm.doc.items[i].idx + ")");
								if (qty > 0) {
									frappe.msgprint("Splitting " + qty + " units of " + d.item_code);
									var new_row = frappe.model.add_child(me.frm.doc, me.frm.doc.items[i].doctype, "items");
									item_length++;

									for (var key in me.frm.doc.items[i]) {
										new_row[key] = me.frm.doc.items[i][key];
									}

									new_row.idx = item_length;
									new_row["stock_qty"] = new_row.conversion_factor * qty;
									new_row["qty"] = qty;
									new_row["material_request"] = "";
									new_row["material_request_item"] = "";
								}
							}
						});
						i++;
					}
					refresh_field("items");
				}
			});
		}, __("Tools"));
	},

	tc_name: function() {
		this.get_terms();
	},

	items_add: function(doc, cdt, cdn) {
		var row = frappe.get_doc(cdt, cdn);
		if(doc.schedule_date) {
			row.schedule_date = doc.schedule_date;
			refresh_field("schedule_date", cdn, "items");
		} else {
			this.frm.script_manager.copy_from_first_row("items", row, ["schedule_date"]);
		}
	},

	unclose_purchase_order: function(){
		cur_frm.cscript.update_status('Re-open', 'Submitted')
	},

	close_purchase_order: function(){
		cur_frm.cscript.update_status('Close', 'Closed')
	},

	delivered_by_supplier: function(){
		cur_frm.cscript.update_status('Deliver', 'Delivered')
	},

	items_on_form_rendered: function() {
		set_schedule_date(this.frm);
	},

	schedule_date: function() {
		set_schedule_date(this.frm);
	}
});

// for backward compatibility: combine new and previous states
$.extend(cur_frm.cscript, new erpnext.buying.PurchaseOrderController({frm: cur_frm}));

cur_frm.cscript.update_status= function(label, status){
	frappe.call({
		method: "erpnext.buying.doctype.purchase_order.purchase_order.update_status",
		args: {status: status, name: cur_frm.doc.name},
		callback: function(r) {
			cur_frm.set_value("status", status);
			cur_frm.reload_doc();
		}
	})
}

cur_frm.fields_dict['items'].grid.get_field('project').get_query = function(doc, cdt, cdn) {
	return {
		filters:[
			['Project', 'status', 'not in', 'Completed, Cancelled']
		]
	}
}

cur_frm.fields_dict['items'].grid.get_field('bom').get_query = function(doc, cdt, cdn) {
	var d = locals[cdt][cdn]
	return {
		filters: [
			['BOM', 'item', '=', d.item_code],
			['BOM', 'is_active', '=', '1'],
			['BOM', 'docstatus', '=', '1'],
			['BOM', 'company', '=', doc.company]
		]
	}
}

function set_schedule_date(frm) {
	if(frm.doc.schedule_date){
		erpnext.utils.copy_value_in_all_rows(frm.doc, frm.doc.doctype, frm.doc.name, "items", "schedule_date");
	}
}

frappe.provide("erpnext.buying");

frappe.ui.form.on("Purchase Order", "is_subcontracted", function(frm) {
	if (frm.doc.is_subcontracted === "Yes") {
		erpnext.buying.get_default_bom(frm);
	}
});
