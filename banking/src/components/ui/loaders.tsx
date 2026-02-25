import { Skeleton } from "./skeleton"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "./table"

export const TableLoader = ({ rows = 10, columns = 5 }: { rows?: number, columns?: number }) => {
    return <Table>
        <TableHeader>
            <TableRow>
                {Array.from({ length: columns }).map((_, index) => (
                    <TableHead key={index}>
                        <Skeleton className="h-4 w-full" />
                    </TableHead>
                ))}
            </TableRow>
        </TableHeader>
        <TableBody>
            {Array.from({ length: rows }).map((_, index) => (
                <TableRow key={index}>
                    {Array.from({ length: columns }).map((_, index) => (
                        <TableCell key={index}>
                            <Skeleton className="h-4 w-full" />
                        </TableCell>
                    ))}
                </TableRow>
            ))}
        </TableBody>
    </Table>
}