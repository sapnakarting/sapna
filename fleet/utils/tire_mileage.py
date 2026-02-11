def calculate_current_mileage(tire, current_truck_odo):
    """Calculate tire's current total mileage"""
    historical_mileage = tire.historical_mileage or 0
    if tire.status == "MOUNTED" and tire.mounted_at_odometer:
        current_segment = current_truck_odo - tire.mounted_at_odometer
        return historical_mileage + current_segment
    return historical_mileage
