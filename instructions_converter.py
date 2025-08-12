# This is the content of the instructions_converter.py file
import streamlit as st
import pandas as pd
import os
from collections import defaultdict

# === Folder & File Setup ===
folder = "/content/sample_data"
# Input filename will be determined by the user upload
output_excel_name = "Import_instructions_localized.xlsx"
output_csv_name = "instruction_import_magento_generated.csv" # Enforce the output CSV filename

output_excel_path = os.path.join(folder, output_excel_name)
output_csv_path = os.path.join(folder, output_csv_name)

# Ensure the folder exists
os.makedirs(folder, exist_ok=True)

st.title("Instruction Localizer and Magento CSV Generator")

# === Unified Translation Mapping ===
translation_dict = {
    "Fresh Cut": "مقطع طازج", # Updated term
    "Medium Slices": "شرائح متوسطة", # Updated term
    "Regular Cut": "تقطيع عادي", # Updated term
    "Fine Grated": "مبشور ناعم",
    "Whole Piece": "قطعة واحدة", # Updated term
    "Rough Grated": "مبشور خشن",
    "Sandwich Slices": "تقطيع ساندوتشات", # Updated term
    "Thick Slices": "تقطيع سميك", # Updated term
    "Thin Slices": "تقطيع رفيع", # Updated term
    "Medium Cubes": "مكعبات متوسطة", # Updated term
    "Large Cubes": "مكعبات كبيرة", # Updated term
    "Small Cubes": "مكعبات صغيرة", # Updated term
    "Ball": "كُرة",
    "Firm": "قوام متماسك", # Added new term
    "Soft": "قوام طري" # Added new term
}

# === File Upload Section ===
st.header("1. Upload Your Excel File")
st.write("Please upload your Excel file containing 'English Instructions' and 'Arabic Instructions'.")
uploaded_file = st.file_uploader("Choose an Excel file", type=["xlsx"])

df = None # Initialize df to None

