class CallPopup {
	constructor({ call_from, call_log }) {
		this.number = call_from;
		this.call_log = call_log;
		this.make();
	}

	make() {
		this.dialog = new frappe.ui.Dialog({
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
			}, {
				'fieldtype': 'Button',
				'label': 'Submit',
				'click': () => {
					this.dialog.get_value();
				}
			}]
		});
		this.set_call_status(this.call_log.call_status);
		this.make_customer_contact();
		this.dialog.show();
		this.dialog.get_close_btn().show();
		this.dialog.header.find('.indicator').removeClass('hidden').addClass('blue');
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

	make_summary_section() {
		//
	}

	set_call_status() {
		let title = '';
		if (this.call_log.call_status === 'Incoming') {
			if (this.contact) {
				title = __('Incoming call from {0}', [this.contact.name]);
			} else {
				title = __('Incoming call from unknown number');
			}
		} else {
			title = __('Call Connected');
		}
		this.dialog.set_title(title);
	}

	update(data) {
		this.call_log = data.call_log;
		this.set_call_status();
	}
}

$(document).on('app_ready', function () {
	frappe.realtime.on('show_call_popup', data => {
		if (!erpnext.call_popup) {
			erpnext.call_popup = new CallPopup(data);
		} else {
			erpnext.call_popup.update(data);
			erpnext.call_popup.dialog.show();
		}
	});
});
