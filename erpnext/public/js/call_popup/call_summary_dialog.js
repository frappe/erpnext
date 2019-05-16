class CallSummaryDialog {
	constructor(opts) {
		this.number = opts.number;
		this.make();
	}

	make() {
		var d = new frappe.ui.Dialog({
			'title': `Incoming Call: ${this.number}`,
			'fields': [{
				'fieldname': 'customer_info',
				'fieldtype': 'HTML'
			}, {
				'fieldtype': 'Section Break'
			}, {
				'fieldtype': 'Text',
				'label': "Last Communication",
				'fieldname': 'last_communication',
				'default': 'This is not working please helpppp',
				'placeholder': __("Select or add new customer"),
				'readonly': true
			}, {
				'fieldtype': 'Column Break'
			}, {
				'fieldtype': 'Text',
				'label': 'Call Summary',
				'fieldname': 'call_communication',
				'default': 'This is not working please helpppp',
				"placeholder": __("Select or add new customer")
			}]
		});
		// this.body.html(this.get_dialog_skeleton());
		frappe.xcall('erpnext.crm.call_summary.call_summary_utils.get_contact_doc', {
			phone_number: this.number
		}).then(res => {
			this.make_customer_contact(res, d.fields_dict["customer_info"].$wrapper);
			// this.make_last_communication_section();
		});
		d.show();
	}

	get_dialog_skeleton() {
		return `
			<div class="call-summary-body">
				<div class="customer-info flex">
				</div>
				<div class="flex">
					<div class="last-communication"></div>
					<div class="call-summary"></div>
				</div>
				<hr>
				<div class="flex">
					<div class="section-right"></div>
					<div class="section-left"></div>
				</div>
			</div>
		`;
	}
	make_customer_contact(res, wrapper) {
		if (!res) {
			wrapper.append('<b>Unknown Contact</b>');
		} else {
			wrapper.append(`
				<img src="${res.image}">
				<div class='flex-column'>
					<span>${res.first_name} ${res.last_name}</span>
					<span>${res.mobile_no}</span>
					<span>Customer: <b>Some Enterprise</b></span>
				</div>
			`);
		}
	}

	make_last_communication_section() {
		const last_communication_section = this.body.find('.last-communication');
		const last_communication = frappe.ui.form.make_control({
			parent: last_communication_section,
			df: {
				fieldtype: "Text",
				label: "Last Communication",
				fieldname: "last_communication",
				'default': 'This is not working please helpppp',
				"placeholder": __("Select or add new customer")
			},
		});
		last_communication.set_value('This is not working please helpppp');
	}

	make_summary_section() {
		//
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
