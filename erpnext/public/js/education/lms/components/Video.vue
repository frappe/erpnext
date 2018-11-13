<template>
<div>
    <section class='video-top-section video-section-bg'>
    <div class='container'>
        <div class="embed-responsive embed-responsive-16by9">
            <iframe class="embed-responsive-item" :src="'https://www.youtube.com/embed/' + contentData.url" allowfullscreen></iframe>
        </div>
        <div class="mt-3 row">
            <div class="col-md-8">
                <h2>{{ contentData.name }}</h2>
                <span class="text-muted">
                    <i class="octicon octicon-clock" title="Duration"></i> {{ contentData.duration }} Mins
                    &mdash; Published on {{ contentData.publish_date }}.
                </span>
            </div>
            <div class="col-md-4 text-right">
                    <slot></slot>
            </div>
        </div>
        <hr>
    </div>
</section>
<section class="video-description-section">
    <div class='container'>
        <div class="content" :html="contentData.description">
        </div>
        <div class="text-right hidden">
            <a class='btn btn-outline-secondary' href="/classrooms/module">Previous</a>
            <a class='btn btn-primary' href="/classrooms/module">Next</a>
        </div>
        <div class="mt-3 text-right">
            <a class="text-muted" href="/report"><i class="octicon octicon-issue-opened" title="Report"></i> Report a
                Mistake</a>
        </div>
    </div>
</section>
</div>
</template>
<script>
export default {
	props: ['content', 'type'],
	name: 'Video',
	data() {
    	return {
    		contentData: ''
    	}
    },
    mounted() {
    	frappe.call({
    		method: "erpnext.www.lms.get_content",
    		args: {
    			content_name: this.content,
    			content_type: this.type
    		}
    	}).then(r => {
    			this.contentData = r.message
    	});
    },
};
</script>
