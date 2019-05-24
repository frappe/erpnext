<template>
	<div class="py-5">
		<div class="row">
			<div class="col-sm-12">
				<div>
					<h3>{{ fullName }}</h3>
					<ul>
						<li class="row">
							<div class="col-md-3 col-sm-4 pr-0 text-muted">Email:</div>
							<div class="col-md-9 col-sm-8">{{ email }}</div>
						</li>
						<li v-if="joiningDate" class="row">
							<div class="col-md-3 col-sm-4 pr-0 text-muted">Date of Joining:</div>
							<div class="col-md-9 col-sm-8">{{ joiningDate }}</div>
						</li>
						<li class="row">
							<div class="col-md-3 col-sm-4 pr-0 text-muted">Programs Enrolled:</div>
							<div class="col-md-9 col-sm-8">
								<ul v-if="enrolledPrograms">
									<li v-for="program in enrolledPrograms" :key="program">{{ program }}</li>
								</ul>
								<span v-else>None</span>
							</div>
						</li>
					</ul>
				</div>
				<a href="/update-profile" class="edit-button text-muted">Edit Profile</a>
			</div>
		</div>
		<div ></div>
	</div>
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
			joiningDate: ''
		}
	},
	mounted(){
		this.getJoiningDate().then(data => {
			if(data) {
				this.joiningDate = lms.moment(String(data)).format('D MMMM YYYY')
			}
		})
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
	.edit-button {
		position: absolute;
		top: 0;
		right: 0;
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