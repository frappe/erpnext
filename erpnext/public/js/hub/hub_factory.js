frappe.provide('erpnext.hub');

frappe.views.marketplaceFactory = class marketplaceFactory extends frappe.views.Factory {
	show() {
		if (frappe.pages.marketplace) {
			frappe.container.change_to('marketplace');
			erpnext.hub.marketplace.refresh();
		} else {
			this.make('marketplace');
		}
	}

	make(page_name) {
		const assets = [
			'/assets/js/marketplace.min.js'
		];

		frappe.require(assets, () => {
			erpnext.hub.marketplace = new erpnext.hub.Marketplace({
				parent: this.make_page(true, page_name)
			});
		});
	}
}

$(document).on('toolbar_setup', () => {
	$('#toolbar-user .navbar-reload').after(`
		<li>
			<a href="#marketplace/home">${__('Marketplace')}
		</li>
	`)
})
