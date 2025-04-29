import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(
   page_title=" Contract Info ",
   page_icon="🩻"
)

st.title("I-CAB M Contract Info")

uploaded_file = st.file_uploader("Upload an Excel file", type=["xlsx", "xls"])

if uploaded_file is not None:
    try:
        # Read the uploaded file into a DataFrame
        df = pd.read_excel(uploaded_file)

        # Clean 'effective_date' column
        if 'effective_date' in df.columns:
            df['effective_date'] = pd.to_datetime(df['effective_date'], errors='coerce')
            df = df.dropna(subset=['effective_date'])  # Remove rows with invalid dates
        else:
            st.warning("The file does not contain an 'effective_date' column.")

        # Filter by description
        if 'description' in df.columns:
            descriptions = df['description'].dropna().unique()

            # Add filter input for descriptions
            filter_text = st.text_input("Type to filter transporters:")
            filtered_options = [d for d in sorted(descriptions) if filter_text.lower() in d.lower()]

            selected_descriptions = st.multiselect(
                "Select one or more transporters:",
                options=filtered_options,
                key="description_selector"
            )

            if selected_descriptions:
                st.subheader("Grouped by Transporter")
                today = pd.to_datetime(datetime.today().date())

                # Filter dataframe based on descriptions
                filtered_df = df[df['description'].isin(selected_descriptions)]

                # Group and summarize
                grouped = (
                    filtered_df
                    .groupby(['description', 'serial_nr'])['effective_date']
                    .min()
                    .reset_index()
                    .rename(columns={
                        'description': 'Transporter',
                        'serial_nr': 'Serial Number',
                        'effective_date': 'First Effective Date'
                    })
                )

                # Format date and calculate months
                grouped['First Effective Date'] = grouped['First Effective Date'].dt.to_period('M').astype(str)

                # Calculate Active Months: months between First Effective Date and today
                grouped['Active Months'] = grouped['First Effective Date'].apply(
                    lambda date: (today.year - int(date[:4])) * 12 + (today.month - int(date[5:7]))
                )

                # Show final result
                st.dataframe(grouped.sort_values(by=['Transporter', 'Serial Number']))

                # --- Summary Table: Contract Age Buckets ---
                # Convert Active Months to Years
                grouped['Contract Age (Years)'] = grouped['Active Months'] / 12

                # Define bins and labels
                bins = [0, 1, 2, 3, float('inf')]
                labels = ['0-1', '1-2', '2-3', '3+']

                # Categorize into buckets
                grouped['Contract Age Bucket'] = pd.cut(grouped['Contract Age (Years)'], bins=bins, labels=labels, right=False)

                # Count how many fall into each bucket
                summary = grouped['Contract Age Bucket'].value_counts().reindex(labels, fill_value=0).reset_index()
                summary.columns = ['Contract Age (years)', 'Count']

                # Display summary table
                st.subheader("Summary of Contract Ages")
                st.table(summary)

        else:
            st.warning("The uploaded file does not contain a 'description' column.")

        # Input for serial numbers history
        serial_input = st.text_input("Enter one or more serial numbers (comma separated):")
        if serial_input:
            serial_numbers = [sn.strip() for sn in serial_input.split(",")]

            # Filter data for specified serial numbers
            serial_history = df[df['serial_nr'].isin(serial_numbers)]

            if not serial_history.empty:
                st.subheader("Serial Number History")
                # Sort by serial number and effective date (old to new)
                serial_history_sorted = serial_history.sort_values(by=['serial_nr', 'effective_date'])

                # Remove duplicates based on both serial number and effective date
                serial_history_sorted = serial_history_sorted.drop_duplicates(subset=['serial_nr', 'effective_date'])

                # Concatenate 'effective_date' and 'description' for each serial number occurrence
                serial_history_sorted['Effective Date and Description'] = (
                    serial_history_sorted['effective_date'].dt.strftime('%Y-%m-%d') + ' - ' + serial_history_sorted['description']
                )

                # Add the "First Effective Date" and "Active Months" columns before groupby
                serial_history_sorted['First Effective Date'] = serial_history_sorted.groupby('serial_nr')['effective_date'].transform('min')
                serial_history_sorted['Active Months'] = serial_history_sorted['First Effective Date'].apply(
                    lambda date: (today.year - date.year) * 12 + (today.month - date.month)
                )

                # Group by 'serial_nr' and concatenate all occurrences into a single "Device History" column
                serial_history_pivoted = serial_history_sorted.groupby('serial_nr').agg(
                    Device_History=('Effective Date and Description', lambda x: ' | '.join(x)),
                    First_Effective_Date=('First Effective Date', 'min'),
                    Active_Months=('Active Months', 'min'),
                    Count=('serial_nr', 'size')
                ).reset_index()

                # Reorder columns
                columns = ['serial_nr', 'First_Effective_Date', 'Active_Months', 'Count', 'Device_History']
                serial_history_pivoted = serial_history_pivoted[columns]

                # Display the pivoted DataFrame
                st.dataframe(serial_history_pivoted)

            else:
                st.warning("No data found for the specified serial numbers.")

    except Exception as e:
        st.error(f"Error reading the file: {e}")

