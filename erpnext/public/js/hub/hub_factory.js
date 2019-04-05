frappe.provide('erpnext.hub');

frappe.views.MarketplaceFactory = class MarketplaceFactory extends frappe.views.Factory {
	show() {
		is_marketplace_disabled()
			.then(disabled => {
				if (disabled) {
					frappe.show_not_found('Marketplace');
					return;
				}

				if (frappe.pages.marketplace) {
					frappe.container.change_to('marketplace');
					erpnext.hub.marketplace.refresh();
				} else {
					this.make('marketplace');
				}
			});
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
};

function is_marketplace_disabled() {
	return frappe.call({
		method: "erpnext.hub_node.doctype.marketplace_settings.marketplace_settings.is_marketplace_enabled"
	}).then(r => r.message)
}

$(document).on('toolbar_setup', () => {
	$('#toolbar-user .navbar-reload').after(`
		<li>
			<a class="marketplace-link" href="#marketplace/home">${__('Marketplace')}
		</li>
	`);

	is_marketplace_disabled()
		.then(disabled => {
			if (disabled) {
				$('#toolbar-user .marketplace-link').hide();
			}
		});
});
