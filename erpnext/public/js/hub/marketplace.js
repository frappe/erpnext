import Vue from 'vue/dist/vue.js';
import './vue-plugins';

// components
import PageContainer from './PageContainer.vue';
import Sidebar from './Sidebar.vue';
import { ProfileDialog } from './components/profile_dialog';

// helpers
import './hub_call';
import EventEmitter from './event_emitter';

frappe.provide('hub');
frappe.provide('erpnext.hub');

$.extend(erpnext.hub, EventEmitter.prototype);

erpnext.hub.Marketplace = class Marketplace {
	constructor({ parent }) {
		this.$parent = $(parent);
		this.page = parent.page;

		frappe.db.get_doc('Hub Settings')
			.then(doc => {
				hub.settings = doc;
				this.registered = doc.registered;

				this.setup_header();
				this.make_sidebar();
				this.make_body();
				this.setup_events();
				this.refresh();
			});
	}

	setup_header() {
		this.page.set_title(__('Marketplace'));
	}

	setup_events() {
		this.$parent.on('click', '[data-route]', (e) => {
			const $target = $(e.currentTarget);
			const route = $target.data().route;
			frappe.set_route(route);
		});

		// generic action handler
		this.$parent.on('click', '[data-action]', e => {
			const $target = $(e.currentTarget);
			const action = $target.data().action;

			if (action && this[action]) {
				this[action].apply(this, $target);
			}
		})
	}

	make_sidebar() {
		this.$sidebar = this.$parent.find('.layout-side-section').addClass('hidden-xs');

		new Vue({
			el: $('<div>').appendTo(this.$sidebar)[0],
			render: h => h(Sidebar)
		});
	}

	make_body() {
		this.$body = this.$parent.find('.layout-main-section');
		this.$page_container = $('<div class="hub-page-container">').appendTo(this.$body);

		new Vue({
			el: '.hub-page-container',
			render: h => h(PageContainer)
		});

		erpnext.hub.on('seller-registered', () => {
			this.registered = 1;
			this.make_sidebar_nav_buttons();
		});
	}

	refresh() {

	}

	_refresh() {
		const route = frappe.get_route();
		this.subpages = this.subpages || {};

		for (let page in this.subpages) {
			this.subpages[page].hide();
		}

		if (route[1] === 'home' && !this.subpages.home) {
			this.subpages.home = new erpnext.hub.HomePage(this.$body);
		}

		if (route[1] === 'search' && !this.subpages.search) {
			this.subpages.search = new erpnext.hub.SearchPage(this.$body);
		}

		if (route[1] === 'category' && route[2] && !this.subpages.category) {
			this.subpages.category = new erpnext.hub.CategoryPage(this.$body);
		}

		if (route[1] === 'item' && route[2] && !this.subpages.item) {
			this.subpages.item = new erpnext.hub.ItemPage(this.$body);
		}

		if (route[1] === 'seller' && !this.subpages['seller']) {
			this.subpages['seller'] = new erpnext.hub.SellerPage(this.$body);
		}

		if (route[1] === 'register' && !this.subpages.register) {
			if (this.registered) {
				frappe.set_route('marketplace', 'home');
				return;
			}
			this.subpages.register = new erpnext.hub.Register(this.$body);
		}

		// registered seller routes
		if (route[1] === 'saved-products' && !this.subpages['saved-products']) {
			this.subpages['saved-products'] = new erpnext.hub.SavedProductsPage(this.$body);
		}

		if (route[1] === 'profile' && !this.subpages.profile) {
			this.subpages.profile = new erpnext.hub.ProfilePage(this.$body);
		}

		if (route[1] === 'publish' && !this.subpages.publish) {
			this.subpages.publish = new erpnext.hub.PublishPage(this.$body);
		}

		if (route[1] === 'my-products' && !this.subpages['my-products']) {
			this.subpages['my-products'] = new erpnext.hub.PublishedProductsPage(this.$body);
		}

		if (route[1] === 'buying' && !this.subpages['buying']) {
			this.subpages['buying'] = new erpnext.hub.Buying(this.$body);
		}

		if (route[1] === 'selling' && !this.subpages['selling']) {
			this.subpages['selling'] = new erpnext.hub.Selling(this.$body, 'Selling');
		}

		// dont allow unregistered users to access registered routes
		const registered_routes = ['saved-products', 'profile', 'publish', 'my-products', 'messages'];
		if (!hub.settings.registered && registered_routes.includes(route[1])) {
			frappe.set_route('marketplace', 'home');
			return;
		}

		if (!Object.keys(this.subpages).includes(route[1])) {
			if (!this.subpages.not_found) {
				this.subpages.not_found = new erpnext.hub.NotFoundPage(this.$body);
			}
			route[1] = 'not_found';
		}

		this.update_sidebar();
		frappe.utils.scroll_to(0);
		this.subpages[route[1]].show();
	}

	show_register_dialog() {
		this.register_dialog = ProfileDialog(
			__('Become a Seller'),
			{
				label: __('Register'),
				on_submit: this.register_seller.bind(this)
			}
		);

		this.register_dialog.show();
	}

	register_seller(form_values) {
		frappe.call({
		    method: 'erpnext.hub_node.doctype.hub_settings.hub_settings.register_seller',
		    args: form_values
		}).then(() => {
			this.register_dialog.hide();
			frappe.set_route('marketplace', 'publish');

		    erpnext.hub.trigger('seller-registered');
		});
	}
}
