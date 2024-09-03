import React, { useState, useEffect } from 'react';
import { useHistory } from 'react-router-dom';
import { Button } from "@/components/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import api from '../utils/api';

interface WorkOrder {
  id: string;
  production_item: string;
  qty: number;
  planned_start_date: string;
  status: string;
}

export function WorkOrderList() {
  const [workOrders, setWorkOrders] = useState<WorkOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const history = useHistory();

  useEffect(() => {
    fetchWorkOrders();
  }, []);

  const fetchWorkOrders = async () => {
    try {
      const response = await api.get('/manufacturing/work-orders');
      setWorkOrders(response.data);
    } catch (error) {
      setError('Failed to fetch work orders. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div>Loading...</div>;
  if (error) return <div>{error}</div>;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Work Orders</CardTitle>
        <Button onClick={() => history.push('/manufacturing/work-orders/new')}>Create New Work Order</Button>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Production Item</TableHead>
              <TableHead>Quantity</TableHead>
              <TableHead>Planned Start Date</TableHead>
              <TableHead>Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {workOrders.map((workOrder) => (
              <TableRow key={workOrder.id}>
                <TableCell>{workOrder.production_item}</TableCell>
                <TableCell>{workOrder.qty}</TableCell>
                <TableCell>{new Date(workOrder.planned_start_date).toLocaleDateString()}</TableCell>
                <TableCell>{workOrder.status}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}