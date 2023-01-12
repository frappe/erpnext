frappe.provide("erpnext.stock");

erpnext.stock.PackingController = class PackingController extends erpnext.stock.StockController {
	item_code(doc, cdt, cdn) {
		return this.get_item_details(doc, cdt, cdn);
	}

	get_item_details(doc, cdt, cdn) {
		let me = this;
		let item = frappe.get_doc(cdt, cdn);

		if (item.item_code) {
			return me.frm.call({
				method: "erpnext.stock.doctype.packing_slip.packing_slip.get_item_details",
				child: item,
				args: {
					args: {
						item_code: item.item_code,
						qty: item.qty || 1,
						uom: item.uom,
						weight_uom: me.frm.doc.weight_uom,
						company: me.frm.doc.company,
						posting_date: me.frm.doc.posting_date,
						doctype: me.frm.doc.doctype,
						name: me.frm.doc.name,
						child_doctype: item.doctype,
						default_source_warehouse: me.frm.doc.default_source_warehouse,
					}
				},
				callback: function(r) {
					if (!r.exc) {
						me.calculate_totals();
					}
				}
			});
		}
	}

	default_source_warehouse() {
		for (const table_field of this.item_table_fields) {
			this.autofill_warehouse(this.frm.doc[table_field], "source_warehouse", this.frm.doc.default_source_warehouse);
		}
	}

	qty() {
		this.calculate_totals();
	}

	uom(doc, cdt, cdn) {
		let me = this;
		let item = frappe.get_doc(cdt, cdn);

		if (item.item_code && item.uom) {
			return this.frm.call({
				method: "erpnext.stock.get_item_details.get_conversion_factor",
				child: item,
				args: {
					item_code: item.item_code,
					uom: item.uom
				},
				callback: function(r) {
					if (!r.exc) {
						me.conversion_factor(me.frm.doc, cdt, cdn);
					}
				}
			});
		}
	}

	conversion_factor() {
		this.calculate_totals();
	}

	items_remove() {
		this.calculate_totals();
	}
	packaging_items_remove() {
		this.calculate_totals();
	}
	packing_slips_remove() {
		this.calculate_totals();
	}

	net_weight_per_unit() {
		this.calculate_totals();
	}

	net_weight(doc, cdt, cdn) {
		let item = frappe.get_doc(cdt, cdn);
		if (flt(item.stock_qty)) {
			item.net_weight_per_unit = flt(item.net_weight) / flt(item.stock_qty);
		}
		this.calculate_totals();
	}

	tare_weight_per_unit() {
		this.calculate_totals();
	}

	tare_weight(doc, cdt, cdn) {
		let item = frappe.get_doc(cdt, cdn);
		if (flt(item.stock_qty)) {
			item.tare_weight_per_unit = flt(item.tare_weight) / flt(item.stock_qty);
		}
		this.calculate_totals();
	}

	gross_weight_per_unit(doc, cdt, cdn) {
		let item = frappe.get_doc(cdt, cdn);
		item.net_weight_per_unit = flt(item.gross_weight_per_unit) - flt(item.tare_weight_per_unit);
		this.calculate_totals();
	}

	gross_weight(doc, cdt, cdn) {
		let item = frappe.get_doc(cdt, cdn);
		if (flt(item.stock_qty)) {
			let new_gross_weight = flt(item.gross_weight) / flt(item.stock_qty);
			frappe.model.set_value(item.doctype, item.name, "gross_weight_per_unit", new_gross_weight);
		} else {
			this.calculate_totals();
		}
	}

	weight_uom() {
		return this.get_item_weights_per_unit();
	}

	get_item_weights_per_unit() {
		let me = this;

		let item_codes = [];
		for (const table_field of me.item_table_fields) {
			for (let item of me.frm.doc[table_field] || []) {
				if (item.item_code && !item_codes.includes(item.item_code)) {
					item_codes.push(item.item_code);
				}
			}
		}

		if (me.frm.doc.weight_uom && item_codes.length) {
			return frappe.call({
				method: "erpnext.stock.doctype.packing_slip.packing_slip.get_item_weights_per_unit",
				args: {
					item_codes: item_codes,
					weight_uom: me.frm.doc.weight_uom,
				},
				callback: function(r) {
					if (r.message && !r.exc) {
						for (const table_field of me.item_table_fields) {
							for (let item of me.frm.doc[table_field] || []) {
								if (item.item_code) {
									item.net_weight_per_unit = flt(r.message[item.item_code].net_weight_per_unit);
									item.tare_weight_per_unit = flt(r.message[item.item_code].tare_weight_per_unit);
								}
							}
						}
						me.calculate_totals();
					}
				}
			});
		}
	}

	calculate_totals() {

	}
};