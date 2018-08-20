import { NotificationMessage } from '../components/notification_message';

export default class SubPage {
	constructor(parent, options) {
		this.$parent = $(parent);
		this.make_wrapper(options);

		// generic action handler
		this.$wrapper.on('click', '[data-action]', e => {
			const $target = $(e.currentTarget);
			const action = $target.data().action;

			if (action && this[action]) {
				this[action].apply(this, $target);
			}
		})

		// handle broken images after every render
		if (this.render) {
			this._render = this.render.bind(this);

			this.render = (...args) => {
				this._render(...args);
				frappe.dom.handle_broken_images(this.$wrapper);
			}
		}
	}

	make_wrapper() {
		const page_name = frappe.get_route()[1];
		this.$wrapper = $(`<div class="marketplace-page" data-page-name="${page_name}">`).appendTo(this.$parent);
		this.hide();
	}

	empty() {
		this.$wrapper.empty();
	}

	show() {
		this.refresh();
		this.$wrapper.show();
	}

	hide() {
		this.$wrapper.hide();
	}

	show_message(message) {
		this.$wrapper.prepend(NotificationMessage(message));
	}
}
