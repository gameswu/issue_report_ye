from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult, MessageChain
from astrbot.api.star import Context, Star, register
from astrbot.api import logger, AstrBotConfig
import astrbot.api.message_components as Comp

from .issue import Issue, IssueData, IssueType, IssueStatus, IssueManager

@register("issue_report_ye", "gameswu", "问题反馈插件", "0.1.0")
class MyPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.receivers = config.get("receivers", [])

    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""
        logger.info(f"Plugin has initialized with receivers: {self.receivers}")
    
    @filter.command_group("issue")
    def issue(self, event: AstrMessageEvent):
        pass

    @issue.command("report")
    async def report_issue(self, event: AstrMessageEvent, issue_type_str: str, description: str):
        """提交问题报告"""
        issue_type = IssueType(issue_type_str)
        reporter = event.get_sender_id()
        reporter_group = event.get_group_id() if not event.is_private_chat() else None

        issue = Issue(issue_type, description, reporter, reporter_group)
        issue_manager = IssueManager()
        issue_manager.add_issue(issue)

        report_info = (
            f"问题已提交！\n"
            f"ID: {issue.id}\n"
            f"类型: {issue.data.type}\n"
            f"状态: {issue.data.status}\n"
            f"描述: {issue.data.description}\n"
        )

        await event.send(MessageChain().message(report_info))
        logger.info(f"Issue reported by {reporter} in group {reporter_group}: {issue.data.description}")

        receive_info = (
            f"新问题报告：\n"
            f"ID: {issue.id}\n"
            f"类型: {issue.data.type}\n"
            f"状态: {issue.data.status}\n"
            f"描述: {issue.data.description}\n"
            f"报告者: {reporter}\n"
            f"报告者群组: {reporter_group if reporter_group else '私聊'}\n"
        )
        message_chain = MessageChain().message(receive_info)
        for receiver in self.receivers:
            await self.send_notification(message_chain=message_chain, receiver=receiver)

    @issue.command("check")
    async def check_issue(self, event: AstrMessageEvent):
        """检查用户提交的问题的处理状态"""
        issues = IssueManager().get_issues_by_reporter(event.get_sender_id())
        if not issues:
            await event.send(MessageChain().message("您没有提交过任何问题记录。"))
            return
        response = (
            "您的问题记录：\n" +
            "\n".join(
                f"ID: {issue.id}, 类型: {issue.data.type}, 状态: {issue.data.status}, 描述: {issue.data.description}"
                for issue in issues
            )
        )
        await event.send(MessageChain().message(response))

    @issue.command("feedback")
    async def feedback(self, event: AstrMessageEvent, issue_id: str, new_status: str, feedback: str):
        """反馈问题处理结果"""
        if event.get_sender_id() not in self.receivers:
            await event.send(MessageChain().message("您没有权限反馈问题。"))
            return
        issue = IssueManager().get_issue_by_id(issue_id)
        if not issue:
            await event.send(MessageChain().message("未找到该问题记录。"))
            return
        reporter = issue.data.reporter
        reporter_group = issue.data.reporter_group

        success = IssueManager().update_issue(issue_id=issue_id, new_status=IssueStatus(new_status))
        if not success:
            await event.send(MessageChain().message("更新问题反馈失败。"))
            return

        feedback_info = (
            f"问题反馈已提交！\n"
            f"ID: {issue.id}\n"
            f"新状态: {new_status}\n"
            f"反馈: {feedback}\n"
        )
        await event.send(MessageChain().message(feedback_info))
        await self.send_notification(message_chain=MessageChain().message(feedback_info), receiver=reporter, receiver_group=reporter_group)

    @issue.command("list")
    async def list_issues(self, event: AstrMessageEvent, status: str = None):
        """列出所有问题记录"""
        if event.get_sender_id() not in self.receivers:
            await event.send(MessageChain().message("您没有权限查看问题记录。"))
            return
        issues = IssueManager().get_issues_by_status(IssueStatus(status) if status else None)
        if not issues:
            status_desc = f"状态为{status}的" if status else ""
            await event.send(MessageChain().message(f"没有找到任何{status_desc}问题记录。"))
            return
        response = (
            f"问题记录列表：\n" +
            "\n".join(
                f"ID: {issue.id}, 类型: {issue.data.type}, 状态: {issue.data.status}, 描述: {issue.data.description}, 报告者: {issue.data.reporter}, 群组: {issue.data.reporter_group if issue.data.reporter_group else '私聊'}"
                for issue in issues
            )
        )
        await event.send(MessageChain().message(response))

    @issue.command("help")
    async def help(self, event: AstrMessageEvent):
        """显示帮助信息"""
        help_info = (
            "问题反馈插件使用帮助：\n"
            "1. /issue report <类型> <描述> - 提交问题报告\n"
            "2. /issue check - 检查您提交的问题处理状态\n"
            "3. /issue feedback <ID> <新状态> <反馈> - 反馈问题处理结果\n"
            "4. /issue list [状态] - 列出所有问题记录或指定状态的问题记录\n"
            "5. /issue help - 显示帮助信息\n"
            "支持的类型：\n"
            f"{', '.join([item.value for item in IssueType])}\n"
            "支持的状态：\n"
            f"{', '.join([item.value for item in IssueStatus])}"
        )
        await event.send(MessageChain().message(help_info))

    async def send_notification(self, message_chain: MessageChain, receiver: str, receiver_group: str = None):
        """发送通知给接收者"""
        # QQ平台发送消息
        qq_session = f"aiocqhttp:GroupMessage:{receiver_group}" if receiver_group else f"aiocqhttp:PrivateMessage:{receiver}"
        if receiver_group:
            message_chain.chain.append(Comp.At(qq = receiver))
        await self.context.send_message(qq_session, message_chain)

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
