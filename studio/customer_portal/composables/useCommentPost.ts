/** Posting a comment from a detail page's CommentComposer, shared by every document page. */

import { nextTick, ref } from "vue"
import { call, toast } from "frappe-ui"
import { readableError } from "@app/utils"
import { __ } from "@app/lib/translate"

export function useCommentPost(context: any, doctype: string, name: () => string) {
	const posting = ref(false)
	// the composer only empties by remounting, so a sent comment hides it for one tick
	const clearing = ref(false)

	/** CommentComposer emits { body, attachments }; attachments are not wired. */
	async function postComment(payload: any) {
		const body = (payload?.body ?? "").trim()
		if (!body || posting.value) return
		posting.value = true
		try {
			await call("erpnext.portal.customer_portal.add_portal_comment", {
				doctype,
				name: name(),
				content: body,
			})
		} catch (error) {
			// the draft stays in the box, so the customer can send it again
			toast.error(readableError(error, __("Could not post your comment. Please try again.")))
			return
		} finally {
			posting.value = false
		}
		clearing.value = true
		await nextTick()
		clearing.value = false
		await context.comments?.reload()
	}

	return { postComment, posting, clearing }
}
