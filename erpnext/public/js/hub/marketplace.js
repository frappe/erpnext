// pages
import './pages/home';
import './pages/favourites';
import './pages/search';
import './pages/category';
import './pages/item';
import './pages/seller';
import './pages/register';
import './pages/profile';
import './pages/publish';
import './pages/published_products';
import './pages/messages';
import './pages/not_found';

// components
import { ProfileDialog } from './components/profile_dialog';

// helpers
import './hub_call';

frappe.provide('hub');
frappe.provide('erpnext.hub');

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
			? `<li class="hub-sidebar-item" data-route="marketplace/favourites">
					${__('Favorites')}
				</li>
				<li class="hub-sidebar-item text-muted" data-route="marketplace/profile">
					${__('Your Profile')}
				</li>
				<li class="hub-sidebar-item text-muted" data-route="marketplace/publish">
					${__('Publish Products')}
				</li>
				<li class="hub-sidebar-item text-muted" data-route="marketplace/messages">
					${__('Messages')}
				</li>`

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
		this.$body.on('seller-registered', () => {
			this.registered = 1;
			this.make_sidebar_nav_buttons();
		});
	}

	update_sidebar() {
		const route = frappe.get_route();
		const route_str = route.slice(0, 2).join('/');
		const $sidebar_item = this.$sidebar.find(`[data-route="${route_str}"]`);

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
			this.subpages.home = new erpnext.hub.Home(this.$body);
		}

		if (route[1] === 'search' && !this.subpages.search) {
			this.subpages.search = new erpnext.hub.SearchPage(this.$body);
		}

		if (route[1] === 'category' && route[2] && !this.subpages.category) {
			this.subpages.category = new erpnext.hub.Category(this.$body);
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
		if (route[1] === 'favourites' && !this.subpages.favourites) {
			this.subpages.favourites = new erpnext.hub.Favourites(this.$body);
		}

		if (route[1] === 'profile' && !this.subpages.profile) {
			this.subpages.profile = new erpnext.hub.Profile(this.$body);
		}

		if (route[1] === 'publish' && !this.subpages.publish) {
			this.subpages.publish = new erpnext.hub.Publish(this.$body);
		}

		if (route[1] === 'my-products' && !this.subpages['my-products']) {
			this.subpages['my-products'] = new erpnext.hub.PublishedProducts(this.$body);
		}

		if (route[1] === 'messages' && !this.subpages['messages']) {
			this.subpages['messages'] = new erpnext.hub.Messages(this.$body);
		}

		// dont allow unregistered users to access registered routes
		const registered_routes = ['favourites', 'profile', 'publish', 'my-products', 'messages'];
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
		this.profile_dialog = ProfileDialog(__('Become a Seller'), {
			label: __('Register'),
			on_submit: this.register_seller.bind(this)
		});

		this.profile_dialog.show();
	}

	register_seller(form_values) {
		frappe.call({
		    method: 'erpnext.hub_node.doctype.hub_settings.hub_settings.register_seller',
		    args: form_values,
		    btn: $(e.currentTarget)
		}).then(() => {
			this.profile_dialog.hide();
			frappe.set_route('marketplace', 'publish');

		    // custom jquery event
		    this.$body.trigger('seller-registered');
		});
	}
}
