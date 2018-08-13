function get_review_html(review) {
	let username = review.username || review.user || __("Anonymous");

	let image_html = review.user_image
		? `<div class="avatar-frame" style="background-image: url(${review.user_image})"></div>`
		: `<div class="standard-image" style="background-color: #fafbfc">${frappe.get_abbr(username)}</div>`

	let edit_html = review.own
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

	let rating_html = get_rating_html(review.rating);

	return get_timeline_item(review, image_html, edit_html, rating_html);
}

function get_timeline_item(data, image_html, edit_html, rating_html) {
	return `<div class="media timeline-item user-content" data-doctype="${''}" data-name="${''}">
		<span class="pull-left avatar avatar-medium hidden-xs" style="margin-top: 1px">
			${image_html}
		</span>
		<div class="pull-left media-body">
			<div class="media-content-wrapper">
				<div class="action-btns">${edit_html}</div>

				<div class="comment-header clearfix">
					<span class="pull-left avatar avatar-small visible-xs">
						${image_html}
					</span>

					<div class="asset-details">
						<span class="author-wrap">
							<i class="octicon octicon-quote hidden-xs fa-fw"></i>
							<span>${data.username}</span>
						</span>
						<a class="text-muted">
							<span class="text-muted hidden-xs">&ndash;</span>
							<span class="hidden-xs">${comment_when(data.modified)}</span>
						</a>
					</div>
				</div>
				<div class="reply timeline-content-show">
					<div class="timeline-item-content">
						<p class="text-muted">
							${rating_html}
						</p>
						<h6 class="bold">${data.subject}</h6>
						<p class="text-muted">
							${data.content}
						</p>
					</div>
				</div>
			</div>
		</div>
	</div>`;
}

function get_rating_html(rating) {
	let rating_html = ``;
	for (var i = 0; i < 5; i++) {
		let star_class = 'fa-star';
		if (i >= rating) star_class = 'fa-star-o';
		rating_html += `<i class='fa fa-fw ${star_class} star-icon' data-index=${i}></i>`;
	}
	return rating_html;
}

export {
	get_review_html,
    get_rating_html
}
