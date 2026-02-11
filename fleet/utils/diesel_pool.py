def calculate_net_diesel_pool(today_pumped, yest_stock, today_stock_left, today_air):
    """Calculate Net Diesel Pool for coal batch efficiency"""
    return today_pumped + yest_stock - today_stock_left - today_air
