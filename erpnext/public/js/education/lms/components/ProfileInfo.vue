<template>
<section>
		<div class='container'>
			<div class="row">
				<div class="col-sm-3 text-center">
					<span class="sidebar-standard-image" title="Lorem Ipsum">
						<span v-if="avatar" class="avatar-frame" :style="avatarStyle">
						</span>
						<div v-else class="standard-image" style="background-color: #fafbfc;">
							{{ abbr }}
						</div>
					</span>
				</div>
				<div class="col-sm-9">
					<div>
						<h3>{{ fullName }}</h3>
						<ul>
							<li class="row">
								<div class="col-md-3 col-sm-4 pr-0 text-muted">Email:</div>
								<div class="col-md-9 col-sm-8">{{ email }}</div>
							</li>
							<li class="row">
								<div class="col-md-3 col-sm-4 pr-0 text-muted">Date of Joining:</div>
								<div class="col-md-9 col-sm-8">{{ joiningDate }}</div>
							</li>
							<!-- <li><span class="text-muted">Date of Joining: </span>3rd July 2018</li> -->
							<!-- <li><span class="text-muted">Programs Enrolled: </span>ERPNext Certified Professional 2018</li> -->
							<li class="row">
								<div class="col-md-3 col-sm-4 pr-0 text-muted">Programs Enrolled:</div>
								<div class="col-md-9 col-sm-8">
									<ul>
										<li v-for="program in enrolledPrograms" :key="program">{{ program }}</li>
									</ul>
								</div>
							</li>
						</ul>
					</div>
					<a href="/update-profile" class="edit-button text-muted"><i class="fa fa-pencil" aria-hidden="true"></i></a>
				</div>
			</div>
			<div ></div>
		</div>
	</section>
</template>
<script>

export default {
	props: ['enrolledPrograms'],
	name: "ProfileInfo",
	data() {
		return {
			avatar: frappe.user_image,
			fullName: frappe.full_name,
			abbr: frappe.get_abbr(frappe.get_cookie("full_name")),
			email: frappe.session.user,
			joiningDate: 'fetching...'
		}
	},
	mounted(){
		this.getJoiningDate().then(data => this.joiningDate = lms.moment(String(data)).format('D MMMM YYYY'))
	},
	computed: {
		avatarStyle() {
			return `background-image: url("${this.avatar}")`
		},
	},
	methods: {
		getJoiningDate() {
			return lms.call("get_joining_date")
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