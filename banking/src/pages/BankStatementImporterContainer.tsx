import { Breadcrumb, BreadcrumbItem, BreadcrumbLink, BreadcrumbPage, BreadcrumbSeparator, BreadcrumbList } from '@/components/ui/breadcrumb'
import _ from '@/lib/translate'
import { HomeIcon } from 'lucide-react'
import { Link, Outlet } from 'react-router'

const BankStatementImporterContainer = () => {
    return (
        <div className="flex flex-col pt-1.5">
            <div className="flex gap-2 items-baseline p-4">
                <Breadcrumb>
                    <BreadcrumbList>
                        <BreadcrumbItem>
                            <a href="/desk" className="text-ink-gray-7">
                                <HomeIcon size={16} />
                            </a>
                        </BreadcrumbItem>
                        <BreadcrumbSeparator />
                        <BreadcrumbItem>
                            <BreadcrumbLink asChild>
                                <Link to="/">
                                    {_("Banking")}
                                </Link>
                            </BreadcrumbLink>
                        </BreadcrumbItem>
                        <BreadcrumbSeparator />
                        <BreadcrumbItem>
                            <BreadcrumbPage>{_("Import Bank Statement")}</BreadcrumbPage>
                        </BreadcrumbItem>
                    </BreadcrumbList>
                </Breadcrumb>
            </div>
            <Outlet />
        </div>
    )
}

export default BankStatementImporterContainer