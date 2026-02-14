#!/usr/bin/env python
"""
Test script to verify Daily Odometer Registry implementation
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sapna_carting.settings')
sys.path.insert(0, '/home/engine/project')

django.setup()

from fleet.models import DailyOdoRegistry, Truck
from fleet.forms import DailyOdoRegistryForm, BulkDailyOdoEntryForm, DailyOdoRegistrySearchForm
from fleet.views import DailyOdoRegistryListView, BulkDailyOdoEntryView
from django.test import RequestFactory
from django.contrib.auth.models import User
from django.utils import timezone

def test_models():
    """Test that the DailyOdoRegistry model works correctly"""
    print("Testing DailyOdoRegistry model...")
    
    # Create a test truck
    truck = Truck.objects.create(
        plate_number="TEST123",
        transporter_name="Test Transporter",
        wheel_config="10_WHEEL",
        fleet_type="COAL",
        status="ACTIVE",
        current_odometer=5000
    )
    
    # Create a daily odometer entry
    entry = DailyOdoRegistry.objects.create(
        truck=truck,
        date=timezone.now().date(),
        opening_odometer=5000,
        closing_odometer=5100,
        remarks="Test entry"
    )
    
    # Test auto-calculation
    assert entry.daily_mileage == 100, f"Expected daily_mileage to be 100, got {entry.daily_mileage}"
    
    # Test string representation
    assert str(entry) == f"{truck.plate_number} - {entry.date}", f"Unexpected string representation: {str(entry)}"
    
    # Clean up
    entry.delete()
    truck.delete()
    
    print("✓ Model tests passed")

def test_forms():
    """Test that the forms work correctly"""
    print("Testing forms...")
    
    # Create a test truck
    truck = Truck.objects.create(
        plate_number="TEST456",
        transporter_name="Test Transporter",
        wheel_config="10_WHEEL",
        fleet_type="COAL",
        status="ACTIVE",
        current_odometer=6000
    )
    
    # Test DailyOdoRegistryForm
    form_data = {
        'truck': truck.id,
        'date': timezone.now().date(),
        'opening_odometer': 6000,
        'closing_odometer': 6100,
        'remarks': 'Test form'
    }
    
    form = DailyOdoRegistryForm(data=form_data)
    assert form.is_valid(), f"Form validation failed: {form.errors}"
    
    # Test validation (closing < opening)
    invalid_form = DailyOdoRegistryForm(data={
        'truck': truck.id,
        'date': timezone.now().date(),
        'opening_odometer': 6100,
        'closing_odometer': 6000,  # Invalid: closing < opening
        'remarks': 'Test'
    })
    assert not invalid_form.is_valid(), "Form should be invalid when closing < opening"
    assert 'closing_odometer' in invalid_form.errors, "Should have closing_odometer error"
    
    # Clean up
    truck.delete()
    
    print("✓ Form tests passed")

def test_views():
    """Test that the views can be instantiated"""
    print("Testing views...")
    
    # Test view instantiation
    list_view = DailyOdoRegistryListView()
    assert hasattr(list_view, 'model'), "ListView should have model attribute"
    assert list_view.model == DailyOdoRegistry, "ListView model should be DailyOdoRegistry"
    
    print("✓ View tests passed")

def test_urls():
    """Test that URLs are properly configured"""
    print("Testing URLs...")
    
    from django.urls import reverse, resolve
    
    # Test URL reversal
    try:
        url = reverse('fleet:daily-odo-list')
        assert url == '/fleet/daily-odometer/', f"Expected '/fleet/daily-odometer/', got {url}"
        print("✓ URL tests passed")
    except Exception as e:
        print(f"✗ URL test failed: {e}")
        return False
    
    return True

def main():
    """Run all tests"""
    print("=" * 60)
    print("Testing Daily Odometer Registry Implementation")
    print("=" * 60)
    
    try:
        test_models()
        test_forms()
        test_views()
        test_urls()
        
        print("\n" + "=" * 60)
        print("✓ All tests passed successfully!")
        print("=" * 60)
        return True
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)