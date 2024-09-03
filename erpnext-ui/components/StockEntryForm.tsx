import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select } from "@/components/ui/select"
import { DatePicker } from "@/components/ui/date-picker"
import api from '../utils/api';

interface StockEntryFormData {
  posting_date: Date;
  company: string;
  purpose: string;
  items: Array<{ item_code: string; qty: number; basic_rate: number }>;
}

export function StockEntryForm() {
  const { register, handleSubmit, formState: { errors } } = useForm<StockEntryFormData>();
  const [items, setItems] = useState([{ item_code: '', qty: 0, basic_rate: 0 }]);

  const onSubmit = async (data: StockEntryFormData) => {
    try {
      const response = await api.post('/stock-entries/', data);
      // Handle successful stock entry creation
      console.log('Stock Entry created:', response.data);
    } catch (error) {
      // Handle error
      console.error('Error creating stock entry:', error);
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <DatePicker {...register('posting_date', { required: true })} />
      <Input {...register('company', { required: true })} placeholder="Company" />
      <Select {...register('purpose', { required: true })}>
        <option value="Material Receipt">Material Receipt</option>
        <option value="Material Issue">Material Issue</option>
        <option value="Material Transfer">Material Transfer</option>
      </Select>
      {items.map((item, index) => (
        <div key={index}>
          <Input {...register(`items.${index}.item_code`, { required: true })} placeholder="Item Code" />
          <Input {...register(`items.${index}.qty`, { required: true, min: 0 })} type="number" placeholder="Quantity" />
          <Input {...register(`items.${index}.basic_rate`, { required: true, min: 0 })} type="number" placeholder="Basic Rate" />
        </div>
      ))}
      <Button type="button" onClick={() => setItems([...items, { item_code: '', qty: 0, basic_rate: 0 }])}>
        Add Item
      </Button>
      <Button type="submit">Submit</Button>
    </form>
  );
}