frappe.provide('frappe.ui.form');

frappe.ui.form.ItemQuickEntryForm = frappe.ui.form.QuickEntryForm.extend({
	init: function(doctype, after_insert) {
		this._super(doctype, after_insert);
	},

	render_dialog: function() {
		this.mandatory = this.get_variant_fields().concat(this.mandatory);
		this.mandatory.splice(5, 0, {
			fieldname: 'col_break1',
			fieldtype: 'Column Break'
		});
		this.mandatory = this.mandatory.concat(this.get_attributes_fields());
		this._super();
		this.init_post_render_dialog_operations();
	},

	init_post_render_dialog_operations: function() {
		this.dialog.fields_dict.attribute_html.$wrapper.append(frappe.render_template("item_quick_entry"));
		this.init_for_create_variant_trigger();
		this.init_for_item_template_trigger();
		this.init_for_next_trigger();
		this.init_for_prev_trigger();
		this.init_for_view_attributes();
		// explicitly hide manufacturing fields as hidden not working.
		this.toggle_manufacturer_fields();
		this.dialog.get_field("item_template").df.hidden = 1;
		this.dialog.get_field("item_template").refresh();
	},

	register_primary_action: function() {
		var me = this;
		this.dialog.set_primary_action(__('Save'), function() {
			if (me.dialog.working) return;
			var data = me.dialog.get_values();
			var variant_values = {};

			if (me.dialog.fields_dict.create_variant.$input.prop("checked")) {
				variant_values = me.get_variant_doc();
				if (!Object.keys(variant_values).length) {
					data = null;
				}
			}

			if (data) {
				me.dialog.working = true;
				var values = me.update_doc();
				//patch for manufacturer type variants as extend is overwriting it.
				if (variant_values['variant_based_on'] == "Manufacturer") {
					values['variant_based_on'] = "Manufacturer";
				}
				$.extend(variant_values, values);
				me.insert(variant_values);
			}
		});
	},

	insert: function(variant_values) {
		let me = this;
		return new Promise(resolve => {
			frappe.call({
				method: "frappe.client.insert",
				args: {
					doc: variant_values
				},
				callback: function(r) {
					me.dialog.hide();
					// delete the old doc
					frappe.model.clear_doc(me.dialog.doc.doctype, me.dialog.doc.name);
					me.dialog.doc = r.message;
					if (frappe._from_link) {
						frappe.ui.form.update_calling_link(me.dialog.doc);
					} else {
						if (me.after_insert) {
							me.after_insert(me.dialog.doc);
						} else {
							me.open_from_if_not_list();
						}
					}
				},
				error: function() {
					me.open_doc();
				},
				always: function() {
					me.dialog.working = false;
					resolve(me.dialog.doc);
				},
				freeze: true
			});
		});
	},

	open_doc: function() {
		this.dialog.hide();
		this.update_doc();
		if (this.dialog.fields_dict.create_variant.$input.prop("checked")) {
			var template = this.dialog.fields_dict.item_template.input.value;
			if (template)
				frappe.set_route("Form", this.doctype, template);
		} else {
			frappe.set_route('Form', this.doctype, this.doc.name);
		}
	},

	get_variant_fields: function() {
		var variant_fields = [{
			fieldname: "create_variant",
			fieldtype: "Check",
			label: __("Create Variant")
		}, {
			fieldname: 'item_template',
			label: __('Item Template'),
			reqd: 0,
			fieldtype: 'Link',
			options: "Item",
			get_query: function() {
				return {
					filters: {
						"has_variants": 1
					}
				};
			}
		}];

		return variant_fields;
	},

	get_manufacturing_fields: function() {
		this.manufacturer_fields = [{
			fieldtype: 'Link',
			options: 'Manufacturer',
			label: 'Manufacturer',
			fieldname: "manufacturer",
			hidden: 1,
			reqd: 0
		}, {
			fieldtype: 'Data',
			label: 'Manufacturer Part Number',
			fieldname: 'manufacturer_part_no',
			hidden: 1,
			reqd: 0
		}];
		return this.manufacturer_fields;
	},

	get_attributes_fields: function() {
		var attribute_fields = [{
			fieldname: 'sec_br',
			fieldtype: 'Section Break'
		}, {
			fieldname: 'attribute_html',
			fieldtype: 'HTML'
		}]

		attribute_fields = attribute_fields.concat(this.get_manufacturing_fields());
		return attribute_fields;
	},

	init_for_create_variant_trigger: function() {
		var me = this;

		this.dialog.fields_dict.create_variant.$input.on("click", function() {
			var checked = $(this).prop("checked");
			me.dialog.get_field("item_template").df.reqd = checked;
			me.dialog.get_field("item_code").df.reqd = !checked;
			me.dialog.set_value("item_template", "");
			me.dialog.get_field("item_template").df.hidden = !checked;
			me.dialog.get_field("item_template").refresh();
			me.dialog.get_field("item_code").refresh();
			me.init_post_template_trigger_operations(false, [], true);
		});
	},

	init_for_item_template_trigger: function() {
		var me = this;

		me.dialog.fields_dict["item_template"].df.onchange = () => {
			var template = me.dialog.fields_dict.item_template.input.value;
			if (template) {
				frappe.call({
					method: "frappe.client.get",
					args: {
						doctype: "Item",
						name: template
					},
					callback: function(r) {
						var templ_doc = r.message;
						me.is_manufacturer = false;

						if (templ_doc.variant_based_on === "Manufacturer") {
							me.init_post_template_trigger_operations(true, [], true);
						} else {

							me.init_post_template_trigger_operations(false, templ_doc.attributes, false);
							me.show_attributes(templ_doc.attributes);
						}
					}
				});
			} else {
				me.init_post_template_trigger_operations(false, [], true);
			}
		}
	},

	init_post_template_trigger_operations: function(is_manufacturer, attributes, attributes_flag) {
		this.dialog.fields_dict.attribute_html.$wrapper.find(".attributes").empty();
		this.is_manufacturer = is_manufacturer;
		this.toggle_manufacturer_fields();
		this.set_pagination_details(attributes);
		this.dialog.fields_dict.attribute_html.$wrapper.find(".attributes").toggleClass("hide-control", attributes_flag);
		this.dialog.fields_dict.attribute_html.$wrapper.find(".attributes-header").toggleClass("hide-control", attributes_flag);
	},

	toggle_manufacturer_fields: function() {
		var me = this;
		$.each(this.manufacturer_fields, function(i, dialog_field) {
			me.dialog.get_field(dialog_field.fieldname).df.hidden = !me.is_manufacturer;
			me.dialog.get_field(dialog_field.fieldname).df.reqd = dialog_field.fieldname == 'manufacturer' ? me.is_manufacturer : false;
			me.dialog.get_field(dialog_field.fieldname).refresh();
		});
	},

	show_attributes: function(attributes) {
		this.render_attributes(attributes.slice(0, 3));
		$(this.dialog.fields_dict.attribute_html.wrapper).find(".page-count").text(this.page_count);
	},

	set_pagination_details: function(attributes) {
		this.attributes = attributes;
		this.attribute_values = {};
		this.attributes_count = attributes.length;
		this.current_page = 1;
		this.page_count = Math.ceil(this.attributes_count / 3);
	},

	init_for_next_trigger: function() {
		var me = this;
		$(this.dialog.fields_dict.attribute_html.wrapper).find(".btn-next").click(function() {
			if (me.current_page < me.page_count) {
				me.current_page += 1;
				me.initiate_render_attributes();
			} else {
				frappe.show_alert(__("Maximum page size reached."), 2);
			}
		});
	},

	init_for_prev_trigger: function() {
		var me = this;
		$(this.dialog.fields_dict.attribute_html.wrapper).find(".btn-prev").click(function() {
			if (me.current_page > 1) {
				me.current_page -= 1;
				me.initiate_render_attributes();
			} else {
				frappe.show_alert(__("Minimum page size reached."), 2);
			}
		})
	},

	initiate_render_attributes: function() {
		var end_index = this.current_page * 3;
		var start_index = end_index - 3;
		this.dialog.fields_dict.attribute_html.$wrapper.find(".attributes").empty();
		this.render_attributes(this.attributes.slice(start_index, end_index));
	},

	init_for_view_attributes: function() {
		var me = this;
		$(this.dialog.fields_dict.attribute_html.wrapper).find(".view-attributes").click(function() {
			var html = frappe.render_template("variant_attribute", {
				"attributes": me.attributes,
				"attribute_values": me.attribute_values
			});
			frappe.msgprint(html);
		})
	},

	render_attributes: function(attributes) {
		var me = this;
		this.dialog.fields_dict.attribute_html.$wrapper.find(".cur-page").text(this.current_page);

		$.each(attributes, function(index, row) {
			var desc = "";
			var fieldtype = "Data";
			if (row.numeric_values) {
				fieldtype = "Float";
				desc = "Min Value: " + row.from_range + " , Max Value: " + row.to_range + ", in Increments of: " + row.increment;
			}

			me.init_make_control(fieldtype, row);
			me[row.attribute].set_value(me.attribute_values[row.attribute] || "");
			me[row.attribute].$wrapper.toggleClass("has-error", me.attribute_values[row.attribute] ? false : true);

			// Set Label explicitly as make_control is not displaying label
			$(me[row.attribute].label_area).text(__(row.attribute));
			$(repl(`<p class="help-box small text-muted hidden-xs">%(desc)s</p>`, {
				"desc": desc
			}))
			.insertAfter(me[row.attribute].input_area);

			if (!row.numeric_values) {
				me.init_awesomplete_for_attribute(row);
			} else {
				me[row.attribute].$input.on("change", function() {
					me.attribute_values[row.attribute] = $(this).val();
					$(this).closest(".frappe-control").toggleClass("has-error", $(this).val() ? false : true);
				});
			}
		})
	},

	init_make_control: function(fieldtype, row) {
		this[row.attribute] = frappe.ui.form.make_control({
			df: {
				"fieldtype": fieldtype,
				"label": row.attribute,
				"fieldname": row.attribute,
				"options": row.options || ""
			},
			parent: $(this.dialog.fields_dict.attribute_html.wrapper).find(".attributes"),
			only_input: false
		});
		this[row.attribute].make_input();
	},

	init_awesomplete_for_attribute: function(row) {
		var me = this;

		this[row.attribute].input.awesomplete = new Awesomplete(this[row.attribute].input, {
			minChars: 0,
			maxItems: 99,
			autoFirst: true,
			list: [],
		});

		this[row.attribute].$input.on('input', function(e) {
			frappe.call({
				method: "frappe.client.get_list",
				args: {
					doctype: "Item Attribute Value",
					filters: [
						["parent", "=", $(e.target).attr("data-fieldname")],
						["attribute_value", "like", e.target.value + "%"]
					],
					fields: ["attribute_value"]
				},
				callback: function(r) {
					if (r.message) {
						e.target.awesomplete.list = r.message.map(function(d) {
							return d.attribute_value;
						});
					}
				}
			});
		})
		.on('focus', function(e) {
			$(e.target).val('').trigger('input');
		})
		.on("awesomplete-select", function (e) {
			me.attribute_values[$(e.target).attr("data-fieldname")] = e.target.value;
			$(e.target).closest(".frappe-control").toggleClass("has-error", e.target.value ? false : true);
		})
	},

	get_variant_doc: function() {
		var me = this;
		var variant_doc = {};
		var attribute = this.validate_mandatory_attributes();

		if (Object.keys(attribute).length) {
			frappe.call({
				method: "erpnext.controllers.item_variant.create_variant_doc_for_quick_entry",
				args: {
					"template": me.dialog.fields_dict.item_template.$input.val(),
					args: attribute
				},
				async: false,
				callback: function(r) {
					if (Object.prototype.toString.call(r.message) == "[object Object]") {
						variant_doc = r.message;
					} else {
						var msgprint_dialog = frappe.msgprint(__("Item Variant {0} already exists with same attributes", [repl('<a class="strong variant-click" data-item-code="%(item)s" \
								>%(item)s</a>', {
								item: r.message
							})]));

						msgprint_dialog.$wrapper.find(".variant-click").on("click", function() {
							msgprint_dialog.hide();
							me.dialog.hide();
							if (frappe._from_link) {
								frappe._from_link.set_value($(this).attr("data-item-code"));
							} else {
								frappe.set_route('Form', "Item", $(this).attr("data-item-code"));
							}
						});
					}
				}
			})
		}
		return variant_doc;
	},

	validate_mandatory_attributes: function() {
		var me = this;
		var attribute = {};
		var mandatory = [];

		$.each(this.attributes, function(index, attr) {
			var value = me.attribute_values[attr.attribute] || "";
			if (value) {
				attribute[attr.attribute] = attr.numeric_values ? flt(value) : value;
			} else {
				mandatory.push(attr.attribute);
			}
		})

		if (mandatory.length) {
			frappe.msgprint({
				title: __('Missing Values Required'),
				message: __('Following fields have missing values:') + '<br><br><ul><li>' + mandatory.join('<li>') + '</ul>',
				indicator: 'orange'
			});
			return {};
		}

		if (this.is_manufacturer) {
			$.each(this.manufacturer_fields, function(index, field) {
				attribute[field.fieldname] = me.dialog.fields_dict[field.fieldname].input.value;
			});
		}
		return attribute;
	}
});