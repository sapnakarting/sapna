"""
Gemini AI Integration Module for SAPNA CARTING Fleet Management System.

This module provides AI-powered features including:
- Fuel efficiency insights
- Anomaly detection
- Maintenance recommendations
- OCR processing for mining chalans
"""

import json
import os
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal
from dataclasses import dataclass

from django.conf import settings
from django.db.models import Sum, Avg, Count
from django.utils import timezone

import google.generativeai as genai

from fleet.models import Truck, Driver, FuelLog, TireInventory, DailyOdoRegistry, Alert
from operations.models import MiningLog, CoalLog
from reporting.utils.analytics import calculate_fuel_efficiency, get_fleet_average_efficiency


class GeminiAIError(Exception):
    """Custom exception for Gemini AI errors."""
    pass


@dataclass
class FuelEfficiencyInsight:
    """Data class for fuel efficiency insights."""
    truck_id: int
    truck_plate: str
    current_efficiency: float
    fleet_average: float
    performance_rating: str
    insights: List[str]
    recommendations: List[str]
    potential_savings: Dict[str, Any]
    generated_at: datetime


@dataclass
class AnomalyDetectionResult:
    """Data class for anomaly detection results."""
    truck_id: int
    truck_plate: str
    anomaly_type: str
    severity: str
    description: str
    detected_value: float
    expected_range: Dict[str, float]
    recommended_action: str
    detected_at: datetime


@dataclass
class MaintenanceRecommendation:
    """Data class for maintenance recommendations."""
    truck_id: int
    truck_plate: str
    priority: str
    maintenance_type: str
    description: str
    estimated_cost: float
    estimated_downtime: str
    recommended_date: datetime
    rationale: str
    generated_at: datetime


@dataclass
class OCRResult:
    """Data class for OCR processing results."""
    success: bool
    chalan_no: Optional[str]
    date: Optional[str]
    customer_name: Optional[str]
    net_weight: Optional[float]
    material: Optional[str]
    confidence_score: float
    raw_text: str
    processed_at: datetime
    errors: List[str]


