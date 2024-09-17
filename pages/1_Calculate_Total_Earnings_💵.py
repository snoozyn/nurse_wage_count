import streamlit as st
from datetime import datetime, timedelta, date
from collections import defaultdict
import pandas as pd
import altair as alt
import calendar
from dateutil.relativedelta import relativedelta
from bs4 import BeautifulSoup

# Function definitions
def determine_shift_differential(hour):
    if 19 <= hour or hour < 7:
        return 'Night Shift'
    else:
        return 'Day Shift'

def is_weekend(date):
    return date.weekday() >= 5  # 5 = Saturday (5), 6 = Sunday (6)

def check_overlap(new_start, new_end, existing_periods):
    for start, end, _ in existing_periods:
        if new_start < end and new_end > start:
            return True
    return False

# Function to calculate federal tax based on tax brackets
def calculate_federal_tax(income, tax_brackets):
    tax = 0.0
    for bracket in tax_brackets:
        lower_limit, upper_limit, rate = bracket
        if income > lower_limit:
            taxable_amount = min(income, upper_limit) - lower_limit
            tax += taxable_amount * rate
        else:
            break
    return tax

# Function to calculate total earnings with detailed breakdown
@st.cache_data
def calculate_total_earnings(work_periods, hourly_rate, charge_nurse_pay, night_differential,
                             weekend_differential, on_call_differential, differential_type):
    hours_worked = []
    for start_time, end_time, is_on_call in work_periods:
        current_time = start_time
        while current_time < end_time:
            week_start = current_time - timedelta(days=current_time.weekday())
            week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
            differential = determine_shift_differential(current_time.hour)
            weekend = is_weekend(current_time)
            base_rate = hourly_rate

            # Initialize earnings components
            rate = base_rate
            base_pay = base_rate
            night_diff_pay = 0.0
            weekend_diff_pay = 0.0
            on_call_diff_pay = 0.0
            charge_nurse_pay_hour = 0.0

            if charge_nurse_pay > 0:
                charge_nurse_pay_hour = charge_nurse_pay
                rate += charge_nurse_pay

            if differential == 'Night Shift':
                if differential_type == "Percentage":
                    night_diff_pay = base_rate * (night_differential / 100)
                else:
                    night_diff_pay = night_differential
                rate += night_diff_pay

            if weekend:
                if differential_type == "Percentage":
                    weekend_diff_pay = base_rate * (weekend_differential / 100)
                else:
                    weekend_diff_pay = weekend_differential
                rate += weekend_diff_pay

            if is_on_call:
                if differential_type == "Percentage":
                    on_call_diff_pay = base_rate * (on_call_differential / 100)
                else:
                    on_call_diff_pay = on_call_differential
                rate += on_call_diff_pay

            total_hourly_rate = rate

            hours_worked.append({
                'datetime': current_time,
                'week_start': week_start,
                'base_pay': base_pay,
                'charge_nurse_pay': charge_nurse_pay_hour,
                'night_diff_pay': night_diff_pay,
                'weekend_diff_pay': weekend_diff_pay,
                'on_call_diff_pay': on_call_diff_pay,
                'total_hourly_rate': total_hourly_rate
            })
            current_time += timedelta(hours=1)

    # Create DataFrame from hours_worked
    df_hours = pd.DataFrame(hours_worked)

    # Group by week and calculate earnings components
    df_hours['week'] = df_hours['week_start'].dt.strftime('%Y-%U')
    week_groups = df_hours.groupby('week')

    weekly_data = []
    total_hours = 0
    total_earnings = 0

    for week, group in week_groups:
        hours = len(group)
        total_hours += hours

        # Sum earnings components
        base_pay = group['base_pay'].sum()
        charge_nurse_pay_total = group['charge_nurse_pay'].sum()
        night_diff_pay_total = group['night_diff_pay'].sum()
        weekend_diff_pay_total = group['weekend_diff_pay'].sum()
        on_call_diff_pay_total = group['on_call_diff_pay'].sum()
        total_weekly_pay = group['total_hourly_rate'].sum()

        # Overtime calculations
        if hours > 40:
            regular_hours = 40
            overtime_hours = hours - 40

            # Calculate regular earnings
            regular_earnings = group.iloc[:40]['total_hourly_rate'].sum()

            # Calculate overtime earnings at 1.5x rate
            overtime_rates = group.iloc[40:]['total_hourly_rate'] * 1.5
            overtime_earnings = overtime_rates.sum()

            total_weekly_pay = regular_earnings + overtime_earnings
        else:
            regular_hours = hours
            overtime_hours = 0
            regular_earnings = total_weekly_pay
            overtime_earnings = 0.0

        total_earnings += total_weekly_pay

        weekly_data.append({
            'week': week,
            'week_start': group['week_start'].iloc[0],
            'regular_hours': regular_hours,
            'overtime_hours': overtime_hours,
            'base_pay': base_pay,
            'charge_nurse_pay': charge_nurse_pay_total,
            'night_diff_pay': night_diff_pay_total,
            'weekend_diff_pay': weekend_diff_pay_total,
            'on_call_diff_pay': on_call_diff_pay_total,
            'regular_earnings': regular_earnings,
            'overtime_earnings': overtime_earnings,
            'total_weekly_pay': total_weekly_pay
        })

    return total_earnings, total_hours, weekly_data, df_hours

