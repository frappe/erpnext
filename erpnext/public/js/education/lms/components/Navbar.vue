<template>
    <nav class="navbar navbar-expand-lg navbar-light">
        <div class="container">
            <router-link tag="a" :class="'navbar-brand'" :to="{name: 'home'}">
                <span>{{ portal.title }}</span>
            </router-link>
            <button class="navbar-toggler mr-3" type="button" data-toggle="collapse" data-target="#navbarSupportedContent"
                aria-controls="navbarSupportedContent" aria-expanded="false" aria-label="Toggle navigation">
                <span class="navbar-toggler-icon"></span>
            </button>

            <div class="collapse navbar-collapse mx-3" id="navbarSupportedContent">
                <ul class="navbar-nav mr-auto">
                </ul>
                <ul class="navbar-nav ml-auto justify-content-end">
                    <!-- post login tools -->
                    <li class="nav-item dropdown hide" id="website-post-login" data-label="website-post-login" style="display: none">


                    <li v-if="isLogin" class="nav-item dropdown" id="website-post-login" data-label="website-post-login"
                        style="">
                        <a href="#" class="nav-link dropdown-toggle" data-toggle="dropdown">
                            <span class="user-image-wrapper"><span class="avatar avatar-small" :title="fullName">
                                    <span class="avatar-frame" :style="avatarStyle"
                                        :title="fullName"></span>
                                </span></span>
                            <span class="full-name">{{ fullName }}</span>
                            <b class="caret"></b>
                        </a>
                        <div class="dropdown-menu" role="menu">
                            <router-link tag="a" :class="'dropdown-item'" :to="{name: 'profile'}">
                                My Profile
                            </router-link>
                            <router-link tag="a" :class="'dropdown-item'" :to="{name: 'logout'}">
                                Logout
                            </router-link>
                        </div>
                    </li>
                    <li v-else class="nav-item">
                        <router-link tag="a" :class="'nav-link'" :to="{name: 'login'}">
                            Login
                        </router-link>
                    </li>

                    <li class="nav-item btn-login-area" style="display: none;"><a class="nav-link" href="/login">Login</a></li>
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
            avatar: frappe.get_cookie("user_image"),
            fullName: frappe.get_cookie("full_name"),
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