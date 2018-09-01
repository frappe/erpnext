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

		frappe.model.with_doc('Marketplace Settings').then(doc => {
			hub.settings = doc;
			const is_registered = hub.settings.registered;
			const is_registered_seller = hub.settings.company_email === frappe.session.user;
			this.setup_header();
			this.make_sidebar();
			this.make_body();
			this.setup_events();
			this.refresh();
			if (!is_registered && !is_registered_seller && frappe.user_roles.includes('System Manager')) {
				this.page.set_primary_action('Become a Seller', this.show_register_dialog.bind(this))
			}
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
			this.page.clear_primary_action()
			frappe.model.with_doc('Marketplace Settings').then((doc)=> {
				hub.settings = doc;
			});
		});
	}

	refresh() {

	}

	show_register_dialog() {
		this.register_dialog = ProfileDialog(
			__('Become a Seller'),
			{
				label: __('Register'),
				on_submit: this.register_marketplace.bind(this)
			}
		);

		this.register_dialog.show();
	}

	register_marketplace({company, company_email}) {
		frappe.call({
		    method: 'erpnext.hub_node.api.register_marketplace',
		    args: {
				company,
				company_email,
			}
		}).then((r) => {
			if (r.message && r.message.ok) {
				this.register_dialog.hide();
				frappe.set_route('marketplace', 'publish');
				erpnext.hub.trigger('seller-registered');
			}
		});
	}

}
