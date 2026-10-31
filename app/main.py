
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.rag import ITHelpdeskRAG

from typing import Literal
from fastapi import Query
from app.ticket_store import count_incidents
from typing import Literal


from app.ticket_store import (
    initialize_database,
    create_incident,
    list_incidents,
    get_incident,
    update_incident,
    save_conversation,
    get_conversation_history,
    get_status_history,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()  # Create the incidents table first
    app.state.assistant = ITHelpdeskRAG()
    yield
    app.state.assistant = None

app = FastAPI(
    title="ServiceNow Virtual Agent with RAG",
    description="Local AI-powered IT Helpdesk API",
    version="1.0.0",
    lifespan=lifespan,
)



# 3. Request models (ADD YOUR CODE HERE)
class IncidentCreate(BaseModel):
    title: str = Field(min_length=3, max_length=150)
    description: str = Field(min_length=5, max_length=3000)
    category: Literal[
        "Network", "Account Access", "Software", "Hardware", "Other"
    ]
    priority: Literal["Low", "Medium", "High"] = "Medium"

    # Optional conversation details linked to the ticket
    user_message: str | None = Field(default=None, max_length=2000)
    assistant_response: str | None = Field(default=None, max_length=5000)


class IncidentUpdate(BaseModel):
    status: Literal["Open", "In Progress", "Resolved", "Closed"]


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class Source(BaseModel):
    source: str
    score: float


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]


@app.get("/")
def root():
    return {
        "message": "ServiceNow Virtual Agent with RAG is running",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "IT Helpdesk RAG"
    }

@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    assistant = app.state.assistant

    try:
        result = assistant.answer(request.question)
        return result
    except Exception:
        # Keep internal exception details out of API responses.
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred while processing your question.",
        )


@app.post("/incidents", status_code=201)
def create_ticket(request: IncidentCreate):
    ticket = create_incident(
        title=request.title,
        description=request.description,
        category=request.category,
        priority=request.priority,
    )

    # Save the conversation when both messages are provided.
    if request.user_message and request.assistant_response:
        save_conversation(
            ticket["ticket_number"],
            request.user_message,
            request.assistant_response,
        )

    return ticket



@app.get("/incidents")
def get_all_tickets(
    page: int | None = Query(default=None, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    search: str = "",
    status: Literal[
        "All", "Open", "In Progress", "Resolved", "Closed"
    ] = "All",
    priority: Literal[
        "All", "Low", "Medium", "High"
    ] = "All",
    category: Literal[
        "All", "Network", "Account Access", "Software",
        "Hardware", "Other", "HR / Policy"
    ] = "All",
):
    # Preserve existing behavior when page is not provided
    if page is None:
        return {"incidents": list_incidents()}

    # Get all matching tickets for accurate pagination totals
    total_tickets = count_incidents(
        search=search,
        status=status,
        priority=priority,
        category=category,
)
    offset = (page - 1) * page_size

    # Fetch only the requested page from the database
    tickets = list_incidents(
        limit=page_size,
        offset=offset,
        search=search,
        status=status,
        priority=priority,
        category=category,
    )

    total_pages = (
        total_tickets + page_size - 1
    ) // page_size

    return {
        "incidents": tickets,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_tickets": total_tickets,
            "total_pages": total_pages,
        },
    }



@app.get("/incidents/{ticket_number}")
def get_ticket(ticket_number: str):
    incident = get_incident(ticket_number)

    if incident is None:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found",
        )

    return incident

@app.get("/incidents/{ticket_number}/status-history")
def get_ticket_status_history(ticket_number: str):
    incident = get_incident(ticket_number)

    if incident is None:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found",
        )

    return {
        "ticket_number": incident["ticket_number"],
        "status_history": get_status_history(ticket_number),
    }

@app.get("/incidents/{ticket_number}/conversation")
def get_ticket_conversation(ticket_number: str):
    incident = get_incident(ticket_number)

    if incident is None:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found",
        )

    return {
        "ticket_number": incident["ticket_number"],
        "conversation": get_conversation_history(ticket_number),
    }



@app.patch("/incidents/{ticket_number}")
def update_ticket(
    ticket_number: str,
    request: IncidentUpdate,
):
    try:
        incident = update_incident(
            ticket_number,
            request.status,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    if incident is None:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found",
        )

    return incident






    