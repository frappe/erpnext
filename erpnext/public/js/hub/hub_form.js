frappe.provide('erpnext.hub');

erpnext.hub.HubDetailsPage = class HubDetailsPage extends frappe.views.BaseList {
	setup_defaults() {
		super.setup_defaults();
		this.method = 'erpnext.hub_node.get_details';
		const route = frappe.get_route();
		this.page_name = route[2];
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

		this.attachFooter();
		this.attachTimeline();
		this.attachCommentArea();
		this.addTimelineItem();
	}

	setup_filter_area() { }

	setup_sort_selector() { }

	setup_timeline() {

		// this.timeline = new frappe.ui.form.Timeline({
		// 	parent: this.wrapper.find(".form-comments"),
		// 	frm: this.frm
		// });


		// this.footer = new frappe.ui.form.Footer({
		// 	frm: this,
		// 	parent: $('<div>').appendTo(this.page.main.parent())
		// });
	}

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

		this.sidebar.add_item({
			label: image_html
		});

		let fields = this.get_field_configs();

		this.form = new frappe.ui.FieldGroup({
			parent: this.$result,
			fields
		});

		this.form.make();
		this.form.set_values(this.data);
	}

	toggle_result_area() {
		this.$result.toggle(this.unique_id);
		this.$paging_area.toggle(this.data.length > 0);
		this.$no_result.toggle(this.data.length == 0);

		const show_more = (this.start + this.page_length) <= this.data.length;
		this.$paging_area.find('.btn-more')
			.toggle(show_more);
	}

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
				<button class="btn btn-default btn-new-email btn-xs">
					${ __("New Email") }
				</button>
			</div>
			<div class="timeline-items"></div>
		</div>`;

		let parent = this.$footer.find(".form-comments");
		this.$timeline = $(timelineHtml).appendTo(parent);

		this.$timelineList = this.$timeline.find(".timeline-items");
	}

	attachCommentArea() {
		this.comment_area = new frappe.ui.CommentArea({
			parent: this.$footer.find('.timeline-head'),
			mentions: ['Administrator', 'Guest'],
			on_submit: (val) => {return val;}
		});
	}

	addTimelineItem(data) {
		data = {
			username: 'Pratu',
			own: 1
		};
		let imageHtml = data.user_image
			? `<div class="avatar-frame" style="background-image: url(${data.user_image})"></div>`
			: `<div class="standard-image" style="background-color: #fafbfc">${frappe.get_abbr(data.username)}</div>`

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

		// let liked = d

		$(this.getTimelineItem(data, imageHtml, editHtml))
			.appendTo(this.$timelineList);

	}

	getTimelineItem(data, imageHtml, editHtml) {
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
								<i class="octicon octicon-circle hidden-xs fa-fw"></i>
								<span>${data.username}</span>
							</span>
							<span>
								<a href="#Form/${''}" class="text-muted">
									<strong>link</strong>link
								</a>
							</span>
								<a href="#Form/${''}" class="text-muted">
									<span class="text-muted hidden-xs">&ndash;</span>
									<span class="indicator-right ${'green'}
										delivery-status-indicator">
										<span class="hidden-xs">${__('Sent')}</span>
									</span>
									<span class="text-muted n-dash">&ndash;</span>
									${__("Details")}
								</a>

								<a class="text-muted reply-link pull-right timeline-content-show"
								title="${__('Reply')}">
									${__('Reply')}
								</a>
							<span class="text-muted commented-on hidden-xs">
								&ndash; ${'data.comment_on'}</span>
							<span class="text-muted commented-on-small">
								&ndash; ${'data.comment_on_small'}</span>
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
									<b>${__("Subject")}:</b>
									${'data.subject'}
								</p>

								<hr>

								<p class="text-muted small">
									<i class="fa fa-fw fa-star star-icon" data-idx='0'></i>
									<i class="fa fa-fw fa-star-o star-icon" data-idx='1'></i>
								</p>

								<hr>
						</div>
					</div>
				</div>
			</div>
		</div>`;
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

	get_field_configs() {
		let fields = [];
		this.fields.map(fieldname => {
			fields.push({
				label: toTitle(frappe.model.unscrub(fieldname)),
				fieldname,
				fieldtype: 'Data',
				read_only: 1
			});
		});

		let category_field = {
			label: 'Hub Category',
			fieldname: 'hub_category',
			fieldtype: 'Data'
		}

		if(this.data.company_name === this.hub_settings.company) {
			this.page.set_primary_action(__('Update'), () => {
				this.update_on_hub();
			}, 'octicon octicon-plus');
		} else {
			category_field.read_only = 1;
		}

		fields.unshift(category_field);

		return fields;
	}

	update_on_hub() {
		return new Promise((resolve, reject) => {
			frappe.call({
				method: 'erpnext.hub_node.update_category',
				args: { item: this.unique_id, category: this.form.get_value('hub_category') },
				callback: resolve,
				freeze: true
			}).fail(reject);
		});
	}

	setup_fields() {
		this.fields = ['hub_item_code', 'item_name', 'item_code', 'description',
			'seller', 'company_name', 'country'];
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

	get_field_configs() {
		let fields = [];
		this.fields.map(fieldname => {
			fields.push({
				label: toTitle(frappe.model.unscrub(fieldname)),
				fieldname,
				fieldtype: 'Data',
				read_only: 1
			});
		});

		return fields;
	}

	setup_fields() {
		this.fields = ['company_name', 'description', 'route', 'country', 'seller', 'site_name'];
	}
}
