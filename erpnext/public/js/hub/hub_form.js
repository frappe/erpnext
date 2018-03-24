frappe.provide('erpnext.hub');

erpnext.hub.HubDetailsPage = class HubDetailsPage extends frappe.views.BaseList {
	setup_defaults() {
		super.setup_defaults();
		this.method = 'erpnext.hub_node.get_details';
		const route = frappe.get_route();
		this.page_name = route[2];
	}

	setup_fields() {
		return this.get_meta()
			.then(r => {
				this.meta = r.message.meta || this.meta;
				this.bootstrap_data(r.message);

				this.prepareFormFields();
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

		this.attachFooter();
		this.attachTimeline();
		this.attachReviewArea();
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

		this.form.set_values(this.data);
		this.$result.show();

		this.$timelineList.empty();
		if(this.data.reviews.length) {
			this.data.reviews.map(review => {
				this.addReviewToTimeline(review);
			})
		}
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
			</div>
			<div class="timeline-items"></div>
		</div>`;

		let parent = this.$footer.find(".form-comments");
		this.$timeline = $(timelineHtml).appendTo(parent);

		this.$timelineList = this.$timeline.find(".timeline-items");
	}

	attachReviewArea() {
		this.comment_area = new erpnext.hub.ReviewArea({
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
};

erpnext.hub.ReviewArea = class ReviewArea extends frappe.ui.CommentArea {
	setup_dom() {
		const header = !this.no_wrapper ?
			`<div class="comment-input-header">
				<span class="small text-muted">${__("Add a review")}</span>
				<button class="btn btn-default btn-comment btn-xs disabled pull-right">
					${__("Submit Review")}
				</button>
			</div>` : '';

		const footer = !this.no_wrapper ?
			`<div class="text-muted small">
				${__("Ctrl+Enter to submit")}
			</div>` : '';

		const ratingArea = !this.no_wrapper ?
			`<div class="rating-area text-muted small" style="margin-bottom: 5px">
				${ __("Your rating: ") }
				<i class='fa fa-fw fa-star-o star-icon' data-index=0></i>
				<i class='fa fa-fw fa-star-o star-icon' data-index=1></i>
				<i class='fa fa-fw fa-star-o star-icon' data-index=2></i>
				<i class='fa fa-fw fa-star-o star-icon' data-index=3></i>
				<i class='fa fa-fw fa-star-o star-icon' data-index=4></i>
			</div>` : '';

		this.wrapper = $(`
			<div class="comment-input-wrapper">
				${ header }
				<div class="comment-input-container">
					${ ratingArea }
					<input class="form-control review-subject" type="text"
						placeholder="${__('Subject')}"
						style="border-radius: 3px; border-color: #ebeff2">
					</input>
					<div class="form-control comment-input"></div>
					${ footer }
				</div>
			</div>
		`);
		this.wrapper.appendTo(this.parent);
		this.input = this.parent.find('.comment-input');
		this.subject = this.parent.find('.review-subject');
		this.button = this.parent.find('.btn-comment');
		this.ratingArea = this.parent.find('.rating-area');

		this.rating = 0;
	}

	check_state() {
		return !(this.input.summernote('isEmpty') ||
			this.rating === 0 || !this.subject.val().length);
	}

	set_state() {
		if(this.check_state()) {
			this.button
				.removeClass('btn-default disabled')
				.addClass('btn-primary');
		} else {
			this.button
				.removeClass('btn-primary')
				.addClass('btn-default disabled');
		}
	}

	reset() {
		this.set_rating(0);
		this.subject.val('');
		this.input.summernote('code', '');
	}

	bind_events() {
		super.bind_events();
		this.ratingArea.on('click', '.star-icon', (e) => {
			let index = $(e.target).attr('data-index');
			this.set_rating(parseInt(index) + 1);
		})

		this.subject.on('change', () => {
			this.set_state();
		})
	}

	set_rating(rating) {
		this.ratingArea.find('.star-icon').each((i, icon) => {
			let star = $(icon);
			if(i < rating) {
				star.removeClass('fa-star-o');
				star.addClass('fa-star');
			} else {
				star.removeClass('fa-star');
				star.addClass('fa-star-o');
			}
		})

		this.rating = rating;
		this.set_state();
	}

	val(value) {
		if(value === undefined) {
			return {
				rating: this.rating,
				subject: this.subject.val(),
				content: this.input.summernote('code')
			}
		}
		// Set html if value is specified
		this.input.summernote('code', value);
	}
}

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

	prepareFormFields() {
		let fieldnames = ['hub_item_code', 'item_name', 'item_code', 'description',
			'seller', 'company_name', 'country'];
		this.formFields = this.meta.fields
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

	prepareFormFields() {
		let fieldnames = ['company_name', 'description', 'route', 'country', 'seller', 'site_name'];;
		this.formFields = this.meta.fields
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
}
