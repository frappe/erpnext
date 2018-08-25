import Vue from 'vue/dist/vue.js';

// pages
import './pages/item';
import './pages/seller';
import './pages/profile';
import './pages/messages';
import './pages/buying_messages';
import './pages/not_found';

import Home from './pages/Home.vue';
import SavedProducts from './pages/SavedProducts.vue';
import Publish from './pages/Publish.vue';
import Category from './pages/Category.vue';
import Search from './pages/Search.vue';
import PublishedProducts from './pages/PublishedProducts.vue';

// components
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

		this.make_sidebar_nav_buttons();
		this.make_sidebar_categories();
	}

	make_sidebar_nav_buttons() {
		let $nav_group = this.$sidebar.find('[data-nav-buttons]');
		if (!$nav_group.length) {
			$nav_group = $('<ul class="list-unstyled hub-sidebar-group" data-nav-buttons>').appendTo(this.$sidebar);
		}
		$nav_group.empty();

		const user_specific_items_html = this.registered
			? `<li class="hub-sidebar-item" data-route="marketplace/saved-products">
					${__('Saved Products')}
				</li>
				<li class="hub-sidebar-item text-muted" data-route="marketplace/profile">
					${__('Your Profile')}
				</li>
				<li class="hub-sidebar-item text-muted" data-route="marketplace/publish">
					${__('Publish Products')}
				</li>
				<li class="hub-sidebar-item text-muted" data-route="marketplace/selling">
					${__('Selling')}
				</li>
				<li class="hub-sidebar-item text-muted" data-route="marketplace/buying">
					${__('Buying')}
				</li>
				`

			: `<li class="hub-sidebar-item text-muted" data-action="show_register_dialog">
					${__('Become a seller')}
				</li>`;

		$nav_group.append(`
			<li class="hub-sidebar-item" data-route="marketplace/home">
				${__('Browse')}
			</li>
			${user_specific_items_html}
		`);
	}

	make_sidebar_categories() {
		hub.call('get_categories')
			.then(categories => {
				categories = categories.map(d => d.name);

				const sidebar_items = [
					`<li class="hub-sidebar-item bold is-title">
						${__('Category')}
					</li>`,
					`<li class="hub-sidebar-item active" data-route="marketplace/home">
						${__('All')}
					</li>`,
					...(this.registered
						? [`<li class="hub-sidebar-item active" data-route="marketplace/my-products">
							${__('Your Products')}
						</li>`]
						: []),
					...categories.map(category => `
						<li class="hub-sidebar-item text-muted" data-route="marketplace/category/${category}">
							${__(category)}
						</li>
					`)
				];

				this.$sidebar.append(`
					<ul class="list-unstyled">
						${sidebar_items.join('')}
					</ul>
				`);

				this.update_sidebar();
			});
	}

	make_body() {
		this.$body = this.$parent.find('.layout-main-section');
		erpnext.hub.on('seller-registered', () => {
			this.registered = 1;
			this.make_sidebar_nav_buttons();
		});
	}

	update_sidebar() {
		const route = frappe.get_route();
		const route_str = route.join('/');
		const part_route_str = route.slice(0, 2).join('/');
		const $sidebar_item = this.$sidebar.find(`[data-route="${route_str}"], [data-route="${part_route_str}"]`);


		const $siblings = this.$sidebar.find('[data-route]');
		$siblings.removeClass('active').addClass('text-muted');
		$sidebar_item.addClass('active').removeClass('text-muted');
	}

	refresh() {
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
			this.subpages.item = new erpnext.hub.Item(this.$body);
		}

		if (route[1] === 'seller' && !this.subpages['seller']) {
			this.subpages['seller'] = new erpnext.hub.Seller(this.$body);
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
			this.subpages.profile = new erpnext.hub.Profile(this.$body);
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
				this.subpages.not_found = new erpnext.hub.NotFound(this.$body);
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

erpnext.hub.HomePage = class {
	constructor(parent) {
		this.$wrapper = $(`<div id="vue-area-home">`).appendTo($(parent));

		new Vue({
			render: h => h(Home)
		}).$mount('#vue-area-home');
	}

	show() {
		$('[data-page-name="home"]').show();
	}

	hide() {
		$('[data-page-name="home"]').hide();
	}
}

erpnext.hub.SavedProductsPage = class {
	constructor(parent) {
		this.$wrapper = $(`<div id="vue-area-saved">`).appendTo($(parent));

		new Vue({
			render: h => h(SavedProducts)
		}).$mount('#vue-area-saved');
	}

	show() {
		$('[data-page-name="saved-products"]').show();
	}

	hide() {
		$('[data-page-name="saved-products"]').hide();
	}
}

erpnext.hub.PublishPage = class {
	constructor(parent) {
		this.$wrapper = $(`<div id="vue-area">`).appendTo($(parent));

		new Vue({
			render: h => h(Publish)
		}).$mount('#vue-area');
	}

	show() {
		$('[data-page-name="publish"]').show();
	}

	hide() {
		$('[data-page-name="publish"]').hide();
	}

}

erpnext.hub.CategoryPage = class {
	constructor(parent) {
		this.$wrapper = $(`<div id="vue-area-category">`).appendTo($(parent));

		new Vue({
			render: h => h(Category)
		}).$mount('#vue-area-category');
	}

	show() {
		$('[data-page-name="category"]').show();
	}

	hide() {
		$('[data-page-name="category"]').hide();
	}
}

erpnext.hub.PublishedProductsPage = class {
	constructor(parent) {
		this.$wrapper = $(`<div id="vue-area-published-products">`).appendTo($(parent));

		new Vue({
			render: h => h(PublishedProducts)
		}).$mount('#vue-area-published-products');
	}

	show() {
		$('[data-page-name="published-products"]').show();
	}

	hide() {
		$('[data-page-name="published-products"]').hide();
	}
}

erpnext.hub.SearchPage = class {
	constructor(parent) {
		this.$wrapper = $(`<div id="vue-area-search">`).appendTo($(parent));

		new Vue({
			render: h => h(Search)
		}).$mount('#vue-area-search');
	}

	show() {
		$('[data-page-name="search"]').show();
	}

	hide() {
		$('[data-page-name="search"]').hide();
	}
}
