<template>
	<div>
		<component v-bind:is="currentComponent" :content="content" :type="type">
			<ContentNavigation :nextContent="nextContent" :nextContentType="nextContentType"/>
		</component>
	</div>
</template>
<script>
import Article from "../components/Article.vue"
import Quiz from "../components/Quiz.vue"
import Video from "../components/Video.vue"
import ContentNavigation from "../components/ContentNavigation.vue"

export default {
	props:['program_name', 'course', 'type', 'content'],
	name: "CoursePage",
	data() {
		return{
			nextContent: '',
			nextContentType: '',
		}
	},
	computed: {
	  currentComponent: function() {
	  	if(this.type === "Article") {
	  		return 'Article'
	  	}
	  	else if(this.type === "Quiz") {
	  		return 'Quiz'
	  	}
	  	else if(this.type === "Video") {
	  		return 'Video'
	  	}
	  },
	},
	mounted() {
	  	frappe.call({
	  		method: "erpnext.www.lms.get_next_content",
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
		Article,
		Video,
		Quiz,
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