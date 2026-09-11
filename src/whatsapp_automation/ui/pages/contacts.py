import pandas as pd
import streamlit as st

from ...core import contacts as contact_engine
from ...data.session import get_session


def render_contacts_page():
    st.title("📇 Contacts & Groups Management")
    st.caption("Organize your WhatsApp contacts, group chats, tags, and bulk import CSVs.")

    db = get_session()
    try:
        tab1, tab2, tab3 = st.tabs(["📋 View Contacts", "➕ Add Contact / Group", "📥 CSV Import Wizard"])

        with tab1:
            st.subheader("Filter & Search Contacts")
            col1, col2, col3 = st.columns([2, 1, 1])
            search_query = col1.text_input("🔍 Search by Name, Ref, or Notes", "")
            tag_filter = col2.text_input("🏷️ Tag Filter", "")
            type_filter = col3.selectbox("Type", ["All", "Individual Contacts", "Groups"])

            is_group_param = None
            if type_filter == "Individual Contacts":
                is_group_param = False
            elif type_filter == "Groups":
                is_group_param = True

            contacts = contact_engine.list_contacts(
                db,
                search=search_query if search_query.strip() else None,
                tag=tag_filter if tag_filter.strip() else None,
                is_group=is_group_param,
                limit=500,
            )

            if contacts:
                df_data = []
                for c in contacts:
                    df_data.append(
                        {
                            "ID": c.id,
                            "Name": c.display_name,
                            "WhatsApp Ref": c.whatsapp_ref,
                            "Type": "Group Chat" if c.is_group else "Contact",
                            "Tags": ", ".join(c.tags),
                            "Notes": c.notes or "",
                            "Created At": c.created_at.strftime("%Y-%m-%d %H:%M") if c.created_at else "",
                        }
                    )
                st.dataframe(pd.DataFrame(df_data), use_container_width=True)

                st.markdown("---")
                st.subheader("Action on Selected Contact")
                c_id_input = st.number_input("Enter Contact ID to archive (soft-delete):", min_value=1, step=1)
                if st.button("Archive Contact"):
                    if contact_engine.soft_delete_contact(db, int(c_id_input)):
                        st.success(f"Archived contact ID {c_id_input}")
                        st.rerun()
                    else:
                        st.error("Contact ID not found.")
            else:
                st.info("No contacts found matching criteria.")

        with tab2:
            st.subheader("Create New Contact or Group")
            with st.form("create_contact_form"):
                d_name = st.text_input("Display Name *", placeholder="e.g. John Doe or Study Group")
                wa_ref = st.text_input("WhatsApp Identifier (Phone number or exact Group Name) *", placeholder="+1234567890 or 4th Year Study Group")
                is_grp = st.checkbox("Is WhatsApp Group Chat?")
                tags_str = st.text_input("Tags (comma separated)", placeholder="study-group, urgent, 2026")
                notes_val = st.text_area("Notes", placeholder="Optional notes...")
                submit_btn = st.form_submit_button("Save Contact")

                if submit_btn:
                    if not d_name.strip() or not wa_ref.strip():
                        st.error("Display Name and WhatsApp Identifier are required.")
                    else:
                        tag_list = [t.strip() for t in tags_str.split(",") if t.strip()]
                        c = contact_engine.create_contact(
                            db,
                            display_name=d_name,
                            whatsapp_ref=wa_ref,
                            is_group=is_grp,
                            tags=tag_list,
                            notes=notes_val,
                        )
                        st.success(f"Contact '{c.display_name}' created successfully (ID: {c.id})!")
                        st.rerun()

        with tab3:
            st.subheader("Bulk Import Contacts from CSV")
            uploaded_file = st.file_uploader("Choose a CSV file", type=["csv"])
            if uploaded_file is not None:
                content = uploaded_file.getvalue().decode("utf-8-sig")
                df_preview = pd.read_csv(uploaded_file)
                st.markdown("#### CSV Preview (First 5 rows)")
                st.dataframe(df_preview.head(), use_container_width=True)

                cols = list(df_preview.columns)
                st.markdown("#### Column Mapping")
                c_col1, c_col2, c_col3 = st.columns(3)
                name_map = c_col1.selectbox("Name Column", cols, index=0)
                ref_map = c_col2.selectbox("WhatsApp Ref Column", cols, index=min(1, len(cols) - 1))
                tag_map = c_col3.selectbox("Tags Column (Optional)", ["None"] + cols, index=0)

                is_group_csv = st.checkbox("Flag all imported rows as WhatsApp Groups?")
                skip_dups = st.checkbox("Skip duplicate contacts (matched by name or phone)?", value=True)

                if st.button("Run Bulk Import"):
                    mapping = {"display_name": name_map, "whatsapp_ref": ref_map}
                    if tag_map != "None":
                        mapping["tags"] = tag_map

                    res = contact_engine.bulk_import_csv(
                        db,
                        csv_text_or_path=content,
                        column_mapping=mapping,
                        is_group=is_group_csv,
                        skip_duplicates=skip_dups,
                    )

                    st.success(f"Import completed! Successfully imported: {res['imported_count']} rows.")
                    st.info(f"Skipped Duplicates: {res['skipped_duplicates_count']}")
                    if res["errors"]:
                        st.warning("Warnings / Errors during import:")
                        for err in res["errors"]:
                            st.write(f"- {err}")

    finally:
        db.close()
