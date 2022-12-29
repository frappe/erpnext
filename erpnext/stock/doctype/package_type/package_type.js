// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide("erpnext.stock");

erpnext.stock.PackageTypeController = class PackageTypeController extends erpnext.stock.PackingController {
	item_table_fields = ['packing_items']

	setup() {
		this.setup_queries();
	}

	setup_queries() {
		this.frm.set_query("item_code", "packing_items", function() {
			return erpnext.queries.item({is_stock_item: 1});
		});

		this.frm.set_query("uom", "packing_items", (doc, cdt, cdn) => {
			let item = frappe.get_doc(cdt, cdn);
			return erpnext.queries.item_uom(item.item_code);
		});
	}

	calculate_totals() {
		if (!this.frm.doc.manual_tare_weight) {
			this.frm.doc.total_tare_weight = 0;
		}

		for (let item of this.frm.doc.packing_items || []) {
			frappe.model.round_floats_in(item, null, ['weight_per_unit']);
			item.stock_qty = item.qty * item.conversion_factor;
			item.total_weight = flt(item.weight_per_unit * item.stock_qty, precision("total_weight", item));

			if (!this.frm.doc.manual_tare_weight) {
				this.frm.doc.total_tare_weight += item.total_weight;
			}
		}

		frappe.model.round_floats_in(this.frm.doc, ['total_tare_weight']);

		this.frm.refresh_fields();
	}

	length() {
		this.calculate_volume();
	}
	width() {
		this.calculate_volume();
	}
	height() {
		this.calculate_volume();
	}
	volume_based_on() {
		this.calculate_volume();
	}

	calculate_volume() {
		if (this.frm.doc.volume_based_on == "Dimensions") {
			frappe.model.round_floats_in(this.frm.doc, ['length', 'width', 'height']);
			this.frm.doc.volume = flt(this.frm.doc.length * this.frm.doc.width * this.frm.doc.height,
				precision("volume"));
			this.frm.refresh_field("volume");
		}
	}
};

extend_cscript(cur_frm.cscript, new erpnext.stock.PackageTypeController({frm: cur_frm}));
