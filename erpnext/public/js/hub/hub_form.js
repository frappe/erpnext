frappe.provide('erpnext.hub');

erpnext.hub.HubDetailsPage = class HubDetailsPage extends frappe.views.BaseList {
	setup_defaults() {
		super.setup_defaults();
		this.method = 'erpnext.hub_node.get_details';
		const route = frappe.get_route();
		// this.page_name = route[2];
	}

	setup_fields() {
		return this.get_meta()
			.then(r => {
				this.meta = r.message.meta || this.meta;
				this.categories = r.message.categories || [];
				this.bootstrap_data(r.message);

				this.getFormFields();
			});
	}

	bootstrap_data() { }

	get_meta() {
		return new Promise(resolve =>
			frappe.call('erpnext.hub_node.get_meta', {doctype: 'Hub ' + this.doctype}, resolve));
	}


	set_breadcrumbs() {
		frappe.breadcrumbs.add({
			label: __('Hub'),
			route: '#Hub/' + this.doctype,
			type: 'Custom'
		});
	}

	setup_side_bar() {
		this.sidebar = new frappe.ui.Sidebar({
			wrapper: this.$page.find('.layout-side-section'),
			css_class: 'hub-form-sidebar'
		});
	}

	setup_filter_area() { }

	setup_sort_selector() { }

	// let category = this.quick_view.get_values().hub_category;
	// return new Promise((resolve, reject) => {
	// 	frappe.call({
	// 		method: 'erpnext.hub_node.update_category',
	// 		args: {
	// 			hub_item_code: values.hub_item_code,
	// 			category: category,
	// 		},
	// 		callback: (r) => {
	// 			resolve();
	// 		},
	// 		freeze: true
	// 	}).fail(reject);
	// });

	get_timeline() {
		return `<div class="timeline">
			<div class="timeline-head">
			</div>
			<div class="timeline-new-email">
				<button class="btn btn-default btn-reply-email btn-xs">
					${__("Reply")}
				</button>
			</div>
			<div class="timeline-items"></div>
		</div>`;
	}

	get_footer() {
		return `<div class="form-footer">
			<div class="after-save">
				<div class="form-comments"></div>
			</div>
			<div class="pull-right scroll-to-top">
				<a onclick="frappe.utils.scroll_to(0)"><i class="fa fa-chevron-up text-muted"></i></a>
			</div>
		</div>`;
	}

	get_args() {
		return {
			hub_sync_id: this.unique_id,
			doctype: 'Hub ' + this.doctype
		};
	}

	prepare_data(r) {
		this.data = r.message;
	}

	update_data(r) {
		this.data = r.message;
	}

	render() {
		const image_html = this.data[this.image_field_name] ?
			`<img src="${this.data[this.image_field_name]}">
			<span class="helper"></span>` :
			`<div class="standard-image">${frappe.get_abbr(this.page_title)}</div>`;

		this.sidebar.remove_item('image');
		this.sidebar.add_item({
			name: 'image',
			label: image_html
		});

		if(!this.form) {
			let fields = this.formFields;
			this.form = new frappe.ui.FieldGroup({
				parent: this.$result,
				fields
			});
			this.form.make();
		}

		if(this.data.hub_category) {
			this.form.fields_dict.set_category.hide();
		}

		this.form.set_values(this.data);
		this.$result.show();

		this.$timelineList && this.$timelineList.empty();
		if(this.data.reviews && this.data.reviews.length) {
			this.data.reviews.map(review => {
				this.addReviewToTimeline(review);
			})
		}

		this.postRender()
	}

	postRender() {}

	attachFooter() {
		let footerHtml = `<div class="form-footer">
			<div class="form-comments"></div>
			<div class="pull-right scroll-to-top">
				<a onclick="frappe.utils.scroll_to(0)"><i class="fa fa-chevron-up text-muted"></i></a>
			</div>
		</div>`;

		let parent = $('<div>').appendTo(this.page.main.parent());
		this.$footer = $(footerHtml).appendTo(parent);
	}

	attachTimeline() {
		let timelineHtml = `<div class="timeline">
			<div class="timeline-head">
			</div>
			<div class="timeline-new-email">
				<button class="btn btn-default btn-reply-email btn-xs">
					${ __("Reply") }
				</button>
			</div>
			<div class="timeline-items"></div>
		</div>`;

		let parent = this.$footer.find(".form-comments");
		this.$timeline = $(timelineHtml).appendTo(parent);

		this.$timelineList = this.$timeline.find(".timeline-items");
	}

	attachReviewArea() {
		this.comment_area = new frappe.ui.ReviewArea({
			parent: this.$footer.find('.timeline-head'),
			mentions: [],
			on_submit: (val) => {
				val.user = frappe.session.user;
				val.username = frappe.session.user_fullname;
				frappe.call({
					method: 'erpnext.hub_node.send_review',
					args: {
						hub_item_code: this.data.hub_item_code,
						review: val
					},
					callback: (r) => {
						this.refresh();
						this.comment_area.reset();
					},
					freeze: true
				});
			}
		});
	}

	addReviewToTimeline(data) {
		let username = data.username || data.user || __("Anonymous")
		let imageHtml = data.user_image
			? `<div class="avatar-frame" style="background-image: url(${data.user_image})"></div>`
			: `<div class="standard-image" style="background-color: #fafbfc">${frappe.get_abbr(username)}</div>`

		let editHtml = data.own
			? `<div class="pull-right hidden-xs close-btn-container">
				<span class="small text-muted">
					${'data.delete'}
				</span>
			</div>
			<div class="pull-right edit-btn-container">
				<span class="small text-muted">
					${'data.edit'}
				</span>
			</div>`
			: '';

		let ratingHtml = '';

		for(var i = 0; i < 5; i++) {
			let starIcon = 'fa-star-o'
			if(i < data.rating) {
				starIcon = 'fa-star';
			}
			ratingHtml += `<i class="fa fa-fw ${starIcon} star-icon" data-idx='${i}'></i>`;
		}

		$(this.getTimelineItem(data, imageHtml, editHtml, ratingHtml))
			.appendTo(this.$timelineList);
	}

	getTimelineItem(data, imageHtml, editHtml, ratingHtml) {
		return `<div class="media timeline-item user-content" data-doctype="${''}" data-name="${''}">
			<span class="pull-left avatar avatar-medium hidden-xs" style="margin-top: 1px">
				${imageHtml}
			</span>

			<div class="pull-left media-body">
				<div class="media-content-wrapper">
					<div class="action-btns">${editHtml}</div>

					<div class="comment-header clearfix small ${'linksActive'}">
						<span class="pull-left avatar avatar-small visible-xs">
							${imageHtml}
						</span>

						<div class="asset-details">
							<span class="author-wrap">
								<i class="octicon octicon-quote hidden-xs fa-fw"></i>
								<span>${data.username}</span>
							</span>
								<a href="#Form/${''}" class="text-muted">
									<span class="text-muted hidden-xs">&ndash;</span>
									<span class="indicator-right ${'green'}
										delivery-status-indicator">
										<span class="hidden-xs">${data.pretty_date}</span>
									</span>
								</a>

								<a class="text-muted reply-link pull-right timeline-content-show"
								title="${__('Reply')}"> ${''} </a>
							<span class="comment-likes hidden-xs">
								<i class="octicon octicon-heart like-action text-extra-muted not-liked fa-fw">
								</i>
								<span class="likes-count text-muted">10</span>
							</span>
						</div>
					</div>
					<div class="reply timeline-content-show">
						<div class="timeline-item-content">
								<p class="text-muted small">
									<b>${data.subject}</b>
								</p>

								<hr>

								<p class="text-muted small">
									${ratingHtml}
								</p>

								<hr>
								<p>
									${data.content}
								</p>
						</div>
					</div>
				</div>
			</div>
		</div>`;
	}

	prepareFormFields(fields, fieldnames) {
		return fields
		.filter(field => fieldnames.includes(field.fieldname))
		.map(field => {
			let {
				label,
				fieldname,
				fieldtype,
			} = field;
			let read_only = 1;
			return {
				label,
				fieldname,
				fieldtype,
				read_only,
			};
		});
	}
};

