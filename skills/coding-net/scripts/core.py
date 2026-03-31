"""Coding 开放平台 Open API — 基础设施（HTTP 客户端、Token 解析）。"""

from __future__ import annotations

import json
import logging
import os
import traceback
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

BASE_URL = "https://e.coding.net/open-api/"
DEFAULT_TIMEOUT = 30
# token 值请 export CODING_TOKEN=...，勿把密钥写进代码
TOKEN_ENV = "CODING_TOKEN"
# 默认项目名称
DEFAULT_PROJECT_NAME_ENV = "CODING_DEFAULT_PROJECT_NAME"
DEFAULT_PROJECT_NAME: str | None = None
# DescribeIssueList 的 ITERATION 条件所用迭代 Code 的默认来源
DEFAULT_ITERATION_ENV = "CODING_DEFAULT_ITERATION_CODE"
DEFAULT_ITERATION_CODE: int | None = None


class CodingAPIError(Exception):
    """Coding API 调用失败（HTTP、JSON 或响应结构异常）。"""


def _resolve_project_name(project_name: str | None) -> str:
    if project_name is not None and project_name.strip():
        return project_name.strip()
    env = os.environ.get(DEFAULT_PROJECT_NAME_ENV, "").strip()
    if env:
        return env
    if DEFAULT_PROJECT_NAME is not None and DEFAULT_PROJECT_NAME.strip():
        return DEFAULT_PROJECT_NAME.strip()
    raise ValueError(
        f"未提供项目名称：请传 project_name=...，或设置环境变量 {DEFAULT_PROJECT_NAME_ENV}",
    )


def _resolve_token(token: str | None) -> str:
    if token is not None and token.strip():
        return token.strip()
    env = os.environ.get(TOKEN_ENV, "").strip()
    if env:
        return env
    raise ValueError(
        f"未提供 token：请传 token=...，或设置环境变量 {TOKEN_ENV}",
    )


def _request(
    action: str,
    body: dict[str, Any],
    token: str,
    *,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """向 Coding Open API 发送 POST 请求，返回解析后的 JSON 对象。"""
    query = urlencode({"Action": action, "action": action})
    url = f"{BASE_URL}?{query}"
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = Request(
        url,
        data=data,
        method="POST",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
    )
    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            status = getattr(resp, "status", 200)
    except HTTPError as e:
        try:
            raw = e.read()
        except Exception:
            raw = b""
        logger.error("Coding API HTTP 错误: %s\n%s", e, traceback.format_exc())
        raise CodingAPIError(f"HTTP {e.code}: {e.reason}") from e
    except URLError as e:
        logger.error("Coding API 网络错误: %s\n%s", e, traceback.format_exc())
        raise CodingAPIError(f"请求失败: {e.reason}") from e
    except Exception:
        logger.error("Coding API 请求异常\n%s", traceback.format_exc())
        raise

    try:
        text = raw.decode("utf-8")
        parsed: dict[str, Any] = json.loads(text)
    except json.JSONDecodeError:
        logger.error(
            "Coding API 响应非 JSON\n%s\nbody 片段: %s",
            traceback.format_exc(),
            raw[:500],
        )
        raise CodingAPIError("响应不是合法 JSON") from None

    if status and not (200 <= status < 300):
        logger.error("Coding API 非成功状态: status=%s body=%s", status, parsed)
        raise CodingAPIError(f"HTTP 状态异常: {status}")

    if "Response" not in parsed:
        err = parsed.get("Error") or parsed.get("error") or parsed
        logger.error("Coding API 响应缺少 Response: %s", err)
        raise CodingAPIError(f"响应缺少 Response 字段: {err}")

    return parsed
