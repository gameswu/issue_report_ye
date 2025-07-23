from enum import Enum
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import uuid
import datetime
import json
import os

class IssueType(Enum):
    BUG = "bug"
    FEATURE = "feature"
    QUESTION = "question"
    OTHER = "other"

class IssueStatus(Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"
    REJECTED = "rejected"

@dataclass
class IssueData:
    type: IssueType
    status: IssueStatus
    description: str
    created_at: str
    reporter: str
    updated_at: Optional[str] = None
    reporter_group: Optional[str] = None

class Issue:
    id: str
    data: IssueData

    def __init__(self, issue_type: IssueType, description: str, reporter: str, reporter_group: Optional[str] = None):
        self.id = str(uuid.uuid4())
        self.data = IssueData(
            type=issue_type,
            status=IssueStatus.OPEN,
            description=description,
            created_at=datetime.datetime.now().isoformat(),
            updated_at=None,
            reporter=reporter,
            reporter_group=reporter_group
        )

    def update_status(self, new_status: IssueStatus):
        self.data.status = new_status
        self.data.updated_at = datetime.datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "data": {
                "type": self.data.type.value,
                "status": self.data.status.value,
                "description": self.data.description,
                "created_at": self.data.created_at,
                "updated_at": self.data.updated_at,
                "reporter": self.data.reporter,
                "reporter_group": self.data.reporter_group
            }
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'Issue':
        issue = Issue(
            issue_type=IssueType(data["data"]["type"]),
            description=data["data"]["description"],
            reporter=data["data"]["reporter"],
            reporter_group=data["data"].get("reporter_group")
        )
        issue.id = data["id"]
        issue.data.status = IssueStatus(data["data"]["status"])
        issue.data.created_at = data["data"]["created_at"]
        issue.data.updated_at = data["data"].get("updated_at")
        return issue


class IssueManager:
    """Issue管理器，负责持久化保存和读取issue数据"""
    
    def __init__(self):
        # 获取两层父级目录路径
        self.base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.json_file_path = os.path.join(self.base_path, "issue.json")
        self._ensure_json_file_exists()
    
    def _ensure_json_file_exists(self):
        """确保issue.json文件存在，如果不存在则创建"""
        if not os.path.exists(self.json_file_path):
            # 确保目录存在
            os.makedirs(os.path.dirname(self.json_file_path), exist_ok=True)
            # 创建空的JSON文件
            with open(self.json_file_path, 'w', encoding='utf-8') as f:
                json.dump({"issues": []}, f, ensure_ascii=False, indent=2)
    
    def load_issues(self) -> List[Issue]:
        """从JSON文件加载所有issues"""
        try:
            with open(self.json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                issues = []
                for issue_data in data.get("issues", []):
                    issues.append(Issue.from_dict(issue_data))
                return issues
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"加载issues时出错: {e}")
            return []
    
    def save_issues(self, issues: List[Issue]) -> bool:
        """保存所有issues到JSON文件"""
        try:
            data = {
                "issues": [issue.to_dict() for issue in issues],
                "last_updated": datetime.datetime.now().isoformat()
            }
            with open(self.json_file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存issues时出错: {e}")
            return False
    
    def add_issue(self, issue: Issue) -> bool:
        """添加新的issue"""
        issues = self.load_issues()
        issues.append(issue)
        return self.save_issues(issues)
    
    def update_issue(self, issue_id: str, new_status: IssueStatus) -> bool:
        """更新指定ID的issue状态"""
        issues = self.load_issues()
        for issue in issues:
            if issue.id == issue_id:
                issue.update_status(new_status)
                return self.save_issues(issues)
        return False
    
    def get_issue_by_id(self, issue_id: str) -> Optional[Issue]:
        """根据ID获取issue"""
        issues = self.load_issues()
        for issue in issues:
            if issue.id == issue_id:
                return issue
        return None
    
    def get_issues_by_status(self, status: Optional[IssueStatus]) -> List[Issue]:
        """根据状态获取issues，如果status为None则返回所有issues"""
        issues = self.load_issues()
        if status is None:
            return issues
        return [issue for issue in issues if issue.data.status == status]
    
    def get_issues_by_type(self, issue_type: IssueType) -> List[Issue]:
        """根据类型获取issues"""
        issues = self.load_issues()
        return [issue for issue in issues if issue.data.type == issue_type]
    
    def get_issues_by_reporter(self, reporter: str) -> List[Issue]:
        """根据报告人获取issues"""
        issues = self.load_issues()
        return [issue for issue in issues if issue.data.reporter == reporter]
    
    def delete_issue(self, issue_id: str) -> bool:
        """删除指定ID的issue"""
        issues = self.load_issues()
        original_count = len(issues)
        issues = [issue for issue in issues if issue.id != issue_id]
        if len(issues) < original_count:
            return self.save_issues(issues)
        return False
    
    def get_json_file_path(self) -> str:
        """获取JSON文件的完整路径"""
        return self.json_file_path