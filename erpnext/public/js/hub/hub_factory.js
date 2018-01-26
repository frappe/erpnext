frappe.provide('erpnext.hub.pages');

frappe.views.HubFactory = frappe.views.Factory.extend({
	make(route) {
		const page_name = frappe.get_route_str();
		const page = route[1];

		const assets = {
			'List': [
				'/assets/erpnext/js/hub/hub_page.js',
				'/assets/erpnext/css/hub.css',
			],
			'Form': [
				'/assets/erpnext/js/hub/hub_form.js',
				'/assets/erpnext/css/hub.css',
			]
		};
		console.log("make factory?");

		if (!erpnext.hub.pages[page_name]) {
			console.log("pages?");
			if (page === 'Item' && !route[2]) {
				frappe.require(assets['List'], () => {
					erpnext.hub.pages[page_name] = new erpnext.hub.ItemListing({
						doctype: 'Hub Settings',
						parent: this.make_page(true, page_name)
					});
					window.hub_page = erpnext.hub.pages[page_name];
				});
			} if (page === 'Company' && !route[2]) {
				frappe.require(assets['List'], () => {
					erpnext.hub.pages[page_name] = new erpnext.hub.CompanyListing({
						doctype: 'Hub Settings',
						parent: this.make_page(true, page_name)
					});
					window.hub_page = erpnext.hub.pages[page_name];
				});
			} else if(route[2]) {
				console.log("form?");
				frappe.require(assets['Form'], () => {
					erpnext.hub.pages[page_name] = new erpnext.hub.HubForm({
						hub_item_code: route[2],
						doctype: 'Hub Settings',
						parent: this.make_page(true, page_name)
					});
					window.hub_page = erpnext.hub.pages[page_name];
				});
			}
		} else {
			console.log("else?");
			frappe.container.change_to(page_name);
			window.hub_page = erpnext.hub.pages[page_name];
		}
	}
});
