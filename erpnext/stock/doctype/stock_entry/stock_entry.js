// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors // License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.stock");

frappe.ui.form.on('Stock Entry', {
	setup: function(frm) {
		$.extend(frm.cscript, new erpnext.stock.StockEntry({frm: frm}));

		frm.set_query('production_order', function() {
			return {
				filters: [
					['Production Order', 'docstatus', '=', 1],
					['Production Order', 'qty', '>','`tabProduction Order`.produced_qty'],
					['Production Order', 'company', '=', frm.doc.company]
				]
			}
		});
	// },
	// onload_post_render: function(frm) {

		frm.set_query('batch_no', 'items', function(doc, cdt, cdn) {
			var item = locals[cdt][cdn];
			if(!item.item_code) {
				frappe.throw(__("Please enter Item Code to get Batch Number"));
			} else {
				if (in_list(["Material Transfer for Manufacture", "Manufacture", "Repack", "Subcontract"], doc.purpose)) {
					var filters = {
						'item_code': item.item_code,
						'posting_date': frm.doc.posting_date || frappe.datetime.nowdate()
					}
				} else {
					var filters = {
						'item_code': item.item_code
					}
				}

				if(item.s_warehouse) filters["warehouse"] = item.s_warehouse;
				return {
					query : "erpnext.controllers.queries.get_batch_no",
					filters: filters
				}
			}
		});


	},
	refresh: function(frm) {
		if(!frm.doc.docstatus) {
			frm.add_custom_button(__('Make Material Request'), function() {
				frappe.model.with_doctype('Material Request', function() {
					var mr = frappe.model.get_new_doc('Material Request');
					var items = frm.get_field('items').grid.get_selected_children();
					if(!items.length) {
						items = frm.doc.items;
					}
					items.forEach(function(item) {
						var mr_item = frappe.model.add_child(mr, 'items');
						mr_item.item_code = item.item_code;
						mr_item.item_name = item.item_name;
						mr_item.uom = item.uom;
						mr_item.item_group = item.item_group;
						mr_item.description = item.description;
						mr_item.image = item.image;
						mr_item.qty = item.qty;
						mr_item.warehouse = item.s_warehouse;
						mr_item.required_date = frappe.datetime.nowdate();
					});
					frappe.set_route('Form', 'Material Request', mr.name);
				});
			});
		}
	},
	purpose: function(frm) {
		frm.fields_dict.items.grid.refresh();
		frm.cscript.toggle_related_fields(frm.doc);
	},
	company: function(frm) {
		if(frm.doc.company) {
			var company_doc = frappe.get_doc(":Company", frm.doc.company);
			if(company_doc.default_letter_head) {
				frm.set_value("letter_head", company_doc.default_letter_head);
			}
		}
	},
	set_serial_no: function(frm, cdt, cdn) {
		var d = frappe.model.get_doc(cdt, cdn);
		if(!d.item_code && !d.s_warehouse && !d.qty) return;
		var	args = {
			'item_code'	: d.item_code,
			'warehouse'	: cstr(d.s_warehouse),
			'stock_qty'		: d.transfer_qty
		};
		frappe.call({
			method: "erpnext.stock.get_item_details.get_serial_no",
			args: {"args": args},
			callback: function(r) {
				if (!r.exe){
					frappe.model.set_value(cdt, cdn, "serial_no", r.message);
				}
			}
		});
	},
})

