frappe.provide('frappe.phone_call');

class CallHandler {
	constructor(to_number, frm) {
		this.to_number = to_number;
		this.make();
	}
	make() {
		this.dialog = new frappe.ui.Dialog({
			'title': __('Make a Call'),
			'minimizable': true,
			'fields': [{
				'fieldname': 'from_number',
				'label': 'From Number',
				'fieldtype': 'Data',
				'read_only': 0
			}, {
				'fieldname': 'to_number',
				'label': 'To Number',
				'default': this.to_number,
				'fieldtype': 'Data',
				'read_only': 0
			}, {
				'fieldname': 'caller_id',
				'label': 'Caller ID',
				'fieldtype': 'Select',
				'reqd': 1
			}, {
				'fieldname': 'status',
				'label': 'Status',
				'fieldtype': 'Data',
				'read_only': 1
			}, {
				'fieldtype': 'Button',
				'label': __('Call'),
				'primary': 1,
				'click': () => {
					frappe.xcall('erpnext.erpnext_integrations.exotel_integration.make_a_call', {
						'from_number': this.dialog.get_value('from_number'),
						'to_number': this.dialog.get_value('to_number'),
					}).then(res => {
						this.dialog.set_value('response', JSON.stringify(res));
						this.call_id = res.Call.Sid;
						this.setup_call_status_updater();
					}).catch(e => {
						this.dialog.set_value('response', JSON.stringify(e));
					});
				}
			}, {
				'label': 'Response',
				'fieldtype': 'Section Break',
				'collapsible': 1
			}, {
				'fieldname': 'response',
				'label': 'Response',
				'fieldtype': 'Code',
				'read_only': 1
			}]
		});
		frappe.xcall('erpnext.erpnext_integrations.exotel_integration.get_all_exophones').then(numbers => {
			this.dialog.set_df_property('caller_id', 'options', numbers);
			this.dialog.set_value('caller_id', numbers[0]);
			this.dialog.show();
		});
	}
	setup_call_status_updater() {
		if (!this.updater) {
			this.updater = setInterval(this.set_call_status.bind(this), 1000);
		}
	}
	set_call_status() {
		frappe.xcall('erpnext.erpnext_integrations.exotel_integration.get_call_status', {
			'call_id': this.call_id
		}).then(status => {
			this.dialog.set_value('status', status);
			this.set_indicator(status);
			if (['completed', 'failed', 'busy', 'no-answer'].includes(status)) {
				clearInterval(this.updater);
			}
		}).catch(() => {
			clearInterval(this.updater);
		});
	}

	set_indicator(status) {
		const indicator_class = this.get_status_indicator(status);
		this.dialog.header.find('.indicator').attr('class', `indicator ${indicator_class}`);
	}

	get_status_indicator(status) {
		const indicator_map = {
			'completed': 'red',
			'failed': 'red',
			'busy': 'yellow',
			'no-answer': 'yellow',
			'queued': 'yellow',
			'ringing': 'blue blink',
			'in-progress': 'blue blink'
		};

		const indicator_class = `indicator ${indicator_map[status] || 'blue blink'}`;
		return indicator_class;
	}

}

frappe.phone_call.handler = (to_number, frm) => new CallHandler(to_number, frm);