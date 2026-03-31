#!/usr/bin/env python3
"""
CODING Open API 客户端
用于对接 CODING 项目协同功能
"""

import json
import sys
import requests
from pathlib import Path
from typing import Optional, Dict, List, Any

# 配置文件路径
CONFIG_PATH = Path(__file__).parent / "config.json"


class CodingClient:
    """CODING API 客户端"""
    
    def __init__(self, team: str = None, token: str = None, default_project: str = None):
        """
        初始化客户端
        
        Args:
            team: 团队名称
            token: 访问令牌（个人令牌）或 "用户名:密码" 格式（项目令牌）
            default_project: 默认项目名称
        """
        # 优先使用传入参数，否则从配置文件读取
        config = self._load_config()
        self.team = team or config.get("team", "")
        self.token = token or config.get("token", "")
        self.default_project = default_project or config.get("default_project", "")
        self.auth_type = config.get("auth_type", "token")
        
        self.base_url = f"https://{self.team}.coding.net/open-api"
        
        # 根据认证类型设置 Authorization header
        if self.auth_type == "basic" and ":" in self.token:
            # 项目令牌：Basic 认证
            import base64
            credentials = base64.b64encode(self.token.encode()).decode()
            self.headers = {
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/json"
            }
        else:
            # 个人令牌：Token 认证
            self.headers = {
                "Authorization": f"token {self.token}",
                "Content-Type": "application/json"
            }
    
    def _load_config(self) -> Dict:
        """加载配置文件"""
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}
    
    def _request(self, action: str, data: Dict = None, **kwargs) -> Dict:
        """
        发送 API 请求
        
        Args:
            action: API Action 名称
            data: 请求数据
            **kwargs: 其他请求参数
            
        Returns:
            API 响应
        """
        payload = {"Action": action}
        if data:
            payload.update(data)
        payload.update(kwargs)
        
        try:
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            result = response.json()
            
            if "Response" in result:
                if "Error" in result["Response"]:
                    return {
                        "success": False,
                        "error": result["Response"]["Error"].get("Message", "Unknown error"),
                        "request_id": result["Response"].get("RequestId")
                    }
                return {
                    "success": True,
                    "data": result["Response"],
                    "request_id": result["Response"].get("RequestId")
                }
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ========== 事项管理 ==========
    
    def list_issues(self, project_name: str = None, issue_type: str = None,
                    page: int = 1, page_size: int = 50, **kwargs) -> Dict:
        """
        查询事项列表
        
        Args:
            project_name: 项目名称
            issue_type: 事项类型 (REQUIREMENT/DEFECT/MISSION)
            page: 页码
            page_size: 每页数量
            **kwargs: 其他查询条件
            
        Returns:
            事项列表
        """
        data = {
            "ProjectName": project_name or self.default_project,
            "PageNumber": page,
            "PageSize": page_size,
            **kwargs
        }
        if issue_type:
            data["IssueType"] = issue_type
        
        return self._request("DescribeProjectIssues", data)
    
    def get_issue(self, project_name: str = None, issue_code: int = None) -> Dict:
        """
        查询事项详情
        
        Args:
            project_name: 项目名称
            issue_code: 事项 Code
            
        Returns:
            事项详情
        """
        return self._request("DescribeIssue", {
            "ProjectName": project_name or self.default_project,
            "IssueCode": issue_code
        })
    
    def create_issue(self, name: str, issue_type: str = "REQUIREMENT",
                     project_name: str = None, priority: str = "1",
                     description: str = "", assignee_id: int = None,
                     iteration_code: int = None, label_ids: List[int] = None,
                     **kwargs) -> Dict:
        """
        创建事项
        
        Args:
            name: 事项名称
            issue_type: 事项类型 (REQUIREMENT/DEFECT/MISSION/EPIC/SUB_TASK)
            project_name: 项目名称
            priority: 优先级 ("0"-低, "1"-中, "2"-高, "3"-紧急)
            description: 描述
            assignee_id: 处理人 ID
            iteration_code: 迭代 Code
            label_ids: 标签 ID 列表
            **kwargs: 其他参数
            
        Returns:
            创建结果
        """
        data = {
            "ProjectName": project_name or self.default_project,
            "Name": name,
            "Type": issue_type,
            "Priority": priority,
            "Description": description
        }
        if assignee_id:
            data["AssigneeId"] = assignee_id
        if iteration_code:
            data["IterationCode"] = iteration_code
        if label_ids:
            data["LabelIds"] = label_ids
        data.update(kwargs)
        
        return self._request("CreateIssue", data)
    
    def create_requirement(self, name: str, **kwargs) -> Dict:
        """创建需求"""
        return self.create_issue(name, "REQUIREMENT", **kwargs)
    
    def create_bug(self, name: str, priority: str = "2", **kwargs) -> Dict:
        """
        创建 Bug
        
        Args:
            name: Bug 名称
            priority: 优先级 (默认 "2"-高)
            **kwargs: 其他参数
        """
        return self.create_issue(name, "DEFECT", priority=priority, **kwargs)
    
    def create_task(self, name: str, **kwargs) -> Dict:
        """创建任务"""
        return self.create_issue(name, "MISSION", **kwargs)
    
    def update_issue(self, project_name: str = None, issue_code: int = None,
                     **kwargs) -> Dict:
        """
        更新事项
        
        Args:
            project_name: 项目名称
            issue_code: 事项 Code
            **kwargs: 要更新的字段
        """
        return self._request("ModifyIssue", {
            "ProjectName": project_name or self.default_project,
            "IssueCode": issue_code,
            **kwargs
        })
    
    def update_issue_status(self, project_name: str = None, issue_code: int = None,
                            status_id: int = None) -> Dict:
        """
        更新事项状态
        
        Args:
            project_name: 项目名称
            issue_code: 事项 Code
            status_id: 状态 ID
        """
        return self.update_issue(project_name, issue_code, StatusId=status_id)
    
    def delete_issue(self, project_name: str = None, issue_code: int = None) -> Dict:
        """删除事项"""
        return self._request("DeleteIssue", {
            "ProjectName": project_name or self.default_project,
            "IssueCode": issue_code
        })
    
    # ========== 迭代管理 ==========
    
    def list_iterations(self, project_name: str = None) -> Dict:
        """查询迭代列表"""
        return self._request("DescribeIterations", {
            "ProjectName": project_name or self.default_project
        })
    
    def create_iteration(self, name: str, start_date: str, end_date: str,
                         project_name: str = None) -> Dict:
        """
        创建迭代
        
        Args:
            name: 迭代名称
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            project_name: 项目名称
        """
        return self._request("CreateIteration", {
            "ProjectName": project_name or self.default_project,
            "Name": name,
            "StartDate": start_date,
            "EndDate": end_date
        })
    
    def get_iteration(self, project_name: str = None, iteration_code: int = None) -> Dict:
        """查询迭代详情"""
        return self._request("DescribeIteration", {
            "ProjectName": project_name or self.default_project,
            "IterationCode": iteration_code
        })
    
    # ========== 构建管理 ==========
    
    def trigger_build(self, job_id: int, project_id: int = None,
                      ref: str = "master", env_vars: Dict = None) -> Dict:
        """
        触发构建
        
        Args:
            job_id: 构建计划 ID
            project_id: 项目 ID
            ref: 分支
            env_vars: 环境变量
        """
        data = {
            "JobId": job_id,
            "Ref": ref
        }
        if project_id:
            data["ProjectId"] = project_id
        if env_vars:
            data["EnvVars"] = env_vars
        
        return self._request("TriggerBuild", data)
    
    def list_builds(self, job_id: int, project_id: int = None,
                    page: int = 1, page_size: int = 20) -> Dict:
        """查询构建列表"""
        data = {
            "JobId": job_id,
            "PageNumber": page,
            "PageSize": page_size
        }
        if project_id:
            data["ProjectId"] = project_id
        
        return self._request("DescribeJobBuilds", data)
    
    # ========== 合并请求 ==========
    
    def create_mr(self, depot_id: int, source_branch: str, target_branch: str,
                  title: str, description: str = "") -> Dict:
        """
        创建合并请求
        
        Args:
            depot_id: 仓库 ID
            source_branch: 源分支
            target_branch: 目标分支
            title: 标题
            description: 描述
        """
        return self._request("CreateGitMergeRequest", {
            "DepotId": depot_id,
            "SourceBranch": source_branch,
            "TargetBranch": target_branch,
            "Title": title,
            "Description": description
        })
    
    def merge_mr(self, depot_id: int, merge_id: int) -> Dict:
        """合并 MR"""
        return self._request("MergeGitMergeRequest", {
            "DepotId": depot_id,
            "MergeId": merge_id
        })
    
    def list_mrs(self, depot_id: int, state: str = "open") -> Dict:
        """查询 MR 列表"""
        return self._request("DescribeGitMergeRequests", {
            "DepotId": depot_id,
            "State": state
        })


