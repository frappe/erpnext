frappe.call_summary_dialog = class {
	constructor(opts) {
		this.number = '+91234444444';
		this.make();
	}

	make() {
		var d = new frappe.ui.Dialog();
		this.$modal_body = $(d.body);
		this.call_summary_dialog = d;
		$(d.header).html(`<div>Incoming Call: ${this.number}</div>`);
		frappe.xcall('erpnext.crm.call_summary.call_summary_utils.get_contact_doc', {
			phone_number: this.number
		}).then(res => {
			if (!res) {
				this.$modal_body.html('Unknown Contact');
			} else {
				this.$modal_body.html(`${res.first_name}`);
			}
		});
		d.show();
	}

};