<template>
    <div class="media timeline-item user-content" data-doctype="${''}" data-name="${''}">
		<span class="pull-left avatar avatar-medium hidden-xs" style="margin-top: 1px">
			<!-- ${image_html} -->
		</span>
		<div class="pull-left media-body">
			<div class="media-content-wrapper">
				<div class="action-btns">
                    <!-- ${edit_html} -->
                </div>

				<div class="comment-header clearfix">
					<span class="pull-left avatar avatar-small visible-xs">
						<!-- ${image_html} -->
					</span>

					<div class="asset-details">
						<span class="author-wrap">
							<i class="octicon octicon-quote hidden-xs fa-fw"></i>
							<span>
                                {{ username }}
                            </span>
						</span>
						<a class="text-muted">
							<span class="text-muted hidden-xs">&ndash;</span>
							<span class="hidden-xs" v-html="comment_when"></span>
						</a>
					</div>
				</div>
				<div class="reply timeline-content-show">
					<div class="timeline-item-content">
						<p class="text-muted">
							<rating :rating="rating" :max_rating="5"></rating>
						</p>
						<h6 class="bold">{{ subject }}</h6>
						<p class="text-muted" v-html="content"></p>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script>
import Rating from '../components/Rating.vue';

export default {
    props: ['username', 'comment_when', 'avatar', 'rating', 'subject', 'content'],
    components: {
        Rating
    }
}
</script>