if uploaded_file is not None:
    try:
        # Read the uploaded Excel file
        df = pd.read_excel(uploaded_file)
        st.success("✅ File uploaded successfully!")

        # Use a container for the rest of the processing steps
        processing_container = st.container()

        with processing_container:
            # === Column Normalization ===
            if "English Instructions" not in df.columns:
                st.error("❌ Missing required column: 'English Instructions'")
                df = None # Invalidate df to stop processing

            if df is not None:
                if "Arabic Instructions" not in df.columns:
                    if "Arabic Instructions*" in df.columns:
                        df.rename(columns={"Arabic Instructions*": "Arabic Instructions"}, inplace=True)
                    else:
                        df["Arabic Instructions"] = "" # Add the column if it doesn't exist

                # Ensure columns are strings before stripping and checking
                df["English Instructions"] = df["English Instructions"].astype(str).str.strip()
                df["Arabic Instructions"] = df["Arabic Instructions"].astype(str).str.strip()


                # === Translate and Process Data ===
                st.header("2. Process and Translate Instructions")
                unmatched_terms = set()
                processed_rows = []
                current_sku = None

                for i, row in df.iterrows():
                    en = row["English Instructions"]
                    ar = row["Arabic Instructions"] # Start with existing Arabic

                    translated_ar = ar # Initialize translated_ar with existing Arabic

                    if en in translation_dict:
                        translated_ar = translation_dict[en]
                    elif en.isdigit():
                        current_sku = en # Update current SKU when a digit is found
                        translated_ar = en # Keep the digit for the SKU row
                    elif ar == "" and en != "": # If English is not in dictionary and no existing Arabic
                         unmatched_terms.add(en)


                    # Append processed row
                    processed_rows.append({
                        "English Instructions": en,
                        "Arabic Instructions": translated_ar,
                        "sku": current_sku # Associate with the current SKU
                    })

                # Create a new DataFrame from processed rows
                processed_df = pd.DataFrame(processed_rows)

                # Update the original DataFrame's Arabic column with translated/processed values
                df["Arabic Instructions"] = processed_df["Arabic Instructions"]


                # === Translation Results Section ===
                # Move this section after initial processing
                if unmatched_terms:
                    st.warning("⚠️ The following English terms were not found in the translation dictionary and were not digits:")
                    for t in sorted(unmatched_terms):
                        st.write(f"- {t}")
                    st.info("Please ensure these terms have Arabic translations in the input file or add them to the translation dictionary in the script.")
                else:
                    st.success("✅ All English terms were either translated or identified as potential SKUs.")


                # === Check for Non-Unified Instructions Section ===
                st.header("3. Check for Instruction Inconsistencies")

                # Filter out rows that are likely SKUs (where EN and AR are the same and digits)
                # Use the processed_df for checking inconsistencies based on the translated/filled Arabic
                instruction_rows_for_check = processed_df[~((processed_df["English Instructions"] == processed_df["Arabic Instructions"]) & (processed_df["English Instructions"].str.isdigit()))].copy()

                # Filter out rows where either English or Arabic instruction is empty after translation/processing
                instruction_rows_for_check = instruction_rows_for_check[(instruction_rows_for_check["English Instructions"] != "") & (instruction_rows_for_check["Arabic Instructions"] != "")]


                non_unified_instructions = {}
                if not instruction_rows_for_check.empty:
                    # Group by English Instructions and check for unique Arabic translations
                    grouped = instruction_rows_for_check.groupby("English Instructions")["Arabic Instructions"].unique()

                    for en_instruction, ar_translations in grouped.items():
                        if len(ar_translations) > 1:
                            non_unified_instructions[en_instruction] = ar_translations.tolist()

                if non_unified_instructions:
                    st.warning("⚠️ **Warning: Instruction Inconsistencies Found!**")
                    with st.expander("Details of Inconsistencies"):
                        st.write("The following English instructions have multiple different Arabic translations:")
                        for en, ar_list in non_unified_instructions.items():
                            st.write(f"- **{en}**: {', '.join(ar_list)}")
                    st.info("Please review your input data for these instructions to ensure consistency before proceeding.")
                else:
                    st.success("✅ No instruction inconsistencies found.")


                # === Instruction Confirmation Section ===
                st.header("4. Review and Confirm Instructions")

                # Filter out rows that are likely SKUs (where EN and AR are the same and digits)
                # Use the processed_df for displaying unique instructions
                instruction_rows = processed_df[~((processed_df["English Instructions"] == processed_df["Arabic Instructions"]) & (processed_df["English Instructions"].str.isdigit()))].copy()

                # Filter out rows where either English or Arabic instruction is empty after translation/processing
                instruction_rows = instruction_rows[(instruction_rows["English Instructions"] != "") & (instruction_rows["Arabic Instructions"] != "")]


                if not instruction_rows.empty:
                    unique_instructions = instruction_rows[["English Instructions", "Arabic Instructions"]].drop_duplicates().reset_index(drop=True)
                    st.write("The following unique instruction pairs will be used for generating custom options:")
                    st.dataframe(unique_instructions)

                    # Add a confirmation button in a separate container or section if needed
                    # For now, keeping it close to the table for clarity
                    confirm_button = st.button("Confirm Instructions and Generate Magento CSV")

                    if confirm_button:
                        # === Save Updated Excel (optional, depending on need for intermediate file) ===
                        # To provide a download for the localized Excel, we need to save it.
                        df.to_excel(output_excel_path, index=False)
                        st.success(f"✅ Localized Excel saved to: {output_excel_path}")

                        # === Build Magento-ready CSV ===
                        rows_for_csv = []
                        # Use the processed_df which already has SKUs associated
                        # Filter out SKU rows and rows with empty instructions
                        instruction_rows_for_csv = processed_df[
                            ~((processed_df["English Instructions"] == processed_df["Arabic Instructions"]) & (processed_df["English Instructions"].str.isdigit())) &
                            (processed_df["English Instructions"] != "") &
                            (processed_df["Arabic Instructions"] != "")
                        ].copy()


                        if not instruction_rows_for_csv.empty:
                            # Ensure that only instructions from the confirmed unique list are included
                            # Merge with unique_instructions to filter
                            merged_instructions = pd.merge(
                                instruction_rows_for_csv,
                                unique_instructions,
                                on=["English Instructions", "Arabic Instructions"],
                                how="inner"
                            )

                            if not merged_instructions.empty:
                                # Group by SKU to build the Magento format
                                sku_instructions_for_csv = defaultdict(list)
                                for _, row in merged_instructions.iterrows():
                                     sku_instructions_for_csv[row["sku"]].append({
                                         "en": row["English Instructions"],
                                         "ar": row["Arabic Instructions"]
                                     })


                                def format_options(instructions_list):
                                    en_options = []
                                    ar_options = []
                                    for instruction in instructions_list:
                                        # Basic custom option format - may need adjustment
                                        # Escape commas in instruction titles if necessary for Magento import
                                        en_title = instruction['en'].replace(',', '\\,')
                                        ar_title = instruction['ar'].replace(',', '\\,')
                                        en_options.append(f"name=Custom Option,type=radio,required=0,price=0,price_type=fixed,sku=,option_title={en_title}")
                                        ar_options.append(f"name=Custom Option,type=radio,required=0,price=0,price_type=fixed,sku=,option_title={ar_title}")

                                    return "|".join(en_options), "|".join(ar_options)


                                magento_rows = []
                                for sku, instructions_list in sku_instructions_for_csv.items():
                                    if sku is not None: # Only add if an SKU is associated
                                        custom_options_en, custom_options_ar = format_options(instructions_list)

                                        # Add row for the default store view (English)
                                        magento_rows.append({
                                            "sku": sku,
                                            "store_view_code": "", # Default store view
                                            "attribute_set_code": "Default",
                                            "product_type": "simple",
                                            "custom_options": custom_options_en
                                        })

                                        # Add row for the Arabic store view
                                        magento_rows.append({
                                            "sku": sku,
                                            "store_view_code": "ar_EG", # Arabic store view
                                            "attribute_set_code": "Default",
                                            "product_type": "simple",
                                            "custom_options": custom_options_ar
                                        })

                                if magento_rows:
                                    # Save output CSV
                                    magento_df = pd.DataFrame(magento_rows)
                                    magento_df.to_csv(output_csv_path, index=False, encoding="utf-8-sig")
                                    st.success(f"✅ Magento import file saved to: {output_csv_path} ({len(magento_rows)} rows)")

                                    # === Download Section ===
                                    st.header("5. Download Results")
                                    st.write("Click the buttons below to download the generated files.")

                                    with open(output_excel_path, "rb") as excel_file:
                                        st.download_button(
                                            label="⬇️ Download Localized Excel",
                                            data=excel_file,
                                            file_name=output_excel_name,
                                            mime="application/vnd.openxmlformats-officedocument.spreadsheet.sheet"
                                        )

                                    with open(output_csv_path, "rb") as csv_file:
                                        st.download_button(
                                            label="⬇️ Download Magento CSV",
                                            data=csv_file,
                                            file_name=output_csv_name,
                                            mime="text/csv"
                                        )

                                else:
                                     st.warning("⚠️ No valid instruction rows found with associated SKUs to export to Magento CSV after confirmation.")

                            else:
                                 st.warning("⚠️ No confirmed unique instruction pairs found in the filtered data to export to Magento CSV.")


                        else:
                             st.warning("⚠️ No valid instruction rows found after filtering to export to Magento CSV.")


                else:
                     # If confirm button hasn't been clicked yet, display a message
                     st.info("Click 'Confirm Instructions' to generate the Magento CSV.")


            else:
                st.warning("⚠️ No valid instruction pairs found in the uploaded file after translation.")


    except Exception as e:
        st.error(f"An error occurred during processing: {e}")

else:
    st.info("Please upload an Excel file to begin.")
