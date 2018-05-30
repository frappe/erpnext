frappe.provide('erpnext.hub.pages');

frappe.views.HubFactory = frappe.views.Factory.extend({
	make(route) {
		const page_name = frappe.get_route_str();
		const page = route[1];

		const assets = {
			'List': [
				'/assets/erpnext/js/hub/hub_listing.js',
			],
			'Form': [
				'/assets/erpnext/js/hub/hub_form.js'
			]
		};
		frappe.model.with_doc('Hub Settings', 'Hub Settings', () => {
			this.hub_settings = frappe.get_doc('Hub Settings');

			if (!erpnext.hub.pages[page_name]) {
				if(!frappe.is_online()) {
					this.render_offline_card();
					return;
				}
				if (!route[2]) {
					frappe.require(assets['List'], () => {
						if(page === 'Favourites') {
							erpnext.hub.pages[page_name] = new erpnext.hub['Favourites']({
								parent: this.make_page(true, page_name),
								hub_settings: this.hub_settings
							});
						} else {
							erpnext.hub.pages[page_name] = new erpnext.hub[page+'Listing']({
								parent: this.make_page(true, page_name),
								hub_settings: this.hub_settings
							});
						}
					});
				} else if (!route[3]){
					frappe.require(assets['Form'], () => {
						erpnext.hub.pages[page_name] = new erpnext.hub[page+'Page']({
							unique_id: route[2],
							doctype: route[2],
							parent: this.make_page(true, page_name),
							hub_settings: this.hub_settings
						});
					});
				} else {
					frappe.require(assets['List'], () => {
						frappe.route_options = {};
						frappe.route_options["company_name"] = route[2]
						erpnext.hub.pages[page_name] = new erpnext.hub['ItemListing']({
							parent: this.make_page(true, page_name),
							hub_settings: this.hub_settings
						});
					});
				}
				window.hub_page = erpnext.hub.pages[page_name];
			} else {
				frappe.container.change_to(page_name);
				window.hub_page = erpnext.hub.pages[page_name];
			}
		});
	},

	render_offline_card() {
		let html = `<div class='page-card' style='margin: 140px auto;'>
			<div class='page-card-head'>
				<span class='indicator red'>${'Failed to connect'}</span>
			</div>
			<p>${ __("Please check your network connection.") }</p>
			<div><a href='#Hub/Item' class='btn btn-primary btn-sm'>
				${ __("Reload") }</a></div>
		</div>`;

		let page = $('#body_div');
		page.append(html);

		return;
	}
});
