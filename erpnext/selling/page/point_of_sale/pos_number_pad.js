erpnext.PointOfSale.NumberPad = class {
	constructor({ wrapper, events, cols, keys, css_classes, fieldnames_map }) {
		this.wrapper = wrapper;
		this.events = events;
		this.cols = cols;
		this.keys = keys;
		this.css_classes = css_classes || [];
		this.fieldnames = fieldnames_map || {};

		this.init_component();
	}

	init_component() {
		this.prepare_dom();
		this.bind_events();
	}

	prepare_dom() {
		const { cols, keys, css_classes, fieldnames } = this;

		function get_keys() {
			return keys.reduce((a, row, i) => {
				return a + row.reduce((a2, number, j) => {
					const class_to_append = css_classes && css_classes[i] ? css_classes[i][j] : '';
					const fieldname = fieldnames && fieldnames[number] ?
						fieldnames[number] : typeof number === 'string' ? frappe.scrub(number) : number;

					return a2 + `<div class="numpad-btn ${class_to_append}" data-button-value="${fieldname}">${number}</div>`;
				}, '');
			}, '');
		}

		this.wrapper.html(
			`<div class="numpad-container">
				${get_keys()}
			</div>`
		)
	}

	bind_events() {
		const me = this;
		this.wrapper.on('click', '.numpad-btn', function() {
			const $btn = $(this);
			me.events.numpad_event($btn);
		});
	}
}
