from datetime import datetime

from rich.text import Text
from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    RichLog,
    Static,
)

from api import ApiError, ChatAPI


class UserItem(ListItem):
    def __init__(self, username: str):
        super().__init__(Label(username))
        self.username = username


class GroupItem(ListItem):
    def __init__(self, group: dict):
        super().__init__(Label(group["name"]))
        self.group_id = group["id"]
        self.group_name = group["name"]


class PromptScreen(ModalScreen[str | None]):
    """Modal asking for a single line of text; dismisses with it (or None)."""

    def __init__(self, title: str, placeholder: str = ""):
        super().__init__()
        self._title = title
        self._placeholder = placeholder

    def compose(self) -> ComposeResult:
        with Container(id="prompt-box"):
            yield Static(self._title, id="prompt-title")
            yield Input(placeholder=self._placeholder, id="prompt-input")
            with Horizontal(id="prompt-buttons"):
                yield Button("OK", variant="primary", id="prompt-ok")
                yield Button("Cancel", id="prompt-cancel")

    def on_mount(self) -> None:
        self.query_one("#prompt-input", Input).focus()

    def _submit(self) -> None:
        value = self.query_one("#prompt-input", Input).value.strip()
        self.dismiss(value or None)

    @on(Input.Submitted, "#prompt-input")
    @on(Button.Pressed, "#prompt-ok")
    def submit(self) -> None:
        self._submit()

    @on(Button.Pressed, "#prompt-cancel")
    def cancel(self) -> None:
        self.dismiss(None)


class LoginScreen(Screen):
    def compose(self) -> ComposeResult:
        with Container(id="login-box"):
            yield Static("Kerberos Chat", id="login-title")
            yield Input(placeholder="username", id="username")
            yield Input(placeholder="password", password=True, id="password")
            yield Button("Login", variant="primary", id="login-button")
            yield Static("", id="login-error")

    def on_mount(self) -> None:
        self.query_one("#username", Input).focus()

    @on(Input.Submitted)
    @on(Button.Pressed, "#login-button")
    def submit(self) -> None:
        username = self.query_one("#username", Input).value.strip()
        password = self.query_one("#password", Input).value
        if not username or not password:
            self.query_one("#login-error", Static).update(
                "username and password are required")
            return
        self.do_login(username, password)

    @work(exclusive=True)
    async def do_login(self, username: str, password: str) -> None:
        error = self.query_one("#login-error", Static)
        error.update("logging in...")
        try:
            await self.app.api.login(username, password)
        except ApiError as exc:
            error.update(str(exc))
            return
        self.app.switch_screen(ChatScreen())


