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
    "Fresh cut": "مقطع طازج",
    "Medium slices": "شرائح متوسطة",
    "Regular Cut": "تقطيع منتظم",
    "Fine Grated": "مبشور ناعم",
    "Whole piece": "قطعة واحدة",
    "Rough Grated": "مبشور خشن",
    "Sandwich slices": "شرائح للساندويتش",
    "Thick slices": "شرائح سميكة",
    "Thin slices": "شرائح رفيعة",
    "Medium cubes": "مكعبات متوسطة",
    "Big cubes": "مكعبات كبيرة",
    "Small cubes": "مكعبات صغيرة",
    "Ball": "كُرة",
    # Add the corrected "Large cubes" translation
    "Large cubes": "مكعبات كبيرة" # Assuming "Large cubes" should map to the same as "Big cubes" based on previous output
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

                # === Translate ===
                unmatched_terms = set()
                for i, row in df.iterrows():
                    en = str(row["English Instructions"]).strip()
                    ar = ""

                    if en in translation_dict:
                        ar = translation_dict[en]
                    elif en.isdigit():
                        ar = en
                    elif pd.notna(row["Arabic Instructions"]):
                        ar = str(row["Arabic Instructions"]).strip()
                    else:
                        unmatched_terms.add(en)

                    df.at[i, "Arabic Instructions"] = ar

                # === Translation Results Section ===
                st.header("2. Review Translation Results")
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
                instruction_rows_for_check = df[~((df["English Instructions"].astype(str).str.strip() == df["Arabic Instructions"].astype(str).str.strip()) & (df["English Instructions"].astype(str).str.strip().str.isdigit()))].copy()

                # Filter out rows where either English or Arabic instruction is empty after translation/processing
                instruction_rows_for_check = instruction_rows_for_check[(instruction_rows_for_check["English Instructions"].astype(str).str.strip() != "") & (instruction_rows_for_check["Arabic Instructions"].astype(str).str.strip() != "")]


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
                instruction_rows = df[~((df["English Instructions"].astype(str).str.strip() == df["Arabic Instructions"].astype(str).str.strip()) & (df["English Instructions"].astype(str).str.strip().str.isdigit()))].copy()

                # Filter out rows where either English or Arabic instruction is empty after translation/processing
                instruction_rows = instruction_rows[(instruction_rows["English Instructions"].astype(str).str.strip() != "") & (instruction_rows["Arabic Instructions"].astype(str).str.strip() != "")]


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
                        rows = []
                        current_sku = None

                        # Re-iterate through the original DataFrame to capture SKUs and their subsequent instructions
                        for _, row in df.iterrows():
                            en = str(row["English Instructions"]).strip()
                            ar = str(row["Arabic Instructions"]).strip()

                            if en == ar and en.isdigit():
                                current_sku = en
                            elif current_sku and en and ar:
                                 # Only add instruction rows that are in our confirmed unique list
                                 # Ensure the pair exists in the unique_instructions dataframe
                                 if not unique_instructions[(unique_instructions["English Instructions"].astype(str).str.strip() == en) & (unique_instructions["Arabic Instructions"].astype(str).str.strip() == ar)].empty:
                                    rows.append({
                                        "sku": current_sku,
                                        "instruction_en": en,
                                        "instruction_ar": ar
                                    })

                        if rows:
                            # Generate Magento CSV format
                            magento_rows = []
                            sku_instructions = defaultdict(list)

                            for row in rows:
                                sku_instructions[row["sku"]].append({
                                    "en": row["instruction_en"],
                                    "ar": row["instruction_ar"]
                                })

                            def format_options(instructions_list):
                                en_options = []
                                ar_options = []
                                for instruction in instructions_list:
                                    # Basic custom option format - may need adjustment
                                    en_options.append(f"name=Custom Option,type=radio,required=0,price=0,price_type=fixed,sku=,option_title={instruction['en']}")
                                    ar_options.append(f"name=Custom Option,type=radio,required=0,price=0,price_type=fixed,sku=,option_title={instruction['ar']}")

                                return "|".join(en_options), "|".join(ar_options)


                            for sku, instructions_list in sku_instructions.items():
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
                            st.warning("⚠️ No valid instruction rows found to export to Magento CSV after confirmation.")

                else:
                     # If confirm button hasn't been clicked yet, display a message
                     st.info("Click 'Confirm Instructions' to generate the Magento CSV.")


            else:
                st.warning("⚠️ No valid instruction pairs found in the uploaded file after translation.")


    except Exception as e:
        st.error(f"An error occurred during processing: {e}")

else:
    st.info("Please upload an Excel file to begin.")
