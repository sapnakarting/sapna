"""
Predictive Maintenance utility module.
Identifies maintenance needs based on various factors.
"""

from typing import List, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal

from django.db.models import Q
from django.utils import timezone

from fleet.models import Truck, FuelLog, TireInventory, Alert
from reporting.utils.analytics import calculate_fuel_efficiency


class PredictiveMaintenanceEngine:
    """Engine for predicting maintenance needs."""
    
    def __init__(self):
        self.alerts = []
    
    def check_maintenance_needs(self, truck: Truck) -> List[Dict[str, Any]]:
        """Check all maintenance needs for a truck."""
        truck_alerts = []
        
        # Check odometer-based maintenance
        odometer_alerts = self.check_odometer_based_maintenance(truck)
        truck_alerts.extend(odometer_alerts)
        
        # Check document expiry
        document_alerts = self.check_document_expiry(truck)
        truck_alerts.extend(document_alerts)
        
        # Check tire wear
        tire_alerts = self.check_tire_wear(truck)
        truck_alerts.extend(tire_alerts)
        
        # Check fuel efficiency decline
        efficiency_alerts = self.check_fuel_efficiency_decline(truck)
        truck_alerts.extend(efficiency_alerts)
        
        # Check overdue maintenance
        maintenance_alerts = self.check_overdue_maintenance(truck)
        truck_alerts.extend(maintenance_alerts)
        
        return truck_alerts
    
    def check_odometer_based_maintenance(self, truck: Truck) -> List[Dict[str, Any]]:
        """Check for odometer-based maintenance (every 5000km recommended)."""
        alerts = []
        maintenance_interval = 5000  # km
        current_odo = truck.current_odometer
        
        # Calculate maintenance due odometer
        last_maintenance_odo = current_odo - (current_odo % maintenance_interval)
        
        if current_odo >= last_maintenance_odo:
            if current_odo - last_maintenance_odo >= maintenance_interval:
                # Overdue
                priority = 'CRITICAL'
                urgency_days = self.calculate_urgency_days(current_odo, last_maintenance_odo, maintenance_interval)
            else:
                # Due soon
                priority = 'WARNING'
                urgency_days = self.calculate_urgency_days(current_odo, last_maintenance_odo, maintenance_interval)
            
            # Estimate next due date (assuming 200km/day average)
            daily_avg_distance = 200
            days_until = (maintenance_interval - (current_odo % maintenance_interval)) / daily_avg_distance
            
            alerts.append({
                'truck': truck,
                'alert_type': 'ODOMETER_BASED_MAINTENANCE',
                'priority': priority,
                'description': f'Maintenance due at {last_maintenance_odo + maintenance_interval:,} km',
                'current_reading': current_odo,
                'due_at': last_maintenance_odo + maintenance_interval,
                'days_until': max(0, days_until),
                'recommendation': 'Schedule routine maintenance (oil change, filter replacement, inspection)',
                'estimated_cost': '₹2,500 - ₹5,000'
            })
        
        return alerts
    
    def check_document_expiry(self, truck: Truck) -> List[Dict[str, Any]]:
        """Check for document expiry alerts."""
        alerts = []
        today = datetime.now().date()
        
        documents = [
            ('fitness', truck.fitness_expiry, 'Fitness Certificate'),
            ('insurance', truck.insurance_expiry, 'Insurance'),
            ('pucc', truck.pucc_expiry, 'PUCC'),
            ('tax', truck.tax_expiry, 'Tax Certificate'),
            ('permit', truck.permit_expiry, 'Permit')
        ]
        
        for doc_type, expiry_date, doc_name in documents:
            if not expiry_date:
                continue
                
            days_until = (expiry_date - today).days
            
            if days_until < 0:
                # Already expired
                priority = 'CRITICAL'
                urgency = 'EXPIRED'
            elif days_until <= 7:
                priority = 'CRITICAL'
                urgency = 'URGENT'
            elif days_until <= 15:
                priority = 'WARNING'
                urgency = 'SOON'
            elif days_until <= 30:
                priority = 'INFO'
                urgency = 'PLAN'
            else:
                continue
            
            alerts.append({
                'truck': truck,
                'alert_type': 'DOCUMENT_EXPIRY',
                'priority': priority,
                'description': f'{doc_name} expires in {days_until} days',
                'document_type': doc_type,
                'expiry_date': expiry_date,
                'days_until': days_until,
                'recommendation': f'Renew {doc_name} to avoid penalties and ensure compliance',
                'urgency': urgency
            })
        
        return alerts
    
    def check_tire_wear(self, truck: Truck) -> List[Dict[str, Any]]:
        """Check for tire wear and replacement needs."""
        alerts = []
        tires = truck.tires.filter(status__in=['MOUNTED', 'NEW'])
        
        # Check for high mileage tires
        high_mileage_threshold = 50000  # km
        
        for tire in tires:
            current_mileage = tire.calculate_current_mileage()
            
            if current_mileage >= high_mileage_threshold * 1.2:
                priority = 'CRITICAL'
                recommendation = 'Replace tire immediately - safety risk'
            elif current_mileage >= high_mileage_threshold:
                priority = 'WARNING'
                recommendation = 'Schedule tire replacement within 1000km'
            elif current_mileage >= high_mileage_threshold * 0.8:
                priority = 'INFO'
                recommendation = 'Monitor tire wear closely, plan for replacement'
            else:
                continue
            
            alerts.append({
                'truck': truck,
                'alert_type': 'TIRE_WEAR',
                'priority': priority,
                'description': f'Tire {tire.serial_number} has {current_mileage:,} km mileage',
                'tire': tire,
                'current_mileage': current_mileage,
                'recommendation': recommendation,
                'estimated_cost': f'₹{tire.purchase_cost}'
            })
        
        return alerts
    
    def check_fuel_efficiency_decline(self, truck: Truck) -> List[Dict[str, Any]]:
        """Check for significant fuel efficiency decline."""
        alerts = []
        
        # Calculate current efficiency (last 30 days)
        thirty_days_ago = datetime.now() - timedelta(days=30)
        current_eff = calculate_fuel_efficiency(truck=truck, start_date=thirty_days_ago, end_date=datetime.now())
        
        if current_eff['trips'] < 3:  # Need minimum trips for reliable calculation
            return alerts
        
        # Calculate historical efficiency (previous 30 days)
        sixty_days_ago = datetime.now() - timedelta(days=60)
        historical_eff = calculate_fuel_efficiency(truck=truck, start_date=sixty_days_ago, end_date=thirty_days_ago)
        
        if historical_eff['trips'] < 3:
            return alerts
        
        # Check for efficiency decline
        current_efficiency = current_eff['efficiency']
        historical_efficiency = historical_eff['efficiency']
        
        if historical_efficiency > 0:
            decline_percentage = ((historical_efficiency - current_efficiency) / historical_efficiency) * 100
            
            if decline_percentage >= 20:
                priority = 'CRITICAL'
                recommendation = 'Immediate inspection required - possible engine or fuel system issues'
            elif decline_percentage >= 15:
                priority = 'WARNING'
                recommendation = 'Schedule maintenance inspection - possible issues developing'
            elif decline_percentage >= 10:
                priority = 'INFO'
                recommendation = 'Monitor closely - minor efficiency decline detected'
            else:
                return alerts
            
            alerts.append({
                'truck': truck,
                'alert_type': 'FUEL_EFFICIENCY_DECLINE',
                'priority': priority,
                'description': f'Fuel efficiency declined by {decline_percentage:.1f}%',
                'current_efficiency': current_efficiency,
                'historical_efficiency': historical_efficiency,
                'decline_percentage': decline_percentage,
                'recommendation': recommendation
            })
        
        return alerts
    
    def check_overdue_maintenance(self, truck: Truck) -> List[Dict[str, Any]]:
        """Check for any overdue maintenance based on last service."""
        alerts = []
        
        # Check for trucks that haven't had service in a while
        # This would need a maintenance tracking model in the future
        # For now, we'll check if it's been over 90 days since last odometer entry
        last_odo = truck.daily_odos.order_by('-date').first()
        
        if not last_odo:
            return alerts
        
        days_since_last = (datetime.now().date() - last_odo.date).days
        
        if days_since_last > 30:
            priority = 'INFO' if days_since_last > 60 else 'WARNING'
            alerts.append({
                'truck': truck,
                'alert_type': 'OVERDUE_MAINTENANCE',
                'priority': priority,
                'description': f'No odometer entry for {days_since_last} days',
                'last_odo_date': last_odo.date,
                'days_since_last': days_since_last,
                'recommendation': 'Verify vehicle is in service and update odometer readings'
            })
        
        return alerts
    
    def calculate_urgency_days(self, current_odo: int, last_maintenance_odo: int, 
                               maintenance_interval: int) -> int:
        """Calculate urgency in days based on odometer reading."""
        daily_avg_distance = 200  # km/day
        km_overdue = current_odo - last_maintenance_odo
        days_overdue = km_overdue / daily_avg_distance
        return max(0, int(days_overdue))
    
    def generate_maintenance_schedule(self, trucks: List[Truck]) -> List[Dict[str, Any]]:
        """Generate maintenance schedule for all trucks."""
        all_alerts = []
        
        for truck in trucks:
            truck_alerts = self.check_maintenance_needs(truck)
            all_alerts.extend(truck_alerts)
        
        # Sort by priority and urgency
        priority_order = {'CRITICAL': 1, 'WARNING': 2, 'INFO': 3}
        sorted_alerts = sorted(
            all_alerts, 
            key=lambda x: (priority_order.get(x['priority'], 4), x.get('days_until', 999))
        )
        
        return sorted_alerts
    
    def save_alerts_to_database(self, alerts: List[Dict[str, Any]], user=None):
        """Save alerts to the Alert model."""
        saved_alerts = []
        
        for alert_data in alerts:
            # Check if similar alert already exists
            existing_alert = Alert.objects.filter(
                truck=alert_data['truck'],
                alert_type=self.map_alert_type(alert_data['alert_type']),
                status='PENDING'
            ).first()
            
            if existing_alert:
                continue
            
            # Create new alert
            alert = Alert.objects.create(
                title=f"{alert_data['truck'].plate_number}: {alert_data['description']}",
                alert_type=self.map_alert_type(alert_data['alert_type']),
                alert_level=alert_data['priority'],
                description=alert_data.get('recommendation', ''),
                truck=alert_data['truck'],
                metadata={
                    'recommendation': alert_data.get('recommendation'),
                    'estimated_cost': alert_data.get('estimated_cost'),
                    'days_until': alert_data.get('days_until'),
                    'current_mileage': alert_data.get('current_mileage'),
                    'decline_percentage': alert_data.get('decline_percentage')
                }
            )
            
            if user:
                alert.created_by = user
                alert.save()
            
            saved_alerts.append(alert)
        
        return saved_alerts
    
    def map_alert_type(self, alert_type: str) -> str:
        """Map our alert types to the Alert model choices."""
        mapping = {
            'ODOMETER_BASED_MAINTENANCE': Alert.AlertType.GENERAL,
            'DOCUMENT_EXPIRY': Alert.AlertType.DOCUMENT_EXPIRY,
            'TIRE_WEAR': Alert.AlertType.TIRE_COST,
            'FUEL_EFFICIENCY_DECLINE': Alert.AlertType.FUEL_EFFICIENCY,
            'OVERDUE_MAINTENANCE': Alert.AlertType.GENERAL
        }
        return mapping.get(alert_type, Alert.AlertType.GENERAL)


def get_maintenance_summary() -> Dict[str, Any]:
    """Get summary of all maintenance alerts."""
    engine = PredictiveMaintenanceEngine()
    
    # Get all active trucks
    trucks = Truck.objects.filter(status__in=['ACTIVE', 'MAINTENANCE'])
    
    # Generate maintenance schedule
    maintenance_alerts = engine.generate_maintenance_schedule(trucks)
    
    # Count by priority
    priority_counts = {'CRITICAL': 0, 'WARNING': 0, 'INFO': 0}
    alert_type_counts = {
        'ODOMETER_BASED_MAINTENANCE': 0,
        'DOCUMENT_EXPIRY': 0,
        'TIRE_WEAR': 0,
        'FUEL_EFFICIENCY_DECLINE': 0,
        'OVERDUE_MAINTENANCE': 0
    }
    
    for alert in maintenance_alerts:
        priority_counts[alert['priority']] += 1
        alert_type_counts[alert['alert_type']] += 1
    
    return {
        'total_alerts': len(maintenance_alerts),
        'priority_counts': priority_counts,
        'alert_type_counts': alert_type_counts,
        'alerts': maintenance_alerts,
        'trucks_checked': trucks.count()
    }