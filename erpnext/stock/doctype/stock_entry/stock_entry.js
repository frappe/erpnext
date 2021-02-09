// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors // License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.stock");
frappe.provide("erpnext.accounts.dimensions");

{% include 'erpnext/stock/landed_taxes_and_charges_common.js' %};

frappe.ui.form.on('Stock Entry', {
	setup: function(frm) {
		frm.set_indicator_formatter('item_code', function(doc) {
			if (!doc.s_warehouse) {
				return 'blue';
			} else {
				return (doc.qty<=doc.actual_qty) ? 'green' : 'orange';
			}
		});

		frm.set_query('work_order', function() {
			return {
				filters: [
					['Work Order', 'docstatus', '=', 1],
					['Work Order', 'qty', '>','`tabWork Order`.produced_qty'],
					['Work Order', 'company', '=', frm.doc.company]
				]
			}
		});

		frm.set_query('outgoing_stock_entry', function() {
			return {
				filters: [
					['Stock Entry', 'docstatus', '=', 1],
					['Stock Entry', 'per_transferred', '<','100'],
				]
			}
		});

		frm.set_query('source_warehouse_address', function() {
			return {
				filters: {
					link_doctype: 'Warehouse',
					link_name: frm.doc.from_warehouse
				}
			}
		});

		frm.set_query('target_warehouse_address', function() {
			return {
				filters: {
					link_doctype: 'Warehouse',
					link_name: frm.doc.to_warehouse
				}
			}
		});

		frappe.db.get_value('Stock Settings', {name: 'Stock Settings'}, 'sample_retention_warehouse', (r) => {
			if (r.sample_retention_warehouse) {
				var filters = [
							["Warehouse", 'company', '=', frm.doc.company],
							["Warehouse", "is_group", "=",0],
							['Warehouse', 'name', '!=', r.sample_retention_warehouse]
						]
				frm.set_query("from_warehouse", function() {
					return {
						filters: filters
					};
				});
				frm.set_query("s_warehouse", "items", function() {
					return {
						filters: filters
					};
				});
			}
		});

		frm.set_query('batch_no', 'items', function(doc, cdt, cdn) {
			var item = locals[cdt][cdn];
			if(!item.item_code) {
				frappe.throw(__("Please enter Item Code to get Batch Number"));
			} else {
				if (in_list(["Material Transfer for Manufacture", "Manufacture", "Repack", "Send to Subcontractor"], doc.purpose)) {
					var filters = {
						'item_code': item.item_code,
						'posting_date': frm.doc.posting_date || frappe.datetime.nowdate()
					}
				} else {
					var filters = {
						'item_code': item.item_code
					}
				}

				filters["warehouse"] = item.s_warehouse || item.t_warehouse;

				return {
					query : "erpnext.controllers.queries.get_batch_no",
					filters: filters
				}
			}
		});


		frm.add_fetch("bom_no", "inspection_required", "inspection_required");
		erpnext.accounts.dimensions.setup_dimension_filters(frm, frm.doctype);
	},

	setup_quality_inspection: function(frm) {
		if (!frm.doc.inspection_required) {
			return;
		}

		let quality_inspection_field = frm.get_docfield("items", "quality_inspection");
		quality_inspection_field.get_route_options_for_new_doc = function(row) {
			if (frm.is_new()) return;
			return {
				"inspection_type": "Incoming",
				"reference_type": frm.doc.doctype,
				"reference_name": frm.doc.name,
				"item_code": row.doc.item_code,
				"description": row.doc.description,
				"item_serial_no": row.doc.serial_no ? row.doc.serial_no.split("\n")[0] : null,
				"batch_no": row.doc.batch_no
			}
		}

		frm.set_query("quality_inspection", "items", function(doc, cdt, cdn) {
			var d = locals[cdt][cdn];

			return {
				query:"erpnext.stock.doctype.quality_inspection.quality_inspection.quality_inspection_query",
				filters: {
					'item_code': d.item_code,
					'reference_name': doc.name
				}
			}
		});
	},

	outgoing_stock_entry: function(frm) {
		frappe.call({
			doc: frm.doc,
			method: "set_items_for_stock_in",
			callback: function() {
				refresh_field('items');
			}
		});
	},

	refresh: function(frm) {
		if(!frm.doc.docstatus) {
			frm.trigger('validate_purpose_consumption');
			frm.add_custom_button(__('Create Material Request'), function() {
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
						mr_item.stock_uom = item.stock_uom;
						mr_item.conversion_factor = item.conversion_factor;
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

		if(frm.doc.items) {
			const has_alternative = frm.doc.items.find(i => i.allow_alternative_item === 1);

			if (frm.doc.docstatus == 0 && has_alternative) {
				frm.add_custom_button(__('Alternate Item'), () => {
					erpnext.utils.select_alternate_items({
						frm: frm,
						child_docname: "items",
						warehouse_field: "s_warehouse",
						child_doctype: "Stock Entry Detail",
						original_item_field: "original_item",
						condition: (d) => {
							if (d.s_warehouse && d.allow_alternative_item) {return true;}
						}
					})
				});
			}
		}

		if (frm.doc.docstatus === 1) {
			if (frm.doc.add_to_transit && frm.doc.purpose=='Material Transfer' && frm.doc.per_transferred < 100) {
				frm.add_custom_button('End Transit', function() {
					frappe.model.open_mapped_doc({
						method: "erpnext.stock.doctype.stock_entry.stock_entry.make_stock_in_entry",
						frm: frm
					})
				});
			}

			if (frm.doc.per_transferred > 0) {
				frm.add_custom_button(__('Received Stock Entries'), function() {
					frappe.route_options = {
						'outgoing_stock_entry': frm.doc.name,
						'docstatus': ['!=', 2]
					};

					frappe.set_route('List', 'Stock Entry');
				}, __("View"));
			}
		}

		if (frm.doc.docstatus===0) {
			frm.add_custom_button(__('Purchase Invoice'), function() {
				erpnext.utils.map_current_doc({
					method: "erpnext.accounts.doctype.purchase_invoice.purchase_invoice.make_stock_entry",
					source_doctype: "Purchase Invoice",
					target: frm,
					date_field: "posting_date",
					setters: {
						supplier: frm.doc.supplier || undefined,
					},
					get_query_filters: {
						docstatus: 1
					}
				})
			}, __("Get Items From"));

			frm.add_custom_button(__('Material Request'), function() {
				erpnext.utils.map_current_doc({
					method: "erpnext.stock.doctype.material_request.material_request.make_stock_entry",
					source_doctype: "Material Request",
					target: frm,
					date_field: "schedule_date",
					setters: {},
					get_query_filters: {
						docstatus: 1,
						material_request_type: ["in", ["Material Transfer", "Material Issue"]],
						status: ["not in", ["Transferred", "Issued"]]
					}
				})
			}, __("Get Items From"));
		}
		if (frm.doc.docstatus===0 && frm.doc.purpose == "Material Issue") {
			frm.add_custom_button(__('Expired Batches'), function() {
				frappe.call({
					method: "erpnext.stock.doctype.stock_entry.stock_entry.get_expired_batch_items",
					callback: function(r) {
						if (!r.exc && r.message) {
							frm.set_value("items", []);
							r.message.forEach(function(element) {
								let d = frm.add_child("items");
								d.item_code = element.item;
								d.s_warehouse = element.warehouse;
								d.qty = element.qty;
								d.uom = element.stock_uom;
								d.conversion_factor = 1;
								d.batch_no = element.batch_no;
								d.transfer_qty = element.qty;
								frm.refresh_fields();
							});
						}
					}
				});
			}, __("Get Items From"));
		}

		frm.events.show_bom_custom_button(frm);

		if (frm.doc.company) {
			frm.trigger("toggle_display_account_head");
		}

		if(frm.doc.docstatus==1 && frm.doc.purpose == "Material Receipt" && frm.get_sum('items', 			'sample_quantity')) {
			frm.add_custom_button(__('Create Sample Retention Stock Entry'), function () {
				frm.trigger("make_retention_stock_entry");
			});
		}

		frm.trigger("setup_quality_inspection");
	},

	stock_entry_type: function(frm){
		frm.remove_custom_button('Bill of Materials', "Get Items From");
		frm.events.show_bom_custom_button(frm);
		frm.trigger('add_to_transit');
	},

	purpose: function(frm) {
		frm.trigger('validate_purpose_consumption');
		frm.fields_dict.items.grid.refresh();
		frm.cscript.toggle_related_fields(frm.doc);
	},

	validate_purpose_consumption: function(frm) {
		frappe.call({
			method: "erpnext.manufacturing.doctype.manufacturing_settings.manufacturing_settings.is_material_consumption_enabled",
		}).then(r => {
			if (cint(r.message) == 0
				&& frm.doc.purpose=="Material Consumption for Manufacture") {
				frm.set_value("purpose", 'Manufacture');
				frappe.throw(__('Material Consumption is not set in Manufacturing Settings.'));
			}
		});
	},

	company: function(frm) {
		if(frm.doc.company) {
			var company_doc = frappe.get_doc(":Company", frm.doc.company);
			if(company_doc.default_letter_head) {
				frm.set_value("letter_head", company_doc.default_letter_head);
			}
			frm.trigger("toggle_display_account_head");

			erpnext.accounts.dimensions.update_dimension(frm, frm.doctype);
		}
	},

	set_serial_no: function(frm, cdt, cdn, callback) {
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
				if (!r.exe && r.message){
					frappe.model.set_value(cdt, cdn, "serial_no", r.message);
				}
				if (callback) {
					callback();
				}
			}
		});
	},

	make_retention_stock_entry: function(frm) {
		frappe.call({
			method: "erpnext.stock.doctype.stock_entry.stock_entry.move_sample_to_retention_warehouse",
			args:{
				"company": frm.doc.company,
				"items": frm.doc.items
			},
			callback: function (r) {
				if (r.message) {
					var doc = frappe.model.sync(r.message)[0];
					frappe.set_route("Form", doc.doctype, doc.name);
				}
				else {
					frappe.msgprint(__("Retention Stock Entry already created or Sample Quantity not provided"));
				}
			}
		});
	},

	toggle_display_account_head: function(frm) {
		var enabled = erpnext.is_perpetual_inventory_enabled(frm.doc.company);
		frm.fields_dict["items"].grid.set_column_disp(["cost_center", "expense_account"], enabled);
	},

	set_basic_rate: function(frm, cdt, cdn) {
		const item = locals[cdt][cdn];
		item.transfer_qty = flt(item.qty) * flt(item.conversion_factor);

		const args = {
			'item_code'			: item.item_code,
			'posting_date'		: frm.doc.posting_date,
			'posting_time'		: frm.doc.posting_time,
			'warehouse'			: cstr(item.s_warehouse) || cstr(item.t_warehouse),
			'serial_no'			: item.serial_no,
			'company'			: frm.doc.company,
			'qty'				: item.s_warehouse ? -1*flt(item.transfer_qty) : flt(item.transfer_qty),
			'voucher_type'		: frm.doc.doctype,
			'voucher_no'		: item.name,
			'allow_zero_valuation': 1,
		};

		if (item.item_code || item.serial_no) {
			frappe.call({
				method: "erpnext.stock.utils.get_incoming_rate",
				args: {
					args: args
				},
				callback: function(r) {
					frappe.model.set_value(cdt, cdn, 'basic_rate', (r.message || 0.0));
					frm.events.calculate_basic_amount(frm, item);
				}
			});
		}
	},

	get_warehouse_details: function(frm, cdt, cdn) {
		var child = locals[cdt][cdn];
		if(!child.bom_no) {
			frappe.call({
				method: "erpnext.stock.doctype.stock_entry.stock_entry.get_warehouse_details",
				args: {
					"args": {
						'item_code': child.item_code,
						'warehouse': cstr(child.s_warehouse) || cstr(child.t_warehouse),
						'transfer_qty': child.transfer_qty,
						'serial_no': child.serial_no,
						'qty': child.s_warehouse ? -1* child.transfer_qty : child.transfer_qty,
						'posting_date': frm.doc.posting_date,
						'posting_time': frm.doc.posting_time,
						'company': frm.doc.company,
						'voucher_type': frm.doc.doctype,
						'voucher_no': child.name,
						'allow_zero_valuation': 1
					}
				},
				callback: function(r) {
					if (!r.exc) {
						$.extend(child, r.message);
						frm.events.calculate_basic_amount(frm, child);
					}
				}
			});
		}
	},

	show_bom_custom_button: function(frm){
		if (frm.doc.docstatus === 0 &&
			['Material Issue', 'Material Receipt', 'Material Transfer', 'Send to Subcontractor'].includes(frm.doc.purpose)) {
			frm.add_custom_button(__('Bill of Materials'), function() {
				frm.events.get_items_from_bom(frm);
			}, __("Get Items From"));
		}
	},

	get_items_from_bom: function(frm) {
		let filters = function(){
			return {filters: { docstatus:1 }};
		}

		let fields = [
			{"fieldname":"bom", "fieldtype":"Link", "label":__("BOM"),
			options:"BOM", reqd: 1, get_query: filters()},
			{"fieldname":"source_warehouse", "fieldtype":"Link", "label":__("Source Warehouse"),
			options:"Warehouse"},
			{"fieldname":"target_warehouse", "fieldtype":"Link", "label":__("Target Warehouse"),
			options:"Warehouse"},
			{"fieldname":"qty", "fieldtype":"Float", "label":__("Quantity"),
			reqd: 1, "default": 1},
			{"fieldname":"fetch_exploded", "fieldtype":"Check",
			"label":__("Fetch exploded BOM (including sub-assemblies)"), "default":1},
			{"fieldname":"fetch", "label":__("Get Items from BOM"), "fieldtype":"Button"}
		]

		// Exclude field 'Target Warehouse' in case of Material Issue
		if (frm.doc.purpose == 'Material Issue'){
			fields.splice(2,1);
		}
		// Exclude field 'Source Warehouse' in case of Material Receipt
		else if(frm.doc.purpose == 'Material Receipt'){
			fields.splice(1,1);
		}

		let d = new frappe.ui.Dialog({
			title: __("Get Items from BOM"),
			fields: fields
		});
		d.get_input("fetch").on("click", function() {
			let values = d.get_values();
			if(!values) return;
			values["company"] = frm.doc.company;
			if(!frm.doc.company) frappe.throw(__("Company field is required"));
			frappe.call({
				method: "erpnext.manufacturing.doctype.bom.bom.get_bom_items",
				args: values,
				callback: function(r) {
					if (!r.message) {
						frappe.throw(__("BOM does not contain any stock item"));
					} else {
						erpnext.utils.remove_empty_first_row(frm, "items");
						$.each(r.message, function(i, item) {
							let d = frappe.model.add_child(cur_frm.doc, "Stock Entry Detail", "items");
							d.item_code = item.item_code;
							d.item_name = item.item_name;
							d.item_group = item.item_group;
							d.s_warehouse = values.source_warehouse;
							d.t_warehouse = values.target_warehouse;
							d.uom = item.stock_uom;
							d.stock_uom = item.stock_uom;
							d.conversion_factor = item.conversion_factor ? item.conversion_factor : 1;
							d.qty = item.qty;
							d.expense_account = item.expense_account;
							d.project = item.project;
							frm.events.set_basic_rate(frm, d.doctype, d.name);
						});
					}
					d.hide();
					refresh_field("items");
				}
			});

		});
		d.show();
	},

	calculate_basic_amount: function(frm, item) {
		item.basic_amount = flt(flt(item.transfer_qty) * flt(item.basic_rate),
			precision("basic_amount", item));

		frm.events.calculate_amount(frm);
	},

	calculate_amount: function(frm) {
		frm.events.calculate_total_additional_costs(frm);
		let total_basic_amount = 0;
		if (in_list(["Repack", "Manufacture"], frm.doc.purpose)) {
			total_basic_amount = frappe.utils.sum(
				(frm.doc.items || []).map(function(i) {
					return i.is_finished_item ? flt(i.basic_amount) : 0;
				})
			);
		} else {
			total_basic_amount = frappe.utils.sum(
				(frm.doc.items || []).map(function(i) {
					return i.t_warehouse ? flt(i.basic_amount) : 0;
				})
			);
		}

		for (let i in frm.doc.items) {
			let item = frm.doc.items[i];

			if (((in_list(["Repack", "Manufacture"], frm.doc.purpose) && item.is_finished_item) || item.t_warehouse) && total_basic_amount) {
				item.additional_cost = (flt(item.basic_amount) / total_basic_amount) * frm.doc.total_additional_costs;
			} else {
				item.additional_cost = 0;
			}

			item.amount = flt(item.basic_amount + flt(item.additional_cost), precision("amount", item));

			if (flt(item.transfer_qty)) {
				item.valuation_rate = flt(flt(item.basic_rate) + (flt(item.additional_cost) / flt(item.transfer_qty)),
					precision("valuation_rate", item));
			}
		}

		refresh_field('items');
	},

	calculate_total_additional_costs: function(frm) {
		const total_additional_costs = frappe.utils.sum(
			(frm.doc.additional_costs || []).map(function(c) { return flt(c.base_amount); })
		);

		frm.set_value("total_additional_costs",
			flt(total_additional_costs, precision("total_additional_costs")));
	},

	source_warehouse_address: function(frm) {
		erpnext.utils.get_address_display(frm, 'source_warehouse_address', 'source_address_display', false);
	},

	target_warehouse_address: function(frm) {
		erpnext.utils.get_address_display(frm, 'target_warehouse_address', 'target_address_display', false);
	},

	add_to_transit: function(frm) {
		if(frm.doc.add_to_transit && frm.doc.purpose=='Material Transfer') {
			frm.set_value('stock_entry_type', 'Material Transfer');
			frm.fields_dict.to_warehouse.get_query = function() {
				return {
					filters:{
						'warehouse_type' : 'Transit',
						'is_group': 0,
						'company': frm.doc.company
					}
				};
			};
			frappe.db.get_value('Company', frm.doc.company, 'default_in_transit_warehouse', (r) => {
				if (r.default_in_transit_warehouse) {
					frm.set_value('to_warehouse', r.default_in_transit_warehouse);
				}
			});
		}
	},

	apply_putaway_rule: function (frm) {
		if (frm.doc.apply_putaway_rule) erpnext.apply_putaway_rule(frm, frm.doc.purpose);
	}
});

