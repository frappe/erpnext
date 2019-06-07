class CallPopup {
	constructor(call_log) {
		this.caller_number = call_log.from;
		this.call_log = call_log;
		this.make();
	}

	make() {
		this.dialog = new frappe.ui.Dialog({
			'static': true,
			'minimizable': true,
			'fields': [{
				'fieldname': 'caller_info',
				'fieldtype': 'HTML'
			}, {
				'fielname': 'last_interaction',
				'fieldtype': 'Section Break',
			}, {
				'fieldtype': 'Small Text',
				'label': "Last Communication",
				'fieldname': 'last_communication',
				'read_only': true,
				'default': `<i class="text-muted">${__('No communication found.')}<i>`
			}, {
				'fieldtype': 'Small Text',
				'label': "Last Issue",
				'fieldname': 'last_issue',
				'read_only': true,
				'default': `<i class="text-muted">${__('No issue raised by the customer.')}<i>`
			}, {
				'fieldtype': 'Column Break',
			}, {
				'fieldtype': 'Small Text',
				'label': 'Call Summary',
				'fieldname': 'call_summary',
			}, {
				'fieldtype': 'Button',
				'label': 'Submit',
				'click': () => {
					const values = this.dialog.get_values();
					if (!values.call_summary) return
					frappe.xcall('erpnext.crm.doctype.utils.add_call_summary', {
						'docname': this.call_log.id,
						'summary': values.call_summary,
					}).then(() => {
						this.dialog.set_value('call_summary', '');
					});
				}
			}],
		});
		this.set_call_status();
		this.make_caller_info_section();
		this.dialog.get_close_btn().show();
		this.dialog.$body.addClass('call-popup');
		this.dialog.set_secondary_action(() => {
			delete erpnext.call_popup;
			this.dialog.hide();
		});
		frappe.utils.play_sound("incoming_call");
		this.dialog.show();
	}

	make_caller_info_section() {
		const wrapper = this.dialog.fields_dict['caller_info'].$wrapper;
		wrapper.append('<div class="text-muted"> Loading... </div>');
		frappe.xcall('erpnext.crm.doctype.utils.get_document_with_phone_number', {
			'number': this.caller_number
		}).then(contact_doc => {
			wrapper.empty();
			const contact = this.contact = contact_doc;
			if (!contact) {
				wrapper.append(`
					<div class="caller-info">
						<div>Unknown Number: <b>${this.caller_number}</b></div>
						<a class="contact-link" href="#Form/Contact/New Contact?phone=${this.caller_number}">
							${__('Create New Contact')}
						</a>
					</div>
				`);
			} else {
				const contact_name = frappe.utils.get_form_link('Contact', contact.name, true);
				const link = contact.links ? contact.links[0] : null;
				let contact_link = link ? frappe.utils.get_form_link(link.link_doctype, link.link_name, true): '';
				wrapper.append(`
					<div class="caller-info flex">
						${frappe.avatar(null, 'avatar-xl', contact.name, contact.image)}
						<div>
							<h5>${contact_name}</h5>
							<div>${contact.mobile_no || ''}</div>
							<div>${contact.phone_no || ''}</div>
							${contact_link}
						</div>
					</div>
				`);
				this.set_call_status();
				this.make_last_interaction_section();
			}
		});
	}

	set_indicator(color, blink=false) {
		let classes = `indicator ${color} ${blink ? 'blink': ''}`;
		this.dialog.header.find('.indicator').attr('class', classes);
	}

	set_call_status(call_status) {
		let title = '';
		call_status = call_status || this.call_log.status;
		if (['Ringing'].includes(call_status) || !call_status) {
			title = __('Incoming call from {0}',
				[this.contact ? `${this.contact.first_name || ''} ${this.contact.last_name || ''}` : this.caller_number]);
			this.set_indicator('blue', true);
		} else if (call_status === 'In Progress') {
			title = __('Call Connected');
			this.set_indicator('yellow');
		} else if (call_status === 'Missed') {
			this.set_indicator('red');
			title = __('Call Missed');
		} else if (['Completed', 'Disconnected'].includes(call_status)) {
			this.set_indicator('red');
			title = __('Call Disconnected');
		} else {
			this.set_indicator('blue');
			title = call_status;
		}
		this.dialog.set_title(title);
	}

	update_call_log(call_log) {
		this.call_log = call_log;
		this.set_call_status();
	}

	call_disconnected(call_log) {
		frappe.utils.play_sound("call_disconnect");
		this.update_call_log(call_log);
		setTimeout(this.get_close_btn().click, 10000);
	}

	make_last_interaction_section() {
		frappe.xcall('erpnext.crm.doctype.utils.get_last_interaction', {
			'number': this.caller_number,
			'reference_doc': this.contact
		}).then(data => {
			const comm_field = this.dialog.fields_dict["last_communication"];
			if (data.last_communication) {
				const comm = data.last_communication;
				// this.dialog.set_df_property('last_interaction', 'hidden', false);
				comm_field.set_value(comm.content);
				comm_field.$wrapper.append(frappe.utils.get_form_link('Communication', comm.name));
			}

			if (data.last_issue) {
				const issue = data.last_issue;
				// this.dialog.set_df_property('last_interaction', 'hidden', false);
				const issue_field = this.dialog.fields_dict["last_issue"];
				issue_field.set_value(issue.subject);
				issue_field.$wrapper.append(`<a class="text-medium" href="#List/Issue?customer=${issue.customer}">
					View all issues from ${issue.customer}
				</a>`);
			}
		});
	}
}

$(document).on('app_ready', function () {
	frappe.realtime.on('show_call_popup', call_log => {
		if (!erpnext.call_popup) {
			erpnext.call_popup = new CallPopup(call_log);
		} else {
			erpnext.call_popup.update_call_log(call_log);
			erpnext.call_popup.dialog.show();
		}
	});
	frappe.realtime.on('call_disconnected', call_log => {
		if (erpnext.call_popup && erpnext.call_popup.call_log.id === call_log.id) {
			erpnext.call_popup.call_disconnected(call_log);
		}
	});
});
