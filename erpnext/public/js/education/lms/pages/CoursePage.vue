<template>
<div>
	<TopSection v-bind:title="program.program_name" v-bind:description="program.description">
    </TopSection>
	<CardList :title="'Courses'" :description="''" :sectionType="'section-padding section-bg'">
        <CourseCard slot="card-list-slot" v-for="course in courseData" :course="course" :program_name="program_name" :key="course.name"/>
    </CardList>
</div>
</template>
<script>
import TopSection from "../components/TopSection.vue"
import CardList from "../components/CardList.vue"
import CourseCard from "../components/CourseCard.vue"


export default {
	props: ['program_name'],
    name: "CoursePage",
    components: {
		TopSection,
		CardList,
		CourseCard
	},
	data() {
		return {
			program: {},
			courseData: [],
		}
	},
	mounted() {
		this.getProgramDetails().then(data => this.program = data);
		this.getCourses().then(data => this.courseData = data);
	},
	methods: {
		getProgramDetails() {
			return lms.call('get_program_details', {
				program_name: this.program_name
			});
		},
		getCourses() {
			return lms.call('get_courses', {
				program_name: this.program_name
			})
		}
	}
};
</script>