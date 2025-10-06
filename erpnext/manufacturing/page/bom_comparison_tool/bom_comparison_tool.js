frappe.pages["bom-comparison-tool"].on_page_load = function (wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("BOM Comparison Tool"),
		single_column: true,
	});

	new erpnext.BOMComparisonTool(page);
};

erpnext.BOMComparisonTool = class BOMComparisonTool {
	constructor(page) {
		this.page = page;
		this.make_form();
	}

	make_form() {
		this.form = new frappe.ui.FieldGroup({
			fields: [
				{
					label: __("BOM 1"),
					fieldname: "name1",
					fieldtype: "Link",
					options: "BOM",
					change: () => this.fetch_and_render(),
					get_query: () => {
						return {
							filters: {
								name: ["not in", [this.form.get_value("name2") || ""]],
							},
						};
					},
				},
				{
					fieldtype: "Column Break",
				},
				{
					label: __("BOM 2"),
					fieldname: "name2",
					fieldtype: "Link",
					options: "BOM",
					change: () => this.fetch_and_render(),
					get_query: () => {
						return {
							filters: {
								name: ["not in", [this.form.get_value("name1") || ""]],
							},
						};
					},
				},
				{
					fieldtype: "Section Break",
				},
				{
					fieldtype: "HTML",
					fieldname: "preview",
				},
			],
			body: this.page.body,
		});
		this.form.make();
	}

	fetch_and_render() {
		let { name1, name2 } = this.form.get_values();
		if (!(name1 && name2)) {
			this.form.get_field("preview").html("");
			return;
		}

		// set working state
		this.form.get_field("preview").html(`
			<div class="text-muted margin-top">
				${__("Fetching...")}
			</div>
		`);

		frappe
			.call("erpnext.manufacturing.doctype.bom.bom.get_bom_diff", {
				bom1: name1,
				bom2: name2,
			})
			.then((r) => {
				let diff = r.message;
				frappe.model.with_doctype("BOM", () => {
					this.render("BOM", name1, name2, diff);
				});
			});
	}

	render(doctype, name1, name2, diff) {
		let change_html = (title, doctype, changed) => {
			let values_changed = this.get_changed_values(doctype, changed)
				.map((change) => {
					let [fieldname, value1, value2] = change;
					return `
						<tr>
							<td>${frappe.meta.get_label(doctype, fieldname)}</td>
							<td>${value1}</td>
							<td>${value2}</td>
						</tr>
					`;
				})
				.join("");

			return `
				<h4 class="margin-top">${title}</h4>
				<div>
					<table class="table table-bordered">
						<tr>
							<th width="33%">${__("Field")}</th>
							<th width="33%">${name1}</th>
							<th width="33%">${name2}</th>
						</tr>
						${values_changed}
					</table>
				</div>
			`;
		};

		let value_changes = change_html(__("Values Changed"), doctype, diff.changed);

		let row_changes_by_fieldname = group_items(diff.row_changed, (change) => change[0]);

		let table_changes = Object.keys(row_changes_by_fieldname)
			.map((fieldname) => {
				let changes = row_changes_by_fieldname[fieldname];
				let df = frappe.meta.get_docfield(doctype, fieldname);

				let html = changes
					.map((change) => {
						let [fieldname, , item_code, changes] = change;
						let df = frappe.meta.get_docfield(doctype, fieldname);
						let child_doctype = df.options;
						let values_changed = this.get_changed_values(child_doctype, changes);

						return values_changed
							.map((change, i) => {
								let [fieldname, value1, value2] = change;
								let th =
									i === 0 ? `<th rowspan="${values_changed.length}">${item_code}</th>` : "";
								return `
						<tr>
							${th}
							<td>${frappe.meta.get_label(child_doctype, fieldname)}</td>
							<td>${value1}</td>
							<td>${value2}</td>
						</tr>
					`;
							})
							.join("");
					})
					.join("");

				return `
				<h4 class="margin-top">${__("Changes in {0}", [df.label])}</h4>
				<table class="table table-bordered">
					<tr>
						<th width="25%">${__("Item Code")}</th>
						<th width="25%">${__("Field")}</th>
						<th width="25%">${name1}</th>
						<th width="25%">${name2}</th>
					</tr>
					${html}
				</table>
			`;
			})
			.join("");

		let get_added_removed_html = (title, grouped_items) => {
			return Object.keys(grouped_items)
				.map((fieldname) => {
					let rows = grouped_items[fieldname];
					let df = frappe.meta.get_docfield(doctype, fieldname);
					let fields = frappe.meta.get_docfields(df.options).filter((df) => df.in_list_view);

					let html = rows
						.map((row) => {
							let [, doc] = row;
							let cells = fields.map((df) => `<td>${doc[df.fieldname]}</td>`).join("");
							return `<tr>${cells}</tr>`;
						})
						.join("");

					let header = fields.map((df) => `<th>${df.label}</th>`).join("");
					return `
					<h4 class="margin-top">${$.format(title, [df.label])}</h4>
					<table class="table table-bordered">
						<tr>${header}</tr>
						${html}
					</table>
				`;
				})
				.join("");
		};

		let added_by_fieldname = group_items(diff.added, (change) => change[0]);
		let removed_by_fieldname = group_items(diff.removed, (change) => change[0]);

		let added_html = get_added_removed_html(__("Rows Added in {0}"), added_by_fieldname);
		let removed_html = get_added_removed_html(__("Rows Removed in {0}"), removed_by_fieldname);

		let html = `
			${value_changes}
			${table_changes}
			${added_html}
			${removed_html}
		`;

		this.form.get_field("preview").html(html);
	}

	get_changed_values(doctype, changed) {
		return changed.filter((change) => {
			let [fieldname, value1, value2] = change;
			if (!value1) value1 = "";
			if (!value2) value2 = "";
			if (value1 === value2) return false;
			let df = frappe.meta.get_docfield(doctype, fieldname);
			if (!df) return false;
			if (df.hidden) return false;
			return true;
		});
	}
};

function group_items(array, fn) {
	return array.reduce((acc, item) => {
		let key = fn(item);
		acc[key] = acc[key] || [];
		acc[key].push(item);
		return acc;
	}, {});
}
