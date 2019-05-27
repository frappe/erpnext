<template>
<div>
	<breadcrumb></breadcrumb>
	<TopSection v-bind:title="course.course_name" v-bind:description="course.course_intro">
    </TopSection>
	<CardList :title="'Topics'" :description="''">
        <TopicCard slot="card-list-slot" v-for="topic in topicData" :topic="topic" :course_name="course_name" :program_name="program_name" :key="topic.name"/>
    </CardList>
</div>
</template>
<script>
import TopSection from "../components/TopSection.vue"
import CardList from "../components/CardList.vue"
import TopicCard from "../components/TopicCard.vue"
import Breadcrumb from "../components/Breadcrumb.vue"

export default {
	props: ['program_name','course_name'],
    name: "CoursePage",
    components: {
		TopSection,
		CardList,
		TopicCard,
		Breadcrumb
	},
	data() {
		return {
			course: {},
			topicData: [],
		}
	},
	mounted() {
		this.getCourseDetails().then(data => this.course = data);
		this.getTopics().then(data => this.topicData = data);
	},
	methods: {
		getCourseDetails() {
			return lms.call('get_course_details', {
				course_name: this.course_name
			});
		},
		getTopics() {
			return lms.call('get_topics', {
				course_name: this.course_name
			})
		}
	}
};
</script>