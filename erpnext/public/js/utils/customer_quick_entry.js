frappe.provide('frappe.ui.form');

frappe.ui.form.CustomerQuickEntryForm = frappe.ui.form.QuickEntryForm.extend({
	init: function(doctype, after_insert) {
		this.skip_redirect_on_error = true;
		this._super(doctype, after_insert);
	},

	render_dialog: function() {
		this.mandatory = this.mandatory.concat(this.get_variant_fields());
		this._super();
		this.init_post_render_dialog_operations();
	},

	init_post_render_dialog_operations: function () {
		var me = this;

		me.dialog.fields_dict["tax_id"].df.onchange = () => {
			var value = me.dialog.get_value('tax_id');
			value = erpnext.utils.get_formatted_ntn(value);
			me.dialog.doc.tax_id = value;
			me.dialog.get_field('tax_id').refresh();
			erpnext.utils.validate_duplicate_tax_id(me.dialog.doc, "tax_id");
		};

		me.dialog.fields_dict["tax_cnic"].df.onchange = () => {
			var value = me.dialog.get_value('tax_cnic');
			value = erpnext.utils.get_formatted_cnic(value);
			me.dialog.doc.tax_cnic = value;
			me.dialog.get_field('tax_cnic').refresh();
			erpnext.utils.validate_duplicate_tax_id(me.dialog.doc, "tax_cnic");
		};

		me.dialog.fields_dict["tax_strn"].df.onchange = () => {
			var value = me.dialog.get_value('tax_strn');
			value = erpnext.utils.get_formatted_strn(value);
			me.dialog.doc.tax_strn = value;
			me.dialog.get_field('tax_strn').refresh();
			erpnext.utils.validate_duplicate_tax_id(me.dialog.doc, "tax_strn");
		};

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
	},

	get_variant_fields: function() {
		var variant_fields = [{
			fieldtype: "Section Break",
			label: __("Identification & Tax Id"),
		},
		{
			label: __("Tax Id"),
			fieldname: "tax_id",
			fieldtype: "Data"
		},
		{
			fieldtype: "Column Break"
		},
		{
			label: __("CNIC"),
			fieldname: "tax_cnic",
			fieldtype: "Data"
		},
		{
			fieldtype: "Column Break"
		},
		{
			label: __("STRN"),
			fieldname: "tax_strn",
			fieldtype: "Data"
		},
		{
			fieldtype: "Column Break"
		},
		{
			label: __("Income Tax Status"),
			fieldname: "tax_status",
			fieldtype: "Select"
		},
		{
			fieldtype: "Section Break",
			label: __("Primary Contact Details"),
		},
		{
			label: __("Email Id"),
			fieldname: "email_id",
			fieldtype: "Data"
		},
		{
			fieldtype: "Column Break"
		},
		{
			label: __("Mobile Number (Primary)"),
			fieldname: "mobile_no",
			fieldtype: "Data"
		},
		{
			fieldtype: "Column Break"
		},
		{
			label: __("Mobile Number (Secondary"),
			fieldname: "mobile_no_2",
			fieldtype: "Data"
		},
		{
			fieldtype: "Column Break"
		},
		{
			label: __("Phone Number"),
			fieldname: "phone_no",
			fieldtype: "Data"
		},
		{
			fieldtype: "Section Break",
			label: __("Primary Address Details"),
		},
		{
			label: __("Address Line 1"),
			fieldname: "address_line1",
			fieldtype: "Data"
		},
		{
			label: __("Address Line 2"),
			fieldname: "address_line2",
			fieldtype: "Data"
		},
		{
			label: __("ZIP Code"),
			fieldname: "pincode",
			fieldtype: "Data"
		},
		{
			fieldtype: "Column Break"
		},
		{
			label: __("City"),
			fieldname: "city",
			fieldtype: "Data"
		},
		{
			label: __("State"),
			fieldname: "state",
			fieldtype: "Data"
		},
		{
			label: __("Country"),
			fieldname: "country",
			fieldtype: "Link",
			options: "Country"
		},
		{
			label: __("Customer POS Id"),
			fieldname: "customer_pos_id",
			fieldtype: "Data",
			hidden: 1
		}];

		return variant_fields;
	},
})