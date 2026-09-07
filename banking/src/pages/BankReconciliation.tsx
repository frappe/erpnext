import BankBalance from "@/components/features/BankReconciliation/BankBalance"
import BankPicker from "@/components/features/BankReconciliation/BankPicker"
import BankRecDateFilter from "@/components/features/BankReconciliation/BankRecDateFilter"
import BankTransactionUnreconcileModal from "@/components/features/BankReconciliation/BankTransactionUnreconcileModal"
import CompanySelector from "@/components/features/BankReconciliation/CompanySelector"
import MatchAndReconcile from "@/components/features/BankReconciliation/MatchAndReconcile"
import Settings from "@/components/features/Settings/Settings"
import ActionLog from "@/components/features/ActionLog/ActionLog"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { TooltipProvider } from "@/components/ui/tooltip"
import _ from "@/lib/translate"
import { lazy, Suspense } from "react"
import { AlertTriangleIcon, CheckCircleIcon, HomeIcon, LandmarkIcon, ListIcon, Loader2Icon, ScrollTextIcon, ShuffleIcon } from "lucide-react"
import { Breadcrumb, BreadcrumbItem, BreadcrumbList, BreadcrumbPage, BreadcrumbSeparator } from "@/components/ui/breadcrumb"
import { Empty, EmptyContent, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty"
import { Button } from "@/components/ui/button"
import { useAtomValue } from "jotai"
import { selectedBankAccountAtom } from "@/components/features/BankReconciliation/bankRecAtoms"

const BankReconciliationStatement = lazy(() => import('@/components/features/BankReconciliation/BankReconciliationStatement'))
const BankTransactions = lazy(() => import('@/components/features/BankReconciliation/BankTransactionList'))
const BankClearanceSummary = lazy(() => import('@/components/features/BankReconciliation/BankClearanceSummary'))
const IncorrectlyClearedEntries = lazy(() => import('@/components/features/BankReconciliation/IncorrectlyClearedEntries'))

const BankReconciliation = () => {

    return (
        <div>
            {/* The page owns the viewport height and the tabs/lists below fill what's left, so
                the virtualizers size themselves from layout instead of a measured pixel value. */}
            <div className="p-4 flex-col gap-4 md:flex hidden h-dvh">
                <div className="flex flex-col gap-4 shrink-0">
                    <div className="flex justify-between">
                        <div className="flex items-center gap-6">
                            <Breadcrumb>
                                <BreadcrumbList>
                                    <BreadcrumbItem>
                                        <a href="/desk" className="text-ink-gray-7">
                                            <HomeIcon size={16} />
                                        </a>
                                    </BreadcrumbItem>
                                    <BreadcrumbSeparator />
                                    <BreadcrumbItem>
                                        <BreadcrumbPage>
                                            <div className="flex gap-1 items-center">
                                                {_("Banking")}
                                            </div>

                                        </BreadcrumbPage>
                                    </BreadcrumbItem>
                                </BreadcrumbList>
                            </Breadcrumb>
                            <CompanySelector />
                        </div>
                        <div className="flex items-center gap-2">
                            <TooltipProvider>
                                <Settings />
                                <ActionLog />
                            </TooltipProvider>
                            <BankRecDateFilter />
                        </div>
                    </div>
                    <BankPicker />
                    <BankBalance />
                </div>
                <BankRecTabs />
                <BankTransactionUnreconcileModal />
            </div>
            <div className="md:hidden flex h-screen items-center justify-between">
                <Empty>
                    <EmptyMedia>
                        <LandmarkIcon />
                    </EmptyMedia>
                    <EmptyHeader>
                        <EmptyTitle>
                            {_("Banking")}
                        </EmptyTitle>
                        <EmptyDescription>
                            {_("This screen is not supported on mobile devices.")}
                        </EmptyDescription>
                    </EmptyHeader>
                    <EmptyContent>
                        <Button asChild>
                            <a href="/desk">
                                {_("Go to Desktop")}
                            </a>
                        </Button>
                    </EmptyContent>
                </Empty>

            </div>
        </div>
    )
}

const BankRecTabs = () => {
    const selectedBankAccount = useAtomValue(selectedBankAccountAtom)

    if (!selectedBankAccount) {
        return null
    }

    return <Tabs defaultValue="Match and Reconcile" className="min-h-0 flex-1">
        <TabsList className="shrink-0">
            <TabsTrigger value="Match and Reconcile"><ShuffleIcon /> {_("Match and Reconcile")}</TabsTrigger>
            <TabsTrigger value="Bank Reconciliation Statement"><ScrollTextIcon /> {_("Bank Reconciliation Statement")}</TabsTrigger>
            <TabsTrigger value="Bank Transactions"><ListIcon />{_("Bank Transactions")}</TabsTrigger>
            <TabsTrigger value="Bank Clearance Summary"><CheckCircleIcon />{_("Bank Clearance Summary")}</TabsTrigger>
            <TabsTrigger value="Incorrectly Cleared Entries"><AlertTriangleIcon /> {_("Incorrectly Cleared Entries")}</TabsTrigger>
        </TabsList>
        <TabsContent value="Match and Reconcile" className="flex min-h-0 flex-col">
            <MatchAndReconcile />
        </TabsContent>
        <Suspense fallback={
            <div className="flex items-center justify-center p-16">
                <Loader2Icon className="size-6 animate-spin text-muted-foreground" />
            </div>
        }>
            <TabsContent value="Bank Reconciliation Statement" className="flex min-h-0 flex-col">
                <BankReconciliationStatement />
            </TabsContent>
            <TabsContent value="Bank Transactions" className="flex min-h-0 flex-col">
                <BankTransactions />
            </TabsContent>
            <TabsContent value="Bank Clearance Summary" className="flex min-h-0 flex-col">
                <BankClearanceSummary />
            </TabsContent>
            <TabsContent value="Incorrectly Cleared Entries" className="flex min-h-0 flex-col">
                <IncorrectlyClearedEntries />
            </TabsContent>
        </Suspense>
    </Tabs>
}

export default BankReconciliation