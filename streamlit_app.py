
import requests
import streamlit as st

API_URL = "http://127.0.0.1:8000/chat"


def detect_issue_category(question: str) -> str:
    question = question.lower()

    categories = {
        "HR / Policy": [
            "maternity leave", "parental leave", "annual leave",
            "sick leave", "holiday policy", "hr policy",
            "human resources", "employee benefits", "leave policy"
        ],
        "Network": [
            "vpn", "wifi", "wi-fi", "internet", "network",
            "connection", "connectivity", "dns"
        ],
        "Account Access": [
            "password", "login", "log in", "sign in",
            "locked account", "account access", "authentication"
        ],
        "Hardware": [
            "laptop", "keyboard", "mouse", "monitor",
            "printer", "computer", "hardware", "not starting"
        ],
        "Software": [
            "application", "software", "app crash",
            "install", "installation", "program"
        ],
    }

    for category, keywords in categories.items():
        if any(keyword in question for keyword in keywords):
            return category

    return "Other"




def detect_issue_priority(question: str) -> str:
    question = question.lower()

    high_keywords = [
        "entire network down",
        "company-wide outage",
        "all employees",
        "critical system down",
        "production down",
        "security breach",
        "data breach",
        "ransomware",
        "emergency",
    ]

    low_keywords = [
        "maternity leave",
        "leave policy",
        "hr policy",
        "holiday policy",
        "general question",
    ]

    if any(keyword in question for keyword in high_keywords):
        return "High"

    if any(keyword in question for keyword in low_keywords):
        return "Low"

    return "Medium"


st.set_page_config(
    page_title="IT Helpdesk AI",
    page_icon="💻",
    layout="centered",
)

st.title("💻 IT Helpdesk Assistant")
st.caption("AI-powered IT support using your knowledge base")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        if message.get("sources"):
            with st.expander("Knowledge sources"):
                for source in message["sources"]:
                    st.write(
                        f"- {source['source']} "
                        f"(similarity: {source['score']:.4f})"
                    )

question = st.chat_input("Describe your IT issue...")

if question:
    st.session_state.messages.append({
        "role": "user",
        "content": question,
    })

    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Searching knowledge base..."):
            try:
                response = requests.post(
                    API_URL,
                    json={"question": question},
                    timeout=300,
                )
                response.raise_for_status()
                result = response.json()

                answer = result["answer"]
                sources = result.get("sources", [])
                needs_escalation = result.get("needs_escalation", False)
                relevance_score = result.get("relevance_score")

                
                st.markdown(answer)

                # Display sources only when available.
                if sources:
                    with st.expander("Knowledge sources"):
                        for source in sources:
                            st.write(
                                f"- {source['source']} "
                                f"(similarity: {source['score']:.4f})"
                            )

                # Always save the assistant response,
                # even when the sources list is empty.
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer,
                    "sources": sources,
                    "needs_escalation": needs_escalation,
                    "relevance_score": relevance_score,
                })


            except requests.RequestException:
                answer = (
                    "Unable to connect to the backend. "
                    "Please check that FastAPI is running."
                )
                st.error(answer)

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer,
                    "sources": sources,
                })



# ==========================================
# IT INCIDENT MANAGEMENT
# ==========================================

st.divider()
st.header("🎫 IT Incident Management")

API_BASE = "http://127.0.0.1:8000"

create_tab, track_tab, update_tab = st.tabs([
    "Create Ticket",
    "Track Ticket",
    "Update Status",
])

# ---------- Create Ticket ----------
with create_tab:
    st.subheader("Report an IT issue")

    with st.form("create_ticket_form"):
        title = st.text_input(
            "Issue title",
            placeholder="VPN connection failure",
        )

        description = st.text_area(
            "Describe the issue",
            placeholder="Explain what happened and what you tried.",
        )

        category = st.selectbox(
            "Category",
            ["Network", "Account Access", "Software", "Hardware", "Other"],
        )

        priority = st.selectbox(
            "Priority",
            ["Low", "Medium", "High"],
            index=1,
        )

        submitted = st.form_submit_button(
            "Create Ticket",
            type="primary",
        )

    if submitted:
        if len(title.strip()) < 3:
            st.error("Please enter a title with at least 3 characters.")
        elif len(description.strip()) < 5:
            st.error("Please provide a more detailed description.")
        else:
            try:
                
                response = requests.post(
                f"{API_BASE}/incidents",
                json={
                    "title": ticket_title,
                    "description": ticket_description,
                    "category": escalation_category,
                    "priority": escalation_priority,
                    "user_message": last_question,
                    "assistant_response": last_answer,
                },
                timeout=15,
            )


                if response.status_code == 201:
                    ticket = response.json()
                    st.success(
                        f"Ticket created successfully: "
                        f"{ticket['ticket_number']}"
                    )
                    st.write(f"Status: {ticket['status']}")
                    st.write(f"Priority: {ticket['priority']}")
                else:
                    st.error(
                        f"Ticket creation failed: {response.text}"
                    )

            
            except requests.RequestException as error:
                answer = (
                    "Unable to connect to the backend. "
                    "Please check that FastAPI is running."
                )
                st.error(answer)

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer,
                    "sources": [],
                    "needs_escalation": False,
                    "relevance_score": None,
                })



# ---------- Track Tickets ----------
with track_tab:
    st.subheader("View existing tickets")

    if st.button("Refresh Tickets"):
        st.session_state["refresh_tickets"] = True

    try:
        response = requests.get(
            f"{API_BASE}/incidents",
            timeout=15,
    )
        response.raise_for_status()

        tickets = response.json().get("incidents", [])

        if tickets:
            # Calculate ticket statistics
            total_tickets = len(tickets)

            open_tickets = sum(
                1 for ticket in tickets
                if ticket["status"] == "Open"
            )

            in_progress_tickets = sum(
                1 for ticket in tickets
                if ticket["status"] == "In Progress"
            )

            resolved_tickets = sum(
                1 for ticket in tickets
                if ticket["status"] == "Resolved"
            )

            closed_tickets = sum(
                1 for ticket in tickets
                if ticket["status"] == "Closed"
            )

            # Dashboard heading
            st.subheader("Ticket Overview")

            col1, col2, col3 = st.columns(3)

            col1.metric("Total Tickets", total_tickets)
            col2.metric("Open", open_tickets)
            col3.metric("In Progress", in_progress_tickets)

            col4, col5 = st.columns(2)

            col4.metric("Resolved", resolved_tickets)
            col5.metric("Closed", closed_tickets)

            st.divider()
            st.subheader("All Tickets")

            
            # Search and filter tickets
            search_text = st.text_input(
                "Search by ticket number or title",
                placeholder="e.g. INC000010 or VPN",
                key="ticket_search",
            ).strip().lower()

            filter_col1, filter_col2, filter_col3 = st.columns(3)

            with filter_col1:
                status_filter = st.selectbox(
                    "Filter by Status",
                    ["All", "Open", "In Progress", "Resolved", "Closed"],
                    key="ticket_status_filter",
                )

            with filter_col2:
                priority_filter = st.selectbox(
                    "Filter by Priority",
                    ["All", "Low", "Medium", "High"],
                    key="ticket_priority_filter",
                )

            with filter_col3:
                category_filter = st.selectbox(
                    "Filter by Category",
                    [
                        "All",
                        "Network",
                        "Account Access",
                        "Software",
                        "Hardware",
                        "Other",
                        "HR / Policy",
                    ],
                    key="ticket_category_filter",
                )

            # Reset to page 1 whenever filters change
                filter_signature = (
                    search_text,
                    status_filter,
                    priority_filter,
                    category_filter,
                )

                if st.session_state.get("ticket_filter_signature") != filter_signature:
                    st.session_state["ticket_current_page"] = 1
                    st.session_state["ticket_filter_signature"] = filter_signature


             # ---------- Ticket Dashboard Pagination ----------
            st.subheader("Ticket Dashboard")

            page_size = st.selectbox(
                "Tickets per page",
                [5, 10, 20, 50],
                index=1,
                key="ticket_page_size",
            )

           # Fetch the selected page from the backend
            current_page = st.session_state.get("ticket_current_page", 1)

            params = {
                "page": current_page,
                "page_size": page_size,
                "search": search_text,
                "status": status_filter,
                "priority": priority_filter,
                "category": category_filter,
            }

            page_response = requests.get(
                f"{API_BASE}/incidents",
                params=params,
                timeout=15,
            )
            page_response.raise_for_status()

            page_data = page_response.json()
            page_tickets = page_data.get("incidents", [])
            pagination = page_data.get("pagination", {})

            total_tickets = pagination.get("total_tickets", 0)
            total_pages = max(1, pagination.get("total_pages", 1))

        
            # Keep the selected page within the valid range
            current_page = min(max(1, current_page), total_pages)
            st.session_state["ticket_current_page"] = current_page

            start_index = (
                (current_page - 1) * page_size + 1
                if total_tickets > 0
                else 0
            )
            end_index = min(
                current_page * page_size,
                total_tickets,
            )

            st.caption(
                f"Showing {start_index}–{end_index} "
                f"of {total_tickets} matching tickets"
            )



            st.dataframe(
                [
                    {
                        "Ticket": ticket["ticket_number"],
                        "Title": ticket["title"],
                        "Category": ticket["category"],
                        "Priority": ticket["priority"],
                        "Status": ticket["status"],
                        "Created": ticket["created_at"],
                    }
                    for ticket in page_tickets
                ],
                use_container_width=True,
                hide_index=True,
            )

            # ---------- Previous / Next Buttons ----------
            prev_col, page_col, next_col = st.columns([1, 1, 1])

            with prev_col:
                if st.button(
                    "← Previous",
                    disabled=current_page <= 1,
                    key="previous_ticket_page",
                ):
                    st.session_state["ticket_current_page"] = current_page - 1
                    st.rerun()

            with page_col:
                st.write(f"Page {current_page} of {total_pages}")

            with next_col:
                if st.button(
                    "Next →",
                    disabled=current_page >= total_pages,
                    key="next_ticket_page",
                ):
                    st.session_state["ticket_current_page"] = current_page + 1
                    st.rerun()
        else:
            st.info("No tickets found. Create your first ticket.")



    except requests.RequestException:
        st.error("Unable to load tickets. Check that FastAPI is running.")

    st.subheader("Look up a specific ticket")

    ticket_number = st.text_input(
        "Ticket number",
        placeholder="INC000001",
        key="lookup_ticket",
    )

    if st.button("Find Ticket"):
        if not ticket_number.strip():
            st.warning("Enter a ticket number.")
        else:
            try:
                response = requests.get(
                    f"{API_BASE}/incidents/"
                    f"{ticket_number.strip().upper()}",
                    timeout=15,
                )

                if response.status_code == 200:
                    ticket = response.json()

                    st.success(
                        f"Found ticket {ticket['ticket_number']}"
                    )
                    st.write(f"**Title:** {ticket['title']}")
                    st.write(f"**Description:** {ticket['description']}")
                    st.write(f"**Category:** {ticket['category']}")
                    st.write(f"**Priority:** {ticket['priority']}")
                    st.write(f"**Status:** {ticket['status']}")
                    st.write(f"**Created:** {ticket['created_at']}")

                    
                    # Display saved conversation history
                    st.subheader("Conversation History")

                    try:
                        conversation_response = requests.get(
                            f"{API_BASE}/incidents/"
                            f"{ticket['ticket_number']}/conversation",
                            timeout=15,
                        )
                        conversation_response.raise_for_status()

                        conversations = conversation_response.json().get(
                            "conversation", []
                        )

                        if conversations:
                            for item in conversations:
                                st.markdown("**Employee Question**")
                                st.write(item["user_message"])

                                st.markdown("**AI Assistant Response**")
                                st.write(item["assistant_response"])

                                st.caption(f"Saved at: {item['created_at']}")
                                st.divider()
                        else:
                            st.info("No conversation history is saved for this ticket.")

                    except requests.RequestException as error:
                        st.warning(f"Could not load conversation history: {error}")
                    
                    
                    
                    st.subheader("Status Change History")

                    try:
                        history_response = requests.get(
                            f"{API_BASE}/incidents/"
                            f"{ticket['ticket_number']}/status-history",
                            timeout=15,
                        )
                        history_response.raise_for_status()

                        status_history = history_response.json().get(
                            "status_history", []
                        )

                        if status_history:
                            st.dataframe(
                                [
                                    {
                                        "Previous Status": item["old_status"],
                                        "New Status": item["new_status"],
                                        "Changed At": item["changed_at"],
                                    }
                                    for item in status_history
                                ],
                                use_container_width=True,
                                hide_index=True,
                            )
                        else:
                            st.info("No status changes have been recorded yet.")

                    except requests.RequestException as error:
                        st.warning(f"Could not load status history: {error}")




                elif response.status_code == 404:
                    st.warning("Ticket not found.")
                else:
                    st.error(f"Request failed: {response.text}")

            except requests.RequestException as error:
                st.error(f"Could not connect to backend: {error}")



# ---------- Update Ticket Status ----------
with update_tab:
    st.subheader("Update an incident")

    update_number = st.text_input(
        "Ticket number",
        placeholder="INC000001",
        key="update_number_input",
    )

    if st.button("Check Ticket Status", key="check_ticket_status"):
        if not update_number.strip():
            st.warning("Enter a ticket number.")
        else:
            try:
                response = requests.get(
                    f"{API_BASE}/incidents/"
                    f"{update_number.strip().upper()}",
                    timeout=15,
                )

                if response.status_code == 200:
                    st.session_state["ticket_to_update"] = response.json()
                    st.rerun()
                elif response.status_code == 404:
                    st.warning("Ticket not found.")
                    st.session_state.pop("ticket_to_update", None)
                else:
                    st.error(f"Could not fetch ticket: {response.text}")

            except requests.RequestException as error:
                st.error(f"Could not connect to backend: {error}")

    ticket = st.session_state.get("ticket_to_update")

    if ticket:
        current_status = ticket.get("status")
        ticket_number = ticket.get("ticket_number")

        
        st.subheader("Status Change History")

        if st.button(
            "View Status History",
            key="view_status_history",
        ):
            try:
                history_response = requests.get(
                    f"{API_BASE}/incidents/"
                    f"{ticket_number}/status-history",
                    timeout=15,
                )

                if history_response.status_code == 200:
                    history = history_response.json()

                    # Support either a direct list or a wrapped response.
                    if isinstance(history, dict):
                        history = history.get("history", [])

                    if history:
                        st.dataframe(
                            history,
                            use_container_width=True,
                            hide_index=True,
                        )
                    else:
                        st.info("No status changes recorded yet.")

                elif history_response.status_code == 404:
                    st.warning("Ticket or status history not found.")
                else:
                    st.error(
                        f"Could not load status history: "
                        f"{history_response.text}"
                    )

            except requests.RequestException as error:
                st.error(
                    f"Could not connect to backend: {error}"
                )


        st.info(
            f"Ticket: {ticket_number} | "
            f"Current status: {current_status}"
        )

        allowed_transitions = {
            "Open": ["In Progress"],
            "In Progress": ["Resolved"],
            "Resolved": ["Closed", "In Progress"],
            "Closed": [],
        }

        available_statuses = allowed_transitions.get(
            current_status, []
        )

        if not available_statuses:
            st.warning(
                "This ticket is Closed. No further status changes are allowed."
            )
        else:
            with st.form("update_ticket_form"):
                new_status = st.selectbox(
                    "New status",
                    available_statuses,
                )

                update_submitted = st.form_submit_button(
                    "Update Ticket",
                    type="primary",
                )

            if update_submitted:
                try:
                    response = requests.patch(
                        f"{API_BASE}/incidents/{ticket_number}",
                        json={"status": new_status},
                        timeout=15,
                    )

                    if response.status_code == 200:
                        updated_ticket = response.json()
                        st.session_state["ticket_to_update"] = updated_ticket

                        st.success(
                            f"{updated_ticket['ticket_number']} updated to "
                            f"{updated_ticket['status']}."
                        )
                        st.rerun()

                    elif response.status_code == 400:
                        st.error(
                            f"Invalid status transition: {response.text}"
                        )
                    elif response.status_code == 404:
                        st.warning("Ticket not found.")
                    else:
                        st.error(f"Update failed: {response.text}")

                except requests.RequestException as error:
                    st.error(f"Could not connect to backend: {error}")



# ==========================================
# ESCALATE CHAT TO SUPPORT TICKET
# ==========================================

st.divider()
st.header("🆘 Still need help?")

chat_messages = st.session_state.get("messages", [])
last_question = None
last_answer = None
last_assistant_message = None

# Use the latest assistant response and the immediately preceding user message.
for index in range(len(chat_messages) - 1, -1, -1):
    message = chat_messages[index]
    if message.get("role") == "assistant":
        last_assistant_message = message
        if index > 0 and chat_messages[index - 1].get("role") == "user":
            last_question = chat_messages[index - 1].get("content")
            last_answer = message.get("content")
        break

if last_question and last_answer:
    needs_escalation = last_assistant_message.get("needs_escalation", False)

    if needs_escalation:
        st.warning(
            "The knowledge base could not answer your question with sufficient confidence. "
            "Please create a support ticket if you need further assistance."
        )
    else:
        st.info("If your issue is unresolved, create a ticket using the details from your latest conversation.")

    ticket_title = last_question.strip()[:150]
    ticket_description = (
        f"Employee question:\n{last_question}\n\nAssistant response:\n{last_answer}"
    )[:3000]
    suggested_category = detect_issue_category(last_question)
    suggested_priority = detect_issue_priority(last_question)

    with st.form("escalate_chat_form"):
        st.text_input("Ticket title", value=ticket_title, disabled=True)
        st.text_area("Ticket description", value=ticket_description, disabled=True)
        category_options = [
                "Network",
                "Account Access",
                "Software",
                "Hardware",
                "HR / Policy",
                "Other",
            ]

        escalation_category = st.selectbox(
                "Issue category",
                category_options,
                index=category_options.index(suggested_category),
                key="escalation_category",
            )
        
        priority_options = ["Low", "Medium", "High"]

        escalation_priority = st.selectbox(
            "Priority",
            priority_options,
            index=priority_options.index(suggested_priority),
            key="escalation_priority",
        )

        confirm_escalation = st.checkbox(
            "I confirm that I want to create a support ticket.", key="confirm_escalation",
        )
        submit_escalation = st.form_submit_button("Create Support Ticket", type="primary")

    if submit_escalation:
        if not confirm_escalation:
            st.warning("Please confirm before creating the ticket.")
        else:
            try:
                response = requests.post(
                    f"{API_BASE}/incidents",
                    
                    json={
                        "title": ticket_title,
                        "description": ticket_description,
                        "category": (
                            "Other"
                            if escalation_category == "HR / Policy"
                            else escalation_category
                        ),
                        "priority": escalation_priority,
                        "user_message": last_question,
                        "assistant_response": last_answer,
                    },

                    timeout=15,
                )
                if response.status_code == 201:
                    ticket = response.json()
                    st.success("Support ticket created successfully!")
                    st.write(f"**Ticket number:** {ticket['ticket_number']}")
                    st.write(f"**Status:** {ticket['status']}")
                else:
                    st.error(f"Ticket creation failed: {response.text}")
            except requests.RequestException as error:
                st.error(f"Could not connect to the backend: {error}")
else:
    st.info("Ask the assistant a question to enable escalation.")
