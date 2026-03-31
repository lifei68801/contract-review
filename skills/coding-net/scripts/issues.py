"""Coding 开放平台 Open API — 事项相关接口。"""

from __future__ import annotations

import logging
import os
import sys
import traceback
from typing import Any, Literal

sys.path.insert(0, os.path.dirname(__file__))
from core import (  # noqa: E402
    CodingAPIError,
    DEFAULT_TIMEOUT,
    _request,
    _resolve_project_name,
    _resolve_token,
)
from iterations import _resolve_iteration_code  # noqa: E402

logger = logging.getLogger(__name__)

_STATUS_TYPE_SET = frozenset({"TODO", "PROCESSING", "COMPLETED"})
_BASE_ISSUE_TYPE_SET = frozenset({"REQUIREMENT", "DEFECT", "MISSION"})


# ── 内部辅助 ──────────────────────────────────────────────────────────────────

def _resolve_issue_status_type_filter(
    status_types: list[str] | None,
) -> frozenset[str] | None:
    """None → 默认仅 TODO、PROCESSING；[] → 不过滤；非空 → 仅保留列出的类型。"""
    if status_types is None:
        return frozenset({"TODO", "PROCESSING"})
    if not status_types:
        return None
    bad = [s for s in status_types if s not in _STATUS_TYPE_SET]
    if bad:
        raise ValueError(f"IssueStatusType 仅允许 TODO/PROCESSING/COMPLETED，无效项: {bad}")
    return frozenset(status_types)


def _filter_response_issue_list_by_issue_status_type(
    parsed: dict[str, Any],
    allowed: frozenset[str] | None,
) -> None:
    """就地缩小 Response.IssueList，仅保留 IssueStatusType 在 allowed 内的事项。"""
    if allowed is None:
        return
    resp = parsed.get("Response")
    if not isinstance(resp, dict):
        return
    issues = resp.get("IssueList")
    if not isinstance(issues, list):
        return
    resp["IssueList"] = [
        item for item in issues
        if isinstance(item, dict) and item.get("IssueStatusType") in allowed
    ]


def _summarize_issue_list_item(raw: dict[str, Any]) -> dict[str, Any]:
    """DescribeIssueList 单条事项精简字段（Assignees 第 0/1 个元素对应 Creator/Handler）。"""
    assignee_names: list[str] = []
    for m in (raw.get("Assignees") or []):
        if isinstance(m, dict):
            assignee_names.append(str(m.get("Name") or ""))
    return {
        "ParentType": raw.get("ParentType"),
        "Code": raw.get("Code"),
        "Name": raw.get("Name"),
        "IssueStatusName": raw.get("IssueStatusName"),
        "Priority": raw.get("Priority"),
        "CreatorName": assignee_names[0] if len(assignee_names) > 0 else "",
        "HandlerName": assignee_names[1] if len(assignee_names) > 1 else "",
        "StartDate": raw.get("StartDate"),
        "DueDate": raw.get("DueDate"),
        "CreatedAt": raw.get("CreatedAt"),
        "UpdatedAt": raw.get("UpdatedAt"),
    }


def _summarize_response_issue_list(parsed: dict[str, Any]) -> None:
    """将 Response.IssueList 替换为精简结构（就地）。"""
    resp = parsed.get("Response")
    if not isinstance(resp, dict):
        return
    issues = resp.get("IssueList")
    if not isinstance(issues, list):
        return
    resp["IssueList"] = [
        _summarize_issue_list_item(item) for item in issues if isinstance(item, dict)
    ]


def _build_issue_list_conditions(
    *,
    assignee_ids: list[int] | None,
    iteration: int | None,
    base_issue_type: str | None,
) -> list[dict[str, Any]]:
    conds: list[dict[str, Any]] = []
    if assignee_ids:
        conds.append({"key": "ASSIGNEE", "value": [int(x) for x in assignee_ids]})
    conds.append({"key": "ITERATION", "value": [_resolve_iteration_code(iteration)]})
    if base_issue_type is not None:
        if base_issue_type not in _BASE_ISSUE_TYPE_SET:
            raise ValueError(
                f"BASE_ISSUE_TYPE 仅允许 REQUIREMENT/DEFECT/MISSION，收到: {base_issue_type!r}"
            )
        conds.append({"key": "BASE_ISSUE_TYPE", "value": base_issue_type})
    return conds


def _issue_detail_person_name(obj: Any) -> str:
    if isinstance(obj, dict):
        return str(obj.get("Name") or "")
    return ""


def _summarize_issue_detail(issue: dict[str, Any]) -> dict[str, Any]:
    return {
        "Name": issue.get("Name"),
        "Description": issue.get("Description"),
        "IssueStatusName": issue.get("IssueStatusName"),
        "AssigneeName": _issue_detail_person_name(issue.get("Assignee")),
        "CreatorName": _issue_detail_person_name(issue.get("Creator")),
    }


# ── 公开接口 ──────────────────────────────────────────────────────────────────

def describe_issue(
    project_name: str | None = None,
    issue_code: int = 0,
    *,
    show_image_out_url: bool = True,
    token: str | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """
    DescribeIssue：按事项 Code 查询单条事项详情，返回精简字段。

    :return: {Name, Description, IssueStatusName, AssigneeName, CreatorName}
    """
    t = _resolve_token(token)
    pn = _resolve_project_name(project_name)
    parsed = _request(
        "DescribeIssue",
        {"ProjectName": pn, "IssueCode": int(issue_code), "ShowImageOutUrl": show_image_out_url},
        t,
        timeout=timeout,
    )
    try:
        issue = parsed["Response"]["Issue"]
    except (KeyError, TypeError) as e:
        logger.error("DescribeIssue 响应缺少 Response.Issue\n%s", traceback.format_exc())
        raise CodingAPIError("响应中缺少 Response.Issue") from e
    if not isinstance(issue, dict):
        raise CodingAPIError("Response.Issue 不是对象") from None
    return _summarize_issue_detail(issue)


def describe_issue_list(
    project_name: str | None = None,
    *,
    issue_type: str = "ALL",
    limit: str = "2000",
    assignee_ids: list[int] | None = None,
    iteration: int | None = None,
    status_types: list[str] | None = None,
    base_issue_type: Literal["REQUIREMENT", "DEFECT", "MISSION"] | None = None,
    token: str | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """
    DescribeIssueList：查询项目下事项列表。

    排序固定为 SortKey=PRIORITY/DESC；STATUS_TYPE 由本地过滤实现。
    :param status_types: None → 仅 TODO/PROCESSING；[] → 不过滤；其他 → 指定类型。
    :return: 含 Response.IssueList，每条仅含精简字段（见 _summarize_issue_list_item）。
    """
    t = _resolve_token(token)
    pn = _resolve_project_name(project_name)
    allowed_status = _resolve_issue_status_type_filter(status_types)
    conditions = _build_issue_list_conditions(
        assignee_ids=assignee_ids, iteration=iteration, base_issue_type=base_issue_type,
    )
    body: dict[str, Any] = {
        "ProjectName": pn,
        "IssueType": issue_type,
        "Limit": limit,
        "Conditions": conditions,
        "SortKey": "PRIORITY",
        "SortValue": "DESC",
        "ShowImageOutUrl": False,
    }
    parsed = _request("DescribeIssueList", body, t, timeout=timeout)
    _filter_response_issue_list_by_issue_status_type(parsed, allowed_status)
    _summarize_response_issue_list(parsed)
    return parsed
