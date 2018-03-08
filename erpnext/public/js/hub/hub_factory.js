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
		frappe.model.with_doc('Hub Settings', 'Hub Settings', () => {
			this.hub_settings = frappe.get_doc('Hub Settings');
			console.log('We?', frappe.is_online(false));

			if (!erpnext.hub.pages[page_name]) {
				if(!frappe.is_online(false)) {
					console.log('Well?');
					this.render_offline_card();
					return;
				}
				if (!route[2]) {
					frappe.require(assets['List'], () => {
						erpnext.hub.pages[page_name] = new erpnext.hub[page+'Listing']({
							parent: this.make_page(true, page_name),
							hub_settings: this.hub_settings
						});
						window.hub_page = erpnext.hub.pages[page_name];
					});
				} else {
					frappe.require(assets['Form'], () => {
						erpnext.hub.pages[page_name] = new erpnext.hub[page+'Page']({
							unique_id: route[2],
							doctype: route[2],
							parent: this.make_page(true, page_name),
							hub_settings: this.hub_settings
						});
						window.hub_page = erpnext.hub.pages[page_name];
					});
				}
			} else {
				frappe.container.change_to(page_name);
				window.hub_page = erpnext.hub.pages[page_name];
			}
		});
	},

	render_offline_card() {
		let html = `<div class='page-card'>
			<div class='page-card-head'>
				<span class='indicator red'>
					{{ _("Payment Cancelled") }}</span>
			</div>
			<p>${ __("Your payment is cancelled.") }</p>
			<div><a href='' class='btn btn-primary btn-sm'>
				${ __("Continue") }</a></div>
		</div>`;

		let page = $('.layout-main-section');
		console.log(page);
		page.append(html);

		return;
	}
});
