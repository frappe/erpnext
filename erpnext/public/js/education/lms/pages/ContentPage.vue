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
	props:['program_name', 'course_name', 'topic', 'type', 'content'],
	name: "ContentPage",
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
	  	this.getNextContent().then(data => {
	  		this.nextContent = data.content,
	  		this.nextContentType = data.content_type
	  	});
	},
	methods: {
		getNextContent(){
			return lms.call("get_next_content",
				{
					current_content: this.content,
					current_content_type: this.type,
					topic: this.topic,
			  	}
			);
		}
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