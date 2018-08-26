export default class SubPage {
	constructor(parent, ...options) {
		this.$parent = $(parent);
		this.options = options;
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
		this.$wrapper = $(`<div class="marketplace-page"
			data-page-name="${page_name}">`
		).appendTo(this.$parent);

		this.hide();
	}

	add_section({ title, body } = {}) {
		this._sections = this._sections || {};

		if (title && this._sections[title]) {
			return this._sections[title];
		}

		const $section = $(`
			<div class="row hub-section">
				<div class="col-sm-12 hub-section-header padding-bottom flex">
					<h4>${title || ''}</h4>
				</div>
				<div class="col-sm-12 hub-section-body">
					${body || ''}
				</div>
			</div>
		`);

		if (title) {
			this._sections[title] = $section;
		}

		this.$wrapper.append($section);
		return $section;
	}

	add_back_link(title, route) {
		const $section = this.add_section();
		this.$wrapper.prepend($section);

		$section.addClass('margin-bottom');
		$section.find('.hub-section-header').remove()
		$section.find('.hub-section-body').html(`
			<button class="btn btn-xs btn-default" data-route="${route}">${title}</button>
		`);
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
}
