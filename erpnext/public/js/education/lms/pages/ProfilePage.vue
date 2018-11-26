<template>
<div>
	<section>
		<div class='container'>
			<div class="row">
				<div class="col-sm-3 text-center">
					<span class="sidebar-standard-image" title="Lorem Ipsum">
						<div class="standard-image" style="background-color: #fafbfc;">
							LP
						</div>
					</span>
				</div>
				<div class="col-sm-9">
					<div>
						<h3>Lorem Ipsum</h3>
						<ul>
							<li class="row">
								<div class="col-md-3 col-sm-4 pr-0 text-muted">Email:</div>
								<div class="col-md-9 col-sm-8">lorem@example.com</div>
							</li>
							<li class="row">
								<div class="col-md-3 col-sm-4 pr-0 text-muted">Date of Joining:</div>
								<div class="col-md-9 col-sm-8">18th July 2018</div>
							</li>
							<!-- <li><span class="text-muted">Date of Joining: </span>3rd July 2018</li> -->
							<!-- <li><span class="text-muted">Programs Enrolled: </span>ERPNext Certified Professional 2018</li> -->
							<li class="row">
								<div class="col-md-3 col-sm-4 pr-0 text-muted">Programs Enrolled:</div>
								<div class="col-md-9 col-sm-8">
									<ul>
										<li>Frappe Certified ERPNext Professional</li>
										<li>Frappe Certified Developer</li>
									</ul>
								</div>
							</li>
						</ul>
					</div>
					<a href="" class="edit-button text-muted"><i class="fa fa-pencil" aria-hidden="true"></i></a>
				</div>
			</div>
		</div>
	</section>
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


export default {
    name: "ProfilePage",
    components: {
        AButton: Button,
		TopSection,
		CardList,
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
<style scoped>
	.edit-button{
		position:absolute;
		top:0;
		right:0;
	}
	.standard-image {
		font-size: 72px;
		border-radius: 6px;
	}
	ul {
        list-style-type: none;
        padding: 0;
		margin: 0
    }
</style>