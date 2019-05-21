<template>
<div>
	<breadcrumb></breadcrumb>
	<TopSection v-bind:title="program.program_name" v-bind:description="program.description">
    </TopSection>
	<CardList :title="'Courses'" :description="''">
        <CourseCard slot="card-list-slot" v-for="course in courseData" :course="course" :program_name="program_name" :key="course.name"/>
    </CardList>
</div>
</template>
<script>
import TopSection from "../components/TopSection.vue"
import CardList from "../components/CardList.vue"
import CourseCard from "../components/CourseCard.vue"
import Breadcrumb from "../components/Breadcrumb.vue"

export default {
	props: ['program_name'],
    name: "ProgramPage",
    components: {
		TopSection,
		CardList,
		CourseCard,
		Breadcrumb
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
			return lms.call('get_program', {
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