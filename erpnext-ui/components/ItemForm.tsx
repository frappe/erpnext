import React from 'react';
import { useForm } from 'react-hook-form';
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import api from '../utils/api';

interface ItemFormData {
  item_code: string;
  item_name: string;
  item_group: string;
  stock_uom: string;
  is_stock_item: boolean;
  description?: string;
}

export function ItemForm() {
  const { register, handleSubmit, formState: { errors } } = useForm<ItemFormData>();

  const onSubmit = async (data: ItemFormData) => {
    try {
      const response = await api.post('/items/', data);
      // Handle successful item creation
      console.log('Item created:', response.data);
    } catch (error) {
      // Handle error
      console.error('Error creating item:', error);
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <Input {...register('item_code', { required: true })} placeholder="Item Code" />
      <Input {...register('item_name', { required: true })} placeholder="Item Name" />
      <Input {...register('item_group', { required: true })} placeholder="Item Group" />
      <Input {...register('stock_uom', { required: true })} placeholder="Stock UOM" />
      <Input {...register('description')} placeholder="Description" />
      <Button type="submit">Create Item</Button>
    </form>
  );
}