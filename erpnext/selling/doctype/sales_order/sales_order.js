// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

{% include 'erpnext/selling/sales_common.js' %}

frappe.ui.form.on("Sales Order", {
	setup: function(frm) {
		frm.custom_make_buttons = {
			'Delivery Note': __('Delivery Note'),
			'Pick List': __('Pick List'),
			'Sales Invoice': __('Sales Invoice'),
			'Material Request': __('Material Request'),
			'Purchase Order': __('Purchase Order'),
			'Project': __('Project'),
			'Payment Entry': __("Payment"),
			'Purchase Invoice': __('Purchase Invoice'),
			'Work Order': __("Work Order"),
			'Auto Repeat': __("Subscription"),
			'Payment Request': __("Payment Request"),
			'Vehicle': __("Reserved Vehicles"),
		}

		frm.set_query('company_address', function(doc) {
			if(!doc.company) {
				frappe.throw(__('Please set Company'));
			}

			return {
				query: 'frappe.contacts.doctype.address.address.address_query',
				filters: {
					link_doctype: 'Company',
					link_name: doc.company
				}
			};
		})
	},
	refresh: function(frm) {
		if(frm.doc.docstatus === 1 && frm.doc.status !== 'Closed'
			&& flt(frm.doc.per_delivered, 6) < 100 && flt(frm.doc.per_billed, 6) < 100) {
			frm.add_custom_button(__('Update Items'), () => {
				erpnext.utils.update_child_items({
					frm: frm,
					child_docname: "items",
					child_doctype: "Sales Order Detail",
					cannot_add_row: false,
				})
			});
		}
	},
	onload: function(frm) {
		if (!frm.doc.transaction_date){
			frm.set_value('transaction_date', frappe.datetime.get_today())
		}
		erpnext.queries.setup_queries(frm, "Warehouse", function() {
			return erpnext.queries.warehouse(frm.doc);
		});

		erpnext.queries.setup_warehouse_query(frm);

		if (frm.doc.__islocal) {
			frm.events.delivery_date(frm);
		}
	},

	delivery_date: function(frm) {
		if (frm.doc.delivery_date) {
			$.each(frm.doc.items || [], function (i, d) {
				d.delivery_date = frm.doc.delivery_date;
			});
			refresh_field("items");
		}
	}
});

frappe.ui.form.on("Sales Order Item", {
	item_code: function(frm,cdt,cdn) {
		var row = locals[cdt][cdn];
		if (frm.doc.delivery_date) {
			row.delivery_date = frm.doc.delivery_date;
			refresh_field("delivery_date", cdn, "items");
		} else {
			frm.script_manager.copy_from_first_row("items", row, ["delivery_date"]);
		}
	},
	delivery_date: function(frm, cdt, cdn) {
		if(!frm.doc.delivery_date) {
			erpnext.utils.copy_value_in_all_rows(frm.doc, cdt, cdn, "items", "delivery_date");
		}
	}
});

