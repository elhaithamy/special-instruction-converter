import streamlit as st
import pandas as pd
from collections import defaultdict
from io import BytesIO

st.set_page_config(page_title="Products Special Instruction Reviewer & Importer", layout="wide")
st.title("🛠️ Products Special Instruction Reviewer & Importer")

# === Translation Dictionary ===
translation_dict = {
    "Fresh cut": "مقطع طازج",
    "Medium slices": "شرائح متوسطة",
    "Regular Cut": "تقطيع عادى",
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
    "Large cubes": "مكعبات كبيرة"
}

# === Upload Excel File ===
st.header("1. Upload Your Excel File")
uploaded_file = st.file_uploader("Choose an Excel file", type=["xlsx"])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
        st.success("✅ File uploaded successfully!")

        if "English Instructions" not in df.columns:
            st.error("Missing required column: 'English Instructions'")
            st.stop()

        if "Arabic Instructions" not in df.columns:
            if "Arabic Instructions*" in df.columns:
                df.rename(columns={"Arabic Instructions*": "Arabic Instructions"}, inplace=True)
            else:
                df["Arabic Instructions"] = ""

        # Translation process
        unmatched_terms = set()
        for i, row in df.iterrows():
            en = str(row["English Instructions"]).strip()
            if en in translation_dict:
                ar = translation_dict[en]
            elif en.isdigit():
                ar = en
            elif pd.notna(row["Arabic Instructions"]):
                ar = str(row["Arabic Instructions"]).strip()
            else:
                unmatched_terms.add(en)
                ar = ""
            df.at[i, "Arabic Instructions"] = ar

        # === Step 2: Review Translation Results ===
        st.header("2. Review Translation Results")
        if unmatched_terms:
            st.warning("Untranslated English terms found:")
            for term in sorted(unmatched_terms):
                st.write(f"- {term}")
        else:
            st.success("✅ All terms translated or valid SKUs.")

        # === Step 3: Check for Inconsistencies ===
        st.header("3. Check for Instruction Inconsistencies")
        filtered = df[
            ~((df["English Instructions"].astype(str) == df["Arabic Instructions"].astype(str)) &
              df["English Instructions"].astype(str).str.isdigit())
        ]
        grouped = filtered.groupby("English Instructions")["Arabic Instructions"].nunique()
        inconsistent = grouped[grouped > 1]

        if not inconsistent.empty:
            st.warning("Inconsistent Arabic translations found:")
            for instr in inconsistent.index:
                values = df[df["English Instructions"] == instr]["Arabic Instructions"].unique()
                st.write(f"- {instr}: {', '.join(values)}")
        else:
            st.success("✅ No inconsistencies found.")

        # === Step 4: Review and Confirm Instructions ===
        st.header("4. Review and Confirm Instructions")
        instruction_rows = df[
            ~((df["English Instructions"] == df["Arabic Instructions"]) &
              df["English Instructions"].astype(str).str.isdigit())
        ]
        instruction_rows = instruction_rows[
            (instruction_rows["English Instructions"].astype(str).str.strip() != "") &
            (instruction_rows["Arabic Instructions"].astype(str).str.strip() != "")
        ]
        unique_instructions = instruction_rows[["English Instructions", "Arabic Instructions"]].drop_duplicates()

        st.dataframe(unique_instructions)

        if st.button("✅ Confirm Instructions and Generate Magento CSV"):
            rows = []
            current_sku = None
            for _, row in df.iterrows():
                en = str(row["English Instructions"]).strip()
                ar = str(row["Arabic Instructions"]).strip()

                if en == ar and en.isdigit():
                    current_sku = en
                elif current_sku and en and ar:
                    if not unique_instructions[
                        (unique_instructions["English Instructions"] == en) &
                        (unique_instructions["Arabic Instructions"] == ar)
                    ].empty:
                        rows.append({
                            "sku": current_sku,
                            "instruction_en": en,
                            "instruction_ar": ar
                        })

            # === Group Instructions by SKU ===
            magento_rows = []
            sku_grouped = defaultdict(list)
            for row in rows:
                sku_grouped[row["sku"]].append({
                    "en": row["instruction_en"],
                    "ar": row["instruction_ar"]
                })

            for sku, instructions in sku_grouped.items():
                def format(insts, lang):
                    return "|".join([
                        f"name=Custom Option,type=radio,required=0,price=0,price_type=fixed,sku=,option_title={i[lang]}"
                        for i in insts
                    ])
                magento_rows.append({
                    "sku": sku,
                    "store_view_code": "",
                    "attribute_set_code": "Default",
                    "product_type": "simple",
                    "custom_options": format(instructions, "en")
                })
                magento_rows.append({
                    "sku": sku,
                    "store_view_code": "ar_EG",
                    "attribute_set_code": "Default",
                    "product_type": "simple",
                    "custom_options": format(instructions, "ar")
                })

            magento_df = pd.DataFrame(magento_rows)

            # === Create Files for Download ===
            excel_bytes = BytesIO()
            df.to_excel(excel_bytes, index=False, engine='openpyxl')
            excel_bytes.seek(0)

            csv_bytes = BytesIO()
            magento_df.to_csv(csv_bytes, index=False, encoding="utf-8-sig")
            csv_bytes.seek(0)

            # === Step 5: Download Results ===
            st.header("5. Download Results")
            st.success("✅ Files generated successfully!")

            st.download_button(
                label="⬇️ Download Localized Excel",
                data=excel_bytes,
                file_name="Import_instructions_localized.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            st.download_button(
                label="⬇️ Download Magento CSV",
                data=csv_bytes,
                file_name="instruction_import_magento_generated.csv",
                mime="text/csv"
            )

    except Exception as e:
        st.error(f"❌ Error: {e}")

else:
    st.info("📂 Please upload a file to get started.")
