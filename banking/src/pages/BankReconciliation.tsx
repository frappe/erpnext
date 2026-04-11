import BankBalance from "@/components/features/BankReconciliation/BankBalance"
import BankClearanceSummary from "@/components/features/BankReconciliation/BankClearanceSummary"
import BankPicker from "@/components/features/BankReconciliation/BankPicker"
import BankRecDateFilter from "@/components/features/BankReconciliation/BankRecDateFilter"
import BankReconciliationStatement from "@/components/features/BankReconciliation/BankReconciliationStatement"
import BankTransactions from "@/components/features/BankReconciliation/BankTransactionList"
import BankTransactionUnreconcileModal from "@/components/features/BankReconciliation/BankTransactionUnreconcileModal"
import CompanySelector from "@/components/features/BankReconciliation/CompanySelector"
import IncorrectlyClearedEntries from "@/components/features/BankReconciliation/IncorrectlyClearedEntries"
import MatchAndReconcile from "@/components/features/BankReconciliation/MatchAndReconcile"
import RuleConfigureButton from "@/components/features/BankReconciliation/Rules/RuleConfigureButton"
import Settings from "@/components/features/Settings/Settings"
import ActionLog from "@/components/features/ActionLog/ActionLog"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { TooltipProvider } from "@/components/ui/tooltip"
import _ from "@/lib/translate"
import { useLayoutEffect, useRef, useState } from "react"
import { AlertTriangleIcon, CheckCircleIcon, HomeIcon, ListIcon, ScrollTextIcon, ShuffleIcon } from "lucide-react"
import { Breadcrumb, BreadcrumbItem, BreadcrumbList, BreadcrumbPage, BreadcrumbSeparator } from "@/components/ui/breadcrumb"
import { Badge } from "@/components/ui/badge"


const BankReconciliation = () => {

    const [headerHeight, setHeaderHeight] = useState(0)

    const ref = useRef<HTMLDivElement>(null)

    useLayoutEffect(() => {
        if (ref.current) {
            setHeaderHeight(ref.current.clientHeight)
        }
    }, [])

    const remainingHeightAfterTabs = window.innerHeight - headerHeight - 290

    return (
        <div className="p-4 flex flex-col gap-4">
            <div ref={ref} className="flex flex-col gap-4">
                <div className="flex justify-between">
                    <div className="flex items-center gap-6">
                        <Breadcrumb>
                            <BreadcrumbList>
                                <BreadcrumbItem>
                                    <a href="/desk" className="text-ink-gray-7">
                                        <HomeIcon size={16} strokeWidth={1.5} />
                                    </a>
                                </BreadcrumbItem>
                                <BreadcrumbSeparator />
                                <BreadcrumbItem>
                                    <BreadcrumbPage>
                                        <div className="flex gap-1 items-center">
                                            {_("Banking")} <Badge theme="violet" variant="subtle">{_("Beta")}</Badge>
                                        </div>

                                    </BreadcrumbPage>
                                </BreadcrumbItem>
                            </BreadcrumbList>
                        </Breadcrumb>
                        <CompanySelector />
                    </div>
                    <div className="flex items-center gap-2">
                        <TooltipProvider>
                            <RuleConfigureButton />
                            <Settings />
                            <ActionLog />
                        </TooltipProvider>
                        <BankRecDateFilter />
                    </div>
                </div>
                <BankPicker size="sm" />
                <BankBalance />
            </div>
            <Tabs defaultValue="Match and Reconcile">
                <TabsList>
                    <TabsTrigger value="Match and Reconcile"><ShuffleIcon /> {_("Match and Reconcile")}</TabsTrigger>
                    <TabsTrigger value="Bank Reconciliation Statement"><ScrollTextIcon /> {_("Bank Reconciliation Statement")}</TabsTrigger>
                    <TabsTrigger value="Bank Transactions"><ListIcon />{_("Bank Transactions")}</TabsTrigger>
                    <TabsTrigger value="Bank Clearance Summary"><CheckCircleIcon />{_("Bank Clearance Summary")}</TabsTrigger>
                    <TabsTrigger value="Incorrectly Cleared Entries"><AlertTriangleIcon /> {_("Incorrectly Cleared Entries")}</TabsTrigger>
                </TabsList>
                <TabsContent value="Match and Reconcile">
                    <MatchAndReconcile contentHeight={remainingHeightAfterTabs} />
                </TabsContent>
                <TabsContent value="Bank Reconciliation Statement">
                    <BankReconciliationStatement />
                </TabsContent>
                <TabsContent value="Bank Transactions">
                    <BankTransactions />
                </TabsContent>
                <TabsContent value="Bank Clearance Summary">
                    <BankClearanceSummary />
                </TabsContent>
                <TabsContent value="Incorrectly Cleared Entries">
                    <IncorrectlyClearedEntries />
                </TabsContent>
            </Tabs>

            <BankTransactionUnreconcileModal />
        </div>
    )
}

export default BankReconciliation