erpnext.selling.SalesOrderController = class SalesOrderController extends erpnext.selling.SellingController {
	onload(doc, dt, dn) {
		super.onload();
	}

	refresh(doc, dt, dn) {
		super.refresh();
		this.setup_buttons();

		// formatter for items table
		this.frm.set_indicator_formatter('item_code', function(doc) {
			if (doc.docstatus === 0) {
				if (!doc.is_stock_item) {
					return "blue";
				} else if (!doc.actual_qty) {
					return "red";
				} else if (doc.actual_qty < doc.stock_qty) {
					return "orange";
				} else {
					return "green";
				}
			} else {
				if (!doc.delivered_qty) {
					return "orange";
				} else if (doc.delivered_qty < doc.qty) {
					return "yellow";
				} else {
					return "green";
				}
			}
		});

		if (this.frm.doc.__islocal) {
			this.set_skip_delivery_note();
		}
	}

	setup_buttons() {
		var me = this;
		let allow_delivery = false;

		if (me.frm.doc.docstatus == 0) {
			me.add_get_latest_price_button();
		}
		if (me.frm.doc.docstatus == 1) {
			me.add_update_price_list_button();
		}

		if (me.frm.doc.docstatus==1) {
			if(me.frm.has_perm("submit")) {
				if(me.frm.doc.status === 'On Hold') {
				   // un-hold
				   me.frm.add_custom_button(__('Resume'), function() {
					   me.update_status('Resume', 'Draft')
				   }, __("Status"));

				   if(flt(me.frm.doc.per_delivered, 6) < 100 || flt(me.frm.doc.per_completed) < 100) {
					   // close
					   me.frm.add_custom_button(__('Close'), () => me.close_sales_order(), __("Status"))
				   }
				}
				else if(me.frm.doc.status === 'Closed') {
				   // un-close
				   me.frm.add_custom_button(__('Re-Open'), function() {
					   me.update_status('Re-Open', 'Draft')
				   }, __("Status"));
			   }
			}

			if(me.frm.doc.status !== 'Closed') {
				if(me.frm.doc.status !== 'On Hold') {
					allow_delivery = me.frm.doc.items.some(item => item.delivered_by_supplier === 0 && item.qty > flt(item.delivered_qty))
						&& !me.frm.doc.skip_delivery_note;

					if (me.frm.has_perm("submit")) {
						if(flt(me.frm.doc.per_delivered, 6) < 100 || flt(me.frm.doc.per_completed) < 100) {
							// hold
							me.frm.add_custom_button(__('Hold'), () => me.hold_sales_order(), __("Status"))
							// close
							me.frm.add_custom_button(__('Close'), () => me.close_sales_order(), __("Status"))
						}
					}

					// delivery note
					if(flt(me.frm.doc.per_delivered, 6) < 100 && ["Sales", "Shopping Cart"].indexOf(me.frm.doc.order_type)!==-1 && allow_delivery) {
						me.frm.add_custom_button(__('Delivery Note'), () => me.make_delivery_note_based_on(), __('Create'));
						me.frm.add_custom_button(__('Work Order'), () => me.make_work_order(), __('Create'));

						var has_vehicles = me.frm.doc.items.some(d => d.is_vehicle);
						if (has_vehicles) {
							me.frm.add_custom_button(__('Reserved Vehicles'), () => me.create_vehicles(), __('Create'));
						}
					}

					me.frm.add_custom_button(__('Pick List'), () => me.create_pick_list(), __('Create'));

					// sales invoice
					if(flt(me.frm.doc.per_completed, 6) < 100) {
						me.frm.add_custom_button(__('Sales Invoice'), () => me.make_sales_invoice(), __('Create'));
					}

					// material request
					if(!me.frm.doc.order_type || ["Sales", "Shopping Cart"].indexOf(me.frm.doc.order_type)!==-1
						&& flt(me.frm.doc.per_delivered, 6) < 100) {
						me.frm.add_custom_button(__('Material Request'), () => me.make_material_request(), __('Create'));
						me.frm.add_custom_button(__('Request for Raw Materials'), () => me.make_raw_material_request(), __('Create'));
					}

					// make purchase order
					me.frm.add_custom_button(__('Purchase Order'), () => me.make_purchase_order(), __('Create'));

					// project
					if(flt(me.frm.doc.per_delivered, 2) < 100 && ["Sales", "Shopping Cart"].indexOf(me.frm.doc.order_type)!==-1 && allow_delivery) {
						me.frm.add_custom_button(__('Project'), () => me.make_project(), __('Create'));
					}

					if(!me.frm.doc.auto_repeat) {
						me.frm.add_custom_button(__('Subscription'), function() {
							erpnext.utils.make_subscription(me.frm.doc.doctype, me.frm.doc.name)
						}, __('Create'))
					}

					if (me.frm.doc.docstatus === 1 && !me.frm.doc.inter_company_reference) {
						let me = this;
						frappe.model.with_doc("Customer", me.frm.doc.customer, () => {
							let customer = frappe.model.get_doc("Customer", me.frm.doc.customer);
							let internal = customer.is_internal_customer;
							let disabled = customer.disabled;
							if (internal === 1 && disabled === 0) {
								me.frm.add_custom_button("Inter Company Order", function() {
									me.make_inter_company_order();
								}, __('Create'));
							}
						});
					}
				}
				// payment request
				if(flt(me.frm.doc.per_completed) < 100) {
					me.frm.add_custom_button(__('Payment Request'), () => me.make_payment_request(), __('Create'));
					me.frm.add_custom_button(__('Payment'), () => me.make_payment_entry(), __('Create'));
				}
				me.frm.page.set_inner_btn_group_as_primary(__('Create'));
			}
		}

		if (me.frm.doc.docstatus === 0) {
			me.frm.add_custom_button(__('Quotation'),
				function() {
					erpnext.utils.map_current_doc({
						method: "erpnext.selling.doctype.quotation.quotation.make_sales_order",
						source_doctype: "Quotation",
						target: me.frm,
						setters: [
							{
								label: "Customer",
								fieldname: "party_name",
								fieldtype: "Link",
								options: "Customer",
								default: me.frm.doc.customer || undefined
							},{
								fieldtype: 'Link',
								label: __('Project'),
								options: 'Project',
								fieldname: 'project',
								default: me.frm.doc.project || undefined,
							}
						],
						get_query_filters: {
							company: me.frm.doc.company,
							docstatus: 1,
							status: ["!=", "Lost"]
						}
					})
				}, __("Get Items From"));

			me.add_get_applicable_items_button();
			me.add_get_project_template_items_button();
		}
	}

	create_pick_list() {
		frappe.model.open_mapped_doc({
			method: "erpnext.selling.doctype.sales_order.sales_order.create_pick_list",
			frm: this.frm
		})
	}

	make_work_order() {
		var me = this;
		this.frm.call({
			doc: this.frm.doc,
			method: 'get_work_order_items',
			callback: function(r) {
				if(!r.message) {
					frappe.msgprint({
						title: __('Work Order not created'),
						message: __('No Items with Bill of Materials to Manufacture'),
						indicator: 'orange'
					});
					return;
				}
				else if(!r.message) {
					frappe.msgprint({
						title: __('Work Order not created'),
						message: __('Work Order already created for all items with BOM'),
						indicator: 'orange'
					});
					return;
				} else {
					const fields = [{
						label: 'Items',
						fieldtype: 'Table',
						fieldname: 'items',
						description: __('Select BOM and Qty for Production'),
						fields: [{
							fieldtype: 'Read Only',
							fieldname: 'item_code',
							label: __('Item Code'),
							in_list_view: 1
						}, {
							fieldtype: 'Link',
							fieldname: 'bom',
							options: 'BOM',
							reqd: 1,
							label: __('Select BOM'),
							in_list_view: 1,
							get_query: function (doc) {
								return { filters: { item: doc.item_code } };
							}
						}, {
							fieldtype: 'Float',
							fieldname: 'pending_qty',
							reqd: 1,
							label: __('Qty'),
							in_list_view: 1
						}, {
							fieldtype: 'Data',
							fieldname: 'sales_order_item',
							reqd: 1,
							label: __('Sales Order Item'),
							hidden: 1
						}],
						data: r.message,
						get_data: () => {
							return r.message
						}
					}]
					var d = new frappe.ui.Dialog({
						title: __('Select Items to Manufacture'),
						fields: fields,
						primary_action: function() {
							var data = d.get_values();
							me.frm.call({
								method: 'make_work_orders',
								args: {
									items: data,
									company: me.frm.doc.company,
									sales_order: me.frm.docname,
									project: me.frm.project
								},
								freeze: true,
								callback: function(r) {
									if(r.message) {
										frappe.msgprint({
											message: __('Work Orders Created: {0}',
												[r.message.map(function(d) {
													return repl('<a href="/app/work-order/%(name)s">%(name)s</a>', {name:d})
												}).join(', ')]),
											indicator: 'green'
										})
									}
									d.hide();
								}
							});
						},
						primary_action_label: __('Create')
					});
					d.show();
				}
			}
		});
	}

	create_vehicles() {
		var me = this;
		if (me.frm.doc.docstatus !== 1) {
			return;
		}

		frappe.call({
			method: "erpnext.vehicles.doctype.vehicle.vehicle.get_sales_order_vehicle_qty",
			args: {
				sales_order: me.frm.doc.name
			},
			callback: function (r) {
				if (r.message) {
					const fields = [{
						label: 'Items',
						fieldtype: 'Table',
						fieldname: 'items',
						fields: [{
							fieldtype: 'Read Only',
							fieldname: 'item_code',
							label: __('Item Code'),
							in_list_view: 1
						}, {
							fieldtype: 'Float',
							fieldname: 'ordered_qty',
							read_only: 1,
							label: __('Ordered'),
							in_list_view: 1
						}, {
							fieldtype: 'Float',
							fieldname: 'reserved_qty',
							read_only: 1,
							label: __('Reserved'),
							in_list_view: 1
						}, {
							fieldtype: 'Float',
							fieldname: 'actual_qty',
							read_only: 1,
							label: __('In Stock'),
							in_list_view: 1
						}, {
							fieldtype: 'Int',
							fieldname: 'to_create_qty',
							label: __('To Create'),
							mandatory: 1,
							in_list_view: 1
						}],
						data: r.message,
						get_data: () => {
							return r.message
						}
					}];

					var d = new frappe.ui.Dialog({
						title: __('Quantity of Reserved Vehicles to create'),
						fields: fields,
						size: 'large',
						primary_action: function() {
							var data = d.get_values().items;
							var to_reserve_qty_map = {};
							$.each(data || [], function (i, d) {
								to_reserve_qty_map[d.item_code] = cint(d.to_create_qty);
							});
							frappe.call({
								method: 'erpnext.vehicles.doctype.vehicle.vehicle.create_vehicle_from_so',
								args: {
									sales_order: me.frm.doc.name,
									to_reserve_qty_map: to_reserve_qty_map
								},
								callback: function () {
									d.hide();
								},
								freeze: true
							});
						},
						primary_action_label: __('Create')
					});
					d.show();
				}
			}
		})
	}

	tc_name() {
		this.get_terms();
	}

	set_skip_delivery_note() {
		var items = (this.frm.doc.items || []).filter(d => d.item_code);
		if (!items.length) {
			this.frm.set_value('skip_delivery_note', 0);
			return;
		}

		var has_deliverable = items.some(d => d.is_stock_item || d.is_fixed_asset);
		this.frm.set_value('skip_delivery_note', cint(!has_deliverable));
	}

	make_material_request() {
		frappe.model.open_mapped_doc({
			method: "erpnext.selling.doctype.sales_order.sales_order.make_material_request",
			frm: this.frm
		})
	}

	make_raw_material_request() {
		var me = this;
		this.frm.call({
			doc: this.frm.doc,
			method: 'get_work_order_items',
			args: {
				for_raw_material_request: 1
			},
			callback: function(r) {
				if(!r.message || !r.message.length) {
					frappe.msgprint({
						message: __('No Items with Bill of Materials.'),
						indicator: 'orange'
					});
					return;
				}
				else {
					me.make_raw_material_request_dialog(r);
				}
			}
		});
	}

	make_raw_material_request_dialog(r) {
		var me = this;
		var fields = [
			{fieldtype:'Check', fieldname:'include_exploded_items', default: 1, label: __('Include Exploded Items')},
			{fieldtype:'Check', fieldname:'ignore_existing_ordered_qty', label: __('Ignore Existing Ordered Qty')},
			{fieldtype:'Link', options: 'Warehouse', fieldname:'for_warehouse', label: __('For Warehouse'), reqd: 1,
				default: r.message && r.message[0].warehouse, get_query: () => erpnext.queries.warehouse(me.frm.doc)},
			{
				fieldtype:'Table', fieldname: 'items',
				description: __('Select BOM, Qty and For Warehouse'),
				fields: [
					{fieldtype:'Link', options: "Item", fieldname:'item_code', label: __('Item Code'), read_only: 1, columns: 5, in_list_view:1},
					{fieldtype:'Data', fieldname:'item_name', label: __('Item Name'), read_only: 1},
					{fieldtype:'Link', fieldname:'bom', options: 'BOM', reqd: 1, label: __('BOM'), columns: 3, in_list_view:1,
						get_query: function(doc) {
							return {filters: {item: doc.item_code}};
						}
					},
					{fieldtype:'Float', fieldname:'required_qty', reqd: 1, label: __('Qty'), columns: 2, in_list_view:1},
				],
				data: r.message,
				get_data: function() {
					return r.message
				}
			}
		]
		var d = new frappe.ui.Dialog({
			title: __("Items for Raw Material Request"),
			fields: fields,
			size: "large",
			primary_action: function() {
				var data = d.get_values();
				frappe.call({
					method: 'erpnext.selling.doctype.sales_order.sales_order.make_raw_material_request',
					args: {
						items: data,
						company: me.frm.doc.company,
						sales_order: me.frm.docname,
						project: me.frm.project
					},
					freeze: true,
					callback: function(r) {
						if(r.message) {
							var doc = frappe.model.sync(r.message);
							frappe.set_route("Form", r.message.doctype, r.message.name);
						}
						d.hide();
					}
				});
			},
			primary_action_label: __('Create')
		});
		d.show();
	}

	make_delivery_note_based_on() {
		var me = this;

		var warehouses = [];
		var delivery_dates = [];
		$.each(this.frm.doc.items || [], function(i, d) {
			if(d.warehouse && !warehouses.includes(d.warehouse)) {
				warehouses.push(d.warehouse);
			}
			if(!delivery_dates.includes(d.delivery_date)) {
				delivery_dates.push(d.delivery_date);
			}
		});

		var item_grid = this.frm.fields_dict["items"].grid;
		if(item_grid.get_selected().length) {
			me.make_delivery_note();
		} else if (warehouses.length > 1) {
			me.make_delivery_note_based_on_warehouse(warehouses);
		} else if (delivery_dates.length > 1) {
			me.make_delivery_note_based_on_delivery_date(delivery_dates);
		} else {
			me.make_delivery_note();
		}
	}

	make_delivery_note_based_on_warehouse(warehouses) {
		var me = this;
		var item_grid = this.frm.fields_dict["items"].grid;

		var dialog = new frappe.ui.Dialog({
			title: __("Select Items based on Warehouse"),
			fields: [{fieldtype: "HTML", fieldname: "warehouses_html"}]
		});

		var html = $(`
			<div style="border: 1px solid #d1d8dd">
				<div class="list-item list-item--head">
					<div class="list-item__content list-item__content--flex-2">
						${__('Warehouse')}
					</div>
				</div>
				${warehouses.map(warehouse => `
					<div class="list-item">
						<div class="list-item__content list-item__content--flex-2">
							<label>
							<input type="checkbox" data-warehouse="${warehouse}" checked="checked"/>
							${warehouse}
							</label>
						</div>
					</div>
				`).join("")}
			</div>
		`);

		var wrapper = dialog.fields_dict.warehouses_html.$wrapper;
		wrapper.html(html);

		dialog.set_primary_action(__("Select"), function() {
			var warehouses = wrapper.find('input[type=checkbox]:checked')
				.map((i, el) => $(el).attr('data-warehouse')).toArray();

			if(!warehouses) return;

			$.each(warehouses, function(i, d) {
				$.each(item_grid.grid_rows || [], function(j, row) {
					if(row.doc.warehouse === d) {
						row.doc.__checked = 1;
					}
				});
			})

			me.make_delivery_note(warehouses.length === 1 ? warehouses[0] : null);
			dialog.hide();
		});
		dialog.show();
	}

	make_delivery_note_based_on_delivery_date(delivery_dates) {
		var me = this;
		var item_grid = this.frm.fields_dict["items"].grid;

		var dialog = new frappe.ui.Dialog({
			title: __("Select Items based on Delivery Date"),
			fields: [{fieldtype: "HTML", fieldname: "dates_html"}]
		});

		var html = $(`
			<div style="border: 1px solid #d1d8dd">
				<div class="list-item list-item--head">
					<div class="list-item__content list-item__content--flex-2">
						${__('Delivery Date')}
					</div>
				</div>
				${delivery_dates.map(date => `
					<div class="list-item">
						<div class="list-item__content list-item__content--flex-2">
							<label>
							<input type="checkbox" data-date="${date}" checked="checked"/>
							${frappe.datetime.str_to_user(date)}
							</label>
						</div>
					</div>
				`).join("")}
			</div>
		`);

		var wrapper = dialog.fields_dict.dates_html.$wrapper;
		wrapper.html(html);

		dialog.set_primary_action(__("Select"), function() {
			var dates = wrapper.find('input[type=checkbox]:checked')
				.map((i, el) => $(el).attr('data-date')).toArray();

			if(!dates) return;

			$.each(dates, function(i, d) {
				$.each(item_grid.grid_rows || [], function(j, row) {
					if(row.doc.delivery_date == d) {
						row.doc.__checked = 1;
					}
				});
			})
			me.make_delivery_note();
			dialog.hide();
		});
		dialog.show();
	}

	make_delivery_note(warehouse) {
		frappe.model.open_mapped_doc({
			method: "erpnext.selling.doctype.sales_order.sales_order.make_delivery_note",
			frm: this.frm,
			args: {
				warehouse: warehouse
			}
		})
	}

	make_sales_invoice() {
		frappe.model.open_mapped_doc({
			method: "erpnext.selling.doctype.sales_order.sales_order.make_sales_invoice",
			frm: this.frm
		})
	}

	make_project() {
		frappe.model.open_mapped_doc({
			method: "erpnext.selling.doctype.sales_order.sales_order.make_project",
			frm: this.frm
		})
	}

	make_inter_company_order() {
		frappe.model.open_mapped_doc({
			method: "erpnext.selling.doctype.sales_order.sales_order.make_inter_company_purchase_order",
			frm: this.frm
		});
	}

	make_purchase_invoice() {
		var me = this;
		var dialog = new frappe.ui.Dialog({
			title: __("Supplier"),
			fields: [
				{"fieldtype": "Link", "label": __("Supplier"), "fieldname": "supplier", "options":"Supplier", "reqd":true},
				{"fieldtype": "Button", "label": __("Make Purchase Invoice"), "fieldname": "make_purchase_invoice", "cssClass": "btn-primary"},
			]
		});

		dialog.fields_dict.make_purchase_invoice.$input.click(function() {
			var args = dialog.get_values();
			dialog.hide();
			return frappe.call({
				type: "GET",
				method: "erpnext.selling.doctype.sales_order.sales_order.make_purchase_invoice",
				args: {
					"supplier": args.supplier,
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
	}

	make_purchase_order() {
		var me = this;
		var dialog = new frappe.ui.Dialog({
			title: __("For Supplier"),
			fields: [
				{"fieldtype": "Link", "label": __("Supplier"), "fieldname": "supplier", "options":"Supplier",
				 "description": __("Leave the field empty to make purchase orders for all suppliers"),
					"get_query": function () {
						return {
							query:"erpnext.selling.doctype.sales_order.sales_order.get_supplier",
							filters: {'parent': me.frm.doc.name}
						}
					}},
					{fieldname: 'items_for_po', fieldtype: 'Table', label: 'Select Items',
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
							fieldname:'item_name',
							label: __('Item name'),
							read_only:1,
							in_list_view:1
						},
						{
							fieldtype:'Float',
							fieldname:'qty',
							label: __('Quantity'),
							read_only: 1,
							in_list_view:1
						},
						{
							fieldtype:'Link',
							read_only:1,
							fieldname:'uom',
							label: __('UOM'),
							in_list_view:1
						}
					],
					data: cur_frm.doc.items,
					get_data: function() {
						return cur_frm.doc.items
					}
				},

				{"fieldtype": "Button", "label": __('Create Purchase Order'), "fieldname": "make_purchase_order", "cssClass": "btn-primary"},
			]
		});

		dialog.fields_dict.make_purchase_order.$input.click(function() {
			var args = dialog.get_values();
			let selected_items = dialog.fields_dict.items_for_po.grid.get_selected_children()
			if(selected_items.length == 0) {
				frappe.throw({message: 'Please select Item form Table', title: __('Message'), indicator:'blue'})
			}
			let selected_items_list = []
			for(let i in selected_items){
				selected_items_list.push(selected_items[i].item_code)
			}
			dialog.hide();
			return frappe.call({
				type: "GET",
				method: "erpnext.selling.doctype.sales_order.sales_order.make_purchase_order",
				args: {
					"source_name": me.frm.doc.name,
					"for_supplier": args.supplier,
					"selected_items": selected_items_list
				},
				freeze: true,
				callback: function(r) {
					if(!r.exc) {
						// var args = dialog.get_values();
						if (args.supplier){
							var doc = frappe.model.sync(r.message);
							frappe.set_route("Form", r.message.doctype, r.message.name);
						}
						else{
							frappe.route_options = {
								"sales_order": me.frm.doc.name
							}
							frappe.set_route("List", "Purchase Order");
						}
					}
				}
			})
		});
		dialog.get_field("items_for_po").grid.only_sortable()
		dialog.get_field("items_for_po").refresh()
		dialog.show();
	}

	hold_sales_order() {
		var me = this;
		var d = new frappe.ui.Dialog({
			title: __('Reason for Hold'),
			fields: [
				{
					"fieldname": "reason_for_hold",
					"fieldtype": "Text",
					"reqd": 1,
				}
			],
			primary_action: function() {
				var data = d.get_values();
				frappe.call({
					method: "frappe.desk.form.utils.add_comment",
					args: {
						reference_doctype: me.frm.doctype,
						reference_name: me.frm.docname,
						content: __('Reason for hold: ')+data.reason_for_hold,
						comment_email: frappe.session.user
					},
					callback: function(r) {
						if(!r.exc) {
							me.update_status('Hold', 'On Hold')
							d.hide();
						}
					}
				});
			}
		});
		d.show();
	}

	close_sales_order() {
		this.update_status("Close", "Closed")
	}

	update_status(label, status) {
		var doc = this.frm.doc;
		var me = this;
		frappe.ui.form.is_saving = true;
		frappe.call({
			method: "erpnext.selling.doctype.sales_order.sales_order.update_status",
			args: {status: status, name: doc.name},
			callback: function(r){
				me.frm.reload_doc();
			},
			always: function() {
				frappe.ui.form.is_saving = false;
			}
		});
	}
};
extend_cscript(cur_frm.cscript, new erpnext.selling.SalesOrderController({frm: cur_frm}));
