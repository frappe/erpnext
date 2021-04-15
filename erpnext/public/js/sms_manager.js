// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

erpnext.SMSManager = function SMSManager(doc, options) {
	var me = this;

	if (!options) {
		options = {};
	}

	this.setup = function() {
		if (in_list(['Sales Order', 'Delivery Note', 'Sales Invoice'], doc.doctype)) {
			this.show({
				contact: doc.contact_person,
				mobile_no: doc.contact_mobile,
				party_doctype: 'Customer',
				party_name: doc.customer
			});
		} else if (doc.doctype == 'Quotation') {
			this.show({
				contact: doc.contact_person,
				mobile_no: doc.contact_mobile,
				party_doctype: doc.quotation_to,
				party_name: doc.party_name
			});
		} else if (in_list(['Purchase Order', 'Purchase Receipt'], doc.doctype)) {
			this.show({
				contact: doc.contact_person,
				mobile_no: doc.contact_mobile,
				party_doctype: 'Supplier',
				party_name: doc.supplier
			});
		} else if (doc.doctype == 'Lead') {
			this.show({
				mobile_no: doc.mobile_no
			});
		} else if (doc.doctype == 'Opportunity') {
			this.show({
				contact: doc.contact_no
			});
		} else if (doc.doctype == 'Material Request') {
			this.show({});
		} else if (doc.doctype == 'Vehicle Booking Order') {
			this.show({
				mobile_no: doc.contact_mobile,
				party_doctype: 'Customer',
				party_name: doc.customer
			});
		}
	};

	this.show = function(args) {
		if (!args) {
			args = {};
		}

		me.message = options.message || args.message;
		me.type = options.type || args.type;
		me.contact = options.contact || args.contact;
		me.mobile_no = options.mobile_no || args.mobile_no;
		me.party_doctype = options.party_doctype || args.party_doctype;
		me.party_name = options.party_name || args.party_name;
		me.reference_doctype = options.reference_doctype || doc.doctype;
		me.reference_name = options.reference_name || doc.name;

		this.get_sms_defaults();
	};

	this.get_sms_defaults = function() {
		frappe.call({
			method: "erpnext.setup.doctype.sms_template.sms_template.get_sms_defaults",
			args: {
				dt: doc.doctype,
				dn: doc.name,
				type: me.type,
				contact: me.contact,
				mobile_no: me.mobile_no,
				party_doctype: me.party_doctype,
				party_name: me.party_name
			},
			callback: function(r) {
				if(!r.exc) {
					me.mobile_no = r.message.mobile_no || me.mobile_no;
					me.message = r.message.message || me.message;
					me.show_dialog();
				}
			}
		});
	};

	this.show_dialog = function() {
		if(!me.dialog)
			me.make_dialog();
		me.dialog.set_values({
			'message': me.message,
			'mobile_no': me.mobile_no
		})
		me.dialog.show();
	}

	this.make_dialog = function() {
		var d = new frappe.ui.Dialog({
			title: __('Send {0} SMS', [me.type || '']),
			width: 400,
			fields: [
				{fieldname:'mobile_no', fieldtype:'Data', label:'Mobile Number', reqd: 1},
				{fieldname:'message', fieldtype:'Text', label:'Message', reqd: 1},
				{fieldname:'send', fieldtype:'Button', label:'Send'}
			]
		});

		d.fields_dict.send.input.onclick = function() {
			var btn = d.fields_dict.send.input;
			var v = me.dialog.get_values();
			if(v) {
				$(btn).set_working();
				frappe.call({
					method: "frappe.core.doctype.sms_settings.sms_settings.send_sms",
					args: {
						receiver_list: [v.mobile_no],
						msg: v.message,
						type: me.type,
						reference_doctype: me.reference_doctype,
						reference_name: me.reference_name,
						party_doctype: me.party_doctype,
						party_name: me.party_name
					},
					callback: function(r) {
						$(btn).done_working();
						if(!r.exc) {
							me.dialog.hide();
						}
					}
				});
			}
		};
		
		$(d.fields_dict.send.input).addClass('btn-primary');

		me.dialog = d;
	}

	this.setup();
}
