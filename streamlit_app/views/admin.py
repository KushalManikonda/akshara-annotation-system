import pandas as pd
import streamlit as st
from datetime import datetime, timedelta

import zipfile
import uuid
import shutil
from pathlib import Path

from database.enums import UserRole

from utils.time import now
from utils.validation import is_not_empty, is_valid_email

from services.user_service import (
    create_user,
    get_all_users,
    update_user,
    delete_user,
)

from services.audio_service import (
    upload_audio,
    get_all_datasets,
    get_dataset_files,
    delete_audio,
    delete_dataset,
    import_metadata_for_dataset,
    get_csv_column_names,
)

from services.assignment_service import (
    get_unassigned_audio,
    get_annotators,
    assign_audio,
    get_assignments,
    unassign_audio
)

from utils.logout import logout

# =====================================================
# Dashboard
# =====================================================
def dashboard():
    from services.analytics_service import get_kpi_summary
    
    st.title("Admin Dashboard")
    st.write(f"Welcome, **{st.session_state.user.username}**")
    st.divider()

    kpi = get_kpi_summary()

    # Cards layout using containers
    with st.container(border=True):
        st.subheader("Platform Metrics")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Users", kpi["total_users"])
        c2.metric("Total Audio Files", kpi["total_audio"])
        c3.metric("Audio Duration", f"{kpi['total_duration']:.2f}s")
        c4.metric("Approval Rate", f"{kpi['approved_pct']:.1f}%")

    with st.container(border=True):
        st.subheader("Task Pipeline")
        c1, c2, c3 = st.columns(3)
        c1.metric("Approved", f"{kpi['approved_count']} ✅")
        c2.metric("Pending Review", f"{kpi['submitted_count']} 📤")
        c3.metric("Drafts / In Progress", f"{kpi['draft_count']} ✏️")

    st.divider()
    st.info("Use the sidebar menu to navigate between admin pages.")


