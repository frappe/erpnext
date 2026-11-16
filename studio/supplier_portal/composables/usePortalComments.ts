/** A detail page's comment thread with the buyer: the published comments, and posting one. */

import { computed, nextTick, ref } from "vue"
import { call, toast } from "frappe-ui"
import { readableError } from "@app/utils"
import { __ } from "@app/lib/translate"

/** `key` is the page's route parameter; the thread comes from its `comments` resource. */
export function usePortalComments(context: any, doctype: string, key: string, name: () => string) {
	// until this link's thread arrives, the resource still holds the one opened before
	const comments = computed(() =>
		(context.comments?.data ?? [])
			.filter((c: any) => c.thread === context.route?.params?.[key])
			.map((c: any) => ({
				type: "comment",
				key: `comment:${c.name}`,
				timestamp: c.creation,
				author: { fullname: c.comment_by || c.comment_email, email: c.comment_email },
				data: { name: c.name, content: c.content, attachments: c.attachments ?? [] },
			})),
	)

	const posting = ref(false)
	// the composer only empties by remounting, so a sent comment hides it for one tick
	const clearing = ref(false)

	/** CommentComposer emits { body, attachments }; attachments are not wired. */
	async function postComment(payload: any) {
		const body = (payload?.body ?? "").trim()
		if (!body || posting.value) return
		posting.value = true
		try {
			await call("erpnext.portal.supplier_portal.add_portal_comment", { doctype, name: name(), content: body })
		} catch (error) {
			// the draft stays in the box, so the supplier can send it again
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

	return { comments, postComment, posting, clearing }
}
