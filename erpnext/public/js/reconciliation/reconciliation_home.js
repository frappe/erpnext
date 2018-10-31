import Vue from 'vue/dist/vue.js';
import './vue-plugins';

import Home from './Home.vue';
import Sidebar from './Sidebar.vue';

import EventEmitter from '../hub/event_emitter';

frappe.provide('erpnext.bankreconciliation');
frappe.provide('frappe.route');
frappe.provide('frappe.upload');

$.extend(erpnext.bankreconciliation, EventEmitter.prototype);
$.extend(frappe.route, EventEmitter.prototype);

erpnext.bankreconciliation.Home = class bankreconciliation {
	constructor({ parent }) {
		this.$parent = $(parent);
		this.page = parent.page;
		this.company = frappe.defaults.get_user_default("Company");
		this.setup_header();
		this.make_sidebar();
		this.make_body();
		this.setup_events();
		this.set_secondary_action();
	}

	make_sidebar() {
		this.$sidebar = this.$parent.find('.layout-side-section').addClass('hidden-xs');

		new Vue({
			el: $('<div>').appendTo(this.$sidebar)[0],
			render: h => h(Sidebar)
		});
	}

	make_body() {
		let me = this;
		me.$body = me.$parent.find('.layout-main-section');
		me.$page_container = $('<div class="bankreconciliation-page-container">').appendTo(this.$body);

		new Vue({
			el: me.$page_container[0],
			render(h) {
				return h(Home, {props: { initCompany: me.company}})
			}
		});
	}

	setup_header() {
		this.page.set_title(__('Bank Reconciliation'));
	}

	setup_events() {
		this.$parent.on('click', '[data-route]', (e) => {
			const $target = $(e.currentTarget);
			const route = $target.data().route;
			frappe.set_route(route);
		});

		this.$parent.on('click', '[data-action]', e => {
			const $target = $(e.currentTarget);
			const action = $target.data().action;

			if (action && this[action]) {
				this[action].apply(this, $target);
			}
		})
	}

	set_secondary_action() {
		let me = this;
		this.page.set_secondary_action(this.company, function () {
			me.company_selection_dialog();
		})
	}

	company_selection_dialog() {
		let me = this;
		let dialog = new frappe.ui.Dialog({
			title: __('Select another company'),
			fields: [
				{
					"label": "Company",
					"fieldname": "company",
					"fieldtype": "Link",
					"options": "Company"
				}
			],
			primary_action_label: __('Confirm'),
			primary_action: function(v) {
				me.company = v.company;
				erpnext.bankreconciliation.trigger('company_changed', v.company);
				me.set_secondary_action();
				dialog.hide();
			},
		})
		dialog.show();
	}
};