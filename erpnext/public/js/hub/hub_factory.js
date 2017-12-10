frappe.provide('erpnext.hub.pages');

frappe.views.HubFactory = frappe.views.Factory.extend({
	make(route) {
		const page_name = frappe.get_route_str();
		const page = route[1];

		if (!erpnext.hub.pages[page_name]) {
			if (page === 'Item' && !route[2]) {
				frappe.require('/assets/erpnext/js/hub/hub_page.js', () => {
					erpnext.hub.pages[page_name] = new erpnext.hub.HubPage({
						doctype: 'Hub Settings',
						parent: this.make_page(true, page_name)
					});
					window.hub_page = erpnext.hub.pages[page_name];
				});
			} else if(route[2]) {
				frappe.require('/assets/erpnext/js/hub/hub_form.js', () => {
					erpnext.hub.pages[page_name] = new erpnext.hub.HubForm({
						hub_item_code: route[2],
						doctype: 'Hub Settings',
						parent: this.make_page(true, page_name)
					});
					window.hub_page = erpnext.hub.pages[page_name];
				});
			}
		} else {
			frappe.container.change_to(page_name);
			window.hub_page = erpnext.hub.pages[page_name];
		}
	}
});
