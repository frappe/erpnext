frappe.provide('frappe.ui.form');

frappe.ui.form.ContactQuickEntryForm = class ContactQuickEntryForm extends frappe.ui.form._ContactQuickEntryForm {
	init(doctype, after_insert) {
		super.init(doctype, after_insert);
	}

	render_dialog() {
		var me = this;
		super.render_dialog();

		if (me.dialog.fields_dict["tax_cnic"]) {
			me.dialog.fields_dict["tax_cnic"].df.onchange = () => {
				var value = me.dialog.get_value('tax_cnic');
				value = erpnext.utils.get_formatted_cnic(value);
				me.dialog.doc.tax_cnic = value;
				me.dialog.get_field('tax_cnic').refresh();
			};
		}

		me.dialog.fields_dict["mobile_no"].df.onchange = () => {
			var value = me.dialog.get_value('mobile_no');
			value = erpnext.utils.get_formatted_mobile_pakistan(value);
			me.dialog.doc.mobile_no = value;
			me.dialog.get_field('mobile_no').refresh();
		};

		me.dialog.fields_dict["mobile_no_2"].df.onchange = () => {
			var value = me.dialog.get_value('mobile_no_2');
			value = erpnext.utils.get_formatted_mobile_pakistan(value);
			me.dialog.doc.mobile_no_2 = value;
			me.dialog.get_field('mobile_no_2').refresh();
		};
	}
};
