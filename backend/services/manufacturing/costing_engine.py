"""
Activity-Based Costing (ABC) Engine
Allocates overhead costs to products based on activities and cost drivers

ABC Methodology:
1. Identify activities (setup, machine time, quality inspection, etc.)
2. Assign costs to activity cost pools
3. Determine cost drivers (# of setups, machine hours, # of inspections)
4. Calculate overhead rates per driver unit
5. Allocate costs to products based on driver consumption

Example:
- Setup Activity: Cost Pool = $10,000, Driver = # of setups (100), Rate = $100/setup
- Machine Activity: Cost Pool = $50,000, Driver = machine hours (1000), Rate = $50/hour
- Product A uses 5 setups and 200 machine hours -> Overhead = (5*$100) + (200*$50) = $10,500
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

import models

logger = logging.getLogger(__name__)

class CostingEngine:
    """Activity-Based Costing Engine"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def calculate_bom_cost(self, bom_id: str) -> Dict:
        """
        Calculate total cost for a BOM including materials, labor, and overhead
        """
        bom = self.db.query(models.BillOfMaterials).filter(
            models.BillOfMaterials.id == bom_id
        ).first()
        
        if not bom:
            raise ValueError("BOM not found")
        
        # Material costs
        material_cost = 0.0
        material_details = []
        
        for line in bom.lines:
            component = self.db.query(models.Product).filter(
                models.Product.id == line.component_id
            ).first()
            
            if component:
                unit_cost = component.cost_price or 0.0
                line_cost = unit_cost * line.quantity
                
                # Add scrap cost
                if line.scrap_percentage > 0:
                    scrap_cost = line_cost * (line.scrap_percentage / 100)
                    line_cost += scrap_cost
                
                material_cost += line_cost
                material_details.append({
                    "component": component.name,
                    "quantity": line.quantity,
                    "unit_cost": unit_cost,
                    "scrap_percentage": line.scrap_percentage,
                    "total_cost": line_cost
                })
        
        # Labor costs (from routing)
        labor_cost = 0.0
        labor_details = []
        
        if bom.routing_id:
            routing = self.db.query(models.Routing).filter(
                models.Routing.id == bom.routing_id
            ).first()
            
            if routing:
                for operation in routing.operations:
                    # Labor time in hours
                    setup_hours = operation.setup_time / 60  # Convert minutes to hours
                    run_hours = (operation.run_time_per_unit * bom.quantity_produced) / 60
                    total_hours = setup_hours + run_hours
                    
                    # Labor cost
                    op_labor_cost = total_hours * operation.hourly_rate
                    labor_cost += op_labor_cost
                    
                    labor_details.append({
                        "operation": operation.operation_name,
                        "setup_hours": setup_hours,
                        "run_hours": run_hours,
                        "total_hours": total_hours,
                        "hourly_rate": operation.hourly_rate,
                        "labor_cost": op_labor_cost
                    })
        
        # Overhead allocation
        overhead_cost = self.allocate_overhead_to_bom(bom_id)
        
        # Total costs
        total_cost = material_cost + labor_cost + overhead_cost
        unit_cost = total_cost / bom.quantity_produced if bom.quantity_produced > 0 else 0.0
        
        return {
            "bom_code": bom.bom_code,
            "product_id": bom.product_id,
            "quantity_produced": bom.quantity_produced,
            "material_cost": material_cost,
            "labor_cost": labor_cost,
            "overhead_cost": overhead_cost,
            "total_cost": total_cost,
            "unit_cost": unit_cost,
            "material_details": material_details,
            "labor_details": labor_details
        }
    
    def allocate_overhead_to_bom(self, bom_id: str) -> float:
        """
        Allocate overhead to BOM using activity-based costing
        
        Cost Drivers:
        - Machine hours (from routing run time)
        - Setup count (number of operations with setup time)
        - Labor hours (total labor time)
        - Material value (percentage of material cost)
        """
        bom = self.db.query(models.BillOfMaterials).filter(
            models.BillOfMaterials.id == bom_id
        ).first()
        
        if not bom or not bom.routing_id:
            # No routing, use simple overhead rate (e.g., 50% of labor)
            return 0.0
        
        routing = self.db.query(models.Routing).filter(
            models.Routing.id == bom.routing_id
        ).first()
        
        if not routing:
            return 0.0
        
        total_overhead = 0.0
        
        # Activity 1: Machine time overhead
        total_machine_hours = 0.0
        for operation in routing.operations:
            run_hours = (operation.run_time_per_unit * bom.quantity_produced) / 60
            total_machine_hours += run_hours
            
            # Apply operation-specific overhead rate
            if operation.overhead_rate > 0:
                operation_overhead = run_hours * operation.overhead_rate
                total_overhead += operation_overhead
        
        # Activity 2: Setup overhead
        setup_count = sum(1 for op in routing.operations if op.setup_time > 0)
        setup_overhead_rate = 150.0  # $ per setup (configurable)
        setup_overhead = setup_count * setup_overhead_rate
        total_overhead += setup_overhead
        
        # Activity 3: Quality control overhead
        qc_count = sum(1 for op in routing.operations if op.requires_qc)
        qc_overhead_rate = 75.0  # $ per QC inspection (configurable)
        qc_overhead = qc_count * qc_overhead_rate
        total_overhead += qc_overhead
        
        return total_overhead
    
    def allocate_overhead_to_production_order(
        self,
        production_order_id: str,
        allocation_method: str = "activity_based"
    ) -> Dict:
        """
        Allocate overhead to a production order
        
        Methods:
        - activity_based: ABC allocation based on activities
        - labor_based: Percentage of labor cost
        - machine_based: Based on machine hours
        - unit_based: Fixed rate per unit
        """
        po = self.db.query(models.ProductionOrder).filter(
            models.ProductionOrder.id == production_order_id
        ).first()
        
        if not po:
            raise ValueError("Production order not found")
        
        if allocation_method == "activity_based":
            overhead = self._allocate_overhead_abc(po)
        elif allocation_method == "labor_based":
            # Overhead = labor cost * overhead rate (e.g., 75%)
            overhead_rate = 0.75
            overhead = (po.labor_cost or 0.0) * overhead_rate
        elif allocation_method == "machine_based":
            # Overhead based on machine hours (from routing)
            overhead = self._allocate_overhead_machine_hours(po)
        elif allocation_method == "unit_based":
            # Fixed overhead per unit
            overhead_per_unit = 10.0  # Configurable
            overhead = po.planned_quantity * overhead_per_unit
        else:
            overhead = 0.0
        
        return {
            "production_order": po.po_number,
            "allocation_method": allocation_method,
            "overhead_allocated": overhead
        }
    
    def _allocate_overhead_abc(self, production_order: models.ProductionOrder) -> float:
        """Activity-based costing allocation"""
        if not production_order.routing_id:
            # Fallback to labor-based
            return (production_order.labor_cost or 0.0) * 0.5
        
        routing = self.db.query(models.Routing).filter(
            models.Routing.id == production_order.routing_id
        ).first()
        
        if not routing:
            return 0.0
        
        total_overhead = 0.0
        
        # Machine hours overhead
        for operation in routing.operations:
            run_hours = (operation.run_time_per_unit * production_order.planned_quantity) / 60
            if operation.overhead_rate > 0:
                total_overhead += run_hours * operation.overhead_rate
        
        # Setup overhead
        setup_count = sum(1 for op in routing.operations if op.setup_time > 0)
        total_overhead += setup_count * 150.0  # $150 per setup
        
        # QC overhead
        qc_count = sum(1 for op in routing.operations if op.requires_qc)
        total_overhead += qc_count * 75.0  # $75 per QC
        
        return total_overhead
    
    def _allocate_overhead_machine_hours(self, production_order: models.ProductionOrder) -> float:
        """Machine hours based overhead allocation"""
        if not production_order.routing_id:
            return 0.0
        
        routing = self.db.query(models.Routing).filter(
            models.Routing.id == production_order.routing_id
        ).first()
        
        if not routing:
            return 0.0
        
        # Calculate total machine hours
        total_machine_hours = 0.0
        for operation in routing.operations:
            setup_hours = operation.setup_time / 60
            run_hours = (operation.run_time_per_unit * production_order.planned_quantity) / 60
            total_machine_hours += setup_hours + run_hours
        
        # Overhead rate per machine hour (configurable)
        overhead_rate_per_hour = 45.0  # $/hour
        
        return total_machine_hours * overhead_rate_per_hour
    
    def calculate_production_cost_variance(self, production_order_id: str) -> Dict:
        """
        Calculate variance between standard cost (from BOM) and actual cost
        """
        po = self.db.query(models.ProductionOrder).filter(
            models.ProductionOrder.id == production_order_id
        ).first()
        
        if not po:
            raise ValueError("Production order not found")
        
        if po.status != "completed":
            raise ValueError("Production order not completed yet")
        
        # Actual costs
        actual_material = po.material_cost or 0.0
        actual_labor = po.labor_cost or 0.0
        actual_overhead = po.overhead_cost or 0.0
        actual_total = po.total_cost or 0.0
        
        # Standard costs (from BOM)
        standard_material = 0.0
        standard_labor = 0.0
        standard_overhead = 0.0
        
        if po.bom_id:
            bom_cost = self.calculate_bom_cost(po.bom_id)
            # Adjust for actual quantity produced
            quantity_factor = po.produced_quantity / bom_cost["quantity_produced"] if bom_cost["quantity_produced"] > 0 else 1.0
            
            standard_material = bom_cost["material_cost"] * quantity_factor
            standard_labor = bom_cost["labor_cost"] * quantity_factor
            standard_overhead = bom_cost["overhead_cost"] * quantity_factor
        
        standard_total = standard_material + standard_labor + standard_overhead
        
        # Variances (Favorable if negative, Unfavorable if positive)
        material_variance = actual_material - standard_material
        labor_variance = actual_labor - standard_labor
        overhead_variance = actual_overhead - standard_overhead
        total_variance = actual_total - standard_total
        
        # Variance percentages
        material_variance_pct = (material_variance / standard_material * 100) if standard_material > 0 else 0.0
        labor_variance_pct = (labor_variance / standard_labor * 100) if standard_labor > 0 else 0.0
        overhead_variance_pct = (overhead_variance / standard_overhead * 100) if standard_overhead > 0 else 0.0
        total_variance_pct = (total_variance / standard_total * 100) if standard_total > 0 else 0.0
        
        return {
            "production_order": po.po_number,
            "produced_quantity": po.produced_quantity,
            "actual_costs": {
                "material": actual_material,
                "labor": actual_labor,
                "overhead": actual_overhead,
                "total": actual_total
            },
            "standard_costs": {
                "material": standard_material,
                "labor": standard_labor,
                "overhead": standard_overhead,
                "total": standard_total
            },
            "variances": {
                "material": {
                    "amount": material_variance,
                    "percentage": material_variance_pct,
                    "status": "favorable" if material_variance < 0 else "unfavorable"
                },
                "labor": {
                    "amount": labor_variance,
                    "percentage": labor_variance_pct,
                    "status": "favorable" if labor_variance < 0 else "unfavorable"
                },
                "overhead": {
                    "amount": overhead_variance,
                    "percentage": overhead_variance_pct,
                    "status": "favorable" if overhead_variance < 0 else "unfavorable"
                },
                "total": {
                    "amount": total_variance,
                    "percentage": total_variance_pct,
                    "status": "favorable" if total_variance < 0 else "unfavorable"
                }
            }
        }
    
    def get_cost_driver_analysis(self, company_id: str, period_start: datetime, period_end: datetime) -> Dict:
        """
        Analyze cost drivers across all production orders in a period
        """
        # Get all completed production orders in period
        production_orders = self.db.query(models.ProductionOrder).filter(
            and_(
                models.ProductionOrder.company_id == company_id,
                models.ProductionOrder.status == "completed",
                models.ProductionOrder.actual_end >= period_start,
                models.ProductionOrder.actual_end <= period_end
            )
        ).all()
        
        if not production_orders:
            return {
                "period_start": period_start,
                "period_end": period_end,
                "orders_count": 0,
                "analysis": {}
            }
        
        # Aggregate statistics
        total_units = sum(po.produced_quantity for po in production_orders)
        total_material_cost = sum(po.material_cost or 0.0 for po in production_orders)
        total_labor_cost = sum(po.labor_cost or 0.0 for po in production_orders)
        total_overhead_cost = sum(po.overhead_cost or 0.0 for po in production_orders)
        total_cost = sum(po.total_cost or 0.0 for po in production_orders)
        
        # Average costs
        avg_material_per_unit = total_material_cost / total_units if total_units > 0 else 0.0
        avg_labor_per_unit = total_labor_cost / total_units if total_units > 0 else 0.0
        avg_overhead_per_unit = total_overhead_cost / total_units if total_units > 0 else 0.0
        avg_total_per_unit = total_cost / total_units if total_units > 0 else 0.0
        
        # Cost breakdown
        material_percentage = (total_material_cost / total_cost * 100) if total_cost > 0 else 0.0
        labor_percentage = (total_labor_cost / total_cost * 100) if total_cost > 0 else 0.0
        overhead_percentage = (total_overhead_cost / total_cost * 100) if total_cost > 0 else 0.0
        
        return {
            "period_start": period_start,
            "period_end": period_end,
            "orders_count": len(production_orders),
            "total_units_produced": total_units,
            "total_costs": {
                "material": total_material_cost,
                "labor": total_labor_cost,
                "overhead": total_overhead_cost,
                "total": total_cost
            },
            "average_cost_per_unit": {
                "material": avg_material_per_unit,
                "labor": avg_labor_per_unit,
                "overhead": avg_overhead_per_unit,
                "total": avg_total_per_unit
            },
            "cost_breakdown_percentage": {
                "material": material_percentage,
                "labor": labor_percentage,
                "overhead": overhead_percentage
            }
        }