class ChatScreen(Screen):
    BINDINGS = [("ctrl+r", "refresh", "Refresh")]

    def __init__(self):
        super().__init__()
        self.conversation: tuple[str, str | int] | None = None
        self.last_message_id = 0
        self._users: list[str] = []
        self._groups: list[dict] = []

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="body"):
            with Vertical(id="sidebar"):
                yield Static("Users", classes="sidebar-title")
                yield ListView(id="users")
                yield Static("Groups", classes="sidebar-title")
                yield ListView(id="groups")
                with Vertical(id="sidebar-actions"):
                    yield Button("New group", id="new-group")
                    yield Button("Add member", id="add-member", disabled=True)
                    yield Button("Logout", id="logout", variant="error")
            with Vertical(id="chat"):
                yield Static("Select a user or group", id="conversation-title")
                yield RichLog(id="messages", wrap=True)
                yield Input(placeholder="Type a message...", id="composer", disabled=True)
        yield Footer()

    def on_mount(self) -> None:
        self.sub_title = f"logged in as {self.app.api.username}"
        self.refresh_data()
        self.set_interval(3.0, self.refresh_data)

    def action_refresh(self) -> None:
        self.refresh_data()

    def refresh_data(self) -> None:
        self.load_sidebar()
        self.load_messages()

    @work(exclusive=True, group="sidebar")
    async def load_sidebar(self) -> None:
        try:
            users = [u for u in await self.app.api.list_users()
                     if u != self.app.api.username]
            groups = await self.app.api.list_groups()
        except ApiError as exc:
            self._handle_error(exc)
            return

        if users != self._users:
            self._users = users
            users_list = self.query_one("#users", ListView)
            await users_list.clear()
            await users_list.extend(UserItem(u) for u in users)

        if groups != self._groups:
            self._groups = groups
            groups_list = self.query_one("#groups", ListView)
            await groups_list.clear()
            await groups_list.extend(GroupItem(g) for g in groups)

    @on(ListView.Selected, "#users")
    def select_user(self, event: ListView.Selected) -> None:
        item = event.item
        assert isinstance(item, UserItem)
        self._open_conversation(("dm", item.username), f"@ {item.username}")
        self.query_one("#add-member", Button).disabled = True

    @on(ListView.Selected, "#groups")
    def select_group(self, event: ListView.Selected) -> None:
        item = event.item
        assert isinstance(item, GroupItem)
        self._open_conversation(
            ("group", item.group_id), f"# {item.group_name}")
        self.query_one("#add-member", Button).disabled = False

    def _open_conversation(self, conversation: tuple, title: str) -> None:
        self.conversation = conversation
        self.last_message_id = 0
        self.query_one("#messages", RichLog).clear()
        self.query_one("#conversation-title", Static).update(title)
        composer = self.query_one("#composer", Input)
        composer.disabled = False
        composer.focus()
        self.load_messages()

    @work(exclusive=True, group="messages")
    async def load_messages(self) -> None:
        if self.conversation is None:
            return
        kind, key = self.conversation
        try:
            if kind == "dm":
                messages = await self.app.api.get_conversation(key)
            else:
                messages = await self.app.api.get_group_messages(key)
        except ApiError as exc:
            self._handle_error(exc)
            return

        if self.conversation != (kind, key):
            return

        log = self.query_one("#messages", RichLog)
        for message in messages:
            if message["id"] > self.last_message_id:
                log.write(self._format_message(message))
                self.last_message_id = message["id"]

    def _format_message(self, message: dict) -> Text:
        timestamp = datetime.fromtimestamp(
            message["created_at"]).strftime("%H:%M")
        mine = message["sender"] == self.app.api.username
        text = Text()
        text.append(f"{timestamp} ", style="dim")
        text.append(f"{message['sender']}: ",
                    style="bold cyan" if mine else "bold magenta")
        text.append(message["content"])
        return text

    @on(Input.Submitted, "#composer")
    def submit_message(self, event: Input.Submitted) -> None:
        content = event.value.strip()
        if content and self.conversation is not None:
            self.send_message(self.conversation, content)
        event.input.value = ""

    @work(group="send")
    async def send_message(self, conversation: tuple, content: str) -> None:
        kind, key = conversation
        try:
            if kind == "dm":
                await self.app.api.send_dm(key, content)
            else:
                await self.app.api.send_group_message(key, content)
        except ApiError as exc:
            self._handle_error(exc)
            return
        self.load_messages()

    @on(Button.Pressed, "#new-group")
    def new_group(self) -> None:
        self.app.push_screen(
            PromptScreen("New group", placeholder="group name"),
            self._create_group,
        )

    def _create_group(self, name: str | None) -> None:
        if name:
            self.create_group(name)

    @work(group="groups")
    async def create_group(self, name: str) -> None:
        try:
            group = await self.app.api.create_group(name)
        except ApiError as exc:
            self._handle_error(exc)
            return
        self.notify(f"group {group['name']!r} created")
        self.load_sidebar()

    @on(Button.Pressed, "#add-member")
    def add_member(self) -> None:
        if self.conversation and self.conversation[0] == "group":
            self.app.push_screen(
                PromptScreen("Add member", placeholder="username"),
                self._add_member,
            )

    def _add_member(self, username: str | None) -> None:
        if username and self.conversation and self.conversation[0] == "group":
            self.do_add_member(self.conversation[1], username)

    @work(group="groups")
    async def do_add_member(self, group_id: int, username: str) -> None:
        try:
            await self.app.api.add_member(group_id, username)
        except ApiError as exc:
            self._handle_error(exc)
            return
        self.notify(f"{username} added to the group")

    @on(Button.Pressed, "#logout")
    def logout(self) -> None:
        self.do_logout()

    @work(exclusive=True, group="logout")
    async def do_logout(self) -> None:
        try:
            await self.app.api.logout()
        except ApiError as exc:
            self._handle_error(exc)
            return
        self.app.switch_screen(LoginScreen())

    # --- errors ---

    def _handle_error(self, exc: ApiError) -> None:
        if exc.status == 401:
            self.app.api.token = None
            self.notify("session expired, please log in again",
                        severity="warning")
            self.app.switch_screen(LoginScreen())
        else:
            self.notify(str(exc), severity="error")


class ChatApp(App):
    CSS_PATH = "app.tcss"
    TITLE = "Kerberos Chat"

    def __init__(self, api: ChatAPI | None = None):
        super().__init__()
        self.api = api or ChatAPI()

    def on_mount(self) -> None:
        self.push_screen(LoginScreen())

    async def on_unmount(self) -> None:
        await self.api.close()


if __name__ == "__main__":
    ChatApp().run()
