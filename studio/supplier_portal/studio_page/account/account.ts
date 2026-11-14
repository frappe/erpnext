/** My account: the signed-in user's own name and phone numbers, and their password. */

import { computed, ref, watch } from "vue"
import { call, toast } from "frappe-ui"
import { readableError } from "@app/utils"
import { usePortalNotifications } from "@app/composables/useNotifications"
import { usePortalIdentity } from "@app/composables/usePortalIdentity"
import { useSession } from "@app/composables/useSession"
import { __ } from "@app/lib/translate"

const METHODS = "erpnext.portal.portal_account"

export default function setup(context) {
	const account = computed<any>(() => context.account?.data ?? null)
	const loaded = computed(() => Boolean(account.value))
	const loadFailed = computed(() => Boolean(context.account?.error) && !loaded.value)

	// ---------------------------------------------------------------- profile
	// the controls bind to these by name, so each needs its own ref
	const firstName = ref("")
	const lastName = ref("")
	const phone = ref("")
	const mobile = ref("")
	const email = computed(() => account.value?.email ?? "")

	/** What was last saved: the form starts from it, and Save is offered only when something differs. */
	const saved = ref({ first_name: "", last_name: "", phone: "", mobile_no: "" })
	function fill(values: any) {
		saved.value = {
			first_name: values?.first_name ?? "",
			last_name: values?.last_name ?? "",
			phone: values?.phone ?? "",
			mobile_no: values?.mobile_no ?? "",
		}
		firstName.value = saved.value.first_name
		lastName.value = saved.value.last_name
		phone.value = saved.value.phone
		mobile.value = saved.value.mobile_no
	}
	// the first answer fills the form; a later reload must not overwrite what is being typed
	let filled = false
	watch(
		account,
		(values) => {
			if (!values || filled) return
			filled = true
			fill(values)
		},
		{ immediate: true },
	)

	const typed = computed(() => ({
		first_name: firstName.value.trim(),
		last_name: lastName.value.trim(),
		phone: phone.value.trim(),
		mobile_no: mobile.value.trim(),
	}))
	const profileChanged = computed(() => JSON.stringify(typed.value) !== JSON.stringify(saved.value))
	const savingProfile = ref(false)
	const profileError = ref("")

	async function saveProfile() {
		if (savingProfile.value || !profileChanged.value) return
		savingProfile.value = true
		profileError.value = ""
		try {
			fill(await call(`${METHODS}.update_account`, typed.value))
			toast.success(__("Your details are saved."))
		} catch (error: any) {
			profileError.value = readableError(error)
		} finally {
			savingProfile.value = false
		}
	}

	// ---------------------------------------------------------------- password
	const currentPassword = ref("")
	const newPassword = ref("")
	const confirmPassword = ref("")
	const signOutElsewhere = ref(true)
	const changingPassword = ref(false)
	const passwordError = ref("")

	/** Said under the fields as soon as it applies, rather than after a round trip. */
	const passwordHint = computed(() => {
		if (confirmPassword.value && newPassword.value !== confirmPassword.value) return __("The new passwords do not match.")
		return ""
	})
	const canChangePassword = computed(
		() => Boolean(currentPassword.value && newPassword.value && newPassword.value === confirmPassword.value),
	)

	async function changePassword() {
		if (changingPassword.value || !canChangePassword.value) return
		changingPassword.value = true
		passwordError.value = ""
		try {
			await call(`${METHODS}.change_password`, {
				old_password: currentPassword.value,
				new_password: newPassword.value,
				logout_other_sessions: signOutElsewhere.value ? 1 : 0,
			})
			currentPassword.value = newPassword.value = confirmPassword.value = ""
			toast.success(__("Your password is changed."))
		} catch (error: any) {
			// the site's password policy explains itself; a wrong current password says so
			passwordError.value = readableError(error)
		} finally {
			changingPassword.value = false
		}
	}

	// ---------------------------------------------------------------- sidebar
	const { companyName, companyLogo } = usePortalIdentity(() => "")
	const { user } = useSession()

	return {
		...usePortalNotifications(context),
		companyName, companyLogo, user,
		loaded, loadFailed, email,
		firstName, lastName, phone, mobile, profileChanged, savingProfile, profileError, saveProfile,
		currentPassword, newPassword, confirmPassword, signOutElsewhere,
		changingPassword, passwordError, passwordHint, canChangePassword, changePassword,
	}
}
