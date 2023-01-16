frappe.provide("erpnext.stock");

erpnext.stock.PackingSlipController = class PackingSlipController extends erpnext.stock.PackingController {
	item_table_fields = ['items', 'packaging_items']

	setup() {
		this.frm.custom_make_buttons = {
			'Delivery Note': __('Delivery Note'),
			'Sales Invoice': __('Sales Invoice'),
		}

		this.setup_posting_date_time_check();
		this.setup_queries();
	}

	refresh() {
		erpnext.hide_company();
		this.setup_buttons();
	}

	setup_queries() {
		let me = this;

		me.frm.set_query("item_code", "items", function() {
			return erpnext.queries.item({is_stock_item: 1, is_packaging_material: 0});
		});

		me.frm.set_query("item_code", "packaging_items", function() {
			return erpnext.queries.item({is_stock_item: 1});
		});

		me.setup_warehouse_query();
		erpnext.queries.setup_warehouse_qty_query(me.frm, "source_warehouse", "items");
		erpnext.queries.setup_warehouse_qty_query(me.frm, "source_warehouse", "packaging_items");

		const batch_query = (doc, cdt, cdn) => {
			let item = frappe.get_doc(cdt, cdn);
			if (!item.item_code) {
				frappe.throw(__("Please enter Item Code to get Batch Number"));
			} else {
				let filters = {
					item_code: item.item_code,
					warehouse: item.source_warehouse,
					posting_date: me.frm.doc.posting_date || frappe.datetime.nowdate(),
				}

				return {
					query : "erpnext.controllers.queries.get_batch_no",
					filters: filters
				};
			}
		};
		me.frm.set_query("batch_no", "items", batch_query);
		me.frm.set_query("batch_no", "packaging_items", batch_query);

		me.frm.set_query("uom", "items", (doc, cdt, cdn) => {
			let item = frappe.get_doc(cdt, cdn);
			return erpnext.queries.item_uom(item.item_code);
		});
		me.frm.set_query("uom", "packaging_items", (doc, cdt, cdn) => {
			let item = frappe.get_doc(cdt, cdn);
			return erpnext.queries.item_uom(item.item_code);
		});

		me.frm.set_query("customer", erpnext.queries.customer);
	}

	setup_buttons() {
		this.show_stock_ledger();
		this.show_general_ledger();

		if (this.frm.doc.docstatus == 0) {
			this.frm.add_custom_button(__('Sales Order'), () => {
				this.get_items_from_sales_order();
			}, __("Get Items From"));

			this.frm.add_custom_button(__('Packing Slip'), () => {
				this.get_items_from_packing_slip("Packing Slip");
			}, __("Get Items From"));
		}

		if (this.frm.doc.docstatus == 1) {
			if (this.frm.doc.status == "In Stock") {
				this.frm.add_custom_button(__('Delivery Note'), () => this.make_delivery_note(), __('Create'));
				this.frm.add_custom_button(__('Sales Invoice'), () => this.make_sales_invoice(), __('Create'));

				this.frm.page.set_inner_btn_group_as_primary(__('Create'));
			}
		}
	}

	calculate_totals() {
		this.frm.doc.total_net_weight = 0;
		this.frm.doc.total_tare_weight = 0;

		for (const field of this.item_table_fields) {
			for (let item of this.frm.doc[field] || []) {
				frappe.model.round_floats_in(item, null,
					['net_weight_per_unit', 'tare_weight_per_unit', 'gross_weight_per_unit']);

				item.stock_qty = item.qty * item.conversion_factor;

				if (frappe.meta.has_field(item.doctype, "net_weight_per_unit")) {
					item.net_weight = flt(item.net_weight_per_unit * item.stock_qty, precision("net_weight", item));
				}
				if (frappe.meta.has_field(item.doctype, "tare_weight_per_unit")) {
					item.tare_weight = flt(item.tare_weight_per_unit * item.stock_qty, precision("tare_weight", item));
				}
				if (frappe.meta.has_field(item.doctype, "gross_weight")) {
					item.gross_weight = flt(item.net_weight + item.tare_weight, precision("gross_weight", item));
					if (item.stock_qty && frappe.meta.has_field(item.doctype, "gross_weight_per_unit")) {
						item.gross_weight_per_unit = item.gross_weight / item.stock_qty;
					}
				}

				if (!item.source_packing_slip) {
					this.frm.doc.total_net_weight += flt(item.net_weight);
					this.frm.doc.total_tare_weight += flt(item.tare_weight);
				}
			}
		}

		for (let item of this.frm.doc.packing_slips || []) {
			this.frm.doc.total_net_weight += item.net_weight;
			this.frm.doc.total_tare_weight += item.tare_weight;
		}

		frappe.model.round_floats_in(this.frm.doc, ['total_net_weight', 'total_tare_weight']);
		this.frm.doc.total_gross_weight = flt(this.frm.doc.total_net_weight + this.frm.doc.total_tare_weight,
			precision("total_gross_weight"));

		this.frm.refresh_fields();
	}

	package_type() {
		this.get_package_type_details();
	}

	get_package_type_details() {
		let me = this;
		if (me.frm.doc.package_type) {
			return frappe.call({
				method: "erpnext.stock.doctype.packing_slip.packing_slip.get_package_type_details",
				args: {
					package_type: me.frm.doc.package_type,
					args: {
						weight_uom: me.frm.doc.weight_uom,
						company: me.frm.doc.company,
						posting_date: me.frm.doc.posting_date,
						doctype: me.frm.doc.doctype,
						name: me.frm.doc.name,
						default_source_warehouse: me.frm.doc.default_source_warehouse,
					}
				},
				callback: function (r) {
					if (r.message && !r.exc) {
						return frappe.run_serially([
							() => {
								if (r.message.weight_uom) {
									return me.frm.set_value("weight_uom", r.message.weight_uom);
								}
							},
							() => {
								if (r.message.packaging_items && r.message.packaging_items.length) {
									me.frm.clear_table("packaging_items");
									for (let d of r.message.packaging_items) {
										me.frm.add_child("packaging_items", d);
									}
								}

								me.calculate_totals();
							}
						]);
					}
				}
			});
		}
	}

	items_remove(doc, cdt, cdn) {
		this.remove_packing_slips_without_items();
		super.items_remove(doc, cdt, cdn);
	}

	packing_slips_remove(doc, cdt, cdn) {
		this.remove_items_without_packing_slips();
		super.packing_slips_remove(doc, cdt, cdn);
	}

	remove_packing_slips_without_items() {
		let contents_packing_slips = (this.frm.doc.items || []).map(d => d.source_packing_slip).filter(d => d);
		contents_packing_slips = [...new Set(contents_packing_slips)];

		let to_remove = [];
		for (let row of this.frm.doc.packing_slips || []) {
			if (!contents_packing_slips.includes(row.source_packing_slip)) {
				to_remove.push(row.source_packing_slip);
			}
		}

		this.frm.doc.packing_slips = (this.frm.doc.packing_slips || []).filter(d => !to_remove.includes(d.source_packing_slip));
		this.frm.doc.packing_slips.forEach((row, index) => (row.idx = index + 1));
		this.frm.refresh_field("packing_slips");
	}

	remove_items_without_packing_slips() {
		let packing_slips = (this.frm.doc.packing_slips || []).map(d => d.source_packing_slip).filter(d => d);

		let to_remove = [];
		for (let row of this.frm.doc.items || []) {
			if (!packing_slips.includes(row.source_packing_slip)) {
				to_remove.push(row.source_packing_slip);
			}
		}

		this.frm.doc.items = (this.frm.doc.items || []).filter(d => !d.source_packing_slip || !to_remove.includes(d.source_packing_slip));
		this.frm.doc.items.forEach((row, index) => (row.idx = index + 1));
		this.frm.refresh_field("items");
	}

	get_items_from_sales_order() {
		erpnext.utils.map_current_doc({
			method: "erpnext.selling.doctype.sales_order.sales_order.make_packing_slip",
			source_doctype: "Sales Order",
			target: this.frm,
			setters: {
				customer: this.frm.doc.customer || undefined,
				project: this.frm.doc.project || undefined,
			},
			columns: ['customer_name', 'project'],
			get_query_filters: {
				docstatus: 1,
				status: ["not in", ["Closed", "On Hold"]],
				per_delivered: ["<", 99.99],
				per_packed: ["<", 99.99],
				company: this.frm.doc.company,
			}
		});
	}

	make_delivery_note() {
		frappe.model.open_mapped_doc({
			method: "erpnext.stock.doctype.packing_slip.packing_slip.make_delivery_note",
			frm: this.frm,
		})
	}

	make_sales_invoice() {
		frappe.model.open_mapped_doc({
			method: "erpnext.stock.doctype.packing_slip.packing_slip.make_sales_invoice",
			frm: this.frm,
		})
	}
};

extend_cscript(cur_frm.cscript, new erpnext.stock.PackingSlipController({frm: cur_frm}));
