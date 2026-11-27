<script setup>
import { computed, ref } from "vue";
import { Button, Dialog, Tooltip } from "frappe-ui";
import { BarChart, ChartCard } from "frappe-ui/charts";

import AccountTable from "./AccountTable.vue";
import { useFormat } from "../format.js";

const props = defineProps({
	accounts: { type: Object, required: true },
	closed: { type: Boolean, default: false },
});
const emit = defineEmits(["add-budget"]);

const __ = window.__;
const format = useFormat();
const show_table = ref(false);

/**
 * One bar per expense account: actual, then committed, then what is left of its budget, so a
 * budgeted bar is as long as its budget, less what its earlier fiscal years spent. An account past
 * its budget has nothing left and runs longer; one without a budget is actual and committed only.
 */
const rows = computed(() =>
	props.accounts.expense.map((row) => ({
		label: row.account_name,
		actual: row.actual,
		committed: row.committed,
		left: row.budget ? Math.max(row.budget.available, 0) : 0,
	}))
);
const series = computed(() => [
	"actual",
	...(props.accounts.committed ? ["committed"] : []),
	...(props.accounts.budget_count ? ["left"] : []),
]);
const series_config = {
	actual: { label: __("Spent") },
	committed: { label: __("Committed") },
	left: { label: __("Budget left") },
};
// With no budget there is nothing to compare against, so the card is about spend, and says so.
const title = computed(() =>
	props.accounts.budget_count ? __("Budget vs spend by account") : __("Spend by account")
);

const can_add = computed(() => props.accounts.access.manage_budgets && !props.closed);
</script>

<template>
	<ChartCard class="h-80">
		<BarChart
			:title="title"
			:subtitle="accounts.fiscal_year"
			:data="rows"
			x="label"
			:y="series"
			:series-config="series_config"
			:y-axis="{ format: format.short, min: 0 }"
			horizontal
			stacked
		>
			<template #actions>
				<div class="flex items-center gap-2">
					<Button
						v-if="can_add"
						size="sm"
						icon-left="lucide-plus"
						:label="__('Add budget')"
						@click="emit('add-budget')"
					/>
					<Tooltip :text="__('View as table')">
						<Button
							size="sm"
							variant="ghost"
							icon="lucide-table"
							:aria-label="__('View as table')"
							@click="show_table = true"
						/>
					</Tooltip>
				</div>
			</template>
		</BarChart>

		<Dialog v-model:open="show_table" :title="__('{0} · {1}', [title, accounts.fiscal_year])" size="4xl">
			<AccountTable :accounts="accounts" />
		</Dialog>
	</ChartCard>
</template>
