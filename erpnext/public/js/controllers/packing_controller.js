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

	weight_uom() {
		return this.get_item_weights_per_unit();
	}

	weight_per_unit() {
		this.calculate_totals();
	}

	items_remove() {
		this.calculate_totals();
	}
	packing_items_remove() {
		this.calculate_totals();
	}
	handling_units_remove() {
		this.calculate_totals();
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
									item.weight_per_unit = flt(r.message[item.item_code]);
								}
							}
						}
						me.calculate_totals();
					}
				}
			});
		}
	}

	total_weight(doc, cdt, cdn) {
		let item = frappe.get_doc(cdt, cdn);
		if (flt(item.stock_qty)) {
			item.weight_per_unit = flt(item.total_weight) / flt(item.stock_qty);
		}
		this.calculate_totals();
	}

	total_tare_weight() {
		this.calculate_totals();
	}

	total_gross_weight() {
		if (this.frm.doc.manual_tare_weight) {
			this.frm.doc.total_tare_weight = flt(flt(this.frm.doc.total_gross_weight) - flt(this.frm.doc.total_net_weight),
				precision("total_tare_weight"));
		}

		this.calculate_totals();
	}

	manual_tare_weight() {
		this.calculate_totals();
	}

	calculate_totals() {

	}
};