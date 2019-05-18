class CallSummaryDialog {
	constructor({ contact, call_payload, last_communication }) {
		this.number = call_payload.CallFrom;
		this.contact = contact;
		this.last_communication = last_communication;
		this.make();
	}

	make() {
		this.dialog = new frappe.ui.Dialog({
			'title': __(`Incoming call from ${this.contact ? this.contact.name : 'Unknown Number'}`),
			'static': true,
			'minimizable': true,
			'fields': [{
				'fieldname': 'customer_info',
				'fieldtype': 'HTML'
			}, {
				'fieldtype': 'Section Break'
			}, {
				'fieldtype': 'Small Text',
				'label': "Last Communication",
				'fieldname': 'last_communication',
				'read_only': true
			}, {
				'fieldtype': 'Column Break'
			}, {
				'fieldtype': 'Small Text',
				'label': 'Call Summary',
				'fieldname': 'call_communication',
				'default': 'This is not working please helpppp',
				"placeholder": __("Select or add new customer")
			}, {
				'fieldtype': 'Button',
				'label': 'Submit',
				'click': () => {
					frappe.xcall()
				}
			}]
		});
		this.make_customer_contact();
		this.dialog.show();
		this.dialog.get_close_btn().show();
		this.dialog.header.find('.indicator').removeClass('hidden').addClass('blue');
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

	make_customer_contact() {
		const wrapper = this.dialog.fields_dict["customer_info"].$wrapper;
		const contact = this.contact;
		const customer = this.contact.links ? this.contact.links[0] : null;
		const customer_link = customer ? frappe.utils.get_form_link(customer.link_doctype, customer.link_name, true): '';
		if (!contact) {
			wrapper.append('<b>Unknown Contact</b>');
		} else {
			wrapper.append(`
				<div class="customer-info flex">
					<img src="${contact.image}">
					<div class='flex-column'>
						<span>${contact.first_name} ${contact.last_name}</span>
						<span>${contact.mobile_no}</span>
						${customer_link}
					</div>
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

$(document).on('app_ready', function () {
	frappe.realtime.on('incoming_call', data => {
		frappe.call_summary_dialog = new CallSummaryDialog(data);
	});
});
