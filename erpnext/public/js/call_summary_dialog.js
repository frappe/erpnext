class CallSummaryDialog {
	constructor(opts) {
		this.number = opts.number;
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
				this.$modal_body.append(`${frappe.utils.get_form_link('Contact', res.name, true)}`)
			}
		});
		d.show();
	}
}

$(document).on('app_ready', function() {
	frappe.realtime.on('incoming_call', data => {
		const number = data.CallFrom;
		frappe.call_summary_dialog = new CallSummaryDialog({
			number
		});
	});
});
