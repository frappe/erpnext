class CallPopup {
	constructor({ call_from, call_log, call_status_method }) {
		this.caller_number = call_from;
		this.call_log = call_log;
		this.call_status_method = call_status_method;
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
				'read_only': true
			}, {
				'fieldname': 'last_communication_link',
				'fieldtype': 'HTML',
			}, {
				'fieldtype': 'Small Text',
				'label': "Last Issue",
				'fieldname': 'last_issue',
				'read_only': true
			}, {
				'fieldname': 'last_issue_link',
				'fieldtype': 'HTML',
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
						'docname': this.call_log.name,
						'summary': values.call_summary,
					}).then(() => {
						this.dialog.set_value('call_summary', '');
					});
				}
			}],
			on_minimize_toggle: () => {
				this.set_call_status();
			}
		});
		this.set_call_status(this.call_log.call_status);
		this.make_caller_info_section();
		this.dialog.get_close_btn().show();
		this.setup_call_status_updater();
		this.dialog.$body.addClass('call-popup');
		this.dialog.set_secondary_action(() => {
			clearInterval(this.updater);
			delete erpnext.call_popup;
			this.dialog.hide();
		});
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
						<a class="contact-link text-medium" href="#Form/Contact/New Contact?phone=${this.caller_number}">
							${__('Create New Contact')}
						</a>
					</div>
				`);
			} else {
				const link = contact.links ? contact.links[0] : null;
				const contact_link = link ? frappe.utils.get_form_link(link.link_doctype, link.link_name, true): '';
				wrapper.append(`
					<div class="caller-info flex">
						<img src="${contact.image}">
						<div class='flex-column'>
							<span>${contact.first_name} ${contact.last_name}</span>
							<span>${contact.mobile_no}</span>
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
		this.dialog.header.find('.indicator').removeClass('hidden').toggleClass('blink', blink).addClass(color);
	}

	set_call_status(call_status) {
		let title = '';
		call_status = call_status || this.call_log.call_status;
		if (['busy', 'completed'].includes(call_status) || !call_status) {
			title = __('Incoming call from {0}',
				[this.contact ? `${this.contact.first_name} ${this.contact.last_name}` : this.caller_number]);
			this.set_indicator('blue', true);
		} else if (call_status === 'in-progress') {
			title = __('Call Connected');
			this.set_indicator('yellow');
		} else if (call_status === 'missed') {
			this.set_indicator('red');
			title = __('Call Missed');
		} else if (call_status === 'disconnected') {
			this.set_indicator('red');
			title = __('Call Disconnected');
		} else {
			this.set_indicator('blue');
			title = call_status;
		}
		this.dialog.set_title(title);
	}

	update(data) {
		this.call_log = data.call_log;
		this.set_call_status();
	}

	setup_call_status_updater() {
		this.updater = setInterval(this.get_call_status.bind(this), 20000);
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

	disconnect_call() {
		this.set_call_status('disconnected');
		clearInterval(this.updater);
	}

	make_last_interaction_section() {
		frappe.xcall('erpnext.crm.doctype.utils.get_last_interaction', {
			'number': this.caller_number,
			'reference_doc': this.contact
		}).then(data => {
			if (data.last_communication) {
				const comm = data.last_communication;
				// this.dialog.set_df_property('last_interaction', 'hidden', false);
				const comm_field = this.dialog.fields_dict["last_communication"];
				comm_field.set_value(comm.content);
				comm_field.$wrapper.append(frappe.utils.get_form_link('Communication', comm.name));
			}

			if (data.last_issue) {
				const issue = data.last_issue;
				// this.dialog.set_df_property('last_interaction', 'hidden', false);
				const issue_field = this.dialog.fields_dict["last_issue"];
				issue_field.set_value(issue.subject);
				issue_field.$wrapper
					.append(`<a class="text-medium" href="#List/Issue/List?customer=${issue.customer}">View all issues from ${issue.customer}</a>`);
			}
		});
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

	frappe.realtime.on('call_disconnected', () => {
		if (erpnext.call_popup) {
			erpnext.call_popup.disconnect_call();
		}
	});
});
