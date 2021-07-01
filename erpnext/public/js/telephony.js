frappe.ui.form.ControlData = class ControlData extends frappe.ui.form.ControlData  {
	make_input() {
		super.make_input();
		if (this.df.options == 'Phone') {
			this.setup_phone();
		}
		if (this.frm && this.frm.fields_dict) {
			Object.values(this.frm.fields_dict).forEach(function(field) {
				if (field.df.read_only === 1 && field.df.options === 'Phone'
					&& field.disp_area.style[0] != 'display' && !field.has_icon) {
					field.setup_phone();
					field.has_icon = true;
				}
			});
		}
	}
	setup_phone() {
		if (frappe.phone_call.handler) {
			let control = this.df.read_only ? '.control-value' : '.control-input';
			this.$wrapper.find(control)
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
};