frappe.ui.form.on('Stock Entry Detail', {
	qty: function(frm, cdt, cdn) {
		frm.events.set_serial_no(frm, cdt, cdn, () => {
			frm.events.set_basic_rate(frm, cdt, cdn);
		});
	},

	conversion_factor: function(frm, cdt, cdn) {
		frm.events.set_basic_rate(frm, cdt, cdn);
	},

	s_warehouse: function(frm, cdt, cdn) {
		frm.events.set_serial_no(frm, cdt, cdn, () => {
			frm.events.get_warehouse_details(frm, cdt, cdn);
		});
	},

	t_warehouse: function(frm, cdt, cdn) {
		frm.events.get_warehouse_details(frm, cdt, cdn);
	},

	basic_rate: function(frm, cdt, cdn) {
		var item = locals[cdt][cdn];
		frm.events.calculate_basic_amount(frm, item);
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
				'serial_no'		: d.serial_no,
				'bom_no'		: d.bom_no,
				'expense_account'	: d.expense_account,
				'cost_center'		: d.cost_center,
				'company'		: frm.doc.company,
				'qty'			: d.qty,
				'voucher_type'		: frm.doc.doctype,
				'voucher_no'		: d.name,
				'allow_zero_valuation': 1,
			};

			return frappe.call({
				doc: frm.doc,
				method: "get_item_details",
				args: args,
				callback: function(r) {
					if(r.message) {
						var d = locals[cdt][cdn];
						$.each(r.message, function(k, v) {
							if (v) {
								frappe.model.set_value(cdt, cdn, k, v); // qty and it's subsequent fields weren't triggered
							}
						});
						refresh_field("items");

						let no_batch_serial_number_value = !d.serial_no;
						if (d.has_batch_no && !d.has_serial_no) {
							// check only batch_no for batched item
							no_batch_serial_number_value = !d.batch_no;
						}

						if (no_batch_serial_number_value) {
							erpnext.stock.select_batch_and_serial_no(frm, d);
						}
					}
				}
			});
		}
	},
	expense_account: function(frm, cdt, cdn) {
		erpnext.utils.copy_value_in_all_rows(frm.doc, cdt, cdn, "items", "expense_account");
	},
	cost_center: function(frm, cdt, cdn) {
		erpnext.utils.copy_value_in_all_rows(frm.doc, cdt, cdn, "items", "cost_center");
	},
	sample_quantity: function(frm, cdt, cdn) {
		validate_sample_quantity(frm, cdt, cdn);
	},
	batch_no: function(frm, cdt, cdn) {
		validate_sample_quantity(frm, cdt, cdn);
	},
});

