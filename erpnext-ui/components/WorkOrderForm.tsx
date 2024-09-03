import React, { useState } from 'react';
import { useForm, useFieldArray } from 'react-hook-form';
import { useHistory } from 'react-router-dom';
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { DatePicker } from "@/components/ui/date-picker"
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from "@/components/ui/card"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import api from '../utils/api';
import { uploadFile } from '../utils/fileUpload';

interface WorkOrderFormData {
  production_item: string;
  qty: number;
  planned_start_date: Date;
  operations: Array<{ operation: string; workstation: string; time_in_mins: number }>;
  attachment?: File;
}

export function WorkOrderForm() {
  const { register, control, handleSubmit, formState: { errors } } = useForm<WorkOrderFormData>();
  const { fields, append, remove } = useFieldArray({
    control,
    name: "operations"
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const history = useHistory();

  const onSubmit = async (data: WorkOrderFormData) => {
    setLoading(true);
    setError(null);
    setSuccess(false);
    try {
      let attachmentUrl = null;
      if (data.attachment) {
        const fileName = `work_orders/${Date.now()}_${data.attachment.name}`;
        attachmentUrl = await uploadFile(data.attachment, 'work_orders', fileName);
      }

      const workOrderData = {
        ...data,
        attachment_url: attachmentUrl
      };

      await api.post('/manufacturing/work-orders/', workOrderData);
      setSuccess(true);
      setTimeout(() => history.push('/manufacturing/work-orders'), 2000);
    } catch (error) {
      setError('Failed to create work order. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Create Work Order</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)}>
          <Input 
            {...register('production_item', { required: 'Production Item is required' })} 
            placeholder="Production Item" 
            className="mb-2" 
          />
          {errors.production_item && <p className="text-red-500">{errors.production_item.message}</p>}
          
          <Input 
            {...register('qty', { 
              required: 'Quantity is required', 
              min: { value: 1, message: 'Quantity must be at least 1' } 
            })} 
            type="number" 
            placeholder="Quantity" 
            className="mb-2" 
          />
          {errors.qty && <p className="text-red-500">{errors.qty.message}</p>}
          
          <DatePicker 
            {...register('planned_start_date', { required: 'Planned Start Date is required' })} 
            className="mb-2" 
          />
          {errors.planned_start_date && <p className="text-red-500">{errors.planned_start_date.message}</p>}
          
          {fields.map((field, index) => (
            <div key={field.id} className="mb-2">
              <Input 
                {...register(`operations.${index}.operation`, { required: 'Operation is required' })} 
                placeholder="Operation" 
                className="mb-2" 
              />
              <Input 
                {...register(`operations.${index}.workstation`, { required: 'Workstation is required' })} 
                placeholder="Workstation" 
                className="mb-2" 
              />
              <Input 
                {...register(`operations.${index}.time_in_mins`, { 
                  required: 'Time is required', 
                  min: { value: 1, message: 'Time must be at least 1 minute' } 
                })} 
                type="number" 
                placeholder="Time (minutes)" 
                className="mb-2" 
              />
              <Button type="button" onClick={() => remove(index)}>Remove Operation</Button>
            </div>
          ))}
          
          <Button type="button" onClick={() => append({ operation: '', workstation: '', time_in_mins: 0 })} className="mb-2">
            Add Operation
          </Button>
          
          <Input 
            type="file"
            {...register('attachment')} 
            className="mb-2" 
          />
          
          {error && <Alert variant="destructive"><AlertTitle>Error</AlertTitle><AlertDescription>{error}</AlertDescription></Alert>}
          {success && <Alert><AlertTitle>Success</AlertTitle><AlertDescription>Work Order created successfully!</AlertDescription></Alert>}
          
          <Button type="submit" disabled={loading}>
            {loading ? 'Creating...' : 'Create Work Order'}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}