from datetime import datetime, timedelta

# Function to determine the differential based on the time of day
def determine_shift_differential(hour):
    if 19 <= hour or hour < 7:  # 7 PM to 7 AM (Night Shift)
        return 'Night Shift'
    else:  # 7 AM to 7 PM (Day Shift)
        return 'Day Shift'

# Function to check if the shift is on a weekend
def is_weekend(date):
    return date.weekday() >= 5  # Saturday and Sunday are 5 and 6

# Main function to calculate the earnings for a given period of work
def calculate_weekly_earnings(work_periods, hourly_rate, charge_nurse_pay, night_percent, weekend_percent, on_call_percent):
    total_earnings = 0
    total_hours = 0

    for start_time, end_time in work_periods:
        current_time = start_time
        while current_time < end_time:
            differential = determine_shift_differential(current_time.hour)
            weekend = is_weekend(current_time)

            if charge_nurse_pay > 0:
                rate = hourly_rate + charge_nurse_pay
            else:
                if differential == 'Night Shift':
                    rate = hourly_rate * (1 + night_percent / 100)
                else:  # Day Shift
                    rate = hourly_rate

                if weekend:
                    rate *= (1 + weekend_percent / 100)

            total_hours += 1
            total_earnings += rate
            current_time += timedelta(hours=1)

    # Calculate overtime if total hours exceed 40
    if total_hours > 40:
        overtime_hours = total_hours - 40
        overtime_earnings = 0
        for start_time, end_time in work_periods:
            current_time = start_time
            while current_time < end_time and overtime_hours > 0:
                differential = determine_shift_differential(current_time.hour)
                weekend = is_weekend(current_time)

                if charge_nurse_pay > 0:
                    rate = hourly_rate + charge_nurse_pay
                else:
                    if differential == 'Night Shift':
                        rate = hourly_rate * (1 + night_percent / 100)
                    else:  # Day Shift
                        rate = hourly_rate

                    if weekend:
                        rate *= (1 + weekend_percent / 100)

                overtime_earnings += rate * 0.5  # Additional 0.5x for overtime
                overtime_hours -= 1
                current_time += timedelta(hours=1)

        total_earnings += overtime_earnings

    return total_earnings, total_hours

# Example usage:
work_periods = [
    (datetime(2024, 8, 26, 7, 0), datetime(2024, 8, 26, 19, 0)),  # Aug 26, 7 PM to Aug 27, 7 AM (Night Shift)
    (datetime(2024, 8, 27, 7, 0), datetime(2024, 8, 27, 19, 0)),  # Aug 27, 7 AM to 7 PM (Day Shift)
    (datetime(2024, 8, 28, 7, 0), datetime(2024, 8, 28, 19, 0)),  # Aug 28, 7 AM to 7 PM (Day Shift)
    # (datetime(2024, 8, 29, 7, 0), datetime(2024, 8, 29, 19, 0)),  # Aug 29, 7 AM to 7 PM (Day Shift)
]

hourly_rate = 92.25  # Adjusted for Nurse, Clinical II, Step 2
charge_nurse_pay = 0  # Example for Charge Nurse
night_percent = 16  # 16% differential for Night Shift
weekend_percent = 5  # 5% differential for Weekend Shift
on_call_percent = 50  # 50% differential for On-Call

total_earnings, total_hours = calculate_weekly_earnings(work_periods, hourly_rate, charge_nurse_pay, night_percent, weekend_percent, on_call_percent)
print(f"Total hours worked: {total_hours} hours")
print(f"Total earnings for the week: ${total_earnings:.2f}")
