<template>
<nav class="navbar navbar-light bg-white navbar-expand-lg sticky-top shadow-sm">
    <div class="container">
        <a class="navbar-brand" href="/lms">
            <span>{{ portal.title }}</span>
        </a>
        <button class="navbar-toggler" type="button" data-toggle="collapse" data-target="#navbarSupportedContent" aria-controls="navbarSupportedContent" aria-expanded="false" aria-label="Toggle navigation">
            <span class="navbar-toggler-icon"></span>
        </button>

        <div class="collapse navbar-collapse" id="navbarSupportedContent">
            <ul class="navbar-nav mr-auto">

                <li class="nav-item">
                    <a class="nav-link" href="lms#/List/Program">
                        All Programs
                    </a>
                </li>

                <li class="nav-item">
                    <a class="nav-link" href="/lms#/Profile">
                        Profile
                    </a>
                </li>
            </ul>
            <ul class="navbar-nav ml-auto">
                <!-- post login tools -->
                <li v-if="isLogin" class="nav-item dropdown logged-in" id="website-post-login" data-label="website-post-login">
                    <a href="#" class="nav-link dropdown-toggle" data-toggle="dropdown" aria-expanded="false">
                        <span class="user-image-wrapper">
                            <span class="avatar avatar-small" :title="fullName">
                                    <span class="avatar-frame" :style="avatarStyle" :title="fullName"></span>
                            </span>
                        </span>
                        <span class="full-name">{{ fullName }}</span>
                        <b class="caret"></b>
                    </a>
                    <ul class="dropdown-menu dropdown-menu-right" role="menu">
                        <a class="dropdown-item" href="/me" rel="nofollow"> My Account </a>
                        <a class="dropdown-item" href="/?cmd=web_logout" rel="nofollow"> Logout </a>
                    </ul>
                </li>

                <li v-else class="nav-item">
                    <a class="nav-link btn-login-area" href="/login">Login</a>
                </li>
            </ul>
        </div>
    </div>
</nav>
</template>
<script>
export default {
    name: "Home",
    data() {
    	return{
            portal: {},
            avatar: frappe.user_image,
            fullName: frappe.full_name,
            isLogin: frappe.is_user_logged_in()
    	}
    },
	mounted() {
        this.getPortalDetails().then(data => this.portal = data);
    },
    methods: {
        getPortalDetails() {
            return lms.call("get_portal_details")
        }
    },
    computed: {
		avatarStyle() {
			return `background-image: url("${this.avatar}")`
        },
        // isLogin() {
        //     return frappe.is_user_logged_in()
        // },
	}
};
</script>
<style scoped>
a {
	text-decoration: none;
}
</style>