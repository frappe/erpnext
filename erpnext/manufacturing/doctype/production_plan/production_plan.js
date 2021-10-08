// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Production Plan', {
	setup: function(frm) {
		frm.custom_make_buttons = {
			'Work Order': 'Work Order / Subcontract PO',
			'Material Request': 'Material Request',
		};

		frm.fields_dict['po_items'].grid.get_field('warehouse').get_query = function(doc) {
			return {
				filters: {
					company: doc.company
				}
			}
		}

		frm.set_query('for_warehouse', function(doc) {
			return {
				filters: {
					company: doc.company,
					is_group: 0
				}
			}
		});

		frm.set_query('material_request', 'material_requests', function() {
			return {
				filters: {
					material_request_type: "Manufacture",
					docstatus: 1,
					status: ["!=", "Stopped"],
				}
			};
		});

		frm.fields_dict['po_items'].grid.get_field('item_code').get_query = function(doc) {
			return {
				query: "erpnext.controllers.queries.item_query",
				filters:{
					'is_stock_item': 1,
				}
			}
		}

		frm.fields_dict['po_items'].grid.get_field('bom_no').get_query = function(doc, cdt, cdn) {
			var d = locals[cdt][cdn];
			if (d.item_code) {
				return {
					query: "erpnext.controllers.queries.bom",
					filters:{'item': cstr(d.item_code)}
				}
			} else frappe.msgprint(__("Please enter Item first"));
		}

		frm.fields_dict['mr_items'].grid.get_field('warehouse').get_query = function(doc) {
			return {
				filters: {
					company: doc.company
				}
			}
		}
	},

	refresh: function(frm) {
		if (frm.doc.docstatus === 1) {
			frm.trigger("show_progress");

			if (frm.doc.status !== "Completed") {
				frm.add_custom_button(__("Work Order Tree"), ()=> {
					frappe.set_route('Tree', 'Work Order', {production_plan: frm.doc.name});
				}, __('View'));

				frm.add_custom_button(__("Production Plan Summary"), ()=> {
					frappe.set_route('query-report', 'Production Plan Summary', {production_plan: frm.doc.name});
				}, __('View'));

				if  (frm.doc.status === "Closed") {
					frm.add_custom_button(__("Re-open"), function() {
						frm.events.close_open_production_plan(frm, false);
					}, __("Status"));
				} else {
					frm.add_custom_button(__("Close"), function() {
						frm.events.close_open_production_plan(frm, true);
					}, __("Status"));
				}

				if (frm.doc.po_items && frm.doc.status !== "Closed") {
					frm.add_custom_button(__("Work Order / Subcontract PO"), ()=> {
						frm.trigger("make_work_order");
					}, __('Create'));
				}

				if (frm.doc.mr_items && !in_list(['Material Requested', 'Closed'], frm.doc.status)) {
					frm.add_custom_button(__("Material Request"), ()=> {
						frm.trigger("make_material_request");
					}, __('Create'));
				}
			}
		}

		if (frm.doc.status !== "Closed") {
			frm.page.set_inner_btn_group_as_primary(__('Create'));
		}
		frm.trigger("material_requirement");

		const projected_qty_formula = ` <table class="table table-bordered" style="background-color: #f9f9f9;">
			<tr><td style="padding-left:25px">
				<div>
				<h3 style="text-decoration: underline;">
					<a href = "https://erpnext.com/docs/user/manual/en/stock/projected-quantity">
						${__("Projected Quantity Formula")}
					</a>
				</h3>
					<div>
						<h3 style="font-size: 13px">
							(Actual Qty + Planned Qty + Requested Qty + Ordered Qty) - (Reserved Qty + Reserved for Production + Reserved for Subcontract)
						</h3>
					</div>
					<br>
					<div>
						<ul>
							<li>
								${__("Actual Qty: Quantity available in the warehouse.")}
							</li>
							<li>
								${__("Planned Qty: Quantity, for which, Work Order has been raised, but is pending to be manufactured.")}
							</li>
							<li>
								${__('Requested Qty: Quantity requested for purchase, but not ordered.')}
							</li>
							<li>
								${__('Ordered Qty: Quantity ordered for purchase, but not received.')}
							</li>
							<li>
								${__("Reserved Qty: Quantity ordered for sale, but not delivered.")}
							</li>
							<li>
								${__('Reserved Qty for Production: Raw materials quantity to make manufacturing items.')}
							</li>
							<li>
								${__('Reserved Qty for Subcontract: Raw materials quantity to make subcontracted items.')}
							</li>
						</ul>
					</div>
				</div>
			</td></tr>
		</table>`;

		set_field_options("projected_qty_formula", projected_qty_formula);
	},

	close_open_production_plan: (frm, close=false) => {
		frappe.call({
			method: "set_status",
			freeze: true,
			doc: frm.doc,
			args: {close : close},
			callback: function() {
				frm.reload_doc();
			}
		});
	},

	make_work_order: function(frm) {
		frappe.call({
			method: "make_work_order",
			freeze: true,
			doc: frm.doc,
			callback: function() {
				frm.reload_doc();
			}
		});
	},

	make_material_request: function(frm) {

		frappe.confirm(__("Do you want to submit the material request"),
			function() {
				frm.events.create_material_request(frm, 1);
			},
			function() {
				frm.events.create_material_request(frm, 0);
			}
		);
	},

	create_material_request: function(frm, submit) {
		frm.doc.submit_material_request = submit;

		frappe.call({
			method: "make_material_request",
			freeze: true,
			doc: frm.doc,
			callback: function(r) {
				frm.reload_doc();
			}
		});
	},

	get_sales_orders: function(frm) {
		frappe.call({
			method: "get_open_sales_orders",
			doc: frm.doc,
			callback: function(r) {
				refresh_field("sales_orders");
			}
		});
	},

	get_material_request: function(frm) {
		frappe.call({
			method: "get_pending_material_requests",
			doc: frm.doc,
			callback: function() {
				refresh_field('material_requests');
			}
		});
	},

	get_items: function (frm) {
		frm.clear_table('prod_plan_references');

		frappe.call({
			method: "get_items",
			freeze: true,
			doc: frm.doc,
			callback: function () {
				refresh_field('po_items');
			}
		});
	},
	combine_items: function (frm) {
		frm.clear_table('prod_plan_references');

		frappe.call({
			method: "get_items",
			freeze: true,
			doc: frm.doc,
		});
	},

	get_sub_assembly_items: function(frm) {
		frm.dirty();

		frappe.call({
			method: "get_sub_assembly_items",
			freeze: true,
			doc: frm.doc,
			callback: function() {
				refresh_field("sub_assembly_items");
			}
		});
	},

	get_items_for_mr: function(frm) {
		if (!frm.doc.for_warehouse) {
			frappe.throw(__("To make material requests, 'Make Material Request for Warehouse' field is mandatory"));
		}

		if (frm.doc.ignore_existing_ordered_qty) {
			frm.events.get_items_for_material_requests(frm);
		} else {
			const title = __("Transfer Materials For Warehouse {0}", [frm.doc.for_warehouse]);
			var dialog = new frappe.ui.Dialog({
				title: title,
				fields: [
					{
						'label': __('Target Warehouse'),
						'fieldtype': 'Link',
						'fieldname': 'target_warehouse',
						'read_only': true,
						'default': frm.doc.for_warehouse
					},
					{
						'label': __('Source Warehouses (Optional)'),
						'fieldtype': 'Table MultiSelect',
						'fieldname': 'warehouses',
						'options': 'Production Plan Material Request Warehouse',
						'description': __('If source warehouse selected then system will create the material request with type Material Transfer from Source to Target warehouse. If not selected then will create the material request with type Purchase for the target warehouse.'),
						get_query: function () {
							return {
								filters: {
									company: frm.doc.company
								}
							};
						},
					},
				]
			});

			dialog.show();

			dialog.set_primary_action(__("Get Items"), () => {
				let warehouses = dialog.get_values().warehouses;
				frm.events.get_items_for_material_requests(frm, warehouses);
				dialog.hide();
			});
		}
	},

	get_items_for_material_requests: function(frm, warehouses) {
		const set_fields = ['actual_qty', 'item_code','item_name', 'description', 'uom', 'from_warehouse',
			'min_order_qty', 'required_bom_qty', 'quantity', 'sales_order', 'warehouse', 'projected_qty', 'ordered_qty',
			'reserved_qty_for_production', 'material_request_type'];

		frappe.call({
			method: "erpnext.manufacturing.doctype.production_plan.production_plan.get_items_for_material_requests",
			freeze: true,
			args: {
				doc: frm.doc,
				warehouses: warehouses || []
			},
			callback: function(r) {
				if(r.message) {
					frm.set_value('mr_items', []);
					$.each(r.message, function(i, d) {
						var item = frm.add_child('mr_items');
						for (let key in d) {
							if (d[key] && in_list(set_fields, key)) {
								item[key] = d[key];
							}
						}
					});
				}
				refresh_field('mr_items');
			}
		});
	},

	for_warehouse: function(frm) {
		if (frm.doc.mr_items && frm.doc.for_warehouse) {
			frm.trigger("get_items_for_mr");
		}
	},

	download_materials_required: function(frm) {
		const fields = [{
			fieldname: 'warehouses',
			fieldtype: 'Table MultiSelect',
			label: __('Warehouses'),
			default: frm.doc.from_warehouse,
			options: "Production Plan Material Request Warehouse",
			get_query: function () {
				return {
					filters: {
						company: frm.doc.company
					}
				};
			},
		}];

		frappe.prompt(fields, (row) => {
			let get_template_url = 'erpnext.manufacturing.doctype.production_plan.production_plan.download_raw_materials';
			open_url_post(frappe.request.url, {
				cmd: get_template_url,
				doc: frm.doc,
				warehouses: row.warehouses
			});
		}, __('Select Warehouses to get Stock for Materials Planning'), __('Get Stock'));
	},

	show_progress: function(frm) {
		var bars = [];
		var message = '';
		var title = '';

		// produced qty
		let item_wise_qty = {};
		frm.doc.po_items.forEach((data) => {
			if(!item_wise_qty[data.item_code]) {
				item_wise_qty[data.item_code] = data.produced_qty;
			} else {
				item_wise_qty[data.item_code] += data.produced_qty;
			}
		})

		if (item_wise_qty) {
			for (var key in item_wise_qty) {
				title += __('Item {0}: {1} qty produced. ', [key, item_wise_qty[key]]);
			}
		}

		bars.push({
			'title': title,
			'width': (frm.doc.total_produced_qty / frm.doc.total_planned_qty * 100) + '%',
			'progress_class': 'progress-bar-success'
		});
		if (bars[0].width == '0%') {
			bars[0].width = '0.5%';
		}
		message = title;
		frm.dashboard.add_progress(__('Status'), bars, message);
	},
});

