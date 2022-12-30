frappe.provide("erpnext.stock");

erpnext.stock.PackingSlipController = class PackingSlipController extends erpnext.stock.PackingController {
	item_table_fields = ['items', 'packing_items']

	setup() {
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
			return erpnext.queries.item({is_stock_item: 1});
		});

		me.frm.set_query("item_code", "packing_items", function() {
			return erpnext.queries.item({is_stock_item: 1});
		});

		const batch_query = (doc, cdt, cdn) => {
			let item = frappe.get_doc(cdt, cdn);
			if (!item.item_code) {
				frappe.throw(__("Please enter Item Code to get Batch Number"));
			} else {
				let filters = {
					item_code: item.item_code,
					warehouse: me.frm.doc.from_warehouse,
					posting_date: me.frm.doc.posting_date || frappe.datetime.nowdate(),
				}

				return {
					query : "erpnext.controllers.queries.get_batch_no",
					filters: filters
				};
			}
		};
		me.frm.set_query("batch_no", "items", batch_query);
		me.frm.set_query("batch_no", "packing_items", batch_query);

		me.frm.set_query("uom", "items", (doc, cdt, cdn) => {
			let item = frappe.get_doc(cdt, cdn);
			return erpnext.queries.item_uom(item.item_code);
		});
		me.frm.set_query("uom", "packing_items", (doc, cdt, cdn) => {
			let item = frappe.get_doc(cdt, cdn);
			return erpnext.queries.item_uom(item.item_code);
		});
	}

	setup_buttons() {
		this.show_stock_ledger();
		this.show_general_ledger();
	}

	calculate_totals() {
		this.frm.doc.total_net_weight = 0;
		if (!this.frm.doc.manual_tare_weight) {
			this.frm.doc.total_tare_weight = 0;
		}

		for (const field of this.item_table_fields) {
			for (let item of this.frm.doc[field] || []) {
				frappe.model.round_floats_in(item, null, ['weight_per_unit']);
				item.stock_qty = item.qty * item.conversion_factor;
				item.total_weight = flt(item.weight_per_unit * item.stock_qty, precision("total_weight", item));

				if (item.doctype == "Packing Slip Item") {
					this.frm.doc.total_net_weight += item.total_weight;
				} else if (item.doctype == "Packing Slip Packing Material") {
					if (!this.frm.doc.manual_tare_weight) {
						this.frm.doc.total_tare_weight += item.total_weight;
					}
				}
			}
		}

		for (let item of this.frm.doc.handling_units || []) {
			this.frm.doc.total_net_weight += item.net_weight;
			if (!this.frm.doc.manual_tare_weight) {
				this.frm.doc.total_tare_weight += item.tare_weight;
			}
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
				},
				callback: function (r) {
					if (r.message && !r.exc) {
						if (r.message.packing_items && r.message.packing_items.length) {
							me.frm.clear_table("packing_items");
							for (let d of r.message.packing_items) {
								me.frm.add_child("packing_items", d);
							}
						}

						me.frm.doc.manual_tare_weight = cint(r.message.manual_tare_weight);
						if (r.message.manual_tare_weight && flt(r.message.total_tare_weight)) {
							me.frm.doc.total_tare_weight = flt(r.message.total_tare_weight);
						}

						me.calculate_totals();

						if (r.message.weight_uom) {
							return me.frm.set_value("weight_uom", r.message.weight_uom);
						}
					}
				}
			});
		}
	}
};

extend_cscript(cur_frm.cscript, new erpnext.stock.PackingSlipController({frm: cur_frm}));
