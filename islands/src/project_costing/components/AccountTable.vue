<script setup>
import { Badge, Progress } from "frappe-ui";
import { List, ListCell, ListGroup, ListHeader, ListHeaderCell, ListRow } from "frappe-ui/list";

import { ACCOUNT_STATUS, accountMeta } from "../accounts.js";
import { useFormat } from "../format.js";

defineProps({
	accounts: { type: Object, required: true },
});
const emit = defineEmits(["select"]);

const __ = window.__;
const format = useFormat();
const columns = ["minmax(9rem,1.6fr)", "6rem", "6rem", "6rem", "6rem", "minmax(7.5rem,1fr)", "7.5rem"];

const available = (row) => (row.budget ? row.budget.amount - row.actual - row.committed : null);
const used_percent = (row) => ((row.actual + row.committed) * 100) / row.budget.amount;

const amount_class = (value) =>
	value == null ? "text-ink-gray-4" : value < 0 ? "text-ink-red-5" : "text-ink-gray-8";
</script>

<template>
	<div class="-mx-1 overflow-x-auto px-1">
		<div class="min-w-[840px]">
			<List :columns="columns" :row-height="52">
				<ListHeader>
					<ListHeaderCell>{{ __("Account") }}</ListHeaderCell>
					<ListHeaderCell class="justify-end">{{ __("Budget") }}</ListHeaderCell>
					<ListHeaderCell class="justify-end">{{ __("Actual") }}</ListHeaderCell>
					<ListHeaderCell class="justify-end">{{ __("Committed") }}</ListHeaderCell>
					<ListHeaderCell class="justify-end">{{ __("Available") }}</ListHeaderCell>
					<ListHeaderCell class="pl-4">{{ __("Used") }}</ListHeaderCell>
					<ListHeaderCell class="justify-end">{{ __("Status") }}</ListHeaderCell>
				</ListHeader>

				<ListGroup v-if="accounts.expense.length" :label="__('Expense')">
					<ListRow
						v-for="row in accounts.expense"
						:key="row.account"
						@click="emit('select', row.account)"
					>
						<ListCell>
							<div class="min-w-0">
								<p class="truncate text-base text-ink-gray-8">
									{{ row.account_name }}
								</p>
								<p v-if="accountMeta(row)" class="truncate text-xs text-ink-gray-5">
									{{ accountMeta(row) }}
								</p>
							</div>
						</ListCell>
						<ListCell class="justify-end">
							<span class="text-sm tabular-nums" :class="amount_class(row.budget?.amount)">
								{{ format.money(row.budget?.amount) }}
							</span>
						</ListCell>
						<ListCell class="justify-end">
							<span class="text-sm tabular-nums text-ink-gray-8">{{
								format.money(row.actual)
							}}</span>
						</ListCell>
						<ListCell class="justify-end">
							<span class="text-sm tabular-nums text-ink-gray-7">
								{{ row.committed ? format.money(row.committed) : "—" }}
							</span>
						</ListCell>
						<ListCell class="justify-end">
							<span class="text-sm tabular-nums" :class="amount_class(available(row))">
								{{ format.money(available(row)) }}
							</span>
						</ListCell>
						<ListCell>
							<div v-if="row.budget" class="flex w-full items-center gap-2 pl-4">
								<Progress
									class="flex-1"
									:value="Math.min(used_percent(row), 100)"
									size="sm"
								/>
								<span class="w-10 text-right text-sm tabular-nums text-ink-gray-7">
									{{ format.percent(used_percent(row)) }}
								</span>
							</div>
						</ListCell>
						<ListCell class="justify-end">
							<Badge
								:label="ACCOUNT_STATUS[row.status].label"
								:theme="ACCOUNT_STATUS[row.status].theme"
								variant="subtle"
							/>
						</ListCell>
					</ListRow>

					<ListRow>
						<ListCell>
							<span class="text-base-semibold text-ink-gray-9">{{ __("Total expense") }}</span>
						</ListCell>
						<ListCell class="justify-end">
							<span class="text-sm-semibold tabular-nums text-ink-gray-9">
								{{ format.money(accounts.budget) }}
							</span>
						</ListCell>
						<ListCell class="justify-end">
							<span class="text-sm-semibold tabular-nums text-ink-gray-9">
								{{ format.money(accounts.actual) }}
							</span>
						</ListCell>
						<ListCell class="justify-end">
							<span class="text-sm-semibold tabular-nums text-ink-gray-9">
								{{ format.money(accounts.committed) }}
							</span>
						</ListCell>
						<ListCell class="justify-end">
							<span
								class="text-sm-semibold tabular-nums"
								:class="amount_class(accounts.available)"
							>
								{{ format.money(accounts.available) }}
							</span>
						</ListCell>
						<ListCell />
						<ListCell class="justify-end"></ListCell>
					</ListRow>
				</ListGroup>

				<ListGroup v-if="accounts.income.length" :label="__('Income')">
					<ListRow
						v-for="row in accounts.income"
						:key="row.account"
						@click="emit('select', row.account)"
					>
						<ListCell>
							<div class="min-w-0">
								<p class="truncate text-base text-ink-gray-8">
									{{ row.account_name }}
								</p>
								<p v-if="accountMeta(row)" class="truncate text-xs text-ink-gray-5">
									{{ accountMeta(row) }}
								</p>
							</div>
						</ListCell>
						<ListCell class="justify-end">
							<span class="text-sm tabular-nums" :class="amount_class(row.budget?.amount)">
								{{ format.money(row.budget?.amount) }}
							</span>
						</ListCell>
						<ListCell class="justify-end">
							<span class="text-sm tabular-nums text-ink-gray-8">{{
								format.money(row.actual)
							}}</span>
						</ListCell>
						<ListCell class="justify-end"
							><span class="text-sm text-ink-gray-4">—</span></ListCell
						>
						<ListCell class="justify-end">
							<span class="text-sm tabular-nums text-ink-gray-7">
								{{
									row.budget
										? __("{0} to go", [format.money(row.budget.amount - row.actual)])
										: "—"
								}}
							</span>
						</ListCell>
						<ListCell>
							<div v-if="row.budget" class="flex w-full items-center gap-2 pl-4">
								<Progress
									class="flex-1"
									:value="Math.min((row.actual * 100) / row.budget.amount, 100)"
									size="sm"
								/>
								<span class="w-10 text-right text-sm tabular-nums text-ink-gray-7">
									{{ format.percent((row.actual * 100) / row.budget.amount) }}
								</span>
							</div>
						</ListCell>
						<ListCell />
					</ListRow>
				</ListGroup>
			</List>
		</div>
	</div>
</template>