frappe.ui.form.on("Production Plan Item", {
	item_code: function(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (row.item_code) {
			frappe.call({
				method: "erpnext.manufacturing.doctype.production_plan.production_plan.get_item_data",
				args: {
					item_code: row.item_code
				},
				callback: function(r) {
					for (let key in r.message) {
						frappe.model.set_value(cdt, cdn, key, r.message[key]);
					}
				}
			});
		}
	}
});

frappe.ui.form.on("Material Request Plan Item", {
	warehouse: function(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (row.warehouse && row.item_code && frm.doc.company) {
			frappe.call({
				method: "erpnext.manufacturing.doctype.production_plan.production_plan.get_bin_details",
				args: {
					row: row,
					company: frm.doc.company,
					for_warehouse: row.warehouse
				},
				callback: function(r) {
					let {projected_qty, actual_qty} = r.message;

					frappe.model.set_value(cdt, cdn, 'projected_qty', projected_qty);
					frappe.model.set_value(cdt, cdn, 'actual_qty', actual_qty);
				}
			})
		}
	}
});

frappe.ui.form.on("Production Plan Sales Order", {
	sales_order(frm, cdt, cdn) {
		const { sales_order } = locals[cdt][cdn];
		if (!sales_order) {
			return;
		}
		frappe.call({
			method: "erpnext.manufacturing.doctype.production_plan.production_plan.get_so_details",
			args: { sales_order },
			callback(r) {
				const {transaction_date, customer, grand_total} = r.message;
				frappe.model.set_value(cdt, cdn, 'sales_order_date', transaction_date);
				frappe.model.set_value(cdt, cdn, 'customer', customer);
				frappe.model.set_value(cdt, cdn, 'grand_total', grand_total);
			}
		});
	}
});