# Federal tax brackets for 2023
federal_tax_brackets = {
    'Single': [
        (0, 11000, 0.10),
        (11000, 44725, 0.12),
        (44725, 95375, 0.22),
        (95375, 182100, 0.24),
        (182100, 231250, 0.32),
        (231250, 578125, 0.35),
        (578125, float('inf'), 0.37)
    ],
    'Married Filing Jointly': [
        (0, 22000, 0.10),
        (22000, 89450, 0.12),
        (89450, 190750, 0.22),
        (190750, 364200, 0.24),
        (364200, 462500, 0.32),
        (462500, 693750, 0.35),
        (693750, float('inf'), 0.37)
    ],
    'Head of Household': [
        (0, 15700, 0.10),
        (15700, 59850, 0.12),
        (59850, 95350, 0.22),
        (95350, 182100, 0.24),
        (182100, 231250, 0.32),
        (231250, 578100, 0.35),
        (578100, float('inf'), 0.37)
    ]
}

# Dictionary of state tax rates (approximate highest marginal rates)
state_tax_rates = {
    'Alabama': 5.0,
    'Alaska': 0.0,
    'Arizona': 4.50,
    'Arkansas': 5.90,
    'California': 13.30,
    'Colorado': 4.55,
    'Connecticut': 6.99,
    'Delaware': 6.60,
    'Florida': 0.0,
    'Georgia': 5.75,
    'Hawaii': 11.00,
    'Idaho': 6.925,
    'Illinois': 4.95,
    'Indiana': 3.23,
    'Iowa': 8.53,
    'Kansas': 5.70,
    'Kentucky': 5.0,
    'Louisiana': 6.0,
    'Maine': 7.15,
    'Maryland': 5.75,
    'Massachusetts': 5.0,
    'Michigan': 4.25,
    'Minnesota': 9.85,
    'Mississippi': 5.0,
    'Missouri': 5.40,
    'Montana': 6.90,
    'Nebraska': 6.84,
    'Nevada': 0.0,
    'New Hampshire': 5.0,  # Dividends and interest income only
    'New Jersey': 10.75,
    'New Mexico': 5.90,
    'New York': 8.82,
    'North Carolina': 5.25,
    'North Dakota': 2.90,
    'Ohio': 4.797,
    'Oklahoma': 5.0,
    'Oregon': 9.90,
    'Pennsylvania': 3.07,
    'Rhode Island': 5.99,
    'South Carolina': 7.0,
    'South Dakota': 0.0,
    'Tennessee': 0.0,
    'Texas': 0.0,
    'Utah': 4.95,
    'Vermont': 8.75,
    'Virginia': 5.75,
    'Washington': 0.0,
    'West Virginia': 6.50,
    'Wisconsin': 7.65,
    'Wyoming': 0.0,
    'District of Columbia': 8.95
}

# Streamlit App
st.set_page_config(page_title="Nurse Differential Calculator 👩‍⚕️")

# Work Periods State Management
if 'work_periods' not in st.session_state:
    st.session_state.work_periods = []

# Input: work periods
st.subheader("Enter Work Periods")

# Use columns to align inputs
col1, col2 = st.columns(2)

with col1:
    start_date = st.date_input("Start Date")
    start_time = st.time_input("Start Time")
with col2:
    end_date = st.date_input("End Date", value=start_date)
    end_time = st.time_input("End Time")

is_on_call = st.checkbox("On Call?")

# Differential type
differential_type = st.selectbox("Differential Type", ["Percentage", "Dollar Amount"])

if differential_type == "Percentage":
    night_differential = st.number_input("Night Shift Differential (%)", min_value=0.0, value=16.0)
    weekend_differential = st.number_input("Weekend Differential (%)", min_value=0.0, value=5.0)
    if is_on_call:
        on_call_differential = st.number_input("On-Call Differential (%)", min_value=0.0, value=50.0)
    else:
        on_call_differential = 0.0
else:
    night_differential = st.number_input("Night Shift Differential ($)", min_value=0.0, value=10.0)
    weekend_differential = st.number_input("Weekend Differential ($)", min_value=0.0, value=5.0)
    if is_on_call:
        on_call_differential = st.number_input("On-Call Differential ($)", min_value=0.0, value=5.0)
    else:
        on_call_differential = 0.0

charge_nurse_pay = st.number_input("Charge Nurse Pay ($)", min_value=0.0, value=0.0)

# Real-time validation for date and time inputs
validation_errors = []

# Combine dates and times into datetime objects
start_datetime = datetime.combine(start_date, start_time)
end_datetime = datetime.combine(end_date, end_time)

# Check if end datetime is after start datetime
if end_datetime <= start_datetime:
    validation_errors.append("End date and time must be after the start date and time.")

# Check for overlapping shifts
if check_overlap(start_datetime, end_datetime, st.session_state.work_periods):
    validation_errors.append("This shift overlaps with an existing shift.")

# Display validation errors
if validation_errors:
    for error in validation_errors:
        st.error(error)
else:
    # Show a preview of the shift
    shift_type = determine_shift_differential(start_time.hour)
    formatted_shift = (
        f"{start_date.strftime('%B %d')} to {end_date.strftime('%B %d')}, {shift_type} from "
        f"{start_time.strftime('%I:%M %p').lower()} to {end_time.strftime('%I:%M %p').lower()}"
    )
    st.info(f"Shift to be added: {formatted_shift}")

if st.button("Add Work Period", disabled=bool(validation_errors)):
    st.session_state.work_periods.append((start_datetime, end_datetime, is_on_call))
    st.success(f"Work period added successfully: {formatted_shift}")

# Display work periods with delete buttons
if st.session_state.work_periods:
    st.markdown("<h2 style='text-align: center; color: green;'>Work Periods:</h2>", unsafe_allow_html=True)
    for i, (start, end, is_on_call) in enumerate(st.session_state.work_periods):
        shift_type = determine_shift_differential(start.hour)
        formatted_shift = (
            f"{start.strftime('%B %d')} to {end.strftime('%B %d')}, {shift_type} from "
            f"{start.strftime('%I:%M %p').lower()} to {end.strftime('%I:%M %p').lower()}"
        )
        col1, col2 = st.columns([0.9, 0.1])
        with col1:
            st.markdown(
                f"<div style='border: 1px solid #ccc; padding: 10px; font-size: 1.2em; "
                f"border-radius: 10px; margin-bottom: 10px;'>{formatted_shift}</div>",
                unsafe_allow_html=True,
            )
        with col2:
            if st.button("🗑️", key=f"delete_{start}_{end}"):
                st.session_state.work_periods.pop(i)
                st.rerun()

# Input: hourly rate
hourly_rate = st.number_input("Hourly Rate ($)", min_value=0.0, value=34.45)

# Tax Information
st.subheader("Tax Information")

# Filing Status Selection
filing_status_options = ['Single', 'Married Filing Jointly', 'Head of Household']
selected_filing_status = st.selectbox("Select Your Filing Status", filing_status_options)

# State Selection
state_list = sorted(state_tax_rates.keys())
selected_state = st.selectbox("Select Your State", state_list)
state_tax_rate = state_tax_rates[selected_state]

st.write(f"State Tax Rate for {selected_state}: {state_tax_rate}%")

# Calculate earnings
if st.button("Calculate Earnings"):
    if not st.session_state.work_periods:
        st.error("Please add at least one work period before calculating earnings.")
    else:
        total_earnings, total_hours, weekly_data, df_hours = calculate_total_earnings(
            st.session_state.work_periods, hourly_rate, charge_nurse_pay,
            night_differential, weekend_differential, on_call_differential, differential_type
        )

        # Get the appropriate federal tax brackets based on filing status
        tax_brackets = federal_tax_brackets[selected_filing_status]

        # Calculate federal tax
        federal_tax_amount = calculate_federal_tax(total_earnings, tax_brackets)

        # Calculate state tax
        state_tax_rate_decimal = state_tax_rate / 100.0
        state_tax_amount = total_earnings * state_tax_rate_decimal

        # Total tax amount
        total_tax_amount = federal_tax_amount + state_tax_amount

        post_tax_earnings = total_earnings - total_tax_amount

        st.success(f"Total hours worked: {total_hours} hours")
        st.success(f"Total pre-tax earnings for the period: ${total_earnings:.2f}")
        st.success(f"Federal tax amount ({selected_filing_status}): ${federal_tax_amount:.2f}")
        st.success(f"State tax amount ({selected_state}): ${state_tax_amount:.2f}")
        st.success(f"Total tax amount: ${total_tax_amount:.2f}")
        st.success(f"Total post-tax earnings for the period: ${post_tax_earnings:.2f}")

        st.subheader("Weekly Earnings Breakdown")
        for data in weekly_data:
            week_end = data['week_start'] + timedelta(days=6)
            week_range = f"{data['week_start'].strftime('%b %d')} - {week_end.strftime('%b %d')}"
            st.markdown(f"**Week of {week_range}:**")
            st.markdown(f"- Regular Hours: {data['regular_hours']} hours")
            st.markdown(f"- Overtime Hours: {data['overtime_hours']} hours")
            st.markdown(f"- Base Pay: ${data['base_pay']:.2f}")
            if data['charge_nurse_pay'] > 0:
                st.markdown(f"- Charge Nurse Pay: ${data['charge_nurse_pay']:.2f}")
            if data['night_diff_pay'] > 0:
                st.markdown(f"- Night Differential Pay: ${data['night_diff_pay']:.2f}")
            if data['weekend_diff_pay'] > 0:
                st.markdown(f"- Weekend Differential Pay: ${data['weekend_diff_pay']:.2f}")
            if data['on_call_diff_pay'] > 0:
                st.markdown(f"- On-Call Differential Pay: ${data['on_call_diff_pay']:.2f}")
            st.markdown(f"- Regular Earnings: ${data['regular_earnings']:.2f}")
            st.markdown(f"- Overtime Earnings: ${data['overtime_earnings']:.2f}")
            st.markdown(f"- Total Earnings: ${data['total_weekly_pay']:.2f}")
            st.markdown("---")

        st.info("**Disclaimer:** Tax calculations are estimates and may not reflect your actual tax liability. Please consult a tax professional for accurate information.")

        # Visualization: Bar Chart of Earnings per Week
        st.subheader("Earnings Breakdown per Week")

        # Prepare data for bar chart
        df_weekly = pd.DataFrame(weekly_data)
        df_melted = df_weekly.melt(
            id_vars=['week'],
            value_vars=['base_pay', 'charge_nurse_pay', 'night_diff_pay', 'weekend_diff_pay', 'on_call_diff_pay', 'overtime_earnings'],
            var_name='Earning Type',
            value_name='Amount'
        )

        # Map earning types to more readable labels
        earning_type_labels = {
            'base_pay': 'Base Pay',
            'charge_nurse_pay': 'Charge Nurse Pay',
            'night_diff_pay': 'Night Differential',
            'weekend_diff_pay': 'Weekend Differential',
            'on_call_diff_pay': 'On-Call Differential',
            'overtime_earnings': 'Overtime Pay'
        }
        df_melted['Earning Type'] = df_melted['Earning Type'].map(earning_type_labels)

        # Create the stacked bar chart
        chart = alt.Chart(df_melted).mark_bar().encode(
            x=alt.X('week:N', title='Week'),
            y=alt.Y('Amount:Q', title='Earnings ($)', stack='zero'),
            color=alt.Color('Earning Type:N', legend=alt.Legend(title="Earning Components")),
            tooltip=['week', 'Earning Type', 'Amount']
        ).properties(
            width=700,
            height=400
        )

        st.altair_chart(chart, use_container_width=True)

        # Visualization: Calendar View of Work Periods
        st.subheader("Work Periods Calendar View")

        # Gather all dates with work periods
        work_dates = []
        for start, end, is_on_call in st.session_state.work_periods:
            current_date = start.date()
            end_date = end.date()
            while current_date <= end_date:
                work_dates.append(current_date)
                current_date += timedelta(days=1)

        work_dates = list(set(work_dates))  # Remove duplicates
        work_dates.sort()

        if work_dates:
            # Generate calendars for all months that have work dates
            min_date = work_dates[0].replace(day=1)
            max_date = work_dates[-1].replace(day=1)

            months = []
            current_month = min_date
            while current_month <= max_date:
                months.append(current_month)
                current_month += relativedelta(months=1)

            # Create HTML calendars
            calendars_html = ""
            for month in months:
                cal = calendar.HTMLCalendar(calendar.SUNDAY)
                # Corrected line here
                month_html = cal.formatmonth(month.year, month.month)
                soup = BeautifulSoup(month_html, 'html.parser')

                # Highlight work dates
                for day in soup.find_all('td'):
                    if day.text:
                        try:
                            day_number = int(day.text)
                            date_obj = date(month.year, month.month, day_number)
                            if date_obj in work_dates:
                                day['style'] = 'background-color: #90EE90; font-weight: bold;'
                        except ValueError:
                            continue  # Skip if day.text is not a number

                # Add month title
                month_title = f"<h3 style='text-align:center;'>{month.strftime('%B %Y')}</h3>"
                calendars_html += month_title + str(soup)

            # Display the calendars
            st.components.v1.html(calendars_html, height=600, scrolling=True)
        else:
            st.write("No work periods to display on the calendar.")
