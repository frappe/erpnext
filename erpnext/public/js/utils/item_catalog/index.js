erpnext.ItemCatalog = class ItemCatalog {
	constructor(...args) {
		this.args = args;
		this.render();
	}

	async render() {
		await frappe.require("erpnext_item_catalog.bundle.js");
		this.catalog = new erpnext.ItemCatalogRender(...this.args);
	}
}
