class CallPopup {
	constructor(call_log) {
		this.caller_number = call_log.from;
		this.call_log = call_log;
		this.setup_listener();
		this.make();
	}

	make() {
		frappe.utils.play_sound('incoming-call');
		this.dialog = new frappe.ui.Dialog({
			'static': true,
			'minimizable': true
		});
		this.dialog.get_close_btn().show();
		this.setup_dialog();
		this.set_call_status();
		frappe.utils.bind_actions_with_object(this.dialog.$body, this);
		this.dialog.$wrapper.addClass('call-popup');
		this.dialog.get_close_btn().unbind('click').click(this.close_modal.bind(this));
		this.dialog.show();
	}

	setup_dialog() {
		this.setup_call_details();
		this.dialog.$body.empty().append(this.caller_info);
	}

	set_indicator(color, blink=false) {
		let classes = `indicator ${color} ${blink ? 'blink': ''}`;
		this.dialog.header.find('.indicator').attr('class', classes);
	}

	set_call_status(call_status) {
		let title = '';
		call_status = call_status || this.call_log.status;
		if (['Ringing'].includes(call_status) || !call_status) {
			title = __('Incoming call from {0}', [this.get_caller_name() || this.caller_number]);
			this.set_indicator('blue', true);
		} else if (call_status === 'In Progress') {
			title = __('Call Connected');
			this.set_indicator('green');
		} else if (['No Answer', 'Missed'].includes(call_status)) {
			this.set_indicator('yellow');
			title = __('Call Missed');
		} else if (['Completed', 'Busy', 'Failed'].includes(call_status)) {
			this.set_indicator('red');
			title = __('Call Ended');
		} else {
			this.set_indicator('blue');
			title = call_status;
		}
		this.dialog.set_title(title);
	}

	update_call_log(call_log, missed) {
		this.call_log = call_log;
		this.set_call_status(missed ? 'Missed': null);
	}

	close_modal() {
		this.dialog.hide();
		delete erpnext.call_popup;
	}

	call_ended(call_log, missed) {
		frappe.utils.play_sound('call-disconnect');
		this.update_call_log(call_log, missed);
		setTimeout(() => {
			if (!this.dialog.get_value('call_summary')) {
				this.close_modal();
			}
		}, 60000);
		this.clear_listeners();
	}

	get_caller_name() {
		const contact_link = this.get_contact_link();
		return contact_link.link_title || contact_link.link_name;
	}

	get_contact_link() {
		let log = this.call_log;
		let contact_link = log.links.find(d => d.link_doctype === 'Contact');
		return contact_link || {};
	}

	setup_listener() {
		frappe.realtime.on(`call_${this.call_log.id}_ended`, call_log => {
			this.call_ended(call_log);
		});

		frappe.realtime.on(`call_${this.call_log.id}_missed`, call_log => {
			this.call_ended(call_log, true);
		});
	}

	clear_listeners() {
		frappe.realtime.off(`call_${this.call_log.id}_ended`);
		frappe.realtime.off(`call_${this.call_log.id}_missed`);
	}

	setup_call_details() {
		this.caller_info = $(`<div></div>`);
		this.call_details = new frappe.ui.FieldGroup({
			fields: [{
				'fieldname': 'name',
				'label': 'Name',
				'default': this.get_caller_name() || __('Unknown Caller'),
				'fieldtype': 'Data',
				'read_only': 1
			}, {
				'fieldtype': 'Button',
				'label': __('Open Contact'),
				'click': () => frappe.set_route('Form', 'Contact', this.get_contact_link().link_name),
				'depends_on': () => this.get_caller_name()
			}, {
				'fieldtype': 'Button',
				'label': __('Create New Contact'),
				'click': this.create_new_contact.bind(this),
				'depends_on': () => !this.get_caller_name()
			}, {
				'fieldtype': 'Button',
				'label': __('Create New Customer'),
				'click': this.create_new_customer.bind(this),
				'depends_on': () => !this.get_caller_name()
			}, {
				'fieldtype': 'Button',
				'label': __('Create New Lead'),
				'click': () => frappe.new_doc('Lead', { 'mobile_no': this.caller_number }),
				'depends_on': () => !this.get_caller_name()
			}, {
				'fieldtype': 'Column Break',
			}, {
				'fieldname': 'number',
				'label': 'Phone Number',
				'fieldtype': 'Data',
				'default': this.caller_number,
				'read_only': 1
			}, {
				'fieldtype': 'Section Break',
				'hide_border': 1,
			}, {
				'fieldtype': 'Small Text',
				'label': __('Call Summary'),
				'fieldname': 'call_summary',
			}, {
				'fieldtype': 'Button',
				'label': __('Save'),
				'click': () => {
					const call_summary = this.call_details.get_value('call_summary');
					if (!call_summary) return;
					frappe.xcall('erpnext.telephony.doctype.call_log.call_log.add_call_summary', {
						'call_log': this.call_log.name,
						'summary': call_summary,
					}).then(() => {
						this.close_modal();
						frappe.show_alert({
							message: `
								${__('Call Summary Saved')}
								<br>
								<a
									class="text-small text-muted"
									href="/app/call-log/${this.call_log.name}">
									${__('View call log')}
								</a>
							`,
							indicator: 'green'
						});
					});
				}
			}],
			body: this.caller_info
		});
		this.call_details.make();
	}

	is_known_caller() {
		return Boolean(this.get_caller_name());
	}

	create_new_customer() {
		// to avoid quick entry form
		const new_customer = frappe.model.get_new_doc('Customer');
		new_customer.mobile_no = this.caller_number;
		frappe.set_route('Form', new_customer.doctype, new_customer.name);
	}

	create_new_contact() {
		// TODO: fix new_doc, it should accept child table values
		const new_contact = frappe.model.get_new_doc('Contact');
		const phone_no = frappe.model.add_child(new_contact, 'Contact Phone', 'phone_nos');
		phone_no.phone = this.caller_number;
		phone_no.is_primary_mobile_no = 1;
		frappe.set_route('Form', new_contact.doctype, new_contact.name);
	}
}

$(document).on('app_ready', function () {
	frappe.realtime.on('show_call_popup', call_log => {
		let call_popup = erpnext.call_popup;
		if (call_popup && call_log.name === call_popup.call_log.name) {
			call_popup.update_call_log(call_log);
			call_popup.dialog.show();
		} else {
			erpnext.call_popup = new CallPopup(call_log);
		}
	});
});

window.CallPopup = CallPopup;