# =====================================================
# Users
# =====================================================
def users():

    st.title("👤 User Management")

    if "editing_user" not in st.session_state:
        st.session_state.editing_user = None

    if "delete_user" not in st.session_state:
        st.session_state.delete_user = None
    
    users_list = get_all_users()

    c1, c2 = st.columns([2,1])

    with c1:
        search = st.text_input(
            "Search",
            placeholder="Username or Email"
        )

    with c2:
        role_filter = st.selectbox(
            "Role",
            [
                "All",
                "Admin",
                "Annotator",
                "Reviewer"
            ]
        )

    filtered_users = []

    for user in users_list:

        if search:

            if (
                search.lower() not in user.username.lower()
                and
                search.lower() not in user.email.lower()
            ):
                continue

        if role_filter != "All":

            if user.role.value.title() != role_filter:
                continue

        filtered_users.append(user)

    users_list = filtered_users
    
    if users_list:
        
        # ── Table Header ─────────────────────────────────────────
        st.divider()
        h1, h2, h3, h4, h5 = st.columns([3, 2, 2, 1, 1])
        h1.markdown("**User (Email)**")
        h2.markdown("**Role & Status**")
        h3.markdown("**Last Login**")
        h4.markdown("**Edit**")
        h5.markdown("**Delete**")
        st.divider()

        # ── Table Rows ───────────────────────────────────────────
        for user in users_list:
            c1, c2, c3, c4, c5 = st.columns([3, 2, 2, 1, 1])

            with c1:
                st.markdown(f"**{user.username}**")
                st.caption(user.email)

            with c2:
                st.write(user.role.value.title())
                if user.last_seen:
                    if now() - user.last_seen < timedelta(minutes=2):
                        st.success("🟢 Online")
                    else:
                        st.caption("⚫ Offline")
                else:
                    st.caption("Never Logged In")

            with c3:
                if user.last_login:
                    st.write(user.last_login.strftime("%d-%m-%Y"))
                    st.caption(user.last_login.strftime("%I:%M %p"))
                else:
                    st.caption("-")
    
            with c4:
                if st.button("✏ Edit", key=f"edit_{user.id}", use_container_width=True):
                    st.session_state.editing_user = user.id

            with c5:
                if user.id != st.session_state.user.id:
                    if st.button("🗑 Del", key=f"delete_{user.id}", use_container_width=True):
                        st.session_state.delete_user = user.id

            st.divider()

    else:
        st.info("No users found.")

    if st.session_state.editing_user:

        selected = next(
            (
                u
                for u in users_list
                if u.id == st.session_state.editing_user
            ),
            None
        )

        if selected:

            st.subheader("Edit User")

            with st.form("edit_user"):
    
                username = st.text_input(
                    "Username",
                    value=selected.username
                )

                email = st.text_input(
                    "Email",
                    value=selected.email
                )

                role = st.selectbox(
                    "Role",
                    [
                        UserRole.ADMIN,
                        UserRole.ANNOTATOR,
                        UserRole.REVIEWER
                    ],
                    index=[
                        UserRole.ADMIN,
                        UserRole.ANNOTATOR,
                        UserRole.REVIEWER
                    ].index(selected.role)
                )

                c1, c2 = st.columns(2)

                save = c1.form_submit_button("Save")

                cancel = c2.form_submit_button("Cancel")
    
            if save:

                success, message = update_user(
                    selected.id,
                    username.strip(),
                    email.strip(),
                    role
                )

                if success:

                    st.success(message)

                    st.session_state.editing_user = None

                    st.rerun()

                else:

                    st.error(message)

            if cancel:

                st.session_state.editing_user = None

                st.rerun()
            
    st.divider()

    if st.session_state.delete_user:

        st.warning(
            "Delete this user?"
        )

        c1, c2 = st.columns(2)

        if c1.button("Yes"):

            success, message = delete_user(
                st.session_state.delete_user,
                st.session_state.user.id
            )

            if success:

                st.success(message)

            else:

                st.error(message)

            st.session_state.delete_user = None

            st.rerun()

        if c2.button("No"):

            st.session_state.delete_user = None

            st.rerun()
    
    st.divider()

    st.subheader("Create User")

    with st.form("create_user"):

        username = st.text_input("Username")

        email = st.text_input("Email")

        password = st.text_input(
            "Password",
            type="password"
        )

        confirm = st.text_input(
            "Confirm Password",
            type="password"
        )

        role = st.selectbox(
            "Role",
            [
                UserRole.ADMIN,
                UserRole.ANNOTATOR,
                UserRole.REVIEWER
            ],
            format_func=lambda x: x.value.title()
        )

        submitted = st.form_submit_button("Create User")

    if submitted:

        if not is_not_empty(username) or not is_not_empty(email) or not is_not_empty(password) or not is_not_empty(confirm):

            st.error("Fill all fields.")

        elif not is_valid_email(email):

            st.error("Invalid email format.")

        elif password != confirm:

            st.error("Passwords do not match.")

        else:

            user = create_user(
                username=username.strip(),
                email=email.strip(),
                password=password,
                role=role
            )

            if user:

                st.success("User created successfully.")

                st.rerun()

            else:

                st.error("Username or Email already exists.")

    st.divider()

    if st.button("← Back"):

        st.session_state.admin_page = "dashboard"

        st.rerun()


# =====================================================
# Audio Library
# =====================================================
def audio():
    st.title("🎙️ Audio Library")

    # ── Upload Section ─────────────────────────────────────────
    st.subheader("Upload New Dataset")

    # Counter incremented on successful upload to reset all widgets to placeholder state
    if "upload_session" not in st.session_state:
        st.session_state.upload_session = 0

    s = st.session_state.upload_session  # shorthand

    uploaded_zip = st.file_uploader(
        "Upload Audio Dataset (.zip)",
        type=["zip"],
        key=f"audio_zip_uploader_{s}",
    )

    language = st.selectbox(
        "Language",
        ["English", "Hindi", "Telugu"],
        key=f"audio_language_select_{s}",
    )

    st.markdown("**📄 Metadata CSV** *(optional — attach transcripts at upload time)*")
    st.caption("Upload a `metadata.csv` alongside the ZIP to link transcripts immediately.")

    meta_file = st.file_uploader(
        "Metadata file (optional)",
        type=["csv", "json"],
        key=f"audio_meta_uploader_{s}",
    )

    # Column mapping — appears dynamically when a CSV is selected
    fn_col = tr_col = tl_col = None

    if meta_file is not None and meta_file.name.lower().endswith(".csv"):

        cols = get_csv_column_names(meta_file)

        if cols:
            st.markdown("**Map CSV columns:**")
            col_options = ["(auto-detect)"] + cols

            m1, m2, m3 = st.columns(3)

            with m1:
                fn_col = st.selectbox(
                    "🎵 Filename column",
                    col_options,
                    key=f"upload_fn_col_{s}",
                )

            with m2:
                tr_col = st.selectbox(
                    "📝 Transcript column",
                    col_options,
                    key=f"upload_tr_col_{s}",
                )

            with m3:
                tl_col = st.selectbox(
                    "🌐 Translation column",
                    col_options,
                    key=f"upload_tl_col_{s}",
                )

            fn_col  = None if fn_col  == "(auto-detect)" else fn_col
            tr_col  = None if tr_col  == "(auto-detect)" else tr_col
            tl_col  = None if tl_col  == "(auto-detect)" else tl_col

    if st.button("⬆️ Upload", type="primary", key=f"upload_submit_btn_{s}"):

        if uploaded_zip is None:
            st.error("Please select a ZIP file.")

        else:
            with st.spinner("Uploading and extracting files…"):
                success = upload_audio(
                    uploaded_zip,
                    language,
                    st.session_state.user.id,
                )

            if not success:
                st.error("Upload failed. Check the logs.")

            else:
                # If a metadata file was also provided, import it now
                if meta_file is not None:
                    all_ds = get_all_datasets()
                    new_dataset = all_ds[0] if all_ds else None

                    if new_dataset:
                        with st.spinner("Importing metadata…"):
                            matched, total = import_metadata_for_dataset(
                                new_dataset.id,
                                meta_file,
                                filename_col=fn_col,
                                transcript_col=tr_col,
                                translation_col=tl_col,
                            )

                        if matched > 0:
                            st.success(
                                f"✅ Dataset uploaded & metadata imported: "
                                f"**{matched}/{total}** rows matched."
                            )
                        else:
                            st.warning(
                                f"Dataset uploaded, but metadata import matched 0/{total} rows. "
                                f"You can re-import from the dataset expander below."
                            )
                    else:
                        st.success("Dataset uploaded successfully.")
                else:
                    st.success("Dataset uploaded successfully.")

                # Increment counter → all widget keys change → widgets reset to placeholder
                st.session_state.upload_session += 1
                st.rerun()

    st.divider()


    datasets = get_all_datasets()

    if not datasets:
        st.info("No datasets uploaded yet.")

    else:

        total_files = sum(d.total_files for d in datasets)
        total_size = sum(d.total_size for d in datasets)

        c1, c2, c3 = st.columns(3)

        with c1:
            st.metric("Datasets", len(datasets))

        with c2:
            st.metric("Total Files", total_files)

        with c3:
            st.metric("Total Size (MB)", round(total_size, 2))

        st.divider()
    
        for dataset in datasets:

            with st.expander(
                f"📁 {dataset.name} | {dataset.total_files} files | {dataset.total_size:.2f} MB"
            ):

                st.write(f"**Language:** {dataset.language}")
                st.write(f"**Uploaded:** {dataset.uploaded_at}")

                # ── Delete dataset (with confirmation) ──────────────
                confirm_key = f"confirm_delete_ds_{dataset.id}"

                if confirm_key not in st.session_state:
                    st.session_state[confirm_key] = False

                if not st.session_state[confirm_key]:
                    if st.button(
                        "🗑️ Delete Entire Dataset",
                        key=f"del_ds_btn_{dataset.id}",
                        type="secondary",
                    ):
                        st.session_state[confirm_key] = True
                        st.rerun()
                else:
                    st.warning(
                        f"This will permanently delete **{dataset.total_files} audio files** "
                        f"and all annotations. This cannot be undone."
                    )
                    c_yes, c_no = st.columns(2)
                    if c_yes.button("✅ Yes, delete everything", key=f"confirm_yes_{dataset.id}", type="primary"):
                        ok, err = delete_dataset(dataset.id)
                        st.session_state[confirm_key] = False
                        if ok:
                            st.success("Dataset deleted.")
                            st.rerun()
                        else:
                            st.error(f"Delete failed: {err}")
                    if c_no.button("❌ Cancel", key=f"confirm_no_{dataset.id}"):
                        st.session_state[confirm_key] = False
                        st.rerun()
    
                files = get_dataset_files(dataset.id)

                st.write("---")

                for file in files:

                    col1, col2 = st.columns([8, 1])

                    with col1:
                        st.write(f"🎵 {file.original_filename}")

                    with col2:
                        if st.button("🗑", key=f"delete_{file.id}"):
                            delete_audio(file.id)
                            st.rerun()

                st.write("---")

                st.markdown("**📄 Upload Metadata**")
                st.caption("Upload a `metadata.csv` or `metadata.json` to attach transcripts to this dataset.")

                meta_file = st.file_uploader(
                    "Choose metadata file",
                    type=["csv", "json"],
                    key=f"meta_upload_{dataset.id}",
                )

                if meta_file is not None:

                    # ── Step 1: detect columns and let admin map them ──
                    is_csv = meta_file.name.lower().endswith(".csv")

                    if is_csv:
                        cols = get_csv_column_names(meta_file)

                        if not cols:
                            st.error("Could not read column headers from the CSV.")
                        else:
                            st.markdown("**Map columns** — select which column contains each field:")

                            col_options = ["(auto-detect)"] + cols

                            fn_col = st.selectbox(
                                "🎵 Audio Filename column",
                                col_options,
                                key=f"fn_col_{dataset.id}",
                            )
                            tr_col = st.selectbox(
                                "📝 Transcript column",
                                col_options,
                                key=f"tr_col_{dataset.id}",
                            )
                            tl_col = st.selectbox(
                                "🌐 Translation column (optional)",
                                col_options,
                                key=f"tl_col_{dataset.id}",
                            )

                            if st.button("Import Metadata", key=f"import_meta_{dataset.id}", type="primary"):
                                matched, total = import_metadata_for_dataset(
                                    dataset.id,
                                    meta_file,
                                    filename_col=None if fn_col == "(auto-detect)" else fn_col,
                                    transcript_col=None if tr_col == "(auto-detect)" else tr_col,
                                    translation_col=None if tl_col == "(auto-detect)" else tl_col,
                                )
                                if matched > 0:
                                    st.success(f"✅ Metadata imported: **{matched}/{total}** rows matched to audio files.")
                                    st.rerun()
                                elif total == 0:
                                    st.error("Could not parse the file — no rows found.")
                                else:
                                    st.warning(
                                        f"File parsed ({total} rows) but **0 filenames matched**. "
                                        f"Make sure the filename column contains exact audio filenames "
                                        f"like `clip_0001.mp3` (no folder paths)."
                                    )
                    else:
                        # JSON — no column mapping needed
                        if st.button("Import Metadata", key=f"import_meta_{dataset.id}", type="primary"):
                            matched, total = import_metadata_for_dataset(dataset.id, meta_file)
                            if matched > 0:
                                st.success(f"✅ Metadata imported: **{matched}/{total}** rows matched.")
                                st.rerun()
                            elif total == 0:
                                st.error("Could not parse the JSON file.")
                            else:
                                st.warning(f"Parsed {total} rows but no filenames matched.")

    st.divider()

    if st.button("← Back"):
        st.session_state.admin_page = "dashboard"
        st.rerun()
        

# =====================================================
# Assignments
# =====================================================
def assignments():

    st.title("📂 Assignments")

    st.info(
        "Task distribution is now **automatic**. "
        "Annotators request tasks from their dashboard. "
        "This page shows current assignments for monitoring only."
    )

    st.divider()

    st.subheader("Current Assignments")

    assignments = get_assignments()

    if not assignments:

        st.info("No assignments found.")

    else:

        for audio in assignments:

            with st.expander(audio.original_filename):

                st.write(f"**Language:** {audio.language}")
                st.write(f"**Assigned To:** {audio.assignee.username}")
                st.write(f"**Status:** {audio.status.value}")

    st.divider()

    if st.button("← Back"):

        st.session_state.admin_page = "dashboard"

        st.rerun()



# =====================================================
# Analytics
# =====================================================
def analytics():
    import pandas as pd
    from services.analytics_service import (
        get_kpi_summary,
        get_pipeline_funnel,
        get_annotation_trend,
        get_dataset_breakdown,
        get_language_breakdown,
        get_annotator_leaderboard,
        get_reviewer_leaderboard,
        get_user_detail,
    )
    from database.database import SessionLocal
    from database.models import User
    from database.enums import UserRole

    st.title("📊 Analytics Dashboard")
    if st.button("← Back"):
        st.session_state.admin_page = "dashboard"
        st.rerun()

    st.markdown("---")

    tab_overview, tab_datasets, tab_users, tab_leaderboards = st.tabs([
        "📊 Overview", "📁 Datasets", "👤 Users", "🏆 Leaderboards"
    ])

    # ─────────────────────────────────────────────────────────────────────
    # TAB 1: Overview
    # ─────────────────────────────────────────────────────────────────────
    with tab_overview:
        kpi = get_kpi_summary()

        st.subheader("Key Performance Indicators")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("👥 Total Users",       str(kpi["total_users"]),
                  f"{kpi['total_annotators']} annotators · {kpi['total_reviewers']} reviewers")
        c2.metric("🎙️ Total Audio Files", str(kpi["total_audio"]))
        c3.metric("⏱️ Total Duration",    f"{kpi['total_duration']:.1f}s")
        c4.metric("✅ Approved Duration", f"{kpi['approved_duration']:.1f}s",
                  f"{kpi['approved_pct']:.1f}%")

        st.markdown("---")

        # Pipeline Funnel
        st.subheader("Pipeline Funnel")
        funnel = get_pipeline_funnel()
        df_funnel = pd.DataFrame(funnel)
        df_funnel.columns = ["Stage", "Files"]
        st.dataframe(df_funnel, use_container_width=True, hide_index=True)

        # Annotation state mini-KPIs
        col_a, col_b, col_c, col_d = st.columns(4)
        col_a.metric("📝 Draft",     str(kpi["draft_count"]))
        col_b.metric("📤 Submitted", str(kpi["submitted_count"]))
        col_c.metric("🔄 Returned",  str(kpi["returned_count"]))
        col_d.metric("✅ Approved",  str(kpi["approved_count"]))

        st.markdown("---")

        # Submission trend
        st.subheader("📈 Submission Trend (Last 30 Days)")
        trend = get_annotation_trend(days=30)
        if trend:
            df_trend = pd.DataFrame(trend)
            df_trend = df_trend.rename(columns={"date": "Date", "submitted": "Submissions"})
            df_trend = df_trend.set_index("Date")
            st.line_chart(df_trend, height=300)
        else:
            st.info("No submission data available yet.")

    # ─────────────────────────────────────────────────────────────────────
    # TAB 2: Datasets
    # ─────────────────────────────────────────────────────────────────────
    with tab_datasets:
        st.subheader("Per-Dataset Breakdown")
        ds_data = get_dataset_breakdown()
        if ds_data:
            df_ds = pd.DataFrame(ds_data)
            df_ds = df_ds.rename(columns={
                "name":               "Dataset",
                "language":           "Language",
                "total_files":        "Total Files",
                "total_duration_s":   "Total Duration (s)",
                "approved_files":     "Approved Files",
                "approved_duration_s":"Approved Duration (s)",
                "approved_pct":       "% Approved",
            })
            st.dataframe(df_ds, use_container_width=True, hide_index=True)
        else:
            st.info("No datasets in the system.")

        st.markdown("---")

        st.subheader("🌐 Language Distribution")
        lang_data = get_language_breakdown()
        if lang_data:
            df_lang = pd.DataFrame(lang_data)
            df_lang = df_lang.rename(columns={
                "language":        "Language",
                "file_count":      "Files",
                "total_duration_s":"Total Duration (s)"
            })
            col_l, col_r = st.columns([2, 3])
            with col_l:
                st.dataframe(df_lang, use_container_width=True, hide_index=True)
            with col_r:
                df_lang_chart = df_lang.set_index("Language")[["Files"]]
                st.bar_chart(df_lang_chart, height=300)
        else:
            st.info("No audio files uploaded yet.")

    # ─────────────────────────────────────────────────────────────────────
    # TAB 3: Users
    # ─────────────────────────────────────────────────────────────────────
    with tab_users:
        st.subheader("User Detail Drill-Down")

        db = SessionLocal()
        try:
            all_users = db.query(User).filter(
                User.role.in_([UserRole.ANNOTATOR, UserRole.REVIEWER])
            ).order_by(User.role, User.username).all()
        finally:
            db.close()

        if not all_users:
            st.info("No annotators or reviewers registered yet.")
        else:
            role_filter = st.selectbox(
                "Filter by role",
                options=["All", "ANNOTATOR", "REVIEWER"],
                key="analytics_role_filter"
            )
            filtered = all_users
            if role_filter != "All":
                filtered = [u for u in all_users if u.role.value == role_filter]

            user_options = {f"{u.username} ({u.role.value})": u.id for u in filtered}
            if not user_options:
                st.info("No users match the selected filter.")
            else:
                selected_label = st.selectbox(
                    "Select user",
                    options=list(user_options.keys()),
                    key="analytics_user_select"
                )
                selected_id = user_options[selected_label]
                detail = get_user_detail(selected_id)

                if detail:
                    col_info, col_stats = st.columns([1, 2])
                    with col_info:
                        st.markdown(f"**Username:** {detail['username']}")
                        st.markdown(f"**Email:** {detail['email']}")
                        st.markdown(f"**Role:** {detail['role']}")
                        st.markdown(f"**Joined:** {detail['joined']}")

                    with col_stats:
                        if detail["role"] == "ANNOTATOR":
                            m1, m2, m3, m4 = st.columns(4)
                            m1.metric("Assigned",  str(detail["total_assigned"]))
                            m2.metric("Approved",  str(detail["approved"]))
                            m3.metric("Submitted", str(detail["submitted"]))
                            m4.metric("Returned",  str(detail["returned"]))
                        elif detail["role"] == "REVIEWER":
                            m1, m2, m3 = st.columns(3)
                            m1.metric("Total Reviews", str(detail["total_reviews"]))
                            m2.metric("Approvals",     str(detail["approvals"]))
                            m3.metric("Rejections",    str(detail["rejections"]))

                    st.markdown("---")

                    if detail["role"] == "ANNOTATOR" and detail.get("recent_tasks"):
                        st.markdown("**Recent Tasks**")
                        df_tasks = pd.DataFrame(detail["recent_tasks"])
                        df_tasks = df_tasks.rename(columns={
                            "audio_filename": "File",
                            "state":          "State",
                            "submitted_at":   "Submitted",
                            "duration_s":     "Duration (s)",
                        })
                        st.dataframe(df_tasks, use_container_width=True, hide_index=True)

                    elif detail["role"] == "REVIEWER" and detail.get("recent_reviews"):
                        st.markdown("**Recent Reviews**")
                        df_rev = pd.DataFrame(detail["recent_reviews"])
                        df_rev = df_rev.rename(columns={
                            "audio_filename": "File",
                            "status":         "Decision",
                            "reviewed_at":    "Date",
                        })
                        st.dataframe(df_rev, use_container_width=True, hide_index=True)

    # ─────────────────────────────────────────────────────────────────────
    # TAB 4: Leaderboards
    # ─────────────────────────────────────────────────────────────────────
    with tab_leaderboards:
        col_ann, col_rev = st.columns(2)

        with col_ann:
            st.subheader("🥇 Annotator Leaderboard")
            ann_lb = get_annotator_leaderboard()
            if ann_lb:
                df_ann = pd.DataFrame(ann_lb)
                df_ann.insert(0, "Rank", range(1, len(df_ann) + 1))
                df_ann = df_ann.rename(columns={
                    "username":            "Annotator",
                    "total_assigned":      "Assigned",
                    "approved":            "Approved ✅",
                    "submitted":           "Pending",
                    "returned":            "Returned 🔄",
                    "approved_duration_s": "Approved (s)",
                    "avg_turnaround_days": "Avg Days/Task",
                })
                st.dataframe(df_ann, use_container_width=True, hide_index=True)
            else:
                st.info("No annotators yet.")

        with col_rev:
            st.subheader("🥈 Reviewer Leaderboard")
            rev_lb = get_reviewer_leaderboard()
            if rev_lb:
                df_rev = pd.DataFrame(rev_lb)
                df_rev.insert(0, "Rank", range(1, len(df_rev) + 1))
                df_rev = df_rev.rename(columns={
                    "username":             "Reviewer",
                    "total_reviews":        "Total Reviews",
                    "approvals":            "Approved ✅",
                    "rejections":           "Rejected ❌",
                    "avg_review_time_days": "Avg Review Time (d)",
                })
                st.dataframe(df_rev, use_container_width=True, hide_index=True)
            else:
                st.info("No reviewers yet.")


def show():

    if st.session_state.user.role != UserRole.ADMIN:
        st.error("Access Denied")
        st.stop()

    # ── URL Sync ─────────────────────────────────────────────────────────────
    # Restore from URL on hard reload
    if "admin_page" in st.query_params and "admin_page" not in st.session_state:
        st.session_state.admin_page = st.query_params["admin_page"]

    page = st.session_state.setdefault("admin_page", "dashboard")
    
    # ── Sidebar Navigation ───────────────────────────────────────────────────
    st.sidebar.title("Akshara Admin")
    
    page_options = {
        "dashboard": "🏠 Dashboard",
        "users": "👤 Users",
        "audio": "🎙️ Audio Library",
        "assignments": "📂 Assignments",
        "analytics": "📊 Analytics",
    }
    
    # Create an inverse map to get the internal key from the display label
    label_to_key = {v: k for k, v in page_options.items()}
    
    # Find current index for the radio button
    current_label = page_options.get(page, page_options["dashboard"])
    
    selected_label = st.sidebar.radio(
        "Navigation",
        options=list(page_options.values()),
        index=list(page_options.values()).index(current_label),
        label_visibility="collapsed"
    )
    
    new_page = label_to_key[selected_label]
    if new_page != page:
        st.session_state.admin_page = new_page
        st.query_params["admin_page"] = new_page
        st.rerun()
        
    st.sidebar.divider()
    if st.sidebar.button("🚪 Logout", use_container_width=True):
        logout()

    # ── Route to Page ────────────────────────────────────────────────────────
    pages = {
        "dashboard": dashboard,
        "users": users,
        "audio": audio,
        "assignments": assignments,
        "analytics": analytics,
    }

    pages.get(page, dashboard)()
