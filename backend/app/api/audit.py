"""FastAPI Compliance Audit and Feedback Endpoints (Task 3.6)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field

from app.models.schemas import RiskTier
from app.storage.audit_store import AuditStore, get_audit_store

router = APIRouter(prefix="/audit", tags=["Compliance & Audit"])


class AuditFeedbackRequest(BaseModel):
    """Request payload for recording compliance officer review feedback."""
    model_config = ConfigDict(populate_by_name=True)

    flag_id: str = Field(..., description="Unique identifier of the flag being reviewed")
    feedback_status: str = Field(
        ...,
        description="Analyst determination (e.g. 'CONFIRMED_SUSPICIOUS', 'FALSE_POSITIVE', 'UNDER_REVIEW', 'DISMISSED')",
        examples=["CONFIRMED_SUSPICIOUS"],
    )
    analyst_id: str = Field(
        default="analyst_default",
        description="Identifier of the reviewing compliance officer",
    )
    notes: str = Field(
        default="",
        description="Investigative case notes or rationale for determination",
    )
    query_id: Optional[str] = Field(
        default=None,
        description="Optional associated query identifier",
    )


class AuditFeedbackResponse(BaseModel):
    """Response payload for recorded feedback action."""
    model_config = ConfigDict(populate_by_name=True)

    feedback_id: str
    flag_id: str
    query_id: Optional[str]
    feedback_status: str
    analyst_id: str
    notes: str
    reviewed_at: str


@router.post(
    "/feedback",
    response_model=AuditFeedbackResponse,
    status_code=status.HTTP_200_OK,
    summary="Record Compliance Analyst Review Feedback",
    description="Updates the review status of an AML flag and records an immutable audit feedback log entry.",
)
async def submit_feedback(
    request: AuditFeedbackRequest,
    audit_store: AuditStore = Depends(get_audit_store),
) -> AuditFeedbackResponse:
    try:
        feedback_record = audit_store.log_feedback(
            flag_id=request.flag_id,
            feedback_status=request.feedback_status,
            analyst_id=request.analyst_id,
            notes=request.notes,
            query_id=request.query_id,
        )
        return AuditFeedbackResponse(**feedback_record)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error recording audit feedback: {e}",
        )


@router.get(
    "/queries",
    response_model=List[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="List Investigation Query Audit Logs",
    description="Retrieve paginated history of natural language queries, parsed intents, and execution telemetry.",
)
async def list_queries(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    intent: Optional[str] = Query(default=None, description="Filter by detected intent"),
    status_filter: Optional[str] = Query(default=None, alias="status", description="Filter by status (SUCCESS, FAILED)"),
    audit_store: AuditStore = Depends(get_audit_store),
) -> List[Dict[str, Any]]:
    return audit_store.get_queries(
        limit=limit,
        offset=offset,
        intent=intent,
        status=status_filter,
    )


@router.get(
    "/queries/{query_id}",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get Specific Query Audit Record",
)
async def get_query_by_id(
    query_id: str,
    audit_store: AuditStore = Depends(get_audit_store),
) -> Dict[str, Any]:
    record = audit_store.get_query(query_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Query ID not found in audit store: {query_id}",
        )
    return record


@router.get(
    "/flags",
    response_model=List[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="List Logged AML Detection Flags",
    description="Retrieve filtered and paginated AML detection flags and review states.",
)
async def list_flags(
    query_id: Optional[str] = Query(default=None, description="Filter by query ID"),
    entity_id: Optional[str] = Query(default=None, description="Filter by account/entity ID"),
    severity: Optional[str] = Query(default=None, description="Filter by severity (LOW, MEDIUM, HIGH, CRITICAL)"),
    feedback_status: Optional[str] = Query(default=None, description="Filter by review status (PENDING, CONFIRMED_SUSPICIOUS, etc.)"),
    rule_id: Optional[str] = Query(default=None, description="Filter by rule ID"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    audit_store: AuditStore = Depends(get_audit_store),
) -> List[Dict[str, Any]]:
    return audit_store.get_flags(
        query_id=query_id,
        entity_id=entity_id,
        severity=severity,
        feedback_status=feedback_status,
        rule_id=rule_id,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/flags/{flag_id}",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get Flag Details and Feedback Audit Trail",
)
async def get_flag_by_id(
    flag_id: str,
    audit_store: AuditStore = Depends(get_audit_store),
) -> Dict[str, Any]:
    flag = audit_store.get_flag(flag_id)
    if not flag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Flag ID not found in audit store: {flag_id}",
        )
    return flag


@router.get(
    "/summary",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get Compliance Audit Summary Statistics",
    description="Returns aggregate statistics across queries, severity distributions, feedback determinations, and top rules.",
)
async def get_summary(
    audit_store: AuditStore = Depends(get_audit_store),
) -> Dict[str, Any]:
    return audit_store.get_audit_summary()
