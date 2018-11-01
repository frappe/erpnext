<template>
<div>
    <section class='article-top-section video-section-bg'>
        <div class='container'>
            <div class="row">
                <div class="col-md-8">
                    <h2>{{ contentData.title }}</h2>
                    <span class="text-muted">
                        Published on {{ contentData.publish_date }}, by {{ contentData.author }}
                    </span>
                </div>
                <div class="col-md-4 text-right">
                	<slot></slot>
                </div>
            </div>
            <hr>
        </div>
    </section>
    <section class="article-content-section">
        <div class='container'>
            <div class="content" v-html="contentData.content"></div>
            <div class="text-right">
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
	name: 'ContentArticle',
	data() {
    	return {
    		contentData: ''
    	}
    },
    mounted() {
    	frappe.call({
    		method: "erpnext.www.academy.get_content",
    		args: {
    			content_name: this.content,
    			content_type: this.type
    		}
    	}).then(r => {
    			this.contentData = r.message
    	});
    }
};
</script>
