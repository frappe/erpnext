<template>
<div>
    <div class='mt-2'>
    <div>
        <div class="mt-3 row">
            <div class="col-md-8">
                <h2>{{ contentData.name }}</h2>
                <span class="text-muted">
                    <i class="octicon octicon-clock" title="Duration"></i> <span v-if="contentData.duration"> {{ contentData.duration }} Mins &mdash; </span><span v-if="contentData.publish_date"> Published on {{ contentData.publish_date }}. </span>
                </span>
            </div>
            <div class="col-md-4 text-right">
                <slot></slot>
            </div>
        </div>
        <youtube-player :url="contentData.url" class="mt-3"/>
        <hr>
    </div>
</div>
<div class="video-description-section">
    <div>
        <div class="content" v-html="contentData.description">
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
</div>
</div>
</template>
<script>
import YoutubePlayer from './YoutubePlayer.vue'

export default {
	props: ['content', 'type'],
	name: 'Video',
	data() {
    	return {
            contentData: '',
    	}
    },
    components: {
        YoutubePlayer
    },
    mounted() {
        this.getContent()
            .then(data => this.contentData = data)
    },
    methods: {
        getContent() {
            return lms.call('get_content', {
                content_type: this.type,
                content: this.content
            })
        }
    }
};
</script>