def format_issues_for_display(issues: List[Dict]) -> str:
    """格式化事项列表用于显示"""
    if not issues:
        return "暂无事项"
    
    lines = []
    for issue in issues:
        priority_map = {"0": "低", "1": "中", "2": "高", "3": "紧急"}
        status = issue.get("IssueStatusName", "未知")
        priority = priority_map.get(issue.get("Priority", "1"), "中")
        assignee = issue.get("Assignee", {}).get("Name", "未分配")
        due_date = issue.get("DueDate", "")
        
        line = f"- [{status}] {issue.get('Name', '')} (优先级: {priority}, 处理人: {assignee}"
        if due_date:
            line += f", 截止: {due_date}"
        line += ")"
        lines.append(line)
    
    return "\n".join(lines)


# 命令行入口
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: coding-client.py <command> [args...]")
        print("Commands:")
        print("  list-issues <project> [type]     - 查询事项列表")
        print("  create-issue <project> <name> <type> [priority] - 创建事项")
        print("  list-iterations <project>        - 查询迭代列表")
        sys.exit(1)
    
    client = CodingClient()
    command = sys.argv[1]
    
    if command == "list-issues":
        project = sys.argv[2] if len(sys.argv) > 2 else client.default_project
        issue_type = sys.argv[3] if len(sys.argv) > 3 else None
        result = client.list_issues(project, issue_type)
        if result.get("success"):
            issues = result["data"].get("Issues", [])
            print(format_issues_for_display(issues))
        else:
            print(f"错误: {result.get('error')}")
    
    elif command == "create-issue":
        project = sys.argv[2] if len(sys.argv) > 2 else client.default_project
        name = sys.argv[3] if len(sys.argv) > 3 else "新事项"
        issue_type = sys.argv[4] if len(sys.argv) > 4 else "REQUIREMENT"
        priority = sys.argv[5] if len(sys.argv) > 5 else "1"
        result = client.create_issue(name, issue_type, project, priority)
        if result.get("success"):
            issue = result["data"].get("Issue", {})
            print(f"创建成功: {issue.get('Name')} (Code: {issue.get('Code')})")
        else:
            print(f"错误: {result.get('error')}")
    
    elif command == "list-iterations":
        project = sys.argv[2] if len(sys.argv) > 2 else client.default_project
        result = client.list_iterations(project)
        if result.get("success"):
            iterations = result["data"].get("Iterations", [])
            for it in iterations:
                print(f"- {it.get('Name')} (Code: {it.get('Code')}, 状态: {it.get('Status')})")
        else:
            print(f"错误: {result.get('error')}")
    
    else:
        print(f"未知命令: {command}")