frappe.ui.form.on('Stock Entry Detail', {
	qty: function(frm, cdt, cdn) {
		frm.events.set_serial_no(frm, cdt, cdn);
	},

	s_warehouse: function(frm, cdt, cdn) {
		frm.events.set_serial_no(frm, cdt, cdn);
	},
	barcode: function(doc, cdt, cdn) {
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
	},
	uom: function(doc, cdt, cdn) {
		var d = locals[cdt][cdn];
		if(d.uom && d.item_code){
			return frappe.call({
				method: "erpnext.stock.doctype.stock_entry.stock_entry.get_uom_details",
				args: {
					item_code: d.item_code,
					uom: d.uom,
					qty: d.qty
				},
				callback: function(r) {
					if(r.message) {
						frappe.model.set_value(cdt, cdn, r.message);
					}
				}
			});
		}
	},
	item_code: function(frm, cdt, cdn) {
		var d = locals[cdt][cdn];
		if(d.item_code) {
			var args = {
				'item_code'			: d.item_code,
				'warehouse'			: cstr(d.s_warehouse) || cstr(d.t_warehouse),
				'transfer_qty'		: d.transfer_qty,
				'serial_no	'		: d.serial_no,
				'bom_no'			: d.bom_no,
				'expense_account'	: d.expense_account,
				'cost_center'		: d.cost_center,
				'company'			: frm.doc.company,
				'qty'				: d.qty
			};
			return frappe.call({
				doc: frm.doc,
				method: "get_item_details",
				args: args,
				callback: function(r) {
					if(r.message) {
						var d = locals[cdt][cdn];
						$.each(r.message, function(k, v) {
							d[k] = v;
						});
						refresh_field("items");
						erpnext.stock.select_batch_and_serial_no(frm, d);
					}
				}
			});
		}
	},
	expense_account: function(frm, cdt, cdn) {
		erpnext.utils.copy_value_in_all_row(frm.doc, cdt, cdn, "items", "expense_account");
	},
	cost_center: function(frm, cdt, cdn) {
		erpnext.utils.copy_value_in_all_row(frm.doc, cdt, cdn, "items", "cost_center");
	}
});

frappe.ui.form.on('Landed Cost Taxes and Charges', {
	amount: function(frm) {
		frm.events.calculate_amount();
	}
});

