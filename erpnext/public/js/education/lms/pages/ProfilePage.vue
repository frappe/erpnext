<template>
<div>
	<ProfileInfo :enrolledPrograms="enrolledPrograms"></ProfileInfo>
	<div v-if="enrolledPrograms">
		<CardList :title="'Your Progress'" :description="''">
	        <ProgressCard slot="card-list-slot" v-for="program in enrolledPrograms" :program="program" :key="program"/>
	    </CardList>
		<CardList :title="''" :description="''">
	        <ScoreCard slot="card-list-slot" v-for="program in enrolledPrograms" :program="program" :key="program"/>
	    </CardList>
	</div>
	<div v-else>
		You haven't enrolled in any programs yet.
	</div>

</div>
</template>
<script>
import Button from '../components/Button.vue';
import TopSection from "../components/TopSection.vue"
import CardList from "../components/CardList.vue"
import ProgressCard from "../components/ProgressCard.vue"
import ProfileInfo from "../components/ProfileInfo.vue"
import ScoreCard from "../components/ScoreCard.vue"

export default {
    name: "ProfilePage",
    components: {
        AButton: Button,
		TopSection,
		CardList,
		ProfileInfo,
		ProgressCard,
		ScoreCard
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