class GeminiAIService:
    """Service class for Gemini AI operations."""
    
    def __init__(self):
        self.api_key = getattr(settings, 'GEMINI_API_KEY', None)
        if not self.api_key:
            raise GeminiAIError("GEMINI_API_KEY not configured in settings")
        
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
    
    def _generate_content(self, prompt: str, temperature: float = 0.3) -> str:
        """Generate content using Gemini AI."""
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=2048
                )
            )
            return response.text
        except Exception as e:
            raise GeminiAIError(f"Gemini AI generation failed: {str(e)}")
    
    def generate_fuel_efficiency_insights(self, truck: Truck, days: int = 30) -> FuelEfficiencyInsight:
        """Generate AI-powered fuel efficiency insights for a truck."""
        # Get fuel data
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        fuel_data = calculate_fuel_efficiency(truck=truck, start_date=start_date, end_date=end_date)
        fleet_avg = get_fleet_average_efficiency(start_date=start_date, end_date=end_date)
        
        # Build context for AI
        fuel_logs = FuelLog.objects.filter(
            truck=truck,
            date__gte=start_date.date(),
            date__lte=end_date.date()
        ).order_by('-date')
        
        fuel_log_data = []
        for log in fuel_logs[:20]:  # Last 20 entries
            fuel_log_data.append({
                'date': log.date.isoformat(),
                'liters': float(log.fuel_liters),
                'odometer': log.odometer,
                'distance': log.odometer - log.previous_odometer if log.previous_odometer else 0,
                'efficiency': (log.odometer - log.previous_odometer) / float(log.fuel_liters) 
                    if log.previous_odometer and log.fuel_liters else 0
            })
        
        prompt = f"""
        Analyze the following fuel efficiency data for truck {truck.plate_number} and provide insights.
        
        Truck: {truck.plate_number}
        Fleet Type: {truck.fleet_type}
        Wheel Config: {truck.wheel_config}
        Current Odometer: {truck.current_odometer} km
        
        Performance Metrics:
        - Current Efficiency: {float(fuel_data['efficiency']):.2f} km/l
        - Fleet Average: {float(fleet_avg):.2f} km/l
        - Total Distance: {fuel_data['total_distance']} km
        - Total Fuel: {float(fuel_data['total_fuel']):.2f} liters
        - Trips: {fuel_data['trips']}
        
        Recent Fuel Log Data:
        {json.dumps(fuel_log_data, indent=2)}
        
        Provide a JSON response with the following structure:
        {{
            "performance_rating": "EXCELLENT|GOOD|AVERAGE|BELOW_AVERAGE|POOR",
            "insights": ["insight1", "insight2", ...],
            "recommendations": ["recommendation1", "recommendation2", ...],
            "potential_savings": {{
                "fuel_liters_per_month": float,
                "cost_savings_per_month_inr": float,
                "efficiency_improvement_percent": float
            }}
        }}
        
        Return ONLY the JSON, no markdown formatting or explanation.
        """
        
        try:
            response = self._generate_content(prompt)
            # Clean up response - remove markdown code blocks if present
            response = response.replace('```json', '').replace('```', '').strip()
            result = json.loads(response)
            
            return FuelEfficiencyInsight(
                truck_id=truck.id,
                truck_plate=truck.plate_number,
                current_efficiency=float(fuel_data['efficiency']),
                fleet_average=float(fleet_avg),
                performance_rating=result.get('performance_rating', 'UNKNOWN'),
                insights=result.get('insights', []),
                recommendations=result.get('recommendations', []),
                potential_savings=result.get('potential_savings', {}),
                generated_at=timezone.now()
            )
        except json.JSONDecodeError as e:
            raise GeminiAIError(f"Failed to parse AI response: {str(e)}")
        except Exception as e:
            raise GeminiAIError(f"Failed to generate insights: {str(e)}")
    
    def detect_anomalies(self, truck: Truck, days: int = 30) -> List[AnomalyDetectionResult]:
        """Detect anomalies in truck operations using AI."""
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        # Gather all relevant data
        fuel_logs = FuelLog.objects.filter(
            truck=truck,
            date__gte=start_date.date(),
            date__lte=end_date.date()
        ).order_by('date')
        
        daily_odos = DailyOdoRegistry.objects.filter(
            truck=truck,
            date__gte=start_date.date(),
            date__lte=end_date.date()
        ).order_by('date')
        
        # Build data context
        fuel_data = []
        for log in fuel_logs:
            if log.previous_odometer and log.fuel_liters:
                distance = log.odometer - log.previous_odometer
                efficiency = distance / float(log.fuel_liters) if log.fuel_liters else 0
                fuel_data.append({
                    'date': log.date.isoformat(),
                    'distance': distance,
                    'fuel_liters': float(log.fuel_liters),
                    'efficiency': efficiency
                })
        
        odo_data = []
        for entry in daily_odos:
            odo_data.append({
                'date': entry.date.isoformat(),
                'daily_mileage': entry.daily_mileage,
                'opening': entry.opening_odometer,
                'closing': entry.closing_odometer
            })
        
        prompt = f"""
        Analyze the following operational data for truck {truck.plate_number} and detect any anomalies.
        
        Truck: {truck.plate_number}
        Analysis Period: {start_date.date()} to {end_date.date()}
        
        Fuel Data:
        {json.dumps(fuel_data, indent=2)}
        
        Daily Odometer Data:
        {json.dumps(odo_data, indent=2)}
        
        Look for anomalies such as:
        1. Sudden drops in fuel efficiency
        2. Unusual mileage patterns
        3. Fuel consumption outliers
        4. Odometer discrepancies
        
        Provide a JSON response with the following structure:
        {{
            "anomalies": [
                {{
                    "anomaly_type": "FUEL_EFFICIENCY_DROP|ODOMETER_DISCREPANCY|HIGH_FUEL_CONSUMPTION|IRREGULAR_MILEAGE",
                    "severity": "LOW|MEDIUM|HIGH|CRITICAL",
                    "description": "Detailed description of the anomaly",
                    "detected_value": float,
                    "expected_range": {{"min": float, "max": float}},
                    "recommended_action": "Action to take"
                }}
            ]
        }}
        
        If no anomalies are detected, return an empty anomalies array.
        Return ONLY the JSON, no markdown formatting or explanation.
        """
        
        try:
            response = self._generate_content(prompt)
            response = response.replace('```json', '').replace('```', '').strip()
            result = json.loads(response)
            
            anomalies = []
            for anomaly_data in result.get('anomalies', []):
                anomalies.append(AnomalyDetectionResult(
                    truck_id=truck.id,
                    truck_plate=truck.plate_number,
                    anomaly_type=anomaly_data.get('anomaly_type', 'UNKNOWN'),
                    severity=anomaly_data.get('severity', 'LOW'),
                    description=anomaly_data.get('description', ''),
                    detected_value=anomaly_data.get('detected_value', 0.0),
                    expected_range=anomaly_data.get('expected_range', {'min': 0.0, 'max': 0.0}),
                    recommended_action=anomaly_data.get('recommended_action', ''),
                    detected_at=timezone.now()
                ))
            
            return anomalies
        except json.JSONDecodeError as e:
            raise GeminiAIError(f"Failed to parse AI response: {str(e)}")
        except Exception as e:
            raise GeminiAIError(f"Failed to detect anomalies: {str(e)}")
    
    def generate_maintenance_recommendations(self, truck: Truck) -> List[MaintenanceRecommendation]:
        """Generate AI-powered maintenance recommendations for a truck."""
        # Gather truck data
        tires = TireInventory.objects.filter(truck=truck)
        tire_data = []
        for tire in tires:
            tire_data.append({
                'serial': tire.serial_number,
                'status': tire.status,
                'mileage': tire.calculate_current_mileage(),
                'cost_per_km': float(tire.calculate_cost_per_km())
            })
        
        # Get recent fuel efficiency
        thirty_days_ago = timezone.now() - timedelta(days=30)
        fuel_eff = calculate_fuel_efficiency(truck=truck, start_date=thirty_days_ago, end_date=timezone.now())
        
        # Get document expiry status
        today = timezone.now().date()
        documents = []
        doc_fields = [
            ('fitness', truck.fitness_expiry),
            ('insurance', truck.insurance_expiry),
            ('pucc', truck.pucc_expiry),
            ('tax', truck.tax_expiry),
            ('permit', truck.permit_expiry)
        ]
        for doc_type, expiry in doc_fields:
            if expiry:
                days_until = (expiry - today).days
                documents.append({
                    'type': doc_type,
                    'expiry_date': expiry.isoformat(),
                    'days_until': days_until
                })
        
        prompt = f"""
        Generate maintenance recommendations for truck {truck.plate_number}.
        
        Truck Details:
        - Plate: {truck.plate_number}
        - Type: {truck.fleet_type}
        - Odometer: {truck.current_odometer} km
        - Status: {truck.status}
        
        Recent Fuel Efficiency: {float(fuel_eff['efficiency']):.2f} km/l (over {fuel_eff['trips']} trips)
        
        Tire Status:
        {json.dumps(tire_data, indent=2)}
        
        Document Status:
        {json.dumps(documents, indent=2)}
        
        Provide a JSON response with maintenance recommendations:
        {{
            "recommendations": [
                {{
                    "priority": "CRITICAL|HIGH|MEDIUM|LOW",
                    "maintenance_type": "PREVENTIVE|CORRECTIVE|PREDICTIVE|DOCUMENT_RENEWAL",
                    "description": "Description of required maintenance",
                    "estimated_cost_inr": float,
                    "estimated_downtime": "e.g., 2-3 hours",
                    "recommended_date": "YYYY-MM-DD",
                    "rationale": "Why this maintenance is recommended"
                }}
            ]
        }}
        
        Return ONLY the JSON, no markdown formatting or explanation.
        """
        
        try:
            response = self._generate_content(prompt)
            response = response.replace('```json', '').replace('```', '').strip()
            result = json.loads(response)
            
            recommendations = []
            for rec_data in result.get('recommendations', []):
                try:
                    recommended_date = datetime.strptime(rec_data.get('recommended_date', ''), '%Y-%m-%d')
                    recommended_date = timezone.make_aware(recommended_date)
                except (ValueError, TypeError):
                    recommended_date = timezone.now() + timedelta(days=7)
                
                recommendations.append(MaintenanceRecommendation(
                    truck_id=truck.id,
                    truck_plate=truck.plate_number,
                    priority=rec_data.get('priority', 'LOW'),
                    maintenance_type=rec_data.get('maintenance_type', 'PREVENTIVE'),
                    description=rec_data.get('description', ''),
                    estimated_cost=rec_data.get('estimated_cost_inr', 0.0),
                    estimated_downtime=rec_data.get('estimated_downtime', 'Unknown'),
                    recommended_date=recommended_date,
                    rationale=rec_data.get('rationale', ''),
                    generated_at=timezone.now()
                ))
            
            return recommendations
        except json.JSONDecodeError as e:
            raise GeminiAIError(f"Failed to parse AI response: {str(e)}")
        except Exception as e:
            raise GeminiAIError(f"Failed to generate recommendations: {str(e)}")
    
    def process_chalan_ocr(self, image_path: str, mining_log: MiningLog = None) -> OCRResult:
        """Process mining chalan document using OCR with AI enhancement."""
        try:
            # Upload image to Gemini
            if not os.path.exists(image_path):
                return OCRResult(
                    success=False,
                    chalan_no=None,
                    date=None,
                    customer_name=None,
                    net_weight=None,
                    material=None,
                    confidence_score=0.0,
                    raw_text="",
                    processed_at=timezone.now(),
                    errors=["Image file not found"]
                )
            
            # Upload and process image
            image_file = genai.upload_file(image_path)
            
            prompt = """
            Extract information from this mining chalan document image.
            
            Please identify and extract the following fields:
            1. Chalan Number (receipt/bill number)
            2. Date (in DD/MM/YYYY or YYYY-MM-DD format)
            3. Customer Name (party/consignee name)
            4. Net Weight (in tons/kg)
            5. Material Type (coal, iron ore, etc.)
            
            Provide a JSON response with this exact structure:
            {
                "chalan_no": "extracted chalan number or null",
                "date": "extracted date in YYYY-MM-DD format or null",
                "customer_name": "extracted customer name or null",
                "net_weight": numeric value or null,
                "material": "extracted material type or null",
                "confidence_score": numeric value between 0 and 1,
                "raw_text": "all extracted text from the document"
            }
            
            Return ONLY the JSON, no markdown formatting or explanation.
            """
            
            response = self.model.generate_content([prompt, image_file])
            response_text = response.text.replace('```json', '').replace('```', '').strip()
            
            try:
                result = json.loads(response_text)
            except json.JSONDecodeError:
                # If JSON parsing fails, return raw text
                return OCRResult(
                    success=False,
                    chalan_no=None,
                    date=None,
                    customer_name=None,
                    net_weight=None,
                    material=None,
                    confidence_score=0.0,
                    raw_text=response_text,
                    processed_at=timezone.now(),
                    errors=["Failed to parse AI response as JSON"]
                )
            
            # Update mining log if provided
            if mining_log:
                mining_log.ocr_processed = True
                mining_log.ocr_data = result
                mining_log.save()
            
            # Parse date
            extracted_date = result.get('date')
            if extracted_date:
                try:
                    # Try different date formats
                    for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y']:
                        try:
                            parsed = datetime.strptime(extracted_date, fmt)
                            extracted_date = parsed.strftime('%Y-%m-%d')
                            break
                        except ValueError:
                            continue
                except Exception:
                    extracted_date = None
            
            # Parse net weight
            net_weight = result.get('net_weight')
            if isinstance(net_weight, str):
                try:
                    net_weight = float(net_weight.replace('tons', '').replace('kg', '').replace(',', '').strip())
                except (ValueError, AttributeError):
                    net_weight = None
            
            return OCRResult(
                success=result.get('confidence_score', 0) > 0.5,
                chalan_no=result.get('chalan_no'),
                date=extracted_date,
                customer_name=result.get('customer_name'),
                net_weight=net_weight,
                material=result.get('material'),
                confidence_score=result.get('confidence_score', 0.0),
                raw_text=result.get('raw_text', ''),
                processed_at=timezone.now(),
                errors=[] if result.get('confidence_score', 0) > 0.5 else ['Low confidence score']
            )
            
        except Exception as e:
            return OCRResult(
                success=False,
                chalan_no=None,
                date=None,
                customer_name=None,
                net_weight=None,
                material=None,
                confidence_score=0.0,
                raw_text="",
                processed_at=timezone.now(),
                errors=[str(e)]
            )
    
    def generate_fleet_insights_report(self, days: int = 30) -> Dict[str, Any]:
        """Generate comprehensive fleet insights report using AI."""
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        # Aggregate fleet data
        trucks = Truck.objects.filter(status='ACTIVE')
        total_trucks = trucks.count()
        
        # Fuel statistics
        fuel_stats = FuelLog.objects.filter(
            date__gte=start_date.date(),
            date__lte=end_date.date()
        ).aggregate(
            total_fuel=Sum('fuel_liters'),
            total_cost=Sum('fuel_cost'),
            total_trips=Count('id')
        )
        
        # Efficiency data per truck
        truck_efficiencies = []
        for truck in trucks[:10]:  # Limit to 10 trucks for prompt size
            eff_data = calculate_fuel_efficiency(truck=truck, start_date=start_date, end_date=end_date)
            if eff_data['efficiency'] > 0:
                truck_efficiencies.append({
                    'plate': truck.plate_number,
                    'efficiency': float(eff_data['efficiency']),
                    'distance': eff_data['total_distance'],
                    'fuel': float(eff_data['total_fuel'])
                })
        
        # Maintenance alerts
        pending_alerts = Alert.objects.filter(
            status='PENDING',
            created_at__gte=start_date
        ).count()
        
        prompt = f"""
        Generate a comprehensive fleet management insights report.
        
        Period: Last {days} days ({start_date.date()} to {end_date.date()})
        
        Fleet Overview:
        - Total Active Trucks: {total_trucks}
        - Total Fuel Consumed: {float(fuel_stats['total_fuel'] or 0):.2f} liters
        - Total Fuel Cost: ₹{float(fuel_stats['total_cost'] or 0):,.2f}
        - Total Fuel Trips: {fuel_stats['total_trips'] or 0}
        - Pending Alerts: {pending_alerts}
        
        Top Performing Trucks (by efficiency):
        {json.dumps(sorted(truck_efficiencies, key=lambda x: x['efficiency'], reverse=True)[:5], indent=2)}
        
        Provide a JSON response with this structure:
        {{
            "executive_summary": "Brief summary of fleet performance",
            "key_findings": ["finding1", "finding2", ...],
            "performance_analysis": {{
                "overall_rating": "EXCELLENT|GOOD|SATISFACTORY|NEEDS_IMPROVEMENT",
                "top_performers": ["truck1", "truck2"],
                "underperformers": ["truck3"]
            }},
            "recommendations": [
                {{
                    "category": "FUEL_EFFICIENCY|MAINTENANCE|OPERATIONS",
                    "priority": "HIGH|MEDIUM|LOW",
                    "action": "Specific action to take",
                    "expected_impact": "Expected benefit"
                }}
            ],
            "cost_optimization": {{
                "potential_savings_monthly_inr": float,
                "fuel_efficiency_targets": "Recommended targets",
                "action_items": ["item1", "item2"]
            }}
        }}
        
        Return ONLY the JSON, no markdown formatting or explanation.
        """
        
        try:
            response = self._generate_content(prompt)
            response = response.replace('```json', '').replace('```', '').strip()
            return json.loads(response)
        except json.JSONDecodeError as e:
            raise GeminiAIError(f"Failed to parse AI response: {str(e)}")
        except Exception as e:
            raise GeminiAIError(f"Failed to generate report: {str(e)}")