erpnext.stock.StockEntry = erpnext.stock.StockController.extend({
	setup: function() {
		var me = this;

		this.setup_posting_date_time_check();

		this.frm.fields_dict.bom_no.get_query = function() {
			return {
				filters:{
					"docstatus": 1,
					"is_active": 1
				}
			};
		};

		this.frm.fields_dict.items.grid.get_field('item_code').get_query = function() {
			return erpnext.queries.item({is_stock_item: 1});
		};

		this.frm.set_query("purchase_order", function() {
			return {
				"filters": {
					"docstatus": 1,
					"is_subcontracted": "Yes",
					"company": me.frm.doc.company
				}
			};
		});

		if(cint(frappe.defaults.get_default("auto_accounting_for_stock"))) {
			this.frm.add_fetch("company", "stock_adjustment_account", "expense_account");
			this.frm.fields_dict.items.grid.get_field('expense_account').get_query =
				function() {
					return {
						filters: {
							"company": me.frm.doc.company,
							"is_group": 0
						}
					}
				}
		}

		this.frm.set_indicator_formatter('item_code',
			function(doc) { return (doc.qty<=doc.actual_qty) ? "green" : "orange" })

		this.frm.add_fetch("purchase_order", "supplier", "supplier");

		frappe.dynamic_link = { doc: this.frm.doc, fieldname: 'supplier', doctype: 'Supplier' }
		this.frm.set_query("supplier_address", erpnext.queries.address_query)
	},

	onload_post_render: function() {
		var me = this;
		this.set_default_account(function() {
			if(me.frm.doc.__islocal && me.frm.doc.company && !me.frm.doc.amended_from) {
				me.frm.trigger("company");
			}
		});

		// if(!this.item_selector && false) {
		// 	this.item_selector = new erpnext.ItemSelector({frm: this.frm});
		// }
	},

	refresh: function() {
		var me = this;
		erpnext.toggle_naming_series();
		this.toggle_related_fields(this.frm.doc);
		this.toggle_enable_bom();
		this.show_stock_ledger();
		if (cint(frappe.defaults.get_default("auto_accounting_for_stock"))) {
			this.show_general_ledger();
		}
		erpnext.hide_company();
		erpnext.utils.add_item(this.frm);
	},

	on_submit: function() {
		this.clean_up();
	},

	after_cancel: function() {
		this.clean_up();
	},

	set_default_account: function(callback) {
		var me = this;

		if(cint(frappe.defaults.get_default("auto_accounting_for_stock")) && this.frm.doc.company) {
			return this.frm.call({
				method: "erpnext.accounts.utils.get_company_default",
				args: {
					"fieldname": "stock_adjustment_account",
					"company": this.frm.doc.company
				},
				callback: function(r) {
					if (!r.exc) {
						$.each(me.frm.doc.items || [], function(i, d) {
							if(!d.expense_account) d.expense_account = r.message;
						});
						if(callback) callback();
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
		this.calculate_basic_amount(d);
	},

	production_order: function() {
		var me = this;
		this.toggle_enable_bom();

		return frappe.call({
			method: "erpnext.stock.doctype.stock_entry.stock_entry.get_production_order_details",
			args: {production_order: me.frm.doc.production_order},
			callback: function(r) {
				if (!r.exc) {
					$.each(["from_bom", "bom_no", "fg_completed_qty", "use_multi_level_bom"], function(i, field) {
						me.frm.set_value(field, r.message[field]);
					})

					if (me.frm.doc.purpose == "Material Transfer for Manufacture" && !me.frm.doc.to_warehouse)
						me.frm.set_value("to_warehouse", r.message["wip_warehouse"]);


					if (me.frm.doc.purpose == "Manufacture") {
						if(r.message["additional_costs"].length) {
							$.each(r.message["additional_costs"], function(i, row) {
								me.frm.add_child("additional_costs", row);
							})
							refresh_field("additional_costs");
						}

						if (!me.frm.doc.from_warehouse) me.frm.set_value("from_warehouse", r.message["wip_warehouse"]);
						if (!me.frm.doc.to_warehouse) me.frm.set_value("to_warehouse", r.message["fg_warehouse"]);
					}
					me.get_items()
				}
			}
		});
	},

	toggle_enable_bom: function() {
		this.frm.toggle_enable("bom_no", !!!this.frm.doc.production_order);
	},

	add_excise_button: function() {
		if(frappe.boot.sysdefaults.country === "India")
			this.frm.add_custom_button(__("Excise Invoice"), function() {
				var excise = frappe.model.make_new_doc_and_get_name('Journal Entry');
				excise = locals['Journal Entry'][excise];
				excise.voucher_type = 'Excise Entry';
				frappe.set_route('Form', 'Journal Entry', excise.name);
			}, __("Make"));
	},

	items_add: function(doc, cdt, cdn) {
		var row = frappe.get_doc(cdt, cdn);
		this.frm.script_manager.copy_from_first_row("items", row, ["expense_account", "cost_center"]);

		if(!row.s_warehouse) row.s_warehouse = this.frm.doc.from_warehouse;
		if(!row.t_warehouse) row.t_warehouse = this.frm.doc.to_warehouse;
	},

	source_mandatory: ["Material Issue", "Material Transfer", "Subcontract", "Material Transfer for Manufacture"],
	target_mandatory: ["Material Receipt", "Material Transfer", "Subcontract", "Material Transfer for Manufacture"],

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

	basic_rate: function(doc, cdt, cdn) {
		var item = frappe.model.get_doc(cdt, cdn);
		this.calculate_basic_amount(item);
	},

	s_warehouse: function(doc, cdt, cdn) {
		this.get_warehouse_details(doc, cdt, cdn)
	},

	t_warehouse: function(doc, cdt, cdn) {
		this.get_warehouse_details(doc, cdt, cdn)
	},

	get_warehouse_details: function(doc, cdt, cdn) {
		var me = this;
		var d = locals[cdt][cdn];
		if(!d.bom_no) {
			frappe.call({
				method: "erpnext.stock.doctype.stock_entry.stock_entry.get_warehouse_details",
				args: {
					"args": {
						'item_code': d.item_code,
						'warehouse': cstr(d.s_warehouse) || cstr(d.t_warehouse),
						'transfer_qty': d.transfer_qty,
						'serial_no': d.serial_no,
						'qty': d.s_warehouse ? -1* d.qty : d.qty,
						'posting_date': this.frm.doc.posting_date,
						'posting_time': this.frm.doc.posting_time
					}
				},
				callback: function(r) {
					if (!r.exc) {
						$.extend(d, r.message);
						me.calculate_basic_amount(d);
					}
				}
			});
		}
	},

	calculate_basic_amount: function(item) {
		item.basic_amount = flt(flt(item.transfer_qty) * flt(item.basic_rate),
			precision("basic_amount", item));

		this.calculate_amount();
	},

	calculate_amount: function() {
		this.calculate_total_additional_costs();

		var total_basic_amount = frappe.utils.sum(
			(this.frm.doc.items || []).map(function(i) { return i.t_warehouse ? flt(i.basic_amount) : 0; })
		);

		for (var i in this.frm.doc.items) {
			var item = this.frm.doc.items[i];

			if (item.t_warehouse && total_basic_amount) {
				item.additional_cost = (flt(item.basic_amount) / total_basic_amount) * this.frm.doc.total_additional_costs;
			} else {
				item.additional_cost = 0;
			}

			item.amount = flt(item.basic_amount + flt(item.additional_cost),
				precision("amount", item));

			item.valuation_rate = flt(flt(item.basic_rate)
				+ (flt(item.additional_cost) / flt(item.transfer_qty)),
				precision("valuation_rate", item));
		}

		refresh_field('items');
	},

	calculate_total_additional_costs: function() {
		var total_additional_costs = frappe.utils.sum(
			(this.frm.doc.additional_costs || []).map(function(c) { return flt(c.amount); })
		);

		this.frm.set_value("total_additional_costs", flt(total_additional_costs, precision("total_additional_costs")));
	},

	toggle_related_fields: function(doc) {
		this.frm.toggle_enable("from_warehouse", doc.purpose!='Material Receipt');
		this.frm.toggle_enable("to_warehouse", doc.purpose!='Material Issue');

		this.frm.fields_dict["items"].grid.set_column_disp("s_warehouse", doc.purpose!='Material Receipt');
		this.frm.fields_dict["items"].grid.set_column_disp("t_warehouse", doc.purpose!='Material Issue');

		this.frm.cscript.toggle_enable_bom();

		if (doc.purpose == 'Subcontract') {
			doc.customer = doc.customer_name = doc.customer_address =
				doc.delivery_note_no = doc.sales_invoice_no = null;
		} else {
			doc.customer = doc.customer_name = doc.customer_address =
				doc.delivery_note_no = doc.sales_invoice_no = doc.supplier =
				doc.supplier_name = doc.supplier_address = doc.purchase_receipt_no =
				doc.address_display = null;
		}
		if(doc.purpose == "Material Receipt") {
			this.frm.set_value("from_bom", 0);
		}

		// Addition costs based on purpose
		this.frm.toggle_display(["additional_costs", "total_additional_costs", "additional_costs_section"],
			doc.purpose!='Material Issue');

		this.frm.fields_dict["items"].grid.set_column_disp("additional_cost", doc.purpose!='Material Issue');
	},

	supplier: function(doc) {
		erpnext.utils.get_party_details(this.frm, null, null, null);
	}
});

erpnext.stock.select_batch_and_serial_no = (frm, d = undefined) => {
	let get_warehouse = (item) => {
		if(frm.fields_dict.from_warehouse.disp_status === "Write") {
			value = cstr(item.s_warehouse) || ''
			return ['Source Warehouse', value]
		} else {
			value = cstr(item.t_warehouse) || ''
			return ['Target Warehouse', value]
		}
	}

	let show_modal_with_oldest_batch = (item, item_code, total_qty, warehouse_details, has_batch) => {
		frappe.call({
			method: 'erpnext.stock.doctype.batch.batch.get_batches_by_oldest',
			args: {
				warehouse: warehouse_details[1],
				item_code: item_code
			},
			callback: (r) => {
				if (r.message) {
					batch_rows_by_oldest = [];
					if(warehouse_details[0] === 'Source Warehouse') {
						qty = total_qty;
						for(var i = 0; i < r.message.length; i++) {
							batch_row = {name: 'batch 1'};
							batch_row.batch_no = r.message[i].batch_no;
							batch_row.available_qty = r.message[i].qty;
							if (parseInt(qty) <= parseInt(r.message[i].qty)) {
								batch_row.selected_qty = qty;
								batch_rows_by_oldest.push(batch_row);
								break;
							} else {
								batch_row.selected_qty = r.message[i].qty;
								qty -= r.message[i].qty;
								batch_rows_by_oldest.push(batch_row);
							}
						}
					}
					erpnext.stock.show_batch_serial_modal(frm, item, item_code, total_qty,
						warehouse_details, has_batch, batch_rows_by_oldest);
				}
			}
		});
	}

	if(d && d.has_batch_no && !d.batch_no) {
		// show_modal_with_oldest_batch(d, d.item_code, d.qty, get_warehouse(d), 1);
		erpnext.stock.show_batch_serial_modal(frm, d, d.item_code, d.qty, get_warehouse(d), 1);
	} else if(d && d.has_serial_no && !d.serial_no) {
		erpnext.stock.show_batch_serial_modal(frm, d, d.item_code, d.qty, get_warehouse(d), 0);
	}
}

erpnext.stock.show_batch_serial_modal = (frm, item, item_code, qty, warehouse_details,
	has_batch, oldest = undefined) => {

	let data = oldest ? oldest : []
	let title = "";
	let fields = [
		{fieldname: 'item_code', read_only: 1, fieldtype:'Link', options: 'Item',
			label: __('Item Code'), 'default': item_code},
		{fieldtype:'Column Break'},
		{fieldname: 'warehouse', fieldtype:'Link',
			options: 'Warehouse', label: __(warehouse_details[0]), 'default': warehouse_details[1]},
		{fieldtype:'Column Break'},
		{fieldname: 'qty', fieldtype:'Float', label: __(has_batch ? 'Total Qty' : 'Qty'), 'default': qty},
	];

	if(has_batch) {
		title = __("Select Batch Numbers");
		fields = fields.concat([
			{fieldtype:'Section Break', label: __('Batches')},
			{fieldname: 'batches', fieldtype: 'Table',
				fields: [
					{fieldtype:'Link', fieldname:'batch_no', options: 'Batch',
						label: __('Select Batch'), in_list_view:1, get_query: function(doc) {
							return {filters: {item: item_code }};
						}},
					{fieldtype:'Float', read_only: 1, fieldname:'available_qty',
						label: __('Available'), in_list_view:1, 'default': 0},
					{fieldtype:'Float', fieldname:'selected_qty',
						label: __('Qty'), in_list_view:1, 'default': 0},
				],
				in_place_edit: true,
				data: data,
				get_data: function() {
					return this.data;
				},
				on_setup: function(grid) {
					grid.wrapper.on('change', 'input[data-fieldname="selected_qty"]', function(e) {
						// check if batch is selected
						if($(this).val().length !== 0) {
							let $row = $(this).closest('.grid-row');

							let $batch = $row.find('input[data-fieldname="batch_no"]');
							if($batch.val() === '') {
								$(this).val('').trigger('change');
								frappe.throw(__("Please select a batch"));
							} else {
								// check if greater than available if source
								let $available = $row.find('input[data-fieldname="available_qty"]');
								if(warehouse_details[0] === 'Source Warehouse' &&
									parseInt($available.val()) < parseInt($(this).val())) {

									$(this).val('').trigger('change');
									frappe.throw(__(`For transfer from source, selected quantity cannot be
										greater than available quantity`));
								}
							}
						}

					});
				}

			}
		]);

	} else {
		title = __("Select Serial Numbers");
		fields = fields.concat([
			{fieldtype: 'Section Break', label: __('Serial No')},
			{
				fieldtype: 'Link', fieldname: 'serial_no_select', options: 'Serial No',
				label: __('Select'),
				get_query: function(doc) {
					return { filters: {item_code: item_code}};
				}
			},
			{fieldtype: 'Column Break'},
			{fieldname: 'serial_no', fieldtype: 'Small Text'}
		])
	}

	let dialog = new frappe.ui.Dialog({
		title: title,
		fields: fields
	});

	erpnext.stock.bind_batch_serial_dialog_qty(dialog);

	let map_item_values = (item, values, attribute) => {
		item[attribute] = values[attribute];
		if(warehouse_details[0] === 'Source Warehouse') {
			item.s_warehouse = values.warehouse;
		} else {
			item.t_warehouse = values.warehouse;
		}
		item.qty = values.qty;
	}

	let validate_batch_dialog = (values) => {
		if(values.batches.length === 0 || !values.batches) {
			frappe.throw(__("Please select batches for batched item " + values.item_code));
			return false;
		}
		values.batches.map((batch, i) => {
			if(!batch.selected_qty || batch.selected_qty === 0 ) {
				frappe.throw(__("Please select quantity on row " + (i+1)));
				return false;
			}
		});
		return true;
	}

	let set_batched_items = () => {
		let values = dialog.get_values();
		if(!validate_batch_dialog(values)) {
			return;
		}

		values.batches.map((batch, i) => {
			if(i === 0) {
				map_item_values(item, values, 'batch_no');
			} else {
				var row = frm.add_child("items");
				row.item_code = item.item_code;
				map_item_values(row, values, 'batch_no');
			}
		});
	}

	let validate_serial_no_dialog = (values) => {
		let serial_nos = values.serial_no || '';
		if (!serial_nos || !serial_nos.replace(/\s/g, '').length) {
			frappe.throw(__("Please enter serial numbers for serialized item " + values.item_code));
			return false;
		}
		return true;
	}

	let set_serialized_items = () => {
		let values = dialog.get_values();
		if (!validate_serial_no_dialog(values)) {
			return;
		}
		map_item_values(item, values, 'serial_no');
	}

	dialog.set_primary_action(__('Get Items'), function() {
		if(!dialog.get_values().warehouse) {
			frappe.throw(__("Please select a warehouse"));
		}
		has_batch ? set_batched_items() : set_serialized_items();
		refresh_field("items");
		dialog.hide();
	})
	dialog.show();
}

erpnext.stock.bind_batch_serial_dialog_qty = (dialog) => {
	let serial_no_link = dialog.fields_dict.serial_no_select;
	let serial_no_list = dialog.fields_dict.serial_no;
	let batches_field = dialog.fields_dict.batches;

	let warehouse_field = dialog.fields_dict.warehouse;
	let qty_field = dialog.fields_dict.qty;
	let item_code = dialog.fields_dict.item_code.get_value();

	let update_quantity = (batch) => {
		if(batch) {
			let total_qty = 0;
			batches_field.grid.wrapper.find('input[data-fieldname="selected_qty"]').each(function() {
				total_qty += Number($(this).val());
			});
			qty_field.set_input(total_qty);
		} else {
			serial_numbers = serial_no_list.get_value().replace(/\n/g, ' ').match(/\S+/g) || [];
			qty_field.set_input(serial_numbers.length);
		}
	}

	function set_available_qty(item_code, batch_no, warehouse, field) {
		if(warehouse) {
			frappe.call({
				method: 'erpnext.stock.doctype.batch.batch.get_batch_qty',
				args: {
					batch_no: batch_no,
					warehouse: warehouse,
					item_code: item_code
				},
				callback: (r) => {
					let value = r.message ? r.message : '0';
					field.set_value(value);
					field.$input.val(value);
					field.$input.trigger('change');
				}
			});
		} else {
			frappe.throw(__("Please select a warehouse to get available quantities"));
		}
	}

	if(serial_no_link) {
		serial_no_link.$input.on('awesomplete-selectcomplete', function(e) {
			if(serial_no_link.get_value().length > 0) {
				let new_no = serial_no_link.get_value();
				let list_value = serial_no_list.get_value();
				let new_line = '\n';
				let list = [];
				if(!serial_no_list.get_value()) {
					new_line = '';
				} else {
					list = list_value.replace(/\s+/g, ' ').split(' ');
				}
				if(!list.includes(new_no)) {
					serial_no_link.set_new_description('');
					serial_no_list.set_value(list_value + new_line + new_no);
					update_quantity(0);
				} else {
					serial_no_link.set_new_description(new_no + ' is already selected.');
				}
			}
			serial_no_link.set_input('');
		});

		serial_no_list.$input.on('input', function() {
			update_quantity(0);
		});
	}

	if(batches_field) {
		batches_field.grid.wrapper.on('change', 'input[data-fieldname="batch_no"]', function(e) {
			let $row = $(this).closest('.grid-row');
			let name = $row.attr('data-name');
			let row = batches_field.grid.grid_rows_by_docname[name];
			row.on_grid_fields[2].set_value('0');
			row.on_grid_fields[2].$input.trigger('change');
			if(warehouse_field.get_value().length > 0) {
				set_available_qty(item_code, row.doc.batch_no, warehouse_field.get_value(), row.on_grid_fields[1]);
			} else {
				frappe.throw(__("Please select a warehouse to get available quantities"));
			}
		});

		batches_field.grid.wrapper.on('change', function(e) {
			update_quantity(1);
		});

		warehouse_field.$input.on('change', function() {
			batches_field.grid.df.data = [];
			batches_field.grid.refresh();
		});
	}
}