var validate_sample_quantity = function(frm, cdt, cdn) {
	var d = locals[cdt][cdn];
	if (d.sample_quantity && frm.doc.purpose == "Material Receipt") {
		frappe.call({
			method: 'erpnext.stock.doctype.stock_entry.stock_entry.validate_sample_quantity',
			args: {
				batch_no: d.batch_no,
				item_code: d.item_code,
				sample_quantity: d.sample_quantity,
				qty: d.transfer_qty
			},
			callback: (r) => {
				frappe.model.set_value(cdt, cdn, "sample_quantity", r.message);
			}
		});
	}
};

frappe.ui.form.on('Landed Cost Taxes and Charges', {
	amount: function(frm, cdt, cdn) {
		frm.events.set_base_amount(frm, cdt, cdn);

		// Adding this check because same table in used in LCV
		// This causes an error if you try to post an LCV immediately after a Stock Entry
		if (frm.doc.doctype == 'Stock Entry') {
			frm.events.calculate_amount(frm);
		}
	},

	expense_account: function(frm, cdt, cdn) {
		frm.events.set_account_currency(frm, cdt, cdn);
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

		if(me.frm.doc.company && erpnext.is_perpetual_inventory_enabled(me.frm.doc.company)) {
			this.frm.add_fetch("company", "stock_adjustment_account", "expense_account");
		}

		this.frm.fields_dict.items.grid.get_field('expense_account').get_query = function() {
			if (erpnext.is_perpetual_inventory_enabled(me.frm.doc.company)) {
				return {
					filters: {
						"company": me.frm.doc.company,
						"is_group": 0
					}
				}
			}
		}

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

		this.frm.get_field("items").grid.set_multiple_add("item_code", "qty");
	},

	refresh: function() {
		var me = this;
		erpnext.toggle_naming_series();
		this.toggle_related_fields(this.frm.doc);
		this.toggle_enable_bom();
		this.show_stock_ledger();
		if (this.frm.doc.docstatus===1 && erpnext.is_perpetual_inventory_enabled(this.frm.doc.company)) {
			this.show_general_ledger();
		}
		erpnext.hide_company();
		erpnext.utils.add_item(this.frm);
		this.frm.trigger('add_to_transit');
	},

	scan_barcode: function() {
		let transaction_controller= new erpnext.TransactionController({frm:this.frm});
		transaction_controller.scan_barcode();
	},

	on_submit: function() {
		this.clean_up();
	},

	after_cancel: function() {
		this.clean_up();
	},

	set_default_account: function(callback) {
		var me = this;

		if(this.frm.doc.company && erpnext.is_perpetual_inventory_enabled(this.frm.doc.company)) {
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
		// Clear Work Order record from locals, because it is updated via Stock Entry
		if(this.frm.doc.work_order &&
			in_list(["Manufacture", "Material Transfer for Manufacture", "Material Consumption for Manufacture"],
				this.frm.doc.purpose)) {
			frappe.model.remove_from_locals("Work Order",
				this.frm.doc.work_order);
		}
	},

	fg_completed_qty: function() {
		this.get_items();
	},

	get_items: function() {
		var me = this;
		if(!this.frm.doc.fg_completed_qty || !this.frm.doc.bom_no)
			frappe.throw(__("BOM and Manufacturing Quantity are required"));

		if(this.frm.doc.work_order || this.frm.doc.bom_no) {
			// if work order / bom is mentioned, get items
			return this.frm.call({
				doc: me.frm.doc,
				freeze: true,
				method: "get_items",
				callback: function(r) {
					if(!r.exc) refresh_field("items");
				}
			});
		}
	},

	work_order: function() {
		var me = this;
		this.toggle_enable_bom();
		if(!me.frm.doc.work_order || me.frm.doc.job_card) {
			return;
		}

		return frappe.call({
			method: "erpnext.stock.doctype.stock_entry.stock_entry.get_work_order_details",
			args: {
				work_order: me.frm.doc.work_order,
				company: me.frm.doc.company
			},
			callback: function(r) {
				if (!r.exc) {
					$.each(["from_bom", "bom_no", "fg_completed_qty", "use_multi_level_bom"], function(i, field) {
						me.frm.set_value(field, r.message[field]);
					})

					if (me.frm.doc.purpose == "Material Transfer for Manufacture" && !me.frm.doc.to_warehouse)
						me.frm.set_value("to_warehouse", r.message["wip_warehouse"]);


					if (me.frm.doc.purpose == "Manufacture" || me.frm.doc.purpose == "Material Consumption for Manufacture" ) {
						if (me.frm.doc.purpose == "Manufacture") {
							if (!me.frm.doc.to_warehouse) me.frm.set_value("to_warehouse", r.message["fg_warehouse"]);
						}
						if (!me.frm.doc.from_warehouse) me.frm.set_value("from_warehouse", r.message["wip_warehouse"]);
					}
					me.get_items();
				}
			}
		});
	},

	toggle_enable_bom: function() {
		this.frm.toggle_enable("bom_no", !!!this.frm.doc.work_order);
	},

	add_excise_button: function() {
		if(frappe.boot.sysdefaults.country === "India")
			this.frm.add_custom_button(__("Excise Invoice"), function() {
				var excise = frappe.model.make_new_doc_and_get_name('Journal Entry');
				excise = locals['Journal Entry'][excise];
				excise.voucher_type = 'Excise Entry';
				frappe.set_route('Form', 'Journal Entry', excise.name);
			}, __('Create'));
	},

	items_add: function(doc, cdt, cdn) {
		var row = frappe.get_doc(cdt, cdn);
		this.frm.script_manager.copy_from_first_row("items", row, ["expense_account", "cost_center"]);

		if(!row.s_warehouse) row.s_warehouse = this.frm.doc.from_warehouse;
		if(!row.t_warehouse) row.t_warehouse = this.frm.doc.to_warehouse;
	},

	from_warehouse: function(doc) {
		this.set_warehouse_in_children(doc.items, "s_warehouse", doc.from_warehouse);
	},

	to_warehouse: function(doc) {
		this.set_warehouse_in_children(doc.items, "t_warehouse", doc.to_warehouse);
	},

	set_warehouse_in_children: function(child_table, warehouse_field, warehouse) {
		let transaction_controller = new erpnext.TransactionController();
		transaction_controller.autofill_warehouse(child_table, warehouse_field, warehouse);
	},

	items_on_form_rendered: function(doc, grid_row) {
		erpnext.setup_serial_no();
	},

	toggle_related_fields: function(doc) {
		this.frm.toggle_enable("from_warehouse", doc.purpose!='Material Receipt');
		this.frm.toggle_enable("to_warehouse", doc.purpose!='Material Issue');

		this.frm.fields_dict["items"].grid.set_column_disp("retain_sample", doc.purpose=='Material Receipt');
		this.frm.fields_dict["items"].grid.set_column_disp("sample_quantity", doc.purpose=='Material Receipt');

		this.frm.cscript.toggle_enable_bom();

		if (doc.purpose == 'Send to Subcontractor') {
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

erpnext.stock.select_batch_and_serial_no = (frm, item) => {
	let get_warehouse_type_and_name = (item) => {
		let value = '';
		if(frm.fields_dict.from_warehouse.disp_status === "Write") {
			value = cstr(item.s_warehouse) || '';
			return {
				type: 'Source Warehouse',
				name: value
			};
		} else {
			value = cstr(item.t_warehouse) || '';
			return {
				type: 'Target Warehouse',
				name: value
			};
		}
	}

	if(item && !item.has_serial_no && !item.has_batch_no) return;
	if (frm.doc.purpose === 'Material Receipt') return;

	frappe.require("assets/erpnext/js/utils/serial_no_batch_selector.js", function() {
		new erpnext.SerialNoBatchSelector({
			frm: frm,
			item: item,
			warehouse_details: get_warehouse_type_and_name(item),
		});
	});

}

$.extend(cur_frm.cscript, new erpnext.stock.StockEntry({frm: cur_frm}));
