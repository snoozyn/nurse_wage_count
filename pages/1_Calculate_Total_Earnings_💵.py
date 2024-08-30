import streamlit as st
from datetime import datetime, timedelta
import pandas as pd

# Function to determine the differential based on the time of day
def determine_shift_differential(hour):
    return 'Night Shift' if 19 <= hour or hour < 7 else 'Day Shift'

# Function to check if the shift is on a weekend
def is_weekend(date):
    return date.weekday() >= 5  # Saturday and Sunday

# Function to check if two time periods overlap
def check_overlap(new_start, new_end, existing_periods):
    for start, end, _ in existing_periods:  # Ignore the third value (is_on_call) with _
        if (new_start < end and new_end > start):
            return True
    return False

# Main function to calculate the earnings for a given period of work
@st.cache_data
def calculate_weekly_earnings(work_periods, hourly_rate, charge_nurse_pay, night_differential, weekend_differential, on_call_differential, differential_type):
    total_earnings = 0
    total_hours = 0

    for start_time, end_time, is_on_call in work_periods:
        current_time = start_time
        while current_time < end_time:
            differential = determine_shift_differential(current_time.hour)
            weekend = is_weekend(current_time)

            rate = hourly_rate
            if charge_nurse_pay > 0:
                rate += charge_nurse_pay
            elif differential == 'Night Shift':
                if differential_type == "Percentage":
                    rate *= (1 + night_differential / 100)
                else:
                    rate += night_differential
            if weekend:
                if differential_type == "Percentage":
                    rate *= (1 + weekend_differential / 100)
                else:
                    rate += weekend_differential
            if is_on_call:
                if differential_type == "Percentage":
                    rate *= (1 + on_call_differential / 100)
                else:
                    rate += on_call_differential

            total_hours += 1
            total_earnings += rate
            current_time += timedelta(hours=1)

    # Calculate overtime if total hours exceed 40
    if total_hours > 40:
        overtime_hours = total_hours - 40
        overtime_earnings = 0
        for start_time, end_time, is_on_call in work_periods:
            current_time = start_time
            while current_time < end_time and overtime_hours > 0:
                differential = determine_shift_differential(current_time.hour)
                weekend = is_weekend(current_time)

                rate = hourly_rate
                if charge_nurse_pay > 0:
                    rate += charge_nurse_pay
                elif differential == 'Night Shift':
                    if differential_type == "Percentage":
                        rate *= (1 + night_differential / 100)
                    else:
                        rate += night_differential
                if weekend:
                    if differential_type == "Percentage":
                        rate *= (1 + weekend_differential / 100)
                    else:
                        rate += weekend_differential
                if is_on_call:
                    if differential_type == "Percentage":
                        rate *= (1 + on_call_differential / 100)
                    else:
                        rate += on_call_differential

                overtime_earnings += rate * 0.5  # Additional 0.5x for overtime
                overtime_hours -= 1
                current_time += timedelta(hours=1)

        total_earnings += overtime_earnings

    return total_earnings, total_hours

# Streamlit App
st.set_page_config(page_title="Nurse Differential Calculator")

# Work Periods State Management
if 'work_periods' not in st.session_state:
    st.session_state.work_periods = []

# Input: work periods
st.subheader("Enter Work Periods")

start_date = st.date_input("Start Date")
start_time = st.time_input("Start Time")
end_date = st.date_input("End Date", value=start_date)
end_time = st.time_input("End Time")

is_on_call = st.checkbox("On Call?")

if is_on_call:
    on_call_percent = st.number_input("On-Call Differential", min_value=0.0, value=50.0)
else:
    on_call_percent = 0.0

# Differential type (percentage or dollar amount)
differential_type = st.selectbox("Differential Type", ["Percentage", "Dollar Amount"])
if differential_type == "Percentage":
    night_differential = st.number_input("Night Shift Differential (%)", min_value=0.0, value=16.0)
    weekend_differential = st.number_input("Weekend Differential (%)", min_value=0.0, value=5.0)
else:
    night_differential = st.number_input("Night Shift Differential ($)", min_value=0.0, value=10.0)
    weekend_differential = st.number_input("Weekend Differential ($)", min_value=0.0, value=5.0)

charge_nurse_pay = st.number_input("Charge Nurse Pay ($)", min_value=0.0, value=0.0)

if st.button("Add Work Period"):
    start_datetime = datetime.combine(start_date, start_time)
    end_datetime = datetime.combine(end_date, end_time)
    shift_type = determine_shift_differential(start_time.hour)

    if check_overlap(start_datetime, end_datetime, st.session_state.work_periods):
        st.error("The shift overlaps with an existing shift. Please check the timings.")
    else:
        st.session_state.work_periods.append((start_datetime, end_datetime, is_on_call))
        formatted_shift = f"{start_date.strftime('%B %d')} to {end_date.strftime('%B %d')}, {shift_type} from {start_time.strftime('%I:%M %p').lower()} to {end_time.strftime('%I:%M %p').lower()}"
        st.success(f"Work period added successfully: {formatted_shift}")

# Display work periods in a formatted and prominent manner with delete buttons
if st.session_state.work_periods:
    st.markdown("<h2 style='text-align: center; color: green;'>Work Periods:</h2>", unsafe_allow_html=True)
    for i, (start, end, is_on_call) in enumerate(st.session_state.work_periods):
        shift_type = determine_shift_differential(start.hour)
        formatted_shift = f"{start.strftime('%B %d')} to {end.strftime('%B %d')}, {shift_type} from {start.strftime('%I:%M %p').lower()} to {end.strftime('%I:%M %p').lower()}"
        col1, col2 = st.columns([0.9, 0.1])
        with col1:
            st.markdown(
                f"<div style='border: 1px solid #ccc; padding: 10px; font-size: 1.2em; border-radius: 10px; margin-bottom: 10px;'>{formatted_shift}</div>",
                unsafe_allow_html=True,
            )
        with col2:
            if st.button("🗑️", key=f"delete_{i}"):
                st.session_state.work_periods.pop(i)
                st.rerun()

# Input: hourly rate and differentials
hourly_rate = st.number_input("Hourly Rate ($)", min_value=0.0, value=92.25)

# Calculate earnings
if st.button("Calculate Earnings"):
    total_earnings, total_hours = calculate_weekly_earnings(
        st.session_state.work_periods, hourly_rate, charge_nurse_pay, night_differential, weekend_differential, on_call_percent, differential_type
    )
    st.success(f"Total hours worked: {total_hours} hours")
    st.success(f"Total earnings for the week: ${total_earnings:.2f}")
