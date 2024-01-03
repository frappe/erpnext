import { LinkCatalog } from "frappe/public/js/frappe/ui/catalog";

import CatalogItemGroupTree from "./CatalogItemGroupTree.vue";
import CatalogItemContents from "./CatalogItemContents.vue";

erpnext.ItemCatalogRender = class ItemCatalogRender {
	constructor({ frm }) {
		this.frm = frm;
		if (!this.item_field) {
			this.item_field = "item_code";
		}

		if (!this.item_query) {
			this.item_query = erpnext.queries.item().query;
		}

		this.grid = this.frm.get_field("items").grid;
		this.setup();
	}

	setup() {
		if (!this.grid.catalog_button) {
			const callback = () => {
				if (this.dialog) {
					this.link_catalog?.refresh();
				} else {
					this.make_dialog();
				}

				this.dialog.show();
			};
			this.grid.catalog_button = this.grid.add_custom_button(__("Catalog"), callback, "top");
		}
	}

	make_dialog() {
		this.dialog = new frappe.ui.Dialog({
			size: "extra-large",
			fields: [ { fieldtype: "HTML", fieldname: "catalog" } ],
		});
		const wrapper = this.dialog.body;
		// const wrapper = $(dialog.fields_dict.catalog.$wrapper).get(0);
		this.render(wrapper);
	}

	render(wrapper) {
		this.link_catalog = new LinkCatalog({
			wrapper,
			frm: this.frm,
			options: {
				title: { html: `<h2>${__("Items")}</h2>` },
				link_doctype: "Item",
				search_fields: ["item_name", "item_code"],
				link_fieldname: "item_code",
				quantity_fieldname: "qty",
				table_fieldname: "items",
				sidebar_contents: [
					{ component: CatalogItemGroupTree },
				],
				item_contents: [
					{ component: CatalogItemContents },
				],
				item_footer: [],
			},
		});
	}
};