erpnext.hub.ItemPage = class ItemPage extends erpnext.hub.HubDetailsPage {
	constructor(opts) {
		super(opts);

		this.show();
	}

	setup_defaults() {
		super.setup_defaults();
		this.doctype = 'Item';
		this.image_field_name = 'image';
	}

	setup_page_head() {
		super.setup_page_head();
		this.set_primary_action();
	}

	setup_side_bar() {
		super.setup_side_bar();
		this.attachFooter();
		this.attachTimeline();
		this.attachReviewArea();
	}

	set_primary_action() {
		let item = this.data;
		this.page.set_primary_action(__('Request a Quote'), () => {
			this.show_rfq_modal()
				.then(values => {
					item.item_code = values.item_code;
					delete values.item_code;

					const supplier = values;
					return [item, supplier];
				})
				.then(([item, supplier]) => {
					return this.make_rfq(item, supplier, this.page.btn_primary);
				})
				.then(r => {
					console.log(r);
					if (r.message && r.message.rfq) {
						this.page.btn_primary.addClass('disabled').html(`<span><i class='fa fa-check'></i> ${__('Quote Requested')}</span>`);
					} else {
						throw r;
					}
				})
				.catch((e) => {
					console.log(e); //eslint-disable-line
				});
		}, 'octicon octicon-plus');
	}

	prepare_data(r) {
		super.prepare_data(r);
		this.page.set_title(this.data["item_name"]);
	}

	make_rfq(item, supplier, btn) {
		console.log(supplier);
		return new Promise((resolve, reject) => {
			frappe.call({
				method: 'erpnext.hub_node.make_rfq_and_send_opportunity',
				args: { item, supplier },
				callback: resolve,
				btn,
			}).fail(reject);
		});
	}

	postRender() {
		this.categoryDialog = new frappe.ui.Dialog({
			title: __('Suggest Category'),
			fields: [
				{
					label: __('Category'),
					fieldname: 'category',
					fieldtype: 'Autocomplete',
					options: this.categories,
					reqd: 1
				}
			],
			primary_action_label: __("Send"),
			primary_action: () => {
				let values = this.categoryDialog.get_values();
				frappe.call({
					method: 'erpnext.hub_node.update_category',
					args: {
						hub_item_code: this.data.hub_item_code,
						category: values.category
					},
					callback: () => {
						this.categoryDialog.hide();
						this.refresh();
					},
					freeze: true
				}).fail(() => {});
			}
		});
	}

	getFormFields() {
		let colOneFieldnames = ['item_name', 'item_code', 'description'];
		let colTwoFieldnames = ['seller', 'company_name', 'country'];
		let colOneFields = this.prepareFormFields(this.meta.fields, colOneFieldnames);
		let colTwoFields = this.prepareFormFields(this.meta.fields, colTwoFieldnames);

		let miscFields = [
			{
				label: __('Category'),
				fieldname: 'hub_category',
				fieldtype: 'Data',
				read_only: 1
			},

			{
				label: __('Suggest Category?'),
				fieldname: 'set_category',
				fieldtype: 'Button',
				click: () => {
					this.categoryDialog.show();
				}
			},

			{
				fieldname: 'cb1',
				fieldtype: 'Column Break'
			}
		];
		this.formFields = colOneFields.concat(miscFields, colTwoFields);
	}

	show_rfq_modal() {
		let item = this.data;
		return new Promise(res => {
			let fields = [
				{ label: __('Item Code'), fieldtype: 'Data', fieldname: 'item_code', default: item.item_code },
				{ fieldtype: 'Column Break' },
				{ label: __('Item Group'), fieldtype: 'Link', fieldname: 'item_group', default: item.item_group },
				{ label: __('Supplier Details'), fieldtype: 'Section Break' },
				{ label: __('Supplier Name'), fieldtype: 'Data', fieldname: 'supplier_name', default: item.company_name },
				{ label: __('Supplier Email'), fieldtype: 'Data', fieldname: 'supplier_email', default: item.seller },
				{ fieldtype: 'Column Break' },
				{ label: __('Supplier Group'), fieldname: 'supplier_group',
					fieldtype: 'Link', options: 'Supplier Group' }
			];
			fields = fields.map(f => { f.reqd = 1; return f; });

			const d = new frappe.ui.Dialog({
				title: __('Request for Quotation'),
				fields: fields,
				primary_action_label: __('Send'),
				primary_action: (values) => {
					res(values);
					d.hide();
				}
			});

			d.show();
		});
	}
}

erpnext.hub.CompanyPage = class CompanyPage extends erpnext.hub.HubDetailsPage {
	constructor(opts) {
		super(opts);
		this.show();
	}

	setup_defaults() {
		super.setup_defaults();
		this.doctype = 'Company';
		this.image_field_name = 'company_logo';
	}

	prepare_data(r) {
		super.prepare_data(r);
		this.page.set_title(this.data["company_name"]);
	}

	getFormFields() {
		let fieldnames = ['company_name', 'description', 'route', 'country', 'seller', 'site_name'];;
		this.formFields = this.prepareFormFields(this.meta.fields, fieldnames);
	}
}