cur_frm.fields_dict['sales_orders'].grid.get_field("sales_order").get_query = function() {
	return{
		filters: [
			['Sales Order','docstatus', '=' ,1]
		]
	}
};

frappe.tour['Production Plan'] = [
	{
		fieldname: "get_items_from",
		title: "Get Items From",
		description: __("Select whether to get items from a Sales Order or a Material Request. For now select <b>Sales Order</b>.\n A Production Plan can also be created manually where you can select the Items to manufacture.")
	},
	{
		fieldname: "get_sales_orders",
		title: "Get Sales Orders",
		description: __("Click on Get Sales Orders to fetch sales orders based on the above filters.")
	},
	{
		fieldname: "get_items",
		title: "Get Finished Goods for Manufacture",
		description: __("Click on 'Get Finished Goods for Manufacture' to fetch the items from the above Sales Orders. Items only for which a BOM is present will be fetched.")
	},
	{
		fieldname: "po_items",
		title: "Finished Goods",
		description: __("On expanding a row in the Items to Manufacture table, you'll see an option to 'Include Exploded Items'. Ticking this includes raw materials of the sub-assembly items in the production process.")
	},
	{
		fieldname: "include_non_stock_items",
		title: "Include Non Stock Items",
		description: __("To include non-stock items in the material request planning. i.e. Items for which 'Maintain Stock' checkbox is unticked.")
	},
	{
		fieldname: "include_subcontracted_items",
		title: "Include Subcontracted Items",
		description: __("To add subcontracted Item's raw materials if include exploded items is disabled.")
	}
];