# Convenience functions for direct use

def get_fuel_efficiency_insights(truck_id: int, days: int = 30) -> FuelEfficiencyInsight:
    """Get fuel efficiency insights for a specific truck."""
    truck = Truck.objects.get(pk=truck_id)
    service = GeminiAIService()
    return service.generate_fuel_efficiency_insights(truck, days)


def detect_truck_anomalies(truck_id: int, days: int = 30) -> List[AnomalyDetectionResult]:
    """Detect anomalies for a specific truck."""
    truck = Truck.objects.get(pk=truck_id)
    service = GeminiAIService()
    return service.detect_anomalies(truck, days)


def get_maintenance_recommendations(truck_id: int) -> List[MaintenanceRecommendation]:
    """Get maintenance recommendations for a specific truck."""
    truck = Truck.objects.get(pk=truck_id)
    service = GeminiAIService()
    return service.generate_maintenance_recommendations(truck)


def process_mining_chalan(image_path: str, mining_log_id: int = None) -> OCRResult:
    """Process mining chalan document with OCR."""
    mining_log = None
    if mining_log_id:
        mining_log = MiningLog.objects.get(pk=mining_log_id)
    service = GeminiAIService()
    return service.process_chalan_ocr(image_path, mining_log)


def get_fleet_ai_report(days: int = 30) -> Dict[str, Any]:
    """Get comprehensive AI-powered fleet report."""
    service = GeminiAIService()
    return service.generate_fleet_insights_report(days)
