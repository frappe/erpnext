frappe.ui.form.on('Chart of Accounts Importer', {
	onload: function (frm) {
		frm.set_value("company", "");
		frm.set_value("import_file", "");
	},
	refresh: function (frm) {
		// disable default save
		frm.disable_save();

		// make company mandatory
		frm.set_df_property('company', 'reqd', frm.doc.company ? 0 : 1);
		frm.set_df_property('import_file_section', 'hidden', frm.doc.company ? 0 : 1);

		if (frm.doc.import_file) {
			frappe.run_serially([
				() => generate_tree_preview(frm),
				() => create_import_button(frm),
				() => frm.set_df_property('chart_preview', 'hidden', 0)
			]);
		}

		frm.set_df_property('chart_preview', 'hidden',
			$(frm.fields_dict['chart_tree'].wrapper).html()!="" ? 0 : 1);
	},

	download_template: function(frm) {
		var d = new frappe.ui.Dialog({
			title: __("Download Template"),
			fields: [
				{
					label : "File Type",
					fieldname: "file_type",
					fieldtype: "Select",
					reqd: 1,
					options: ["Excel", "CSV"]
				},
				{
					label: "Template Type",
					fieldname: "template_type",
					fieldtype: "Select",
					reqd: 1,
					options: ["Sample Template", "Blank Template"],
					change: () => {
						let template_type = d.get_value('template_type');

						if (template_type === "Sample Template") {
							d.set_df_property('template_type', 'description',
								`The Sample Template contains all the required accounts pre filled in the  template.
								You can add more accounts or change existing accounts in the template as per your choice.`);
						} else {
							d.set_df_property('template_type', 'description',
								`The Blank Template contains just the account type and root type required to build the Chart
								of Accounts. Please enter the account names and add more rows as per your requirement.`);
						}
					}
				}
			],
			primary_action: function() {
				var data = d.get_values();

				if (!data.template_type) {
					frappe.throw(__('Please select <b>Template Type</b> to download template'));
				}

				open_url_post(
					'/api/method/erpnext.accounts.doctype.chart_of_accounts_importer.chart_of_accounts_importer.download_template',
					{
						file_type: data.file_type,
						template_type: data.template_type
					}
				);

				d.hide();
			},
			primary_action_label: __('Download')
		});
		d.show();
	},

	import_file: function (frm) {
		if (!frm.doc.import_file) {
			frm.page.set_indicator("");
			$(frm.fields_dict['chart_tree'].wrapper).empty(); // empty wrapper on removing file
		}
	},

	company: function (frm) {
		if (frm.doc.company) {
			// validate that no Gl Entry record for the company exists.
			frappe.call({
				method: "erpnext.accounts.doctype.chart_of_accounts_importer.chart_of_accounts_importer.validate_company",
				args: {
					company: frm.doc.company
				},
				callback: function(r) {
					if(r.message===false) {
						frm.set_value("company", "");
						frappe.throw(__("Transactions against the Company already exist! Chart of Accounts can only be imported for a Company with no transactions."));
					} else {
						frm.trigger("refresh");
					}
				}
			});
		}
	}
});

var create_import_button = function(frm) {
	frm.page.set_primary_action(__("Import"), function () {
		return frappe.call({
			method: "erpnext.accounts.doctype.chart_of_accounts_importer.chart_of_accounts_importer.import_coa",
			args: {
				file_name: frm.doc.import_file,
				company: frm.doc.company
			},
			freeze: true,
			freeze_message: __("Creating Accounts..."),
			callback: function(r) {
				if (!r.exc) {
					clearInterval(frm.page["interval"]);
					frm.page.set_indicator(__('Import Successful'), 'blue');
					create_reset_button(frm);
				}
			}
		});
	}).addClass('btn btn-primary');
};

var create_reset_button = function(frm) {
	frm.page.set_primary_action(__("Reset"), function () {
		frm.page.clear_primary_action();
		delete frm.page["show_import_button"];
		frm.reload_doc();
	}).addClass('btn btn-primary');
};

var validate_coa = function(frm) {
	if (frm.doc.import_file) {
		let parent = __('All Accounts');
		return frappe.call({
			'method': 'erpnext.accounts.doctype.chart_of_accounts_importer.chart_of_accounts_importer.get_coa',
			'args': {
				file_name: frm.doc.import_file,
				parent: parent,
				doctype: 'Chart of Accounts Importer',
				file_type: frm.doc.file_type,
				for_validate: 1
			},
			callback: function(r) {
				if (r.message['show_import_button']) {
					frm.page['show_import_button'] = Boolean(r.message['show_import_button']);
				}
			}
		});
	}
};

var generate_tree_preview = function(frm) {
	let parent = __('All Accounts');
	$(frm.fields_dict['chart_tree'].wrapper).empty(); // empty wrapper to load new data

	// generate tree structure based on the csv data
	return new frappe.ui.Tree({
		parent: $(frm.fields_dict['chart_tree'].wrapper),
		label: parent,
		expandable: true,
		method: 'erpnext.accounts.doctype.chart_of_accounts_importer.chart_of_accounts_importer.get_coa',
		args: {
			file_name: frm.doc.import_file,
			parent: parent,
			doctype: 'Chart of Accounts Importer',
			file_type: frm.doc.file_type
		},
		onclick: function(node) {
			parent = node.value;
		}
	});
};
