<script setup>
import { Button } from "frappe-ui";

// One group of the list as a bordered card: a header that folds it, then its tasks.
defineProps({
	label: { type: String, required: true },
	expanded: { type: Boolean, default: true },
	// the header's "+" adds a task that starts in this group
	can_add: { type: Boolean, default: false },
	has_rows: { type: Boolean, default: false },
});
const emit = defineEmits(["toggle", "add"]);

const __ = window.__;
</script>

<template>
	<section class="overflow-hidden rounded-5 border border-outline-gray-1">
		<div
			class="flex min-w-0 flex-wrap items-center gap-x-4 gap-y-1 px-3 py-2"
			:class="expanded && has_rows && 'border-b border-outline-gray-1'"
		>
			<button
				type="button"
				class="flex min-w-0 items-center gap-1.5 rounded-4 text-left focus-visible:focus-ring"
				:aria-expanded="expanded"
				@click="emit('toggle')"
			>
				<span
					:class="expanded ? 'lucide-chevron-down' : 'lucide-chevron-right'"
					class="size-3.5 shrink-0 text-ink-gray-5"
					aria-hidden="true"
				/>
				<span class="truncate text-base font-medium text-ink-gray-8">{{ label }}</span>
			</button>
			<slot name="meta" />
			<span class="ms-auto flex items-center gap-2">
				<slot name="end" />
				<Button
					v-if="can_add"
					variant="ghost"
					size="sm"
					icon="lucide-plus"
					:aria-label="__('Add task to {0}', [label])"
					@click="emit('add')"
				/>
			</span>
		</div>
		<slot v-if="expanded && has_rows" />
	</section>
</template>
