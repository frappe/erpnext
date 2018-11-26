<template>
<div>
	<ProfileInfo :enrolledPrograms="enrolledPrograms"></ProfileInfo>
	<CardList :title="'Your Progress'" :description="''">
        <ProgressCard slot="card-list-slot" v-for="program in enrolledPrograms" :program="program" :key="program"/>
    </CardList>
</div>
</template>
<script>
import Button from '../components/Button.vue';
import TopSection from "../components/TopSection.vue"
import CardList from "../components/CardList.vue"
import ProgressCard from "../components/ProgressCard.vue"
import ProfileInfo from "../components/ProfileInfo.vue"


export default {
    name: "ProfilePage",
    components: {
        AButton: Button,
		TopSection,
		CardList,
		ProfileInfo,		
		ProgressCard		
	},
	data() {
		return {
			enrolledPrograms: {},
		}
	},
	mounted() {
        this.getEnrolledPrograms().then(data => this.enrolledPrograms = data);
    },
    methods: {
        getEnrolledPrograms() {
            return lms.call("get_program_enrollments")
        }
    }
};
</script>