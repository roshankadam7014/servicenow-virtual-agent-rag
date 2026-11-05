import requests
import streamlit as st

# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------
API_BASE = "https://servicenow-virtual-agent-rag.onrender.com"
CHAT_URL = f"{API_BASE}/chat"
REQUEST_TIMEOUT = 30

st.set_page_config(
    page_title="IT Service Desk | Virtual Agent",
    page_icon="💻",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------
# Professional UI styling
# ---------------------------------------------------------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'DM Sans', sans-serif;
    }
    .stApp {
        background: #f5f7fb;
    }
    [data-testid="stSidebar"] {
        background: #101d32;
    }
    [data-testid="stSidebar"] * {
        color: #edf3fb;
    }
    [data-testid="stSidebar"] .stRadio label {
        padding: 8px 10px;
        border-radius: 8px;
    }
    .brand {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 8px 0 22px 0;
    }
    .brand-icon {
        background: #244a75;
        border-radius: 12px;
        width: 42px;
        height: 42px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 23px;
    }
    .brand-name {
        color: white;
        font-size: 18px;
        font-weight: 700;
        line-height: 1.2;
    }
    .brand-sub {
        color: #a9bad0;
        font-size: 11px;
        margin-top: 3px;
    }
    .eyebrow {
        color: #52749d;
        font-size: 12px;
        font-weight: 700;
        letter-spacing: .10em;
        text-transform: uppercase;
        margin-bottom: 6px;
    }
    .hero {
        background: linear-gradient(120deg, #142944 0%, #244d78 100%);
        border-radius: 18px;
        padding: 28px 30px;
        color: white;
        margin: 4px 0 22px 0;
    }
    .hero h1 {
        color: white;
        font-size: 30px;
        margin: 0 0 8px 0;
        font-weight: 700;
    }
    .hero p {
        color: #d6e3f2;
        margin: 0;
        font-size: 14px;
    }
    .section-heading {
        font-size: 20px;
        font-weight: 700;
        color: #18283d;
        margin: 12px 0 4px 0;
    }
    .section-sub {
        color: #6b7b90;
        font-size: 13px;
        margin-bottom: 14px;
    }
    div[data-testid="stMetric"] {
        background: white;
        border: 1px solid #e7ecf3;
        padding: 15px 17px;
        border-radius: 13px;
        box-shadow: 0 2px 8px rgba(22, 42, 68, .035);
    }
    div[data-testid="stMetricLabel"] {
        color: #68798e;
    }
    div[data-testid="stMetricValue"] {
        color: #172b45;
        font-weight: 700;
    }
    .stButton > button[kind="primary"],
    .stFormSubmitButton > button[kind="primary"] {
        background: #245b91;
        border: 1px solid #245b91;
        border-radius: 9px;
        font-weight: 600;
    }
    .stButton > button, .stFormSubmitButton > button {
        border-radius: 9px;
    }
    [data-testid="stChatMessage"] {
        border: 1px solid #e8edf4;
        border-radius: 14px;
        padding: 12px 14px;
        background: white;
    }
    .status-pill {
        display: inline-block;
        padding: 4px 9px;
        border-radius: 20px;
        font-size: 11px;
        font-weight: 700;
        background: #eaf1f8;
        color: #28557f;
    }
    footer {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------
def api_get(path, **kwargs):
    response = requests.get(
        f"{API_BASE}{path}",
        timeout=REQUEST_TIMEOUT,
        **kwargs,
    )
    response.raise_for_status()
    return response


def api_post(path, payload, timeout=REQUEST_TIMEOUT):
    response = requests.post(
        f"{API_BASE}{path}",
        json=payload,
        timeout=timeout,
    )
    response.raise_for_status()
    return response


def api_patch(path, payload):
    response = requests.patch(
        f"{API_BASE}{path}",
        json=payload,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response


def detect_issue_category(question: str) -> str:
    text = question.lower()
    categories = {
        "HR / Policy": [
            "maternity leave", "parental leave", "annual leave",
            "sick leave", "holiday policy", "hr policy",
            "human resources", "employee benefits", "leave policy",
        ],
        "Network": [
            "vpn", "wifi", "wi-fi", "internet", "network",
            "connection", "connectivity", "dns",
        ],
        "Account Access": [
            "password", "login", "log in", "sign in",
            "locked account", "account access", "authentication",
            "mfa", "otp",
        ],
        "Hardware": [
            "laptop", "keyboard", "mouse", "monitor",
            "printer", "computer", "hardware", "not starting",
        ],
        "Software": [
            "application", "software", "app crash",
            "install", "installation", "program", "outlook", "teams",
        ],
    }
    for category, keywords in categories.items():
        if any(keyword in text for keyword in keywords):
            return category
    return "Other"


def detect_issue_priority(question: str) -> str:
    text = question.lower()
    high_keywords = [
        "entire network down", "company-wide outage", "all employees",
        "critical system down", "production down", "security breach",
        "data breach", "ransomware", "emergency",
    ]
    low_keywords = [
        "maternity leave", "leave policy", "hr policy",
        "holiday policy", "general question",
    ]
    if any(keyword in text for keyword in high_keywords):
        return "High"
    if any(keyword in text for keyword in low_keywords):
        return "Low"
    return "Medium"


def show_sources(sources):
    if not sources:
        return
    with st.expander("📚 Knowledge sources and relevance", expanded=False):
        for source in sources:
            name = source.get("source", "Knowledge document")
            score = source.get("score")
            if isinstance(score, (int, float)):
                st.write(f"**{name}** · Similarity: `{score:.4f}`")
                st.progress(max(0.0, min(float(score), 1.0)))
            else:
                st.write(f"**{name}**")


def show_ticket_summary(ticket):
    st.success(f"Ticket created: **{ticket.get('ticket_number', 'N/A')}**")
    c1, c2 = st.columns(2)
    c1.metric("Status", ticket.get("status", "N/A"))
    c2.metric("Priority", ticket.get("priority", "N/A"))


def render_ticket_history(ticket_number):
    st.markdown("#### Conversation history")
    try:
        response = api_get(f"/incidents/{ticket_number}/conversation")
        conversations = response.json().get("conversation", [])
        if conversations:
            for item in conversations:
                with st.container(border=True):
                    st.caption(f"Saved at: {item.get('created_at', 'N/A')}")
                    st.markdown("**Employee question**")
                    st.write(item.get("user_message", ""))
                    st.markdown("**AI assistant response**")
                    st.write(item.get("assistant_response", ""))
        else:
            st.info("No conversation history is saved for this ticket.")
    except requests.RequestException as error:
        st.warning(f"Could not load conversation history: {error}")

    st.markdown("#### Status change history")
    try:
        response = api_get(f"/incidents/{ticket_number}/status-history")
        history = response.json().get("status_history", [])
        if history:
            st.dataframe(
                [
                    {
                        "Previous status": item.get("old_status"),
                        "New status": item.get("new_status"),
                        "Changed at": item.get("changed_at"),
                    }
                    for item in history
                ],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No status changes have been recorded yet.")
    except requests.RequestException as error:
        st.warning(f"Could not load status history: {error}")


# ---------------------------------------------------------
# Session state
# ---------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []
if "ticket_to_update" not in st.session_state:
    st.session_state.ticket_to_update = None
if "ticket_current_page" not in st.session_state:
    st.session_state.ticket_current_page = 1

# ---------------------------------------------------------
# Sidebar navigation
# ---------------------------------------------------------
with st.sidebar:
    st.markdown(
        """
        <div class="brand">
            <div class="brand-icon">🎧</div>
            <div>
                <div class="brand-name">IT Service Desk</div>
                <div class="brand-sub">VIRTUAL AGENT PLATFORM</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("---")
    page = st.radio(
        "WORKSPACE",
        [
            "Overview",
            "AI Helpdesk Chat",
            "Create Ticket",
            "Track Tickets",
            "Update Ticket",
        ],
        label_visibility="visible",
    )
    st.markdown("---")
    st.caption("Connected service")
    st.markdown("🟢 **API configured**")
    st.caption("Powered by RAG · Gemini · FastAPI")
    if st.button("Clear chat history", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# ---------------------------------------------------------
# Header
# ---------------------------------------------------------
st.markdown(
    """
    <div class="eyebrow">IT OPERATIONS / SERVICE MANAGEMENT</div>
    """,
    unsafe_allow_html=True,
)
st.title(page)
st.caption("A unified workspace for employee IT support and incident management.")

# ---------------------------------------------------------
# Overview
# ---------------------------------------------------------
if page == "Overview":
    st.markdown(
        """
        <div class="hero">
            <h1>IT support, made simpler.</h1>
            <p>Get guided answers from the IT knowledge base, create incidents,
            and follow ticket progress from one workspace.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    col1, col2 = st.columns([1, 1])
    with col1:
        with st.container(border=True):
            st.markdown("### 🤖 AI Helpdesk")
            st.write("Ask questions about account access, VPN, Wi-Fi, devices, Outlook, Teams and more.")
            st.caption("Open **AI Helpdesk Chat** from the sidebar.")
    with col2:
        with st.container(border=True):
            st.markdown("### 🎫 Incident management")
            st.write("Create a support ticket, look up an incident, or update its status.")
            st.caption("Use **Create Ticket**, **Track Tickets**, or **Update Ticket** in the sidebar.")

    st.markdown("### Quick access")
    q1, q2, q3 = st.columns(3)
    with q1:
        st.info("**AI assistance**\n\nKnowledge-grounded IT answers.")
    with q2:
        st.info("**Ticket tracking**\n\nSearch incidents and view progress.")
    with q3:
        st.info("**Escalation**\n\nConvert an unresolved chat into a ticket.")

    st.markdown("### Service capabilities")
    st.write(
        "Password reset · Account lockout · MFA · VPN · Wi-Fi · DNS · "
        "Laptop startup · Performance · Outlook · Microsoft Teams"
    )

# ---------------------------------------------------------
# AI Helpdesk Chat
# ---------------------------------------------------------
elif page == "AI Helpdesk Chat":
    st.markdown(
        '<div class="section-sub">Describe the issue in everyday language. '
        'The assistant searches the approved knowledge base for relevant guidance.</div>',
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        st.markdown("**Try asking about:**")
        suggestions = [
            "My corporate VPN keeps disconnecting",
            "My MFA code is not working",
            "Outlook is not synchronizing emails",
            "My laptop is running very slowly",
        ]
        sug_cols = st.columns(4)
        for i, suggestion in enumerate(suggestions):
            with sug_cols[i]:
                if st.button(suggestion, key=f"suggestion_{i}", use_container_width=True):
                    st.session_state["suggested_question"] = suggestion
                    st.rerun()

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            show_sources(message.get("sources", []))
            if message.get("needs_escalation"):
                st.warning("This issue may need assistance from the IT support team.")

    suggested = st.session_state.pop("suggested_question", None)
    question = st.chat_input("Describe your IT issue...")
    if suggested:
        question = suggested

    if question:
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            with st.spinner("Searching the IT knowledge base..."):
                try:
                    response = api_post("/chat", {"question": question}, timeout=300)
                    result = response.json()
                    answer = result.get(
                        "answer",
                        "The assistant returned an empty response. Please contact IT support.",
                    )
                    sources = result.get("sources", [])
                    needs_escalation = result.get("needs_escalation", False)
                    relevance_score = result.get("relevance_score")

                    st.markdown(answer)
                    show_sources(sources)
                    if needs_escalation:
                        st.warning("The knowledge base could not fully resolve this issue. Consider creating a support ticket.")

                    st.session_state.messages.append(
                        {
                            "role": "assistant",
                            "content": answer,
                            "sources": sources,
                            "needs_escalation": needs_escalation,
                            "relevance_score": relevance_score,
                        }
                    )
                except requests.Timeout:
                    answer = "The helpdesk service took too long to respond. Please try again."
                    st.error(answer)
                    st.session_state.messages.append(
                        {"role": "assistant", "content": answer, "sources": []}
                    )
                except requests.RequestException as error:
                    answer = "Unable to connect to the helpdesk service. Please try again shortly."
                    st.error(answer)
                    st.caption(str(error))
                    st.session_state.messages.append(
                        {"role": "assistant", "content": answer, "sources": []}
                    )
                except (ValueError, KeyError) as error:
                    answer = "The service returned an unexpected response. Please try again."
                    st.error(answer)
                    st.caption(str(error))
                    st.session_state.messages.append(
                        {"role": "assistant", "content": answer, "sources": []}
                    )

    # Escalate the latest chat exchange into an incident
    chat_messages = st.session_state.messages
    last_question, last_answer, last_assistant = None, None, None
    for index in range(len(chat_messages) - 1, -1, -1):
        if chat_messages[index].get("role") == "assistant":
            last_assistant = chat_messages[index]
            if index > 0 and chat_messages[index - 1].get("role") == "user":
                last_question = chat_messages[index - 1].get("content")
                last_answer = last_assistant.get("content")
            break

    if last_question and last_answer:
        st.divider()
        st.markdown("### Still need help?")
        st.caption("Create an incident using the latest chat exchange.")
        suggested_category = detect_issue_category(last_question)
        suggested_priority = detect_issue_priority(last_question)
        with st.form("chat_escalation_form"):
            st.text_input("Ticket title", value=last_question.strip()[:150], disabled=True)
            st.text_area(
                "Ticket description",
                value=f"Employee question:\n{last_question}\n\nAssistant response:\n{last_answer}"[:3000],
                disabled=True,
            )
            category_options = [
                "Network", "Account Access", "Software", "Hardware",
                "HR / Policy", "Other",
            ]
            priority_options = ["Low", "Medium", "High"]
            category = st.selectbox(
                "Category",
                category_options,
                index=category_options.index(suggested_category),
            )
            priority = st.selectbox(
                "Priority",
                priority_options,
                index=priority_options.index(suggested_priority),
            )
            confirm = st.checkbox("I confirm that I want to create this support ticket.")
            submit = st.form_submit_button("Create support ticket", type="primary")
        if submit:
            if not confirm:
                st.warning("Please confirm before creating the ticket.")
            else:
                payload = {
                    "title": last_question.strip()[:150],
                    "description": (
                        f"Employee question:\n{last_question}\n\n"
                        f"Assistant response:\n{last_answer}"
                    )[:3000],
                    "category": "Other" if category == "HR / Policy" else category,
                    "priority": priority,
                    "user_message": last_question,
                    "assistant_response": last_answer,
                }
                try:
                    response = api_post("/incidents", payload)
                    ticket = response.json()
                    show_ticket_summary(ticket)
                except requests.RequestException as error:
                    st.error(f"Ticket creation failed: {error}")

# ---------------------------------------------------------
# Create Ticket
# ---------------------------------------------------------
elif page == "Create Ticket":
    st.markdown("### Report an IT issue")
    st.markdown(
        '<div class="section-sub">Provide enough detail for the support team to investigate.</div>',
        unsafe_allow_html=True,
    )
    with st.container(border=True):
        with st.form("create_ticket_form", clear_on_submit=True):
            title = st.text_input("Issue title", placeholder="Example: VPN connection failure")
            description = st.text_area(
                "Describe the issue",
                placeholder="What happened? When did it start? What have you tried?",
                height=150,
            )
            c1, c2 = st.columns(2)
            with c1:
                category = st.selectbox(
                    "Category",
                    ["Network", "Account Access", "Software", "Hardware", "Other"],
                )
            with c2:
                priority = st.selectbox("Priority", ["Low", "Medium", "High"], index=1)
            submitted = st.form_submit_button("Submit incident", type="primary", use_container_width=True)

    if submitted:
        if len(title.strip()) < 3:
            st.error("Please enter a title with at least 3 characters.")
        elif len(description.strip()) < 5:
            st.error("Please provide a more detailed description.")
        else:
            try:
                response = api_post(
                    "/incidents",
                    {
                        "title": title.strip(),
                        "description": description.strip(),
                        "category": category,
                        "priority": priority,
                    },
                )
                show_ticket_summary(response.json())
            except requests.RequestException as error:
                st.error(f"Unable to create the ticket: {error}")

# ---------------------------------------------------------
# Track Tickets
# ---------------------------------------------------------
elif page == "Track Tickets":
    st.markdown("### Incident overview")
    st.markdown(
        '<div class="section-sub">Search, filter and inspect tickets recorded in the helpdesk.</div>',
        unsafe_allow_html=True,
    )

    try:
        overview_response = api_get("/incidents")
        all_tickets = overview_response.json().get("incidents", [])
        total = len(all_tickets)
        open_count = sum(t.get("status") == "Open" for t in all_tickets)
        progress_count = sum(t.get("status") == "In Progress" for t in all_tickets)
        resolved_count = sum(t.get("status") == "Resolved" for t in all_tickets)
        closed_count = sum(t.get("status") == "Closed" for t in all_tickets)

        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Total tickets", total)
        m2.metric("Open", open_count)
        m3.metric("In progress", progress_count)
        m4.metric("Resolved", resolved_count)
        m5.metric("Closed", closed_count)

        st.divider()
        st.markdown("### Find incidents")
        search_col, status_col, priority_col, category_col = st.columns([1.5, 1, 1, 1])
        with search_col:
            search_text = st.text_input("Search", placeholder="Ticket number or title").strip()
        with status_col:
            status_filter = st.selectbox("Status", ["All", "Open", "In Progress", "Resolved", "Closed"])
        with priority_col:
            priority_filter = st.selectbox("Priority", ["All", "Low", "Medium", "High"])
        with category_col:
            category_filter = st.selectbox(
                "Category",
                ["All", "Network", "Account Access", "Software", "Hardware", "Other", "HR / Policy"],
            )

        page_size = st.selectbox("Rows per page", [5, 10, 20, 50], index=1)
        if st.button("Refresh ticket list"):
            st.rerun()

        params = {
            "page": st.session_state.ticket_current_page,
            "page_size": page_size,
            "search": search_text,
            "status": status_filter,
            "priority": priority_filter,
            "category": category_filter,
        }
        page_response = api_get("/incidents", params=params)
        page_data = page_response.json()
        page_tickets = page_data.get("incidents", [])
        pagination = page_data.get("pagination", {})
        total_matching = pagination.get("total_tickets", len(page_tickets))
        total_pages = max(1, pagination.get("total_pages", 1))
        current_page = min(max(1, st.session_state.ticket_current_page), total_pages)
        st.session_state.ticket_current_page = current_page

        st.caption(f"Showing {len(page_tickets)} of {total_matching} matching tickets · Page {current_page} of {total_pages}")
        if page_tickets:
            st.dataframe(
                [
                    {
                        "Ticket": ticket.get("ticket_number"),
                        "Title": ticket.get("title"),
                        "Category": ticket.get("category"),
                        "Priority": ticket.get("priority"),
                        "Status": ticket.get("status"),
                        "Created": ticket.get("created_at"),
                    }
                    for ticket in page_tickets
                ],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No tickets match the selected filters.")

        previous_col, page_col, next_col = st.columns([1, 2, 1])
        with previous_col:
            if st.button("← Previous", disabled=current_page <= 1, use_container_width=True):
                st.session_state.ticket_current_page = current_page - 1
                st.rerun()
        with page_col:
            st.markdown(f"<div style='text-align:center;padding:8px'>Page <b>{current_page}</b> of <b>{total_pages}</b></div>", unsafe_allow_html=True)
        with next_col:
            if st.button("Next →", disabled=current_page >= total_pages, use_container_width=True):
                st.session_state.ticket_current_page = current_page + 1
                st.rerun()

    except requests.RequestException as error:
        st.error(f"Unable to load tickets: {error}")

    st.divider()
    st.markdown("### Look up a specific ticket")
    with st.form("lookup_ticket_form"):
        ticket_number = st.text_input("Ticket number", placeholder="INC000001")
        lookup = st.form_submit_button("Find ticket", type="primary")
    if lookup:
        if not ticket_number.strip():
            st.warning("Enter a ticket number.")
        else:
            number = ticket_number.strip().upper()
            try:
                response = api_get(f"/incidents/{number}")
                ticket = response.json()
                st.success(f"Found ticket {ticket.get('ticket_number', number)}")
                c1, c2, c3 = st.columns(3)
                c1.metric("Status", ticket.get("status", "N/A"))
                c2.metric("Priority", ticket.get("priority", "N/A"))
                c3.metric("Category", ticket.get("category", "N/A"))
                st.write(f"**Title:** {ticket.get('title', '')}")
                st.write(f"**Description:** {ticket.get('description', '')}")
                st.caption(f"Created: {ticket.get('created_at', 'N/A')}")
                render_ticket_history(ticket.get("ticket_number", number))
            except requests.HTTPError as error:
                if error.response is not None and error.response.status_code == 404:
                    st.warning("Ticket not found. Check the ticket number.")
                else:
                    st.error(f"Could not retrieve ticket: {error}")
            except requests.RequestException as error:
                st.error(f"Could not connect to the backend: {error}")

# ---------------------------------------------------------
# Update Ticket
# ---------------------------------------------------------
elif page == "Update Ticket":
    st.markdown("### Update incident status")
    st.markdown(
        '<div class="section-sub">Check the current status and move the incident through an allowed workflow.</div>',
        unsafe_allow_html=True,
    )

    with st.form("check_ticket_status_form"):
        update_number = st.text_input("Ticket number", placeholder="INC000001")
        check_status = st.form_submit_button("Load ticket", type="primary")

    if check_status:
        if not update_number.strip():
            st.warning("Enter a ticket number.")
        else:
            try:
                response = api_get(f"/incidents/{update_number.strip().upper()}")
                st.session_state.ticket_to_update = response.json()
            except requests.HTTPError as error:
                st.session_state.ticket_to_update = None
                if error.response is not None and error.response.status_code == 404:
                    st.warning("Ticket not found.")
                else:
                    st.error(f"Could not fetch ticket: {error}")
            except requests.RequestException as error:
                st.error(f"Could not connect to backend: {error}")

    ticket = st.session_state.get("ticket_to_update")
    if ticket:
        ticket_number = ticket.get("ticket_number")
        current_status = ticket.get("status")
        st.success(f"{ticket_number} · Current status: {current_status}")
        st.write(f"**Title:** {ticket.get('title', '')}")
        st.write(f"**Priority:** {ticket.get('priority', '')}")

        with st.expander("View status history"):
            try:
                history_response = api_get(f"/incidents/{ticket_number}/status-history")
                history_data = history_response.json()
                history = history_data.get("history", history_data.get("status_history", [])) if isinstance(history_data, dict) else history_data
                if history:
                    st.dataframe(history, use_container_width=True, hide_index=True)
                else:
                    st.info("No status changes recorded yet.")
            except requests.RequestException as error:
                st.warning(f"Could not load status history: {error}")

        allowed_transitions = {
            "Open": ["In Progress"],
            "In Progress": ["Resolved"],
            "Resolved": ["Closed", "In Progress"],
            "Closed": [],
        }
        available_statuses = allowed_transitions.get(current_status, [])
        if not available_statuses:
            st.warning("This ticket is Closed. No further status changes are allowed.")
        else:
            with st.form("update_ticket_form"):
                new_status = st.selectbox("New status", available_statuses)
                update_submitted = st.form_submit_button("Update status", type="primary")
            if update_submitted:
                try:
                    response = api_patch(
                        f"/incidents/{ticket_number}",
                        {"status": new_status},
                    )
                    st.session_state.ticket_to_update = response.json()
                    st.success(f"{ticket_number} updated to {new_status}.")
                    st.rerun()
                except requests.HTTPError as error:
                    details = error.response.text if error.response is not None else str(error)
                    st.error(f"Status update failed: {details}")
                except requests.RequestException as error:
                    st.error(f"Could not connect to backend: {error}")

st.markdown("---")
st.caption("IT Service Desk · Knowledge-grounded support · Incident management")
