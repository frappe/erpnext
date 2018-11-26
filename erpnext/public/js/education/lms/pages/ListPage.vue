<template>
	<div>
		<TopSection :title="portal.title" :description="portal.description">
        	<AButton v-if="isLogin" :type="'primary'" :size="'lg'" :route="{ name: 'signup'}">Sign Up</AButton>
    	</TopSection>
		<CardList :title="'All Programs'" :description="''">
			<ProgramCard slot="card-list-slot" v-for="item in masterData" :key="item.program.name" :program="item.program" :enrolled="item.is_enrolled"/>
		</CardList>
	</div>
</template>
<script>
import ProgramCard from '../components/ProgramCard.vue';
import CourseCard from "../components/CourseCard.vue"
import Button from '../components/Button.vue';
import TopSection from "../components/TopSection.vue"
import CardList from "../components/CardList.vue"


export default {
	props: ['master'],
    name: "ListPage",
    components: {
        AButton: Button,
		CourseCard,
		ProgramCard,
		CardList,
		TopSection		
	},
	data() {
		return {
			portal: {},
			masterData: {}
		}
	},
	mounted() {
        this.getPortalDetails().then(data => this.portal = data);
        this.getMaster().then(data => this.masterData = data);
    },
    methods: {
        getPortalDetails() {
            return lms.call("get_portal_details")
        },
        getMaster() {
            return lms.call("get_all_programs")
        }
	},
	computed: {
		isLogin() {
			return !lms.store.checkLogin()
		}
	}
};
</script>