import streamlit as st
from datetime import datetime, timedelta
from collections import defaultdict

# Function definitions
def determine_shift_differential(hour):
    if 19 <= hour or hour < 7:
        return 'Night Shift'
    else:
        return 'Day Shift'

def is_weekend(date):
    return date.weekday() >= 5  # 5 = Saturday, 6 = Sunday

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

# Function to calculate total earnings
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
            rate = hourly_rate

            if charge_nurse_pay > 0:
                rate += charge_nurse_pay

            if differential == 'Night Shift':
                if differential_type == "Percentage":
                    rate += hourly_rate * (night_differential / 100)
                else:
                    rate += night_differential

            if weekend:
                if differential_type == "Percentage":
                    rate += hourly_rate * (weekend_differential / 100)
                else:
                    rate += weekend_differential

            if is_on_call:
                if differential_type == "Percentage":
                    rate += hourly_rate * (on_call_differential / 100)
                else:
                    rate += on_call_differential

            hours_worked.append({'datetime': current_time, 'rate': rate, 'week_start': week_start})
            current_time += timedelta(hours=1)

    week_hours_list = defaultdict(list)
    for hour_data in hours_worked:
        week_start = hour_data['week_start']
        week_hours_list[week_start].append(hour_data)

    total_hours = 0
    total_earnings = 0
    weekly_data = []

    for week_start, hours_list in week_hours_list.items():
        hours = len(hours_list)
        earnings = sum([h['rate'] for h in hours_list])

        if hours > 40:
            # Sort hours by time to identify overtime hours
            hours_list = sorted(hours_list, key=lambda x: x['datetime'])
            regular_hours_list = hours_list[:40]
            overtime_hours_list = hours_list[40:]

            regular_earnings = sum([h['rate'] for h in regular_hours_list])
            overtime_earnings = sum([h['rate'] * 1.5 for h in overtime_hours_list])  # 1.5x for overtime
            week_total_earnings = regular_earnings + overtime_earnings

            regular_hours = 40
            overtime_hours = hours - 40
        else:
            regular_hours = hours
            overtime_hours = 0
            regular_earnings = earnings
            overtime_earnings = 0
            week_total_earnings = earnings

        total_hours += hours
        total_earnings += week_total_earnings

        weekly_data.append({
            'week_start': week_start,
            'regular_hours': regular_hours,
            'overtime_hours': overtime_hours,
            'regular_earnings': regular_earnings,
            'overtime_earnings': overtime_earnings,
            'week_total_earnings': week_total_earnings
        })

    return total_earnings, total_hours, weekly_data

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

start_date = st.date_input("Start Date")
start_time = st.time_input("Start Time")
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

if st.button("Add Work Period"):
    start_datetime = datetime.combine(start_date, start_time)
    end_datetime = datetime.combine(end_date, end_time)
    shift_type = determine_shift_differential(start_time.hour)

    if check_overlap(start_datetime, end_datetime, st.session_state.work_periods):
        st.error("The shift overlaps with an existing shift. Please check the timings.")
    else:
        st.session_state.work_periods.append((start_datetime, end_datetime, is_on_call))
        formatted_shift = (
            f"{start_date.strftime('%B %d')} to {end_date.strftime('%B %d')}, {shift_type} from "
            f"{start_time.strftime('%I:%M %p').lower()} to {end_time.strftime('%I:%M %p').lower()}"
        )
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
    total_earnings, total_hours, weekly_data = calculate_total_earnings(
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
        st.markdown(f"- Regular Earnings: ${data['regular_earnings']:.2f}")
        st.markdown(f"- Overtime Earnings: ${data['overtime_earnings']:.2f}")
        st.markdown(f"- Total Earnings: ${data['week_total_earnings']:.2f}")
        st.markdown("---")

    st.info("**Disclaimer:** Tax calculations are estimates and may not reflect your actual tax liability. Please consult a tax professional for accurate information.")
