<template>
	<div>
		<component v-bind:is="currentComponent" :content="content" :type="type">
			<ContentNavigation :nextContent="nextContent" :nextContentType="nextContentType"/>
		</component>
	</div>
</template>
<script>
import ContentArticle from "../components/ContentArticle.vue"
import ContentQuiz from "../components/ContentQuiz.vue"
import ContentVideo from "../components/ContentVideo.vue"
import ContentNavigation from "../components/ContentNavigation.vue"

export default {
	props:['code', 'course', 'type', 'content'],
	name: "AcademyCoursePage",
	data() {
		return{
			nextContent: true,
			nextContentType: '',
		}
	},
	computed: {
	  currentComponent: function() {
	  	if(this.type === "Article") {
	  		return 'ContentArticle'
	  	}
	  	else if(this.type === "Quiz") {
	  		return 'ContentQuiz'
	  	}
	  	else if(this.type === "Video") {
	  		return 'ContentVideo'
	  	}
	  },
	},
	mounted() {
	  	frappe.call({
	  		method: "erpnext.www.academy.get_next_content",
	  		args:{
	  			content: this.content,
	  			content_type: this.type,
	  			course: this.course
	  		}
	  	}).then(r => {
	  		this.nextContent = r.message.content,
	  		this.nextContentType = r.message.content_type
	  	});
	},
	components: {
		ContentArticle,
		ContentVideo,
		ContentQuiz,
		ContentNavigation
	}
};
</script>

<style>
.footer-message {
	display: none;
}

.video-top-section {
	padding-top: 3rem !important;
	padding-bottom: 1rem !important;
}

.video-description-section {
	padding-top: 0em !important;
}

.article-top-section {
	padding-top: 0.5em !important;
	padding-bottom: 0rem !important;
}

.article-content-section {
	padding-top: 0em !important;
}

.quiz-section {
	padding-top: 0.5em !important;
	padding-bottom: 0rem !important;
}
</style>