// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Item Price", {
	setup(frm) {
		frm.set_query("item_code", function () {
			return {
				filters: {
					has_variants: 0,
				},
			};
		});

		frm._price_list_filters = {};
		frm.set_query("price_list", () => ({ filters: frm._price_list_filters }));
	},

	refresh(frm) {
		if (frm.doc.item_code) {
			frm.trigger("item_code");
		}
	},

	onload(frm) {
		// Fetch price list details
		frm.add_fetch("price_list", "buying", "buying");
		frm.add_fetch("price_list", "selling", "selling");
		frm.add_fetch("price_list", "currency", "currency");

		// Fetch item details
		frm.add_fetch("item_code", "item_name", "item_name");
		frm.add_fetch("item_code", "description", "item_description");
		frm.add_fetch("item_code", "stock_uom", "uom");

		frm.set_df_property(
			"bulk_import_help",
			"options",
			'<a href="/app/data-import-tool/Item Price">' + __("Import in Bulk") + "</a>"
		);

		frm.set_query("batch_no", function () {
			return {
				filters: {
					item: frm.doc.item_code,
				},
			};
		});
	},

	item_code(frm) {
		frm._price_list_filters = {};
		if (frm.doc.item_code) {
			frappe.db
				.get_value("Item", frm.doc.item_code, ["is_sales_item", "is_purchase_item"])
				.then((r) => {
					if (!r.message) return;
					if (r.message.is_sales_item && !r.message.is_purchase_item) {
						frm._price_list_filters.selling = 1;
					} else if (r.message.is_purchase_item && !r.message.is_sales_item) {
						frm._price_list_filters.buying = 1;
					}
				});
		}
	},
});
