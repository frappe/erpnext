class CallPopup {
	constructor({ call_from, call_log, call_status_method }) {
		this.number = call_from;
		this.call_log = call_log;
		this.call_status_method = call_status_method;
		this.make();
		this.make_customer_contact();
		this.setup_call_status_updater();
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
		this.dialog.show();
		this.dialog.get_close_btn().show();
	}

	make_customer_contact() {
		const wrapper = this.dialog.fields_dict["customer_info"].$wrapper;
		wrapper.append('<div class="text-muted"> Loading... </div>');
		frappe.xcall('erpnext.crm.doctype.utils.get_document_with_phone_number', {
			'number': this.number
		}).then(contact_doc => {
			wrapper.empty();
			const contact = contact_doc;
			if (!contact) {
				wrapper.append('<div>Unknown Contact</div>');
				wrapper.append(`<a href="#Form/Contact/New Contact?phone=${this.number}">${__('Make New Contact')}</a>`);
			} else {
				const link = contact.links ? contact.links[0] : null;
				const contact_link = link ? frappe.utils.get_form_link(link.link_doctype, link.link_name, true): '';
				wrapper.append(`
					<div class="customer-info flex">
						<img src="${contact.image}">
						<div class='flex-column'>
							<span>${contact.first_name} ${contact.last_name}</span>
							<span>${contact.mobile_no}</span>
							${contact_link}
						</div>
					</div>
				`);
			}
		});
	}

	set_indicator(color) {
		this.dialog.header.find('.indicator').removeClass('hidden').addClass('blink').addClass(color);
	}

	set_call_status(call_status) {
		let title = '';
		call_status = this.call_log.call_status;
		if (call_status === 'busy') {
			title = __('Incoming call');
			this.set_indicator('blue');
		} else if (call_status === 'in-progress') {
			title = __('Call Connected');
			this.set_indicator('yellow');
		} else if (call_status === 'missed') {
			this.set_indicator('red');
			title = __('Call Missed');
		}
		this.dialog.set_title(title);
	}

	update(data) {
		this.call_log = data.call_log;
		this.set_call_status();
	}

	setup_call_status_updater() {
		this.updater = setInterval(this.get_call_status.bind(this), 2000);
	}

	get_call_status() {
		frappe.xcall(this.call_status_method, {
			'call_id': this.call_log.call_id
		}).then((call_status) => {
			if (call_status === 'completed') {
				clearInterval(this.updater);
			}
		});
	}

	terminate_popup() {
		clearInterval(this.updater);
		this.dialog.hide();
		delete erpnext.call_popup;
		frappe.msgprint('Call Forwarded');
	}
}

$(document).on('app_ready', function () {
	frappe.realtime.on('show_call_popup', data => {
		if (!erpnext.call_popup) {
			erpnext.call_popup = new CallPopup(data);
		} else {
			console.log(data);
			erpnext.call_popup.update(data);
			erpnext.call_popup.dialog.show();
		}
	});

	frappe.realtime.on('terminate_call_popup', () => {
		if (erpnext.call_popup) {
			erpnext.call_popup.terminate_popup();
		}
	});
});
