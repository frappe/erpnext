frappe.ui.form.ControlData = frappe.ui.form.ControlData.extend( {
	make_input() {
		this._super();
		if (this.df.options == 'Phone') {
			this.setup_phone();
		}
	},
	setup_phone() {
		if (frappe.phone_call.handler) {
			this.$wrapper.find('.control-input')
				.append(`
					<span class="phone-btn">
						<a class="btn-open no-decoration" title="${__('Make a call')}">
							${frappe.utils.icon('call')}
					</span>
				`)
				.find('.phone-btn')
				.click(() => {
					frappe.phone_call.handler(this.get_value(), this.frm);
				});
		}
	}
});
