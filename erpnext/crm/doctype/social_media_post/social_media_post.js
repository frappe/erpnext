// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
frappe.ui.form.on('Social Media Post', {
	validate: function(frm) {
		if (frm.doc.twitter === 0 && frm.doc.linkedin === 0) {
			frappe.throw(__("Select atleast one Social Media Platform to Share on."));
		}
		if (frm.doc.scheduled_time) {
			let scheduled_time = new Date(frm.doc.scheduled_time);
			let date_time = new Date();
			if (scheduled_time.getTime() < date_time.getTime()) {
				frappe.throw(__("Scheduled Time must be a future time."));
			}
		}
		frm.trigger('validate_tweet_length');
	},

	text: function(frm) {
		if (frm.doc.text) {
			frm.set_df_property('text', 'description', `${frm.doc.text.length}/280`);
			frm.refresh_field('text');
			frm.trigger('validate_tweet_length');
		}
	},

	validate_tweet_length: function(frm) {
		if (frm.doc.text && frm.doc.text.length > 280) {
			frappe.throw(__("Tweet length Must be less than 280."));
		}
	},

	onload: function(frm) {
		frm.trigger('make_dashboard');
	},

	make_dashboard: function(frm) {
		if (frm.doc.post_status == "Posted") {
			frappe.call({
				doc: frm.doc,
				method: 'get_post',
				freeze: true,
				callback: (r) => {
					if (!r.message) {
						return;
					}

					let datasets = [], colors = [];
					if (r.message && r.message.twitter) {
						colors.push('#1DA1F2');
						datasets.push({
							name: 'Twitter',
							values: [r.message.twitter.favorite_count, r.message.twitter.retweet_count]
						});
					}
					if (r.message && r.message.linkedin) {
						colors.push('#0077b5');
						datasets.push({
							name: 'LinkedIn',
							values: [r.message.linkedin.totalShareStatistics.likeCount, r.message.linkedin.totalShareStatistics.shareCount]
						});
					}

					if (datasets.length) {
						frm.dashboard.render_graph({
							data: {
								labels: ['Likes', 'Retweets/Shares'],
								datasets: datasets
							},

							title: __("Post Metrics"),
							type: 'bar',
							height: 300,
							colors: colors
						});
					}
				}
			});
		}
	},

	refresh: function(frm) {
		frm.trigger('text');

		if (frm.doc.docstatus === 1) {
			if (!['Posted', 'Deleted'].includes(frm.doc.post_status)) {
				frm.trigger('add_post_btn');
			}
			if (frm.doc.post_status !='Deleted') {
				frm.add_custom_button(('Delete Post'), function() {
					frappe.confirm(__('Are you sure want to delete the Post from Social Media platforms?'),
						function() {
							frappe.call({
								doc: frm.doc,
								method: 'delete_post',
								freeze: true,
								callback: () => {
									frm.reload_doc();
								}
							});
						}
					);
				});
			}

			if (frm.doc.post_status !='Deleted') {
				let html='';
				if (frm.doc.twitter) {
					let color = frm.doc.twitter_post_id ? "green" : "red";
					let status = frm.doc.twitter_post_id ? "Posted" : "Not Posted";
					html += `<div class="col-xs-6">
								<span class="indicator whitespace-nowrap ${color}"><span>Twitter : ${status} </span></span>
							</div>` ;
				}
				if (frm.doc.linkedin) {
					let color = frm.doc.linkedin_post_id ? "green" : "red";
					let status = frm.doc.linkedin_post_id ? "Posted" : "Not Posted";
					html += `<div class="col-xs-6">
								<span class="indicator whitespace-nowrap ${color}"><span>LinkedIn : ${status} </span></span>
							</div>` ;
				}
				html = `<div class="row">${html}</div>`;
				frm.dashboard.set_headline_alert(html);
			}
		}
	},

	add_post_btn: function(frm) {
		frm.add_custom_button(__('Post Now'), function() {
			frappe.call({
				doc: frm.doc,
				method: 'post',
				freeze: true,
				callback: function() {
					frm.reload_doc();
				}
			});
		});
	}
});
