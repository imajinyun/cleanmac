"""Centralized protection data for app, bundle, path, and uninstaller policies."""

from __future__ import annotations

from typing import Any

DEFAULT_PROTECTED_BUNDLE_IDS = (
    "com.apple.AddressBook",
    "com.apple.CalendarAgent",
    "com.apple.FaceTime",
    "com.apple.Home",
    "com.apple.Maps",
    "com.apple.MobileSMS",
    "com.apple.Notes",
    "com.apple.Passbook",
    "com.apple.Photos",
    "com.apple.Safari",
    "com.apple.Settings",
    "com.apple.SystemSettings",
    "com.apple.Spotlight",
    "com.apple.accountsd",
    "com.apple.akd",
    "com.apple.assistant",
    "com.apple.bird",
    "com.apple.bookmarks",
    "com.apple.calaccessd",
    "com.apple.cloudkit",
    "com.apple.contacts",
    "com.apple.findmy",
    "com.apple.iCal",
    "com.apple.iChat",
    "com.apple.iCloudDrive",
    "com.apple.iMessage",
    "com.apple.identityservicesd",
    "com.apple.imagent",
    "com.apple.mail",
    "com.apple.messages",
    "com.apple.notes",
    "com.apple.photoanalysisd",
    "com.apple.reminders",
    "com.apple.security",
    "com.apple.siri",
    "com.apple.soagent",
    "com.apple.suggestd",
    "com.apple.syncdefaultsd",
    "com.apple.telephonyutilities.callservicesd",
    "com.apple.tips",
    "com.apple.translationd",
    "com.apple.wallet",
    "com.apple.webapp",
    "com.apple.webkit",
    "com.apple.xpc.launchd",
    "com.apple.finder",
    "com.apple.dock",
    "com.apple.loginwindow",
    "com.apple.SystemUIServer",
    "com.apple.SecurityAgent",
    "com.apple.AppStore",
    "com.apple.Preview",
    "com.apple.TextEdit",
    "com.apple.KeychainAccess",
    "com.apple.systempreferences",
    "com.apple.systemsettings",
    "com.apple.controlcenter",
    "com.apple.notificationcenterui",
    "com.apple.backgroundtaskmanagementagent",
    "com.apple.sharedfilelist",
    "com.apple.Terminal",
    "com.apple.ActivityMonitor",
    "com.apple.Console",
    "com.apple.DiskUtility",
    "com.apple.keychainaccess",
    "com.google.Drive",
    "com.microsoft.OneDrive",
    "com.dropbox.DropboxMacUpdate",
    "com.getdropbox.dropbox",
    "com.backblaze.Backblaze",
    "com.1password.1password",
    "com.agilebits.onepassword7",
    "com.bitwarden.desktop",
    "com.dashlane.dashlanephonefinal",
    "com.lastpass.LastPass",
    "com.docker.docker",
    "com.orbstack.OrbStack",
    "com.tailscale.ipn.macos",
    "com.cloudflare.1dot1dot1dot1.macos",
    "org.pqrs.Karabiner-Elements",
    "im.rime.inputmethod.Squirrel",
    "com.anthropic.claudefordesktop",
    "com.openai.chat",
    "com.todesktop.230313mzl4w4u92",
    "com.cursor.Cursor",
    "com.ollama.ollama",
)


PROTECTED_BUNDLE_PREFIXES = ("com.apple.",)


APPLE_UNINSTALLABLE_BUNDLE_PATTERNS = (
    "com.apple.dt.*",
    "com.apple.FinalCut*",
    "com.apple.Motion",
    "com.apple.Compressor",
    "com.apple.logic*",
    "com.apple.garageband*",
    "com.apple.iMovie",
    "com.apple.iWork.*",
    "com.apple.MainStage*",
    "com.apple.server.*",
    "com.apple.Playgrounds",
)


SYSTEM_CRITICAL_BUNDLE_PATTERNS = (
    "com.apple.finder",
    "com.apple.dock",
    "com.apple.Safari",
    "com.apple.mail",
    "com.apple.systempreferences*",
    "com.apple.SystemSettings",
    "com.apple.Settings*",
    "com.apple.controlcenter*",
    "com.apple.Spotlight",
    "com.apple.notificationcenterui",
    "com.apple.loginwindow",
    "com.apple.Preview",
    "com.apple.TextEdit",
    "com.apple.Notes",
    "com.apple.reminders",
    "com.apple.iCal",
    "com.apple.AddressBook",
    "com.apple.Photos",
    "com.apple.AppStore",
    "com.apple.ActivityMonitor",
    "com.apple.Console",
    "com.apple.DiskUtility",
    "com.apple.KeychainAccess",
    "com.apple.Terminal",
    "com.apple.SecurityAgent",
    "com.apple.CoreServices*",
    "com.apple.SystemUIServer",
    "com.apple.backgroundtaskmanagement*",
    "com.apple.loginitems*",
    "com.apple.sharedfilelist*",
    "com.apple.sfl*",
    "com.apple.metadata*",
    "com.apple.MobileSoftwareUpdate*",
    "com.apple.SoftwareUpdate*",
    "com.apple.installer*",
    "com.apple.security*",
    "com.apple.keychain*",
    "com.apple.trustd*",
    "com.apple.securityd*",
    "com.apple.cloudd*",
    "com.apple.iCloud*",
    "com.apple.WiFi*",
    "com.apple.airport*",
    "com.apple.Bluetooth*",
    "com.apple.inputmethod.*",
    "com.apple.inputsource*",
    "com.apple.TextInput*",
    "com.apple.CharacterPicker*",
    "com.apple.PressAndHold*",
    "loginwindow",
    "dock",
    "systempreferences",
    "finder",
    "safari",
    "backgroundtaskmanagementagent",
    "keychain*",
    "security*",
    "bluetooth*",
    "wifi*",
    "network*",
    "tcc",
    "notification*",
    "accessibility*",
    "universalaccess*",
    "HIToolbox*",
    "textinput*",
    "TextInput*",
    "keyboard*",
    "Keyboard*",
    "inputsource*",
    "InputSource*",
    "keylayout*",
    "KeyLayout*",
    "GlobalPreferences",
    ".GlobalPreferences",
    "org.pqrs.Karabiner*",
)


DATA_PROTECTED_BUNDLE_PATTERNS = (
    "com.tencent.inputmethod.QQInput",
    "com.sogou.inputmethod.*",
    "com.baidu.inputmethod.*",
    "com.googlecode.rimeime.*",
    "im.rime.*",
    "*.inputmethod",
    "*.InputMethod",
    "*IME",
    "com.1password.*",
    "com.agilebits.*",
    "com.lastpass.*",
    "com.dashlane.*",
    "com.bitwarden.*",
    "com.keepassx.*",
    "org.keepassx.*",
    "org.keepassxc.*",
    "com.authy.*",
    "com.yubico.*",
    "com.jetbrains.*",
    "JetBrains*",
    "com.microsoft.VSCode",
    "com.visualstudio.code.*",
    "com.microsoft.VSCodeInsiders",
    "com.sublimetext.*",
    "com.sublimehq.*",
    "com.docker.*",
    "com.getpostman.*",
    "com.postmanlabs.mac",
    "com.insomnia.*",
    "com.konghq.insomnia",
    "com.todesktop.*",
    "Cursor",
    "com.cursor.*",
    "com.anthropic.claude*",
    "Claude",
    "com.openai.chat*",
    "ChatGPT",
    "com.openai.codex",
    "Codex",
    "codex-runtimes",
    "com.ollama.ollama",
    "Ollama",
    "com.lmstudio.lmstudio",
    "LM Studio",
    "co.supertool.chatbox",
    "page.jan.jan",
    "com.huggingface.huggingchat",
    "Gemini",
    "com.perplexity.Perplexity",
    "com.exafunction.windsurf",
    "com.quora.poe.electron",
    "com.nssurge.*",
    "com.v2ray.*",
    "com.clash.*",
    "com.clash.app",
    "ClashX*",
    "Surge*",
    "Shadowrocket*",
    "Quantumult*",
    "clash-*",
    "Clash-*",
    "*-clash",
    "*-Clash",
    "clash.*",
    "Clash.*",
    "clash_*",
    "*clash-verge*",
    "*Clash-Verge*",
    "clashverge*",
    "ClashVerge*",
    "com.tailscale.*",
    "io.tailscale.*",
    "com.cloudflare.*",
    "net.tunnelblick.*",
    "com.crowdstrike.*",
    "com.jamf.*",
    "com.jamfsoftware.*",
    "com.sentinelone.*",
    "com.sentinel-labs.*",
    "com.eset.*",
    "com.paloaltonetworks.*",
    "com.cisco.anyconnect*",
    "com.cisco.secureclient*",
)


CRITICAL_SYSTEM_PATHS_EXACT = (
    "/",
    "/bin",
    "/sbin",
    "/usr",
    "/usr/bin",
    "/usr/sbin",
    "/usr/lib",
    "/System",
    "/Library/Apple",
    "/Library",
    "/Library/Extensions",
    "/Library/Keychains",
    "/Applications",
    "/Applications/Finder.app",
    "/Applications/Safari.app",
    "/Users",
    "/Users/Shared",
    "/Users/Guest",
    "/private",
    "/etc",
    "/private/etc",
    "/var",
    "/var/db",
    "/var/audit",
    "/private/var",
    "/private/var/db",
    "/private/var/audit",
)


CRITICAL_SYSTEM_PATH_PREFIXES = (
    "/bin/",
    "/sbin/",
    "/usr/bin/",
    "/usr/sbin/",
    "/usr/lib/",
    "/System/",
    "/Library/Apple/",
    "/Library/Extensions/",
    "/Library/Keychains/",
    "/Applications/Finder.app/",
    "/Applications/Safari.app/",
    "/Users/Guest/",
    "/etc/",
    "/private/etc/",
    "/var/db/",
    "/var/audit/",
    "/private/var/db/",
    "/private/var/audit/",
)


SENSITIVE_USER_DATA_FRAGMENTS = (
    "/.ssh/",
    "/.gnupg/",
    "/library/keychains",
    "/library/mail/",
    "/library/messages/",
    "/library/application support/clouddocs",
    "/library/application support/com.apple.sharedfilelist",
    "/library/application support/com.apple.tcc",
    "/library/application support/*/credentials",
    "/library/application support/*/credential",
    "/library/application support/*/secrets",
    "/library/application support/*/tokens",
    "/library/application support/*/auth",
    "/library/application support/com.apple.controlcenter",
    "/library/application support/com.apple.systemsettings",
    "/library/application support/com.apple.systempreferences",
    "/library/tcc",
    "/library/preferences/.globalpreferences",
    "/library/preferences/globalpreferences",
    "/library/preferences/com.apple.dock.plist",
    "/library/preferences/com.apple.finder.plist",
    "/library/preferences/com.apple.security",
    "/library/preferences/com.apple.tcc",
    "/library/preferences/com.apple.networkextension",
    "/library/preferences/com.apple.vpn",
    "/library/preferences/com.apple.wifi",
    "/library/preferences/com.apple.bluetooth",
    "/library/preferences/com.apple.airport",
    "/library/preferences/com.apple.wireless",
    "/library/preferences/org.cups.printingprefs",
    "/library/preferences/org.pqrs.karabiner",
    "/library/preferences/systemconfiguration",
    "/library/preferences/byhost/com.apple.bluetooth",
    "/library/preferences/byhost/com.apple.wifi",
    "/library/group containers/group.com.apple.networkextension",
    "/library/application support/tunnelblick",
    "/library/application support/tailscale",
    "/library/application support/cloudflare",
    "/library/application support/clash",
    "/library/application support/clashx",
    "/library/application support/surge",
    "/library/application support/v2ray",
    "/library/application support/globalprotect",
    "/library/application support/cisco/anyconnect",
    "/library/application support/cisco/secure client",
    "/library/application support/crowdstrike",
    "/library/application support/jamf",
    "/library/application support/sentinelone",
    "/library/application support/sentinel labs",
    "/library/application support/eset",
    "/library/input methods",
    "/library/keyboard layouts",
    "/library/application support/rime",
    "/library/rime",
    "/.config/ibus/rime",
    "/library/application support/karabiner",
    "/library/application support/org.pqrs/karabiner",
    "/.config/karabiner",
    "/library/application support/1password",
    "/library/application support/bitwarden",
    "/library/application support/dashlane",
    "/library/application support/lastpass",
    "/library/application support/keepass",
    "/library/application support/keepassxc",
    "/library/application support/authy",
    "/library/application support/yubico",
    "/library/application support/dropbox",
    "/library/application support/google/drivefs",
    "/library/application support/jetbrains",
    "/library/preferences/jetbrains",
    "/library/application support/code/user/",
    "/.vscode/",
    "/.docker/",
    "/library/application support/postman",
    "/library/application support/insomnia",
    "/.claude/",
    "/.claude.json",
    "/.codex/",
    "/.cursor/",
    "/.ollama/",
    "/library/application support/claude",
    "/library/application support/cursor",
    "/library/application support/chatgpt",
    "/library/application support/com.openai.chat",
    "/library/application support/codex",
    "/library/application support/windsurf",
    "/library/application support/lm studio",
    "/library/application support/jan",
    "/library/application support/chatbox",
    "/library/application support/perplexity",
    "/library/application support/poe",
)

# Exact regenerable cache leaves inside otherwise blanket-protected AI CLI
# dotdirectories. Only these leaves (and their contents) escape the sensitive
# data guard; credentials, sessions, configuration, and history siblings stay
# protected. Match against the resolved, lowercased absolute path.
DOTDIR_REGENERABLE_CACHE_PATHS: tuple[str, ...] = (
    "/.codex/.tmp",
    "/.codex/cache",
    "/.claude/cache",
)

# Home-relative roots that hold multiple on-disk AI CLI versions. Only direct
# non-active version directories are reachable, and only via the
# aiToolOldVersions provider, which resolves each tool's active-version marker
# before listing anything; a missing or unreadable marker prunes nothing.
AI_TOOL_VERSION_ROOTS: tuple[str, ...] = (
    "/.codex/packages/standalone/releases/",
    "/.local/share/cursor-agent/versions/",
)


APPLE_CONTAINER_CACHE_EXCEPTIONS = (
    "/Data/Library/Caches/",
    "/Data/tmp/",
    "/Data/Library/Mail Downloads/",
)

# Curated Apple daemon sandboxed containers whose Data/Library/Caches or
# Data/tmp leaves hold only regenerable system caches and scratch files. These
# exact leaves are reachable only through the appleDaemonContainerCaches
# category/provider; they do NOT loosen the generic com.apple container
# protection applied to userAppCache. Documents, databases, preferences, and
# every other Data subtree stay protected. Mirrors Mole's explicit Apple
# container cache allowlist in clean_app_caches.
APPLE_DAEMON_CONTAINER_CACHE_LEAVES: dict[str, tuple[str, ...]] = {
    "com.apple.wallpaper.agent": ("Library/Caches",),
    "com.apple.mediaanalysisd": ("Library/Caches", "tmp"),
    "com.apple.AppStore": ("Library/Caches",),
    "com.apple.configurator.xpc.InternetService": ("tmp",),
    "com.apple.wallpaper.extension.aerials": ("tmp",),
    "com.apple.geod": ("tmp",),
    "com.apple.stocks": ("Library/Caches",),
    "com.apple.AvatarUI.AvatarPickerMemojiPicker": ("Library/Caches",),
    "com.apple.AMPArtworkAgent": ("Library/Caches",),
    "com.apple.CoreDevice.CoreDeviceService": ("Library/Caches",),
    "com.apple.NeptuneOneExtension": ("Library/Caches",),
    "com.apple.AppleMediaServicesUI.UtilityExtension": ("tmp",),
}

# Exact regenerable cache leaves inside ~/Library/Messages. Only preview and
# sticker caches may escape the blanket Messages guard; received attachments
# under ~/Library/Messages/Attachments stay protected and belong to imessage.
MESSAGES_REGENERABLE_CACHE_LEAVES: tuple[str, ...] = (
    "/library/messages/stickercache/",
    "/library/messages/caches/previews/attachments/",
    "/library/messages/caches/previews/stickercache/",
)

# Exact recent-items list files (LaunchServices shared file lists and the
# recent-items preferences plist). These are regenerable privacy lists; no
# other com.apple.sharedfilelist content may escape its protection guard.
RECENT_ITEMS_FILE_RELPATHS: tuple[str, ...] = (
    "/library/application support/com.apple.sharedfilelist/com.apple.lssharedfilelist.recentapplications.sfl2",
    "/library/application support/com.apple.sharedfilelist/com.apple.lssharedfilelist.recentdocuments.sfl2",
    "/library/application support/com.apple.sharedfilelist/com.apple.lssharedfilelist.recentservers.sfl2",
    "/library/application support/com.apple.sharedfilelist/com.apple.lssharedfilelist.recenthosts.sfl2",
    "/library/application support/com.apple.sharedfilelist/com.apple.lssharedfilelist.recentapplications.sfl",
    "/library/application support/com.apple.sharedfilelist/com.apple.lssharedfilelist.recentdocuments.sfl",
    "/library/application support/com.apple.sharedfilelist/com.apple.lssharedfilelist.recentservers.sfl",
    "/library/application support/com.apple.sharedfilelist/com.apple.lssharedfilelist.recenthosts.sfl",
    "/library/preferences/com.apple.recentitems.plist",
)

# Apple Configurator 2 keeps downloaded device firmware (*.ipsw) inside its
# group container (bare ``group.com.apple.configurator`` or a
# ``<TEAMID>.group.com.apple.configurator`` form). Only exact *.ipsw leaves may
# escape the group.com.apple blanket guard; every other container entry stays
# protected. Matched case-insensitively against path parts.
CONFIGURATOR_FIRMWARE_CONTAINER_MARKER = "group.com.apple.configurator"


# Executable names and app-bundle labels; these authorize protection, never deletion.
APP_PROCESS_ALIASES: dict[str, tuple[str, ...]] = {
    "Google Chrome": ("Google Chrome", "Chrome", "Google Chrome Helper"),
    "Microsoft Edge": ("Microsoft Edge", "Microsoft Edge Helper"),
    "Code": ("Code", "Visual Studio Code", "Code Helper"),
    "Feishu": ("Feishu", "LarkShell", "Lark", "Lark Helper"),
    "Lark": ("Lark", "LarkInternational", "Lark Helper"),
    "WeChat": ("WeChat", "WeChat Helper", "微信"),
    "cmux": ("cmux", "cmux Helper"),
    "Trae CN": ("Trae CN", "Trae", "TRAE", "Trae Helper"),
    "TRAE SOLO CN": ("TRAE SOLO CN", "TRAE SOLO", "Trae Solo", "TRAE SOLO CN Helper"),
    "mira": ("mira", "mira Helper"),
    "Codex": ("Codex", "Codex Helper", "codex"),
    "Claude": ("Claude", "Claude Helper", "claude"),
    "Cursor Agent": ("cursor-agent",),
    "ChatGPT": ("ChatGPT", "ChatGPT Helper"),
    "Doubao": ("Doubao", "Doubao Helper", "豆包"),
    "Qianwen": ("Qianwen", "Qianwen Helper", "千问"),
    "CorpLink": ("CorpLink", "CorpLink Helper"),
    "Puppeteer": ("chrome-headless-shell", "headless_shell", "Google Chrome for Testing", "Chromium", "chrome"),
    # Long-tail GUI application family aliases. Names cover localized
    # binaries, helpers, and versioned executables so a running app still
    # pauses its cache category when the marketing name differs from ps comm.
    "WeCom": ("WeCom", "WeCom Helper", "企业微信"),
    "Tencent Meeting": ("TencentMeeting", "腾讯会议", "VooVMeeting"),
    "Autodesk": (
        "Autodesk",
        "AcCoreConsole",
        "ADPClientService",
        "AdSSO",
        "AdskLicensingService",
        "Fusion360",
        "fusion360",
    ),
    "Premiere Pro": (
        "Adobe Premiere Pro 2024",
        "Adobe Premiere Pro 2025",
        "Adobe Premiere Pro 2026",
        "Adobe Premiere Pro",
    ),
    "Steam": ("steam", "steam_osx", "Steam Helper"),
    "EA app": ("EA app", "EADesktop", "EALauncher", "Origin"),
    "Riot Games": ("Riot Client", "RiotClientServices", "VALORANT", "League of Legends"),
    "RPCS3": ("RPCS3", "rpcs3"),
    "Downie": ("Downie 4", "Downie 3", "Downie"),
    "Sunlogin": ("SunloginClient", "SunloginClient_Desktop", "Sunlogin"),
    "TeamViewer": ("TeamViewer", "TeamViewer_Service", "TeamViewer Desktop"),
    "Yinxiang Note": ("印象笔记", "Yinxiang Note"),
    "Kuwo Music": ("kwmusic", "kuwo", "酷我音乐"),
    "Kugou Music": ("KugouMusic", "kugou", "酷狗音乐"),
    "NetEase Music": ("NeteaseMusic", "网易云音乐"),
    "QQ Music": ("QQMusic", "QQMusicMac"),
    "iQIYI": ("iQIYI", "iQiyiPlayer", "爱奇艺"),
    "Tencent Video": ("TencentVideo", "tenvideo", "腾讯视频"),
    "Bilibili": ("bilibili", "Bilibili", "哔哩哔哩"),
    "Douyu": ("douyu", "Douyu", "斗鱼"),
    "Huya": ("huya", "Huya", "虎牙直播"),
    "Youdao Dict": ("YoudaoDict", "有道词典"),
    "Eudic": ("Eudic", "eudic", "欧路词典"),
    "LM Studio": ("LM Studio", "lm-studio"),
    "Quark": ("Quark", "quark", "夸克"),
    "flomo": ("flomo", "Flomo"),
    "Any.do": ("Any.do", "Anydo"),
}

APP_CACHE_OWNER_PATHS: dict[str, tuple[str, ...]] = {
    "Codex": (
        "~/.codex/.tmp",
        "~/.codex/cache",
        "~/.codex/packages/standalone/releases",
    ),
    "Claude": (
        "~/.claude/cache",
        "~/.claude/Cache",
    ),
    "Cursor Agent": ("~/.local/share/cursor-agent/versions",),
    "ChatGPT": ("~/Library/Caches/com.openai.chat", "~/Library/Application Support/ChatGPT"),
    "Google Chrome": ("~/Library/Caches/Google/Chrome", "~/Library/Application Support/Google/Chrome"),
    "Microsoft Edge": ("~/Library/Caches/Microsoft Edge", "~/Library/Application Support/Microsoft Edge"),
    "Code": ("~/Library/Application Support/Code",),
    "Feishu": (
        "~/Library/Caches/LarkShell*",
        "~/Library/Application Support/LarkShell*",
        "~/Library/Caches/com.bytedance.feishu",
        "~/Library/Caches/com.bytedance.lark",
    ),
    "Lark": ("~/Library/Caches/LarkInternational", "~/Library/Application Support/LarkInternational"),
    "WeChat": ("~/Library/Containers/com.tencent.xinWeChat", "~/Library/Caches/com.tencent.xinWeChat"),
    "cmux": ("~/Library/Caches/com.cmuxterm.app",),
    "Puppeteer": ("~/.cache/puppeteer",),
}

APP_SUPPORT_CACHE_DIRECTORIES = (
    "Code Cache",
    "GPUCache",
    "DawnCache",
    "GrShaderCache",
    "ShaderCache",
    "GraphiteDawnCache",
    "DawnGraphiteCache",
    "DawnWebGPUCache",
    "Crashpad/completed",
    "component_crx_cache",
    "extensions_crx_cache",
    "Shared Dictionary/cache",
    "Service Worker/CacheStorage",
    # ScriptCache holds MV3 extension service-worker bytecode; removing it
    # breaks registered workers and triggers security warnings even while the
    # browser is closed (Mole #785, #964, #968). Never a generic cache target.
)
AMBIGUOUS_APP_CACHE_DIRECTORIES = ("Cache", "CachedData")
KNOWN_ELECTRON_CACHE_APPS = (
    "Code",
    "Trae CN",
    "TRAE SOLO CN",
    "mira",
    "Codex",
    "Claude",
    "Doubao",
    "Qianwen",
    "LarkShell",
    "LarkInternational",
    "CorpLink",
    "DBW",
    "Cursor",
    "Windsurf",
    "ChatGPT",
    "LM Studio",
    "Jan",
    "Chatbox",
    "Perplexity",
    "Poe",
)
# Service Worker CacheStorage origins that must survive a browser cache
# cleanup: offline web editors, Google Workspace offline mode, and PWA/code
# platforms. Chromium names origin directories with hashes, so this match is
# best effort like Mole's; it protects every origin whose on-disk name embeds
# the domain. Enumerated per origin by browserServiceWorkerCaches.
PROTECTED_SERVICE_WORKER_DOMAINS: tuple[str, ...] = (
    "capcut.com",
    "photopea.com",
    "pixlr.com",
    "docs.google.com",
    "sheets.google.com",
    "slides.google.com",
    "drive.google.com",
    "mail.google.com",
    "github.com",
    "gitlab.com",
    "codepen.io",
    "codesandbox.io",
    "replit.com",
    "stackblitz.com",
    "notion.so",
    "figma.com",
    "linear.app",
    "excalidraw.com",
)

# Profile-root globs (relative to home) whose Service Worker/CacheStorage
# stores are enumerated per origin by browserServiceWorkerCaches.
BROWSER_SERVICE_WORKER_ROOTS: tuple[str, ...] = (
    "Library/Application Support/Google/Chrome/*",
    "Library/Application Support/Microsoft Edge/*",
    "Library/Application Support/BraveSoftware/Brave-Browser/*",
    "Library/Application Support/Arc/*",
    "Library/Application Support/Arc/User Data/*",
    "Library/Application Support/Vivaldi/*",
    "Library/Application Support/Dia/User Data/*",
    "Library/Application Support/com.operasoftware.Opera",
)

APP_CACHE_PROTECTED_PATTERNS = (
    "Cookies*",
    "History*",
    "Bookmarks*",
    "Login Data*",
    "Preferences",
    "Local State",
    "*/Local Storage*",
    "*/IndexedDB*",
    "*/Session Storage*",
    "*/Sessions*",
    "*/credentials*",
    "*/secrets*",
    "*/tokens*",
    "*/auth.json",
    "*.key",
    "*.keychain*",
)


OFFICIAL_UNINSTALLER_RULES: tuple[dict[str, str | tuple[str, ...]], ...] = (
    {"vendor": "ESET", "bundle_prefixes": ("com.eset.",), "name_fragments": ("eset",)},
    {
        "vendor": "Jamf",
        "bundle_prefixes": ("com.jamfsoftware.", "com.jamf."),
        "name_fragments": ("jamf", "self service"),
    },
    {"vendor": "CrowdStrike", "bundle_prefixes": ("com.crowdstrike.",), "name_fragments": ("crowdstrike", "falcon")},
    {
        "vendor": "SentinelOne",
        "bundle_prefixes": ("com.sentinelone.", "com.sentinel-labs."),
        "name_fragments": ("sentinelone", "sentinel one", "sentinel agent"),
    },
    {
        "vendor": "GlobalProtect",
        "bundle_prefixes": ("com.paloaltonetworks.",),
        "name_fragments": ("globalprotect", "global protect", "globalprotect.app"),
    },
    {
        "vendor": "Cisco",
        "bundle_prefixes": ("com.cisco.anyconnect", "com.cisco.secureclient", "com.cisco."),
        "name_fragments": ("cisco secure client", "cisco anyconnect", "anyconnect", "secure client"),
    },
)


APP_CLEANUP_RULES: dict[str, dict[str, Any]] = {
    "androidStudio": {
        "title": "Android Studio caches",
        "paths": (
            "~/Library/Caches/Google/AndroidStudio*/",
            "~/Library/Logs/Google/AndroidStudio*/",
            "~/Library/Application Support/Google/AndroidStudio*/caches/",
        ),
        "protected_patterns": ("*.jks", "*.keystore", "*/Android/Sdk/*", "*/.android/avd/*"),
    },
    "jetbrains": {
        "title": "JetBrains IDE caches",
        "paths": ("~/Library/Caches/JetBrains/*/", "~/Library/Logs/JetBrains/*/"),
        "protected_patterns": ("*/options/*", "*/eval/*"),
    },
    "vscode": {
        "title": "VS Code caches",
        "paths": ("~/Library/Application Support/Code/Cache/", "~/Library/Application Support/Code/CachedData/"),
        "protected_patterns": ("*/User/*", "*/workspaceStorage/*"),
    },
    "zed": {
        "title": "Zed editor caches",
        "paths": (
            "~/Library/Application Support/Zed/node/cache/",
            "~/Library/Application Support/Zed/node/node-*/cache/",
        ),
        "protected_patterns": (
            "*/Zed/db/*",
            "*/Zed/extensions/*",
            "*/Zed/copilot/*",
            "*/Zed/languages/*",
            "*/Zed/threads/*",
            "*/Zed/settings.json",
            "*/Zed/node/node-*/bin/*",
            "*/Zed/node/node-*/lib/*",
        ),
    },
    "docker": {
        "title": "Docker desktop caches",
        "paths": ("~/Library/Caches/com.docker.docker/", "~/.docker/buildx/cache/"),
        "protected_patterns": ("~/.docker/config.json", "~/.docker/contexts/*", "~/.docker/daemon.json"),
    },
    "raycast": {"title": "Raycast caches", "paths": ("~/Library/Caches/com.raycast.macos/",)},
    "unity": {
        "title": "Unity caches",
        "paths": ("~/Library/Unity/cache/", "~/Library/Caches/com.unity3d.UnityEditor*/"),
    },
    "unreal": {
        "title": "Unreal Engine caches",
        "paths": ("~/Library/Application Support/Epic/UnrealEngine/Common/DerivedDataCache/",),
    },
    "godot": {"title": "Godot editor caches", "paths": ("~/Library/Application Support/Godot/cache/",)},
    "deveco": {
        "title": "DevEco Studio caches",
        "paths": ("~/Library/Caches/Huawei/DevEcoStudio*/", "~/Library/Logs/Huawei/DevEcoStudio*/"),
    },
    "maestro": {"title": "Maestro caches", "paths": ("~/.maestro/cache/", "~/Library/Caches/maestro/")},
    "chrome": {
        "title": "Chrome browser caches",
        "paths": (
            "~/Library/Caches/Google/Chrome/*/Cache/",
            "~/Library/Caches/Google/Chrome/*/Code Cache/",
            "~/Library/Caches/Google/Chrome/*/GPUCache/",
            "~/Library/Caches/Google/Chrome/*/Media Cache/",
            "~/Library/Application Support/Google/Chrome/*/Cache/",
            "~/Library/Application Support/Google/Chrome/*/Application Cache/",
            "~/Library/Application Support/Google/Chrome/*/Code Cache/",
            "~/Library/Application Support/Google/Chrome/*/GPUCache/",
            "~/Library/Application Support/Google/Chrome/*/Service Worker/CacheStorage/",
            "~/Library/Application Support/Google/Chrome/*/DawnCache/",
            "~/Library/Application Support/Google/Chrome/*/GrShaderCache/",
            "~/Library/Application Support/Google/Chrome/*/GraphiteDawnCache/",
            "~/Library/Application Support/Google/Chrome/ShaderCache/",
            "~/Library/Application Support/Google/Chrome/GrShaderCache/",
            "~/Library/Application Support/Google/Chrome/GraphiteDawnCache/",
            "~/Library/Application Support/Google/Chrome/component_crx_cache/",
            "~/Library/Application Support/Google/Chrome/extensions_crx_cache/",
            "~/Library/Application Support/Google/Chrome/Crashpad/completed/",
            # On-device AI/model stores managed by Chrome's component updater;
            # re-downloaded on demand and often multiple GB.
            "~/Library/Application Support/Google/Chrome/OptGuideOnDeviceModel/",
            "~/Library/Application Support/Google/Chrome/OptGuideOnDeviceClassifierModel/",
            "~/Library/Application Support/Google/Chrome/optimization_guide_model_store/",
            "~/Library/Application Support/Google/GoogleUpdater/crx_cache/",
            "~/Library/Application Support/Google/GoogleUpdater/*.old",
        ),
        # Service Worker CacheStorage stays visible but locked in the generic
        # browser category; per-origin cleanup is the advanced
        # browserServiceWorkerCaches provider. ScriptCache is never discovered.
        "protected_patterns": (
            "*/Bookmarks*",
            "*/Cookies*",
            "*/History*",
            "*/Login Data*",
            "*/Preferences",
            "*/Local State",
            "*/Extensions/*",
            "*/Service Worker/CacheStorage/*",
        ),
    },
    "edge": {
        "title": "Microsoft Edge browser caches",
        "paths": (
            "~/Library/Caches/Microsoft Edge/",
            "~/Library/Caches/com.microsoft.edgemac/",
            "~/Library/Application Support/Microsoft Edge/*/Cache/",
            "~/Library/Application Support/Microsoft Edge/*/Application Cache/",
            "~/Library/Application Support/Microsoft Edge/*/Code Cache/",
            "~/Library/Application Support/Microsoft Edge/*/GPUCache/",
            "~/Library/Application Support/Microsoft Edge/*/Service Worker/CacheStorage/",
            "~/Library/Application Support/Microsoft Edge/*/DawnCache/",
            "~/Library/Application Support/Microsoft Edge/*/GrShaderCache/",
            "~/Library/Application Support/Microsoft Edge/*/GraphiteDawnCache/",
            "~/Library/Application Support/Microsoft Edge/ShaderCache/",
            "~/Library/Application Support/Microsoft Edge/GrShaderCache/",
            "~/Library/Application Support/Microsoft Edge/GraphiteDawnCache/",
            "~/Library/Application Support/Microsoft Edge/component_crx_cache/",
            "~/Library/Application Support/Microsoft Edge/Crashpad/completed/",
            "~/Library/Application Support/Microsoft Edge/OptGuideOnDeviceModel/",
            "~/Library/Application Support/Microsoft Edge/OptGuideOnDeviceClassifierModel/",
            "~/Library/Application Support/Microsoft Edge/optimization_guide_model_store/",
        ),
        # Service Worker CacheStorage stays visible but locked in the generic
        # browser category; per-origin cleanup is the advanced
        # browserServiceWorkerCaches provider. ScriptCache is never discovered.
        "protected_patterns": (
            "*/Bookmarks*",
            "*/Cookies*",
            "*/History*",
            "*/Login Data*",
            "*/Preferences",
            "*/Local State",
            "*/Extensions/*",
            "*/Local Storage/*",
            "*/IndexedDB/*",
            "*/Service Worker/CacheStorage/*",
        ),
    },
    "brave": {
        "title": "Brave browser caches",
        "paths": (
            "~/Library/Caches/BraveSoftware/",
            "~/Library/Application Support/BraveSoftware/Brave-Browser/*/Cache/",
            "~/Library/Application Support/BraveSoftware/Brave-Browser/*/Application Cache/",
            "~/Library/Application Support/BraveSoftware/Brave-Browser/*/Code Cache/",
            "~/Library/Application Support/BraveSoftware/Brave-Browser/*/GPUCache/",
            "~/Library/Application Support/BraveSoftware/Brave-Browser/*/Service Worker/CacheStorage/",
            "~/Library/Application Support/BraveSoftware/Brave-Browser/*/DawnCache/",
            "~/Library/Application Support/BraveSoftware/Brave-Browser/*/GrShaderCache/",
            "~/Library/Application Support/BraveSoftware/Brave-Browser/*/GraphiteDawnCache/",
            "~/Library/Application Support/BraveSoftware/Brave-Browser/ShaderCache/",
            "~/Library/Application Support/BraveSoftware/Brave-Browser/GrShaderCache/",
            "~/Library/Application Support/BraveSoftware/Brave-Browser/GraphiteDawnCache/",
            "~/Library/Application Support/BraveSoftware/Brave-Browser/component_crx_cache/",
            "~/Library/Application Support/BraveSoftware/Brave-Browser/Crashpad/completed/",
        ),
        # Service Worker CacheStorage stays visible but locked in the generic
        # browser category; per-origin cleanup is the advanced
        # browserServiceWorkerCaches provider. ScriptCache is never discovered.
        "protected_patterns": (
            "*/Bookmarks*",
            "*/Cookies*",
            "*/History*",
            "*/Login Data*",
            "*/Preferences",
            "*/Local State",
            "*/Extensions/*",
            "*/Local Storage/*",
            "*/IndexedDB/*",
            "*/Service Worker/CacheStorage/*",
        ),
    },
    "arc": {
        "title": "Arc browser caches",
        "paths": (
            "~/Library/Caches/company.thebrowser.Browser/",
            "~/Library/Application Support/Arc/*/Cache/",
            "~/Library/Application Support/Arc/*/Code Cache/",
            "~/Library/Application Support/Arc/*/GPUCache/",
            "~/Library/Application Support/Arc/*/Service Worker/CacheStorage/",
            "~/Library/Application Support/Arc/*/DawnCache/",
            "~/Library/Application Support/Arc/*/GrShaderCache/",
            "~/Library/Application Support/Arc/*/GraphiteDawnCache/",
            "~/Library/Application Support/Arc/ShaderCache/",
            "~/Library/Application Support/Arc/GrShaderCache/",
            "~/Library/Application Support/Arc/GraphiteDawnCache/",
            "~/Library/Application Support/Arc/component_crx_cache/",
            "~/Library/Application Support/Arc/extensions_crx_cache/",
            "~/Library/Application Support/Arc/Crashpad/completed/",
            "~/Library/Application Support/Arc/User Data/*/Cache/",
            "~/Library/Application Support/Arc/User Data/*/Code Cache/",
            "~/Library/Application Support/Arc/User Data/*/GPUCache/",
            "~/Library/Application Support/Arc/User Data/*/Service Worker/CacheStorage/",
            "~/Library/Application Support/Arc/User Data/*/DawnCache/",
            "~/Library/Application Support/Arc/User Data/*/GrShaderCache/",
            "~/Library/Application Support/Arc/User Data/*/GraphiteDawnCache/",
            "~/Library/Application Support/Arc/User Data/ShaderCache/",
            "~/Library/Application Support/Arc/User Data/GrShaderCache/",
            "~/Library/Application Support/Arc/User Data/GraphiteDawnCache/",
            "~/Library/Application Support/Arc/User Data/component_crx_cache/",
            "~/Library/Application Support/Arc/User Data/extensions_crx_cache/",
            "~/Library/Application Support/Arc/User Data/Crashpad/completed/",
        ),
        # Service Worker CacheStorage (both Arc layouts) stays visible but
        # locked in the generic browser category; per-origin cleanup is the
        # advanced browserServiceWorkerCaches provider. ScriptCache is never
        # discovered.
        "protected_patterns": (
            "*/Bookmarks*",
            "*/Cookies*",
            "*/History*",
            "*/Login Data*",
            "*/Preferences",
            "*/Local State",
            "*/Extensions/*",
            "*/Local Storage/*",
            "*/IndexedDB/*",
            "*/Service Worker/CacheStorage/*",
        ),
    },
    "firefox": {
        "title": "Firefox browser caches",
        "paths": (
            "~/Library/Caches/Firefox/Profiles/*/cache2/entries/",
            "~/Library/Caches/Firefox/Profiles/*/shader-cache/",
            "~/Library/Caches/Firefox/Profiles/*/startupCache/",
            "~/Library/Application Support/Firefox/Profiles/*/cache2/entries/",
            "~/Library/Application Support/Firefox/Profiles/*/shader-cache/",
            "~/Library/Application Support/Firefox/Profiles/*/startupCache/",
        ),
        "protected_patterns": (
            "*/places.sqlite",
            "*/cookies.sqlite",
            "*/logins.json",
            "*/key4.db",
            "*/cert9.db",
            "*/extensions/*",
            "*/prefs.js",
        ),
    },
    "discord": {
        "title": "Discord caches",
        "paths": (
            "~/Library/Application Support/discord/Cache/",
            "~/Library/Application Support/discord/Code Cache/",
            "~/Library/Application Support/discord/GPUCache/",
            "~/Library/Application Support/discord/Service Worker/CacheStorage/",
            "~/Library/Application Support/Discord/Cache/",
            "~/Library/Application Support/Discord/Code Cache/",
            "~/Library/Application Support/Discord/GPUCache/",
            "~/Library/Application Support/Discord/Service Worker/CacheStorage/",
            "~/Library/Caches/com.hnc.Discord/",
        ),
        "protected_patterns": (
            "*/Cookies*",
            "*/Local Storage/*",
            "*/IndexedDB/*",
            "*/storage/*",
            "*/Session Storage/*",
        ),
    },
    "notion": {
        "title": "Notion caches",
        "paths": (
            "~/Library/Application Support/Notion/Cache/",
            "~/Library/Application Support/Notion/Code Cache/",
            "~/Library/Application Support/Notion/GPUCache/",
            "~/Library/Application Support/Notion/Service Worker/CacheStorage/",
            "~/Library/Caches/notion.id/",
        ),
        "protected_patterns": (
            "*/Cookies*",
            "*/Local Storage/*",
            "*/IndexedDB/*",
            "*/databases/*",
            "*/storage/*",
        ),
    },
    "slack": {
        "title": "Slack caches",
        "paths": (
            "~/Library/Application Support/Slack/Cache/",
            "~/Library/Application Support/Slack/Code Cache/",
            "~/Library/Application Support/Slack/GPUCache/",
            "~/Library/Application Support/Slack/Service Worker/CacheStorage/",
            "~/Library/Caches/com.tinyspeck.slackmacgap/",
        ),
        "protected_patterns": ("*/Cookies*", "*/Local Storage/*", "*/IndexedDB/*", "*/storage/*"),
    },
    "zoom": {
        "title": "Zoom caches",
        "paths": ("~/Library/Application Support/zoom.us/data/Cache/", "~/Library/Caches/us.zoom.xos/"),
        "protected_patterns": ("*/Cookies*", "*/data/zoomus.enc.db", "*/data/zoomus.db"),
    },
    "teams": {
        "title": "Microsoft Teams caches",
        "paths": (
            "~/Library/Caches/com.microsoft.teams2/",
            "~/Library/Application Support/Microsoft/Teams/Cache/",
            "~/Library/Application Support/Microsoft/Teams/Code Cache/",
            "~/Library/Application Support/Microsoft/Teams/GPUCache/",
            "~/Library/Application Support/Microsoft/Teams/Service Worker/CacheStorage/",
            "~/Library/Application Support/Microsoft/Teams/Application Cache/",
            "~/Library/Application Support/Microsoft/Teams/logs/",
            "~/Library/Application Support/Microsoft/Teams/tmp/",
        ),
        "protected_patterns": ("*/Cookies*", "*/Local Storage/*", "*/IndexedDB/*", "*/storage/*"),
    },
    "nodePackageCaches": {
        "title": "Node package manager caches",
        "paths": (
            "~/.npm/_cacache/",
            "~/.npm/_npx/",
            "~/.npm/_prebuilds/",
            "~/.npm/_logs/",
            "~/Library/pnpm/store/",
            "~/Library/Caches/Yarn/",
        ),
        "protected_patterns": ("~/.npmrc", "~/.yarnrc", "~/.yarnrc.yml", "~/Library/pnpm/rc"),
    },
    "pythonPackageCaches": {
        "title": "Python package manager caches",
        "paths": (
            "~/Library/Caches/pip/",
            "~/Library/Caches/pypoetry/",
            "~/Library/Caches/pdm/",
            # uv defaults to the macOS cache location but honors XDG_CACHE_HOME.
            "~/Library/Caches/uv/",
            "~/.cache/uv/",
        ),
        "protected_patterns": ("~/.pypirc", "~/Library/Application Support/pypoetry/auth.toml"),
    },
    "goBuildCaches": {
        "title": "Go build and module download caches",
        "paths": ("~/Library/Caches/go-build/", "~/go/pkg/mod/cache/download/"),
        "protected_patterns": ("~/.netrc", "~/.gitconfig", "~/go/env"),
    },
    "homebrewCaches": {
        "title": "Homebrew download caches",
        "paths": ("~/Library/Caches/Homebrew/",),
        "protected_patterns": ("/opt/homebrew/*", "/usr/local/Homebrew/*"),
    },
    "gradleCaches": {
        "title": "Gradle caches",
        "paths": ("~/.gradle/caches/", "~/.gradle/wrapper/dists/"),
        "protected_patterns": ("~/.gradle/gradle.properties", "~/.gradle/init.gradle", "~/.gradle/init.d/*"),
    },
    "cargoCaches": {
        "title": "Cargo registry and git caches",
        "paths": (
            "~/.cargo/registry/cache/",
            "~/.cargo/registry/src/",
            "~/.cargo/git/checkouts/",
            "~/.cargo/git/db/",
        ),
        "protected_patterns": ("~/.cargo/credentials", "~/.cargo/config", "~/.cargo/config.toml"),
    },
    "cocoaPodsCaches": {
        "title": "CocoaPods caches",
        "paths": ("~/Library/Caches/CocoaPods/", "~/.cocoapods/repos/"),
        "protected_patterns": ("~/.netrc", "~/.gem/credentials", "~/.cocoapods/config.yaml"),
    },
    "bunCaches": {
        "title": "Bun package and installer caches",
        "paths": ("~/.bun/install/cache/",),
        "protected_patterns": ("~/.bunfig.toml",),
    },
    "corepackCaches": {
        "title": "Corepack package manager shim caches",
        "paths": ("~/.cache/node/corepack/",),
        "protected_patterns": ("~/.npmrc",),
    },
    "preCommitCaches": {
        "title": "pre-commit hook environment caches",
        "paths": ("~/.cache/pre-commit/",),
    },
    "bundlerCaches": {
        "title": "Ruby Bundler caches",
        "paths": ("~/.bundle/cache/",),
        "protected_patterns": ("~/.bundle/config", "~/.gem/credentials"),
    },
    "gitHubCliCaches": {
        "title": "GitHub CLI caches",
        "paths": ("~/.cache/gh/",),
        "protected_patterns": ("~/.config/gh/hosts.yml", "~/.config/gh/config.yml"),
    },
    "postman": {
        "title": "Postman caches",
        "paths": (
            "~/Library/Application Support/Postman/Cache/",
            "~/Library/Application Support/Postman/Code Cache/",
            "~/Library/Caches/Postman/",
        ),
        "protected_patterns": ("*/IndexedDB/*", "*/Local Storage/*", "*/Cookies*", "*/workspaceStorage/*"),
    },
    "insomnia": {
        "title": "Insomnia caches",
        "paths": (
            "~/Library/Application Support/Insomnia/Cache/",
            "~/Library/Application Support/Insomnia/Code Cache/",
            "~/Library/Caches/Insomnia/",
        ),
        "protected_patterns": ("*/insomnia.*.db", "*/Local Storage/*", "*/Cookies*"),
    },
    "aiToolCaches": {
        "title": "AI tool caches",
        "paths": (
            "~/.codex/.tmp/",
            "~/.codex/cache/",
            "~/.claude/cache/",
            "~/.claude/Cache/",
            "~/Library/Application Support/Claude/Cache/",
            "~/Library/Application Support/Claude/Code Cache/",
            "~/Library/Application Support/Cursor/Cache/",
            "~/Library/Application Support/Cursor/CachedData/",
            "~/Library/Application Support/Windsurf/Cache/",
            "~/Library/Application Support/Windsurf/CachedData/",
            "~/Library/Application Support/Windsurf/Code Cache/",
            "~/Library/Application Support/Windsurf/GPUCache/",
            "~/Library/Application Support/Windsurf/Service Worker/CacheStorage/",
            "~/Library/Application Support/ChatGPT/Cache/",
            "~/Library/Caches/com.openai.chat/",
            "~/.cache/opencode/",
            "~/.ollama/models/.cache/",
        ),
        "protected_patterns": (
            # Dotdirectories are blanket-protected as sensitive AI CLI state;
            # only the exact cache leaves in paths are reachable. List the state
            # siblings explicitly so wildcard patterns cannot cover cache leaves.
            "~/.codex/auth.json",
            "~/.codex/config.toml",
            "~/.codex/config.yaml",
            "~/.codex/sessions/*",
            "~/.codex/projects/*",
            "~/.codex/history.jsonl",
            "~/.codex/log/*",
            "~/.claude/.credentials*",
            "~/.claude/settings*.json",
            "~/.claude/projects/*",
            "~/.claude/sessions/*",
            "~/.claude/history*",
            "~/.cursor/*",
            "~/.ollama/id_*",
            "~/.ollama/config*",
            "*/Application Support/Claude/*/storage/*",
            "*/Application Support/Cursor/User/*",
            "*/Application Support/Windsurf/User/*",
            "*/Application Support/Windsurf/Local Storage*",
            "*/Application Support/Windsurf/IndexedDB/*",
            "*/Application Support/Windsurf/*/Local Storage*",
            "*/Application Support/Windsurf/*/IndexedDB/*",
            "*/Application Support/ChatGPT/Local Storage/*",
            "*/Application Support/ChatGPT/IndexedDB/*",
            # OpenCode keeps sessions/auth/storage under XDG dirs; only the
            # exact ~/.cache/opencode leaf is reachable.
            "~/.local/share/opencode/*",
            "~/.config/opencode/*",
        ),
    },
    "otherLanguageCaches": {
        # Mole clean_dev_other_langs / clean_dev_elixir / clean_dev_ocaml.
        "title": "Other language and build tool caches",
        "paths": (
            "~/.composer/cache/",
            "~/Library/Caches/composer/",
            "~/.cache/bazel/",
            "~/.cache/zig/",
            "~/.hex/cache/",
            "~/.opam/download-cache/",
        ),
        "protected_patterns": (
            # ~/.composer holds auth.json beside cache/; opam switches are
            # siblings of download-cache/ and stay outside the exact leaf.
            "~/.composer/auth.json",
            "~/.config/composer/auth.json",
            "~/.opam/config",
        ),
    },
    "ciCdCaches": {
        # Mole clean_dev_cicd, minus ~/.jenkins/workspace targets (active CI
        # checkouts are project-artifact data, not a redundant cache copy).
        "title": "CI/CD and DevOps tool caches",
        "paths": (
            "~/.cache/terraform/",
            "~/.grafana/cache/",
            "~/.cache/gitlab-runner/",
            "~/.github/cache/",
            "~/.circleci/cache/",
            "~/.sonar/cache/",
        ),
        "protected_patterns": (
            "~/.terraformrc",
            "~/.terraform.d/credentials.tfrc.json",
            "~/.circleci/cli.yml",
            "~/.grafana/grafana.ini",
        ),
    },
    "devUtilityCaches": {
        # Mole clean_dev_misc (Prisma/OpenCode leaves), clean_dev_shell, and
        # clean_dev_network. OpenCode lives with the other AI tool caches.
        "title": "Shell, network, and developer utility caches",
        "paths": (
            "~/.cache/prisma/",
            "~/.oh-my-zsh/cache/",
            "~/.cache/curl/",
            "~/.cache/wget/",
            "~/Library/Caches/curl/",
            "~/Library/Caches/wget/",
        ),
        "protected_patterns": ("~/.zshrc", "~/.zshenv"),
    },
    "windsurf": {
        "title": "Windsurf caches",
        "paths": (
            "~/Library/Application Support/Windsurf/Cache/",
            "~/Library/Application Support/Windsurf/CachedData/",
            "~/Library/Application Support/Windsurf/Code Cache/",
            "~/Library/Application Support/Windsurf/GPUCache/",
            "~/Library/Application Support/Windsurf/Service Worker/CacheStorage/",
        ),
        "protected_patterns": (
            "*/Application Support/Windsurf/User/*",
            "*/Application Support/Windsurf/Local Storage*",
            "*/Application Support/Windsurf/IndexedDB/*",
            "*/Application Support/Windsurf/*/Local Storage*",
            "*/Application Support/Windsurf/*/IndexedDB/*",
            "*/Cookies*",
            "*/storage/*",
        ),
    },
    "spotify": {
        "title": "Spotify caches",
        "paths": (
            "~/Library/Caches/com.spotify.client/",
            "~/Library/Application Support/Spotify/PersistentCache/",
            "~/Library/Application Support/Spotify/Storage/",
        ),
        "protected_patterns": (
            "*/Application Support/Spotify/prefs",
            "*/Application Support/Spotify/Users/*",
            "*/Application Support/Spotify/local-files.bnk",
            # Offline, encrypted track blobs: when present, Mole leaves the
            # whole Spotify cache tree untouched to protect downloads.
            "*/Application Support/Spotify/Storage/*.file",
            "*/Application Support/Spotify/PersistentCache/Storage/*.file",
            "*/Application Support/Spotify/PersistentCache/Storage/offline.bnk",
        ),
    },
    "telegram": {
        "title": "Telegram caches",
        "paths": (
            "~/Library/Caches/ru.keepcoder.Telegram/",
            "~/Library/Caches/org.telegram.desktop/",
            "~/Library/Application Support/Telegram Desktop/tdata/user_data/cache/",
        ),
        "protected_patterns": (
            "*/tdata/*",
            "*/user_data/*",
            "*/config/*",
        ),
    },
    "wechat": {
        "title": "WeChat caches",
        "paths": (
            "~/Library/Containers/com.tencent.xinWeChat/Data/Library/Caches/",
            "~/Library/Caches/com.tencent.xinWeChat/",
        ),
        "protected_patterns": (
            "*/WeChat Files/*/Msg/*",
            "*/WeChat Files/*/Contacts/*",
            "*/com.tencent.xinWeChat/Data/Documents/*",
        ),
    },
    "whatsapp": {
        "title": "WhatsApp caches",
        "paths": (
            "~/Library/Containers/net.whatsapp.WhatsApp/Data/Library/Caches/",
            "~/Library/Caches/net.whatsapp.WhatsApp/",
            "~/Library/Application Support/WhatsApp/Cache/",
        ),
        "protected_patterns": (
            "*/ChatStorage.sqlite",
            "*/Documents/*",
        ),
    },
    "signal": {
        "title": "Signal caches",
        "paths": (
            "~/Library/Application Support/Signal/Cache/",
            "~/Library/Application Support/Signal/Code Cache/",
            "~/Library/Application Support/Signal/GPUCache/",
            "~/Library/Caches/org.whispersystems.signal-desktop/",
        ),
        "protected_patterns": (
            "*/config.json",
            "*/sql/db.sqlite",
            "*/Local Storage/*",
            "*/IndexedDB/*",
            "*/Cookies*",
        ),
    },
    "figma": {
        "title": "Figma caches",
        "paths": (
            "~/Library/Application Support/Figma/Cache/",
            "~/Library/Application Support/Figma/Code Cache/",
            "~/Library/Application Support/Figma/GPUCache/",
            "~/Library/Application Support/Figma/Service Worker/CacheStorage/",
            "~/Library/Caches/com.figma.Desktop/",
        ),
        "protected_patterns": (
            "*/Local Storage/*",
            "*/IndexedDB/*",
            "*/Cookies*",
            "*/Preferences",
        ),
    },
    "microsoftOffice": {
        "title": "Microsoft Office caches",
        "paths": (
            "~/Library/Caches/com.microsoft.Word/",
            "~/Library/Caches/com.microsoft.Excel/",
            "~/Library/Caches/com.microsoft.Powerpoint/",
            "~/Library/Containers/com.microsoft.Word/Data/Library/Caches/",
            "~/Library/Containers/com.microsoft.Word/Data/tmp/",
            "~/Library/Containers/com.microsoft.Word/Data/Library/Logs/",
            "~/Library/Containers/com.microsoft.Excel/Data/Library/Caches/",
            "~/Library/Containers/com.microsoft.Excel/Data/tmp/",
            "~/Library/Containers/com.microsoft.Excel/Data/Library/Logs/",
            "~/Library/Containers/com.microsoft.Powerpoint/Data/Library/Caches/",
            "~/Library/Containers/com.microsoft.Outlook/Data/Library/Caches/",
            "~/Library/Caches/com.microsoft.office/",
            "~/Library/Caches/com.microsoft.Office/Microsoft Office Upload Center/",
        ),
        "protected_patterns": (
            "*/Data/Documents/*",
            "*/Data/Library/Preferences/*",
            "*/Group Containers/UBF8T346G9.Office/*",
        ),
    },
    "iwork": {
        "title": "Apple iWork caches",
        "paths": ("~/Library/Caches/com.apple.iWork.*/",),
        "protected_patterns": ("*/Containers/*/Data/Documents/*", "*/Group Containers/*iWork*"),
    },
    "wps": {
        "title": "WPS Office caches",
        "paths": ("~/Library/Caches/com.kingsoft.wpsoffice.mac/",),
        "protected_patterns": ("*/Application Support/Kingsoft/*",),
    },
    "thunderbird": {
        "title": "Mozilla Thunderbird caches",
        "paths": ("~/Library/Caches/org.mozilla.thunderbird/",),
        "protected_patterns": (
            "*/Thunderbird/Profiles/*",
            "*/key4.db",
            "*/logins.json",
            "*/Mail/*",
            "*/ImapMail/*",
        ),
    },
    "mailCache": {
        "title": "Apple Mail cache",
        "paths": ("~/Library/Caches/com.apple.mail/",),
        "protected_patterns": (
            "*/Containers/com.apple.mail/Data/Documents/*",
            "*/Library/Mail/*",
            "*/Mail Downloads/*",
        ),
    },
    "onenote": {
        "title": "Microsoft OneNote caches",
        "paths": (
            "~/Library/Containers/com.microsoft.onenote.mac/Data/Library/Caches/",
            "~/Library/Containers/com.microsoft.onenote.mac/Data/Library/Caches/Metadata/",
        ),
        "protected_patterns": (
            "*/Data/Documents/*",
            "*/Data/Library/Application Support/*",
        ),
    },
    "obsidian": {
        "title": "Obsidian caches",
        "paths": (
            "~/Library/Application Support/obsidian/Cache/",
            "~/Library/Application Support/obsidian/Code Cache/",
            "~/Library/Application Support/obsidian/GPUCache/",
            "~/Library/Application Support/obsidian/Service Worker/CacheStorage/",
            "~/Library/Caches/md.obsidian/",
        ),
        "protected_patterns": (
            "*/obsidian.json",
            "*/obsidian-vault.json",
            "*/Local Storage/*",
            "*/IndexedDB/*",
            "*/Cookies*",
            "*/Preferences",
        ),
    },
    "sublimeText": {
        "title": "Sublime Text caches",
        "paths": (
            "~/Library/Caches/com.sublimetext.4/",
            "~/Library/Caches/com.sublimetext.3/",
            "~/Library/Caches/com.sublimetext.2/",
            "~/Library/Application Support/Sublime Text/Cache/",
            "~/Library/Application Support/Sublime Text 3/Cache/",
            "~/Library/Application Support/Sublime Text 4/Cache/",
        ),
        "protected_patterns": (
            "*/Packages/User/*",
            "*/Local/License.sublime_license",
            "*/Local/Session.sublime_session",
            "*/Installed Packages/*",
        ),
    },
    "opera": {
        "title": "Opera browser caches",
        "paths": (
            "~/Library/Application Support/com.operasoftware.Opera/Cache/",
            "~/Library/Application Support/com.operasoftware.Opera/Code Cache/",
            "~/Library/Application Support/com.operasoftware.Opera/GPUCache/",
            "~/Library/Caches/com.operasoftware.Opera/",
        ),
        # Service Worker CacheStorage is enumerated per origin by the
        # browserServiceWorkerCaches provider; ScriptCache is never deleted.
        "protected_patterns": (
            "*/Bookmarks*",
            "*/Cookies*",
            "*/History*",
            "*/Login Data*",
            "*/Preferences",
            "*/Local State",
            "*/Extensions/*",
            "*/Local Storage/*",
            "*/IndexedDB/*",
        ),
    },
    "safari": {
        "title": "Safari browser caches",
        "paths": ("~/Library/Caches/com.apple.Safari/",),
        "protected_patterns": (
            "*/History*",
            "*/Cookies*",
            "*/Downloads*",
            "*/Databases/*",
            "*/LocalStorage/*",
        ),
    },
    "chromium": {
        "title": "Chromium browser caches",
        "paths": ("~/Library/Caches/Chromium/",),
        "protected_patterns": (
            "*/Bookmarks*",
            "*/Cookies*",
            "*/History*",
            "*/Login Data*",
        ),
    },
    "dia": {
        "title": "Dia browser caches",
        "paths": (
            "~/Library/Caches/company.thebrowser.dia/",
            "~/Library/Caches/Dia/User Data/*/Cache/",
            "~/Library/Caches/Dia/User Data/*/Code Cache/",
            "~/Library/Application Support/Dia/User Data/GraphiteDawnCache/",
            "~/Library/Application Support/Dia/User Data/GPUPersistentCache/",
            "~/Library/Application Support/Dia/User Data/component_crx_cache/",
            "~/Library/Application Support/Dia/User Data/extensions_crx_cache/",
            "~/Library/Application Support/Dia/User Data/*/DawnGraphiteCache/",
            "~/Library/Application Support/Dia/User Data/*/DawnWebGPUCache/",
            "~/Library/Application Support/Dia/User Data/*/GPUCache/",
        ),
        "protected_patterns": (
            "*/Bookmarks*",
            "*/Cookies*",
            "*/History*",
            "*/Login Data*",
            "*/Preferences",
            "*/Local State",
            "*/Extensions/*",
            "*/Local Storage/*",
            "*/IndexedDB/*",
        ),
    },
    "helium": {
        "title": "Helium browser caches",
        "paths": (
            "~/Library/Caches/net.imput.helium/",
            "~/Library/Application Support/net.imput.helium/*/GPUCache/",
            "~/Library/Application Support/net.imput.helium/*/Application Cache/",
            "~/Library/Application Support/net.imput.helium/component_crx_cache/",
            "~/Library/Application Support/net.imput.helium/extensions_crx_cache/",
            "~/Library/Application Support/net.imput.helium/GrShaderCache/",
            "~/Library/Application Support/net.imput.helium/GraphiteDawnCache/",
            "~/Library/Application Support/net.imput.helium/ShaderCache/",
        ),
        "protected_patterns": (
            "*/Bookmarks*",
            "*/Cookies*",
            "*/History*",
            "*/Login Data*",
            "*/Preferences",
            "*/Local State",
            "*/Extensions/*",
            "*/Local Storage/*",
            "*/IndexedDB/*",
        ),
    },
    "yandex": {
        "title": "Yandex browser caches",
        "paths": (
            "~/Library/Caches/Yandex/YandexBrowser/",
            "~/Library/Application Support/Yandex/YandexBrowser/ShaderCache/",
            "~/Library/Application Support/Yandex/YandexBrowser/GrShaderCache/",
            "~/Library/Application Support/Yandex/YandexBrowser/GraphiteDawnCache/",
            "~/Library/Application Support/Yandex/YandexBrowser/*/GPUCache/",
        ),
        "protected_patterns": (
            "*/Bookmarks*",
            "*/Cookies*",
            "*/History*",
            "*/Login Data*",
            "*/Preferences",
            "*/Local State",
            "*/Extensions/*",
            "*/Local Storage/*",
            "*/IndexedDB/*",
        ),
    },
    "vivaldi": {
        "title": "Vivaldi browser caches",
        "paths": (
            "~/Library/Caches/com.vivaldi.Vivaldi/",
            "~/Library/Application Support/Vivaldi/*/Code Cache/",
            "~/Library/Application Support/Vivaldi/*/GPUCache/",
            "~/Library/Application Support/Vivaldi/*/DawnCache/",
            "~/Library/Application Support/Vivaldi/*/GrShaderCache/",
            "~/Library/Application Support/Vivaldi/*/GraphiteDawnCache/",
            "~/Library/Application Support/Vivaldi/ShaderCache/",
            "~/Library/Application Support/Vivaldi/GrShaderCache/",
            "~/Library/Application Support/Vivaldi/GraphiteDawnCache/",
            "~/Library/Application Support/Vivaldi/Crashpad/completed/",
        ),
        "protected_patterns": (
            "*/Bookmarks*",
            "*/Cookies*",
            "*/History*",
            "*/Login Data*",
            "*/Preferences",
            "*/Local State",
            "*/Extensions/*",
            "*/Local Storage/*",
            "*/IndexedDB/*",
        ),
    },
    "comet": {
        "title": "Comet browser caches",
        "paths": ("~/Library/Caches/Comet/",),
        "protected_patterns": (
            "*/Bookmarks*",
            "*/Cookies*",
            "*/History*",
            "*/Login Data*",
        ),
    },
    "orion": {
        "title": "Orion browser caches",
        "paths": ("~/Library/Caches/com.kagi.kagimacOS/",),
        "protected_patterns": (
            "*/Bookmarks*",
            "*/Cookies*",
            "*/History*",
            "*/Login Data*",
        ),
    },
    "zen": {
        "title": "Zen browser caches",
        "paths": ("~/Library/Caches/zen/",),
        "protected_patterns": (
            "*/Bookmarks*",
            "*/Cookies*",
            "*/History*",
            "*/Login Data*",
            "*/places.sqlite",
        ),
    },
    "qqBrowser3": {
        "title": "QQ Browser caches",
        "paths": (
            "~/Library/Caches/com.tencent.QQBrowser3/",
            "~/Library/Application Support/QQBrowser3/*/Code Cache/",
            "~/Library/Application Support/QQBrowser3/*/GPUCache/",
            "~/Library/Application Support/QQBrowser3/ShaderCache/",
            "~/Library/Application Support/QQBrowser3/GrShaderCache/",
            "~/Library/Application Support/QQBrowser3/GraphiteDawnCache/",
            "~/Library/Application Support/QQBrowser3/component_crx_cache/",
            "~/Library/Application Support/QQBrowser3/Crashpad/completed/",
        ),
        "protected_patterns": (
            "*/Bookmarks*",
            "*/Cookies*",
            "*/History*",
            "*/Login Data*",
            "*/Preferences",
            "*/Local State",
            "*/Extensions/*",
            "*/Local Storage/*",
            "*/IndexedDB/*",
        ),
    },
    "dropbox": {
        "title": "Dropbox caches",
        "paths": (
            "~/Library/Caches/com.getdropbox.dropbox/",
            "~/Library/Caches/com.dropbox.*/",
            "~/Library/Application Support/Dropbox/Cache/",
        ),
        "protected_patterns": (
            "~/Dropbox/*",
            "*/.dropbox/*",
            "*/Application Support/Dropbox/info.json",
            "*/Application Support/Dropbox/config.dbx",
        ),
    },
    "linear": {
        "title": "Linear caches",
        "paths": (
            "~/Library/Application Support/Linear/Cache/",
            "~/Library/Application Support/Linear/Code Cache/",
            "~/Library/Application Support/Linear/GPUCache/",
            "~/Library/Application Support/Linear/Service Worker/CacheStorage/",
            "~/Library/Caches/com.linear.macOS/",
        ),
        "protected_patterns": (
            "*/Cookies*",
            "*/Local Storage/*",
            "*/IndexedDB/*",
            "*/Preferences",
        ),
    },
    "sketch": {
        "title": "Sketch caches",
        "paths": (
            "~/Library/Caches/com.bohemiancoding.sketch3/",
            "~/Library/Application Support/com.bohemiancoding.sketch3/",
        ),
        "protected_patterns": (
            "*/Application Support/com.bohemiancoding.sketch3/Plugins/*",
            "*/Application Support/com.bohemiancoding.sketch3/Libraries/*",
            "*/Application Support/com.bohemiancoding.sketch3/*.license",
        ),
    },
    "zeplin": {
        "title": "Zeplin caches",
        "paths": (
            "~/Library/Application Support/Zeplin/Cache/",
            "~/Library/Application Support/Zeplin/Code Cache/",
            "~/Library/Application Support/Zeplin/GPUCache/",
            "~/Library/Caches/io.zeplin.osx/",
        ),
        "protected_patterns": (
            "*/Cookies*",
            "*/Local Storage/*",
            "*/IndexedDB/*",
            "*/Preferences",
        ),
    },
    "vlc": {
        "title": "VLC media player caches",
        "paths": (
            "~/Library/Caches/org.videolan.vlc/",
            "~/Library/Application Support/org.videolan.vlc/",
        ),
        "protected_patterns": (
            "*/Application Support/org.videolan.vlc/vlcrc",
            "*/Application Support/org.videolan.vlc/bookmarks.*",
            "*/Application Support/org.videolan.vlc/playlists/*",
        ),
    },
    "handbrake": {
        "title": "HandBrake caches",
        "paths": (
            "~/Library/Caches/fr.handbrake.HandBrake/",
            "~/Library/Application Support/HandBrake/",
        ),
        "protected_patterns": (
            "*/Application Support/HandBrake/UserPresets.plist",
            "*/Application Support/HandBrake/Queue.plist",
            "*/Application Support/HandBrake/*.plist",
        ),
    },
    "appleMusic": {
        "title": "Apple Music caches",
        "paths": (
            "~/Library/Caches/com.apple.Music/",
            "~/Library/Application Support/Music/",
        ),
        "protected_patterns": (
            "~/Music/Music Library.musiclibrary/*",
            "~/Music/Music/*",
            "*/Application Support/Music/*.itl",
            "*/Application Support/Music/Media/*",
        ),
    },
    "podcasts": {
        "title": "Podcasts app caches",
        "paths": (
            "~/Library/Caches/com.apple.podcasts/",
            "~/Library/Containers/com.apple.podcasts/Data/Library/Caches/",
            "~/Library/Containers/com.apple.podcasts/Data/tmp/StreamedMedia/",
            "~/Library/Containers/com.apple.podcasts/Data/tmp/*.heic",
            "~/Library/Containers/com.apple.podcasts/Data/tmp/*.img",
            "~/Library/Containers/com.apple.podcasts/Data/tmp/*CFNetworkDownload*.tmp",
        ),
        "protected_patterns": (
            "*/Containers/com.apple.podcasts/Data/Documents/*",
            "*/Containers/com.apple.podcasts/Data/Library/Preferences/*",
        ),
    },
    "reddit": {
        "title": "Reddit caches",
        "paths": (
            "~/Library/Application Support/Reddit/Cache/",
            "~/Library/Application Support/Reddit/Code Cache/",
            "~/Library/Application Support/Reddit/GPUCache/",
            "~/Library/Caches/com.reddit.Reddit/",
        ),
        "protected_patterns": (
            "*/Cookies*",
            "*/Local Storage/*",
            "*/IndexedDB/*",
            "*/Preferences",
        ),
    },
    "googleDrive": {
        "title": "Google Drive caches",
        "paths": (
            "~/Library/Caches/com.google.GoogleDrive/",
            "~/Library/Application Support/Google/DriveFS/",
        ),
        "protected_patterns": (
            "~/Google Drive/*",
            "~/Library/CloudStorage/GoogleDrive*/*",
            "*/Application Support/Google/DriveFS/*.db",
            "*/Application Support/Google/DriveFS/settings*",
        ),
    },
    "baiduNetdisk": {
        "title": "Baidu Netdisk caches",
        "paths": ("~/Library/Caches/com.baidu.netdisk/",),
        "protected_patterns": ("*/Application Support/*/config*",),
    },
    "teambitionDisk": {
        "title": "Teambition Cloud Drive caches",
        "paths": ("~/Library/Caches/com.alibaba.teambitiondisk/",),
        "protected_patterns": ("*/Application Support/teambitiondisk/*",),
    },
    "box": {
        "title": "Box Drive caches",
        "paths": ("~/Library/Caches/com.box.desktop/",),
        "protected_patterns": ("~/Box/*", "*/Application Support/Box/*"),
    },
    "onedrive": {
        "title": "OneDrive caches",
        "paths": (
            "~/Library/Caches/com.microsoft.OneDrive/",
            "~/Library/Containers/com.microsoft.OneDrive-mac/Data/Library/Caches/",
        ),
        "protected_patterns": (
            "~/OneDrive - *",
            "~/OneDrive/*",
            "*/Containers/com.microsoft.OneDrive-mac/Data/Library/Preferences/*",
        ),
    },
    "todoist": {
        "title": "Todoist caches",
        "paths": (
            "~/Library/Application Support/Todoist/Cache/",
            "~/Library/Application Support/Todoist/Code Cache/",
            "~/Library/Application Support/Todoist/GPUCache/",
            "~/Library/Caches/com.todoist.mac.Todoist/",
        ),
        "protected_patterns": (
            "*/Cookies*",
            "*/Local Storage/*",
            "*/IndexedDB/*",
            "*/Preferences",
        ),
    },
    "things": {
        "title": "Things 3 caches",
        "paths": (
            "~/Library/Containers/com.culturedcode.ThingsMac/Data/Library/Caches/",
            "~/Library/Caches/com.culturedcode.ThingsMac/",
        ),
        "protected_patterns": (
            "*/Containers/com.culturedcode.ThingsMac/Data/Documents/*",
            "*/Containers/com.culturedcode.ThingsMac/Data/Library/Application Support/*",
            "*/Containers/com.culturedcode.ThingsMac/Data/Library/Preferences/*",
        ),
    },
    "iterm2": {
        "title": "iTerm2 caches",
        "paths": (
            "~/Library/Caches/com.googlecode.iterm2/",
            "~/Library/Application Support/iTerm2/",
        ),
        "protected_patterns": (
            "*/Application Support/iTerm2/com.googlecode.iterm2.plist",
            "*/Application Support/iTerm2/DynamicProfiles/*",
            "*/Application Support/iTerm2/Scripts/*",
            "*/Application Support/iTerm2/Sources/*",
        ),
    },
    "qq": {
        "title": "QQ caches",
        "paths": (
            "~/Library/Containers/com.tencent.qq/Data/Library/Caches/",
            "~/Library/Caches/com.tencent.qq/",
            "~/Library/Application Support/QQ/caches/",
        ),
        "protected_patterns": (
            "*/Containers/com.tencent.qq/Data/Documents/*",
            "*/Containers/com.tencent.qq/Data/Library/Preferences/*",
            "*/Application Support/QQ/Users/*/Msg/*",
        ),
    },
    "dingTalk": {
        "title": "DingTalk caches",
        "paths": (
            "~/Library/Caches/com.alibaba.DingTalkMac/",
            "~/Library/Caches/dd.work.exclusive4aliding/",
            "~/Library/Caches/com.alibaba.AliLang.osx/",
            "~/Library/Application Support/DingTalk/cache/",
            "~/Library/Application Support/iDingTalk/log/",
            "~/Library/Application Support/iDingTalk/holmeslogs/",
            "~/Library/Containers/com.alibaba.DingTalkMac/Data/Library/Caches/",
        ),
        "protected_patterns": (
            "*/Application Support/DingTalk/users/*",
            "*/Containers/com.alibaba.DingTalkMac/Data/Documents/*",
            "*/Containers/com.alibaba.DingTalkMac/Data/Library/Preferences/*",
        ),
    },
    "feishu": {
        "title": "Feishu caches",
        "paths": (
            "~/Library/Caches/com.bytedance.lark/",
            "~/Library/Caches/com.bytedance.feishu/",
            "~/Library/Caches/com.feishu.*/",
            "~/Library/Application Support/Lark/Cache/",
            "~/Library/Application Support/Lark/Code Cache/",
            "~/Library/Application Support/Lark/GPUCache/",
        ),
        "protected_patterns": (
            "*/Application Support/Lark/Local Storage/*",
            "*/Application Support/Lark/IndexedDB/*",
            "*/Application Support/Lark/Cookies*",
            "*/Application Support/Lark/Preferences",
            "*/Application Support/Lark/user_data/*",
        ),
    },
    "evernote": {
        "title": "Evernote caches",
        "paths": (
            "~/Library/Caches/com.evernote.Evernote/",
            "~/Library/Caches/com.evernote.*/",
            "~/Library/Containers/com.evernote.Evernote/Data/Library/Caches/",
            "~/Library/Application Support/Evernote/Cache/",
        ),
        "protected_patterns": (
            "*/Containers/com.evernote.Evernote/Data/Library/Application Support/*",
            "*/Containers/com.evernote.Evernote/Data/Documents/*",
            "*/Application Support/Evernote/Accounts/*",
        ),
    },
    "youdaoNote": {
        "title": "Youdao Note caches",
        "paths": (
            "~/Library/Caches/com.youdao.YoudaoNote/",
            "~/Library/Containers/com.youdao.YoudaoNote/Data/Library/Caches/",
        ),
        "protected_patterns": (
            "*/Containers/com.youdao.YoudaoNote/Data/Documents/*",
            "*/Containers/com.youdao.YoudaoNote/Data/Library/Application Support/*",
            "*/Containers/com.youdao.YoudaoNote/Data/Library/Preferences/*",
        ),
    },
    "warp": {
        "title": "Warp caches",
        "paths": (
            "~/Library/Caches/dev.warp.Warp-Stable/",
            "~/Library/Caches/SentryCrash/Warp/",
            "~/Library/Logs/warp.log",
            "~/Library/Application Support/dev.warp.Warp-Stable/Cache/",
            "~/Library/Application Support/dev.warp.Warp-Stable/Code Cache/",
            "~/Library/Application Support/dev.warp.Warp-Stable/GPUCache/",
        ),
        "protected_patterns": (
            "*/Application Support/dev.warp.Warp-Stable/settings.json",
            "*/Application Support/dev.warp.Warp-Stable/Preferences",
            "*/Application Support/dev.warp.Warp-Stable/Local Storage/*",
            "*/Application Support/dev.warp.Warp-Stable/IndexedDB/*",
            "*/.warp/*",
        ),
    },
    "tablePlus": {
        "title": "TablePlus caches",
        "paths": (
            "~/Library/Caches/com.tinyapp.TablePlus/",
            "~/Library/Application Support/com.tinyapp.TablePlus/Cache/",
        ),
        "protected_patterns": (
            "*/Application Support/com.tinyapp.TablePlus/Connections/*",
            "*/Application Support/com.tinyapp.TablePlus/*.plist",
            "*/Application Support/com.tinyapp.TablePlus/License",
        ),
    },
    "torBrowser": {
        "title": "Tor Browser caches",
        "paths": (
            "~/Library/Application Support/TorBrowser-Data/Browser/Caches/",
            "~/Library/Caches/org.mozilla.torproject.torbrowser/",
        ),
        "protected_patterns": (
            "*/TorBrowser-Data/Browser/profile.default/bookmarks.*",
            "*/TorBrowser-Data/Browser/profile.default/logins.json",
            "*/TorBrowser-Data/Browser/profile.default/prefs.js",
            "*/TorBrowser-Data/Browser/profile.default/extensions/*",
        ),
    },
    "mega": {
        "title": "MEGA caches",
        "paths": (
            "~/Library/Caches/mega.mac/",
            "~/Library/Application Support/MEGA/Cache/",
        ),
        "protected_patterns": (
            "~/MEGA/*",
            "*/Application Support/MEGA/mega.cfg",
            "*/Application Support/MEGA/mega_encrypted_cfg.bin",
        ),
    },
    "sync": {
        "title": "Sync.com caches",
        "paths": (
            "~/Library/Caches/com.sync.desktop/",
            "~/Library/Application Support/Sync/Cache/",
        ),
        "protected_patterns": (
            "~/Sync/*",
            "*/Application Support/Sync/Sync Preferences",
            "*/Application Support/Sync/config*",
        ),
    },
    "webex": {
        "title": "Webex caches",
        "paths": (
            "~/Library/Caches/com.cisco.webex.meetings/",
            "~/Library/Application Support/Cisco/Webex/Cache/",
            "~/Library/Application Support/WebEx Folder/",
        ),
        "protected_patterns": (
            "*/Application Support/Cisco/Webex/Preferences",
            "*/Application Support/WebEx Folder/Recording/*",
            "*/Application Support/WebEx Folder/Meeting Data/*",
        ),
    },
    "blender": {
        "title": "Blender caches",
        "paths": (
            "~/Library/Caches/blenderfoundation/blender/",
            "~/Library/Caches/org.blenderfoundation.blender/",
            "~/Library/Application Support/Blender/",
        ),
        "protected_patterns": (
            "*/Application Support/Blender/*/config/*",
            "*/Application Support/Blender/*/scripts/*",
            "*/Application Support/Blender/*/datafiles/*",
            "*.blend",
        ),
    },
    "affinity": {
        "title": "Affinity caches",
        "paths": (
            "~/Library/Caches/com.seriflabs.affinityphoto/",
            "~/Library/Caches/com.seriflabs.affinitydesigner/",
            "~/Library/Caches/com.seriflabs.affinitypublisher/",
        ),
        "protected_patterns": (
            "~/Library/Application Support/Affinity Photo/*",
            "~/Library/Application Support/Affinity Designer/*",
            "~/Library/Application Support/Affinity Publisher/*",
            "*.afphoto",
            "*.afdesign",
            "*.afpub",
        ),
    },
    "alfred": {
        "title": "Alfred caches",
        "paths": (
            "~/Library/Caches/com.runningwithcrayons.Alfred/",
            "~/Library/Caches/com.runningwithcrayons.Alfred-Preferences/",
        ),
        "protected_patterns": (
            "~/Library/Application Support/Alfred/*",
            "*/Application Support/Alfred/Alfred.alfredpreferences/*",
            "*/Application Support/Alfred/settings.json",
            "*/Application Support/Alfred/workflows/*",
        ),
    },
    "notionCalendar": {
        "title": "Notion Calendar caches",
        "paths": (
            "~/Library/Caches/notion-calendar/",
            "~/Library/Application Support/Notion Calendar/Cache/",
            "~/Library/Application Support/Notion Calendar/Code Cache/",
            "~/Library/Application Support/Notion Calendar/GPUCache/",
        ),
        "protected_patterns": (
            "*/Application Support/Notion Calendar/Local Storage/*",
            "*/Application Support/Notion Calendar/IndexedDB/*",
            "*/Application Support/Notion Calendar/Cookies*",
            "*/Application Support/Notion Calendar/Preferences",
        ),
    },
    "hopper": {
        "title": "Hopper Disassembler caches",
        "paths": (
            "~/Library/Caches/com.cryptic-apps.hopper-web-4/",
            "~/Library/Application Support/Hopper/",
        ),
        "protected_patterns": (
            "*/Application Support/Hopper/Licenses/*",
            "*/Application Support/Hopper/*.license",
            "*.hopper",
        ),
    },
    "charles": {
        "title": "Charles Proxy caches",
        "paths": (
            "~/Library/Caches/com.xk72.charles/",
            "~/Library/Application Support/Charles/cache/",
        ),
        "protected_patterns": (
            "*/Application Support/Charles/charles.config",
            "*/Application Support/Charles/ca.crt",
            "*/Application Support/Charles/ca.key",
            "*/Application Support/Charles/Licenses/*",
        ),
    },
    "proxyman": {
        "title": "Proxyman caches",
        "paths": (
            "~/Library/Caches/com.namndev.proxyman.mac/",
            "~/Library/Containers/com.namndev.proxyman.mac/Data/Library/Caches/",
        ),
        "protected_patterns": (
            "*/Containers/com.namndev.proxyman.mac/Data/Documents/*",
            "*/Containers/com.namndev.proxyman.mac/Data/Library/Preferences/*",
            "*/Application Support/Proxyman/Licenses/*",
            "*.proxyman",
        ),
    },
    "parallels": {
        "title": "Parallels Desktop caches",
        "paths": (
            "~/Library/Caches/com.parallels.desktop.console/",
            "~/Library/Application Support/Parallels/Cache/",
            "/Library/Caches/Parallels/",
        ),
        "protected_patterns": (
            "*.pvm",
            "*.hdd",
            "*/Parallels/*.pvm",
            "~/Parallels/*",
            "*/Application Support/Parallels/licenses.*",
            "*/Application Support/Parallels/settings/*",
        ),
    },
    "vmwareFusion": {
        "title": "VMware Fusion caches",
        "paths": (
            "~/Library/Caches/com.vmware.fusion/",
            "~/Library/Application Support/VMware Fusion/",
        ),
        "protected_patterns": (
            "*.vmwarevm",
            "*.vmdk",
            "~/Virtual Machines.localized/*",
            "*/Application Support/VMware Fusion/License*",
            "*/Application Support/VMware Fusion/preferences",
        ),
    },
    "utm": {
        "title": "UTM virtual machine caches",
        # Mole parity (clean_utm_caches): app cache, sandboxed container cache,
        # and container tmp. VM bundles (*.utm, disk images) never live in scope.
        "paths": (
            "~/Library/Caches/com.utmapp.UTM/",
            "~/Library/Containers/com.utmapp.UTM/Data/Library/Caches/",
            "~/Library/Containers/com.utmapp.UTM/Data/tmp/",
        ),
        "protected_patterns": (
            "*.utm",
            "*.qcow2",
            "*.img",
            "*.iso",
            "*.ipsw",
            "*/Containers/com.utmapp.UTM/Data/Documents/*",
        ),
    },
    "virtualbox": {
        "title": "VirtualBox cache",
        # Mole parity: only the hidden .cache leaf beside the VM folder.
        "paths": ("~/VirtualBox VMs/.cache/",),
        "protected_patterns": (
            "*.vdi",
            "*.vmdk",
            "*.vhd",
            "*.vbox",
            "*.vbox-prev",
            "*.ova",
            "*.ovf",
            "*.iso",
        ),
    },
    "lima": {
        "title": "Lima downloaded image cache",
        # Mole parity: downloaded OS image blobs keyed by URL hash.
        "paths": ("~/Library/Caches/lima/download/by-url-sha256/",),
        "protected_patterns": (
            "*/Caches/lima/instances/*",
            "*/Caches/lima/_config/*",
            "*.yaml",
        ),
    },
    "vagrant": {
        "title": "Vagrant temporary files",
        # Mole parity: package extraction tempdir only; boxes/data stay out.
        "paths": ("~/.vagrant.d/tmp/",),
        "protected_patterns": (
            "*/.vagrant.d/boxes/*",
            "*/.vagrant.d/data/*",
            "*/.vagrant.d/Vagrantfile",
            "*.box",
        ),
    },
    "canva": {
        "title": "Canva caches",
        "paths": (
            "~/Library/Caches/com.canva.CanvaDesktop/",
            "~/Library/Application Support/Canva/Cache/",
            "~/Library/Application Support/Canva/Code Cache/",
            "~/Library/Application Support/Canva/GPUCache/",
        ),
        "protected_patterns": (
            "*/Application Support/Canva/Local Storage/*",
            "*/Application Support/Canva/IndexedDB/*",
            "*/Application Support/Canva/Cookies*",
            "*/Application Support/Canva/Preferences",
        ),
    },
    "principle": {
        "title": "Principle caches",
        "paths": (
            "~/Library/Caches/com.danielhooper.principle/",
            "~/Library/Application Support/Principle/",
        ),
        "protected_patterns": (
            "*/Application Support/Principle/License*",
            "*.principle",
        ),
    },
    "framer": {
        "title": "Framer caches",
        "paths": (
            "~/Library/Caches/com.framer.desktop/",
            "~/Library/Application Support/Framer/Cache/",
            "~/Library/Application Support/Framer/Code Cache/",
            "~/Library/Application Support/Framer/GPUCache/",
        ),
        "protected_patterns": (
            "*/Application Support/Framer/Local Storage/*",
            "*/Application Support/Framer/IndexedDB/*",
            "*/Application Support/Framer/Cookies*",
            "*/Application Support/Framer/Preferences",
            "*/Application Support/Framer/projects/*",
        ),
    },
    "imovie": {
        "title": "iMovie caches",
        "paths": (
            "~/Library/Caches/com.apple.iMovieApp/",
            "~/Library/Containers/com.apple.iMovieApp/Data/Library/Caches/",
            "~/Library/Application Support/iMovie/Render Files/",
            "~/Movies/iMovie Library.imovielibrary/Render Files/",
        ),
        "protected_patterns": (
            "*.imovielibrary/*",
            "~//Movies/iMovie Library.imovielibrary/*",
            "*/Containers/com.apple.iMovieApp/Data/Documents/*",
            "~/Movies/*.mp4",
            "~/Movies/*.mov",
        ),
    },
    "finalCutPro": {
        "title": "Final Cut Pro caches",
        "paths": (
            "~/Library/Caches/com.apple.FinalCut/",
            "~/Library/Containers/com.apple.FinalCut/Data/Library/Caches/",
        ),
        "protected_patterns": (
            "*.fcpbundle/*",
            "*/Containers/com.apple.FinalCut/Data/Documents/*",
            "~/Movies/*",
        ),
    },
    "logicPro": {
        "title": "Logic Pro caches",
        "paths": (
            "~/Library/Caches/com.apple.logic10/",
            "~/Library/Application Support/Logic/Cache/",
        ),
        "protected_patterns": (
            "*.logicx",
            "~/Music/*",
            "*/Application Support/Logic/Sampler Instruments/*",
            "*/Application Support/Logic/Plug-In Settings/*",
            "*/Application Support/Logic/License*",
        ),
    },
    "bear": {
        "title": "Bear caches",
        "paths": (
            "~/Library/Caches/net.shinyfrog.bear/",
            "~/Library/Caches/com.bear-writer.*/",
            "~/Library/Containers/net.shinyfrog.bear/Data/Library/Caches/",
        ),
        "protected_patterns": (
            "*/Containers/net.shinyfrog.bear/Data/Documents/*",
            "*/Containers/net.shinyfrog.bear/Data/Library/Application Support/*",
            "*/Containers/net.shinyfrog.bear/Data/Library/Preferences/*",
        ),
    },
    "ulysses": {
        "title": "Ulysses caches",
        "paths": (
            "~/Library/Caches/com.soulmen.ulysses.mac/",
            "~/Library/Containers/com.soulmen.ulysses.mac/Data/Library/Caches/",
        ),
        "protected_patterns": (
            "*/Containers/com.soulmen.ulysses.mac/Data/Documents/*",
            "*/Containers/com.soulmen.ulysses.mac/Data/Library/Application Support/*",
            "*/Containers/com.soulmen.ulysses.mac/Data/Library/Preferences/*",
        ),
    },
    "fantastical": {
        "title": "Fantastical caches",
        "paths": (
            "~/Library/Caches/com.flexibits.fantastical2.mac/",
            "~/Library/Containers/com.flexibits.fantastical2.mac/Data/Library/Caches/",
        ),
        "protected_patterns": (
            "*/Containers/com.flexibits.fantastical2.mac/Data/Library/Preferences/*",
            "*/Containers/com.flexibits.fantastical2.mac/Data/Documents/*",
        ),
    },
    "rectangle": {
        "title": "Rectangle caches",
        "paths": (
            "~/Library/Caches/com.knollsoft.Rectangle/",
            "~/Library/Containers/com.knollsoft.Rectangle/Data/Library/Caches/",
        ),
        "protected_patterns": (
            "*/Containers/com.knollsoft.Rectangle/Data/Library/Preferences/*",
            "*/Application Support/Rectangle/com.knollsoft.Rectangle.plist",
            "*/Application Support/Rectangle/Shortcuts.plist",
        ),
    },
    "onePassword": {
        "title": "1Password caches",
        "paths": (
            "~/Library/Caches/com.agilebits.onepassword7/",
            "~/Library/Caches/com.agilebits.onepassword8/",
            "~/Library/Containers/com.agilebits.onepassword7/Data/Library/Caches/",
            "~/Library/Containers/com.agilebits.onepassword8/Data/Library/Caches/",
            "~/Library/Group Containers/2BUA8C4S2C.com.1password/Library/Caches/",
        ),
        "protected_patterns": (
            "*/Group Containers/2BUA8C4S2C.com.1password/Data/*",
            "*/Containers/com.agilebits.onepassword*/Data/Documents/*",
            "*/Containers/com.agilebits.onepassword*/Data/Library/Application Support/*",
            "*/Application Support/1Password/*",
            "*.opvault",
            "*.1pif",
        ),
    },
    "bitwarden": {
        "title": "Bitwarden caches",
        "paths": (
            "~/Library/Caches/com.bitwarden.desktop/",
            "~/Library/Application Support/Bitwarden/Cache/",
            "~/Library/Application Support/Bitwarden/Code Cache/",
            "~/Library/Application Support/Bitwarden/GPUCache/",
            "~/Library/Containers/com.bitwarden.desktop/Data/Library/Caches/",
        ),
        "protected_patterns": (
            "*/Application Support/Bitwarden/Local Storage/*",
            "*/Application Support/Bitwarden/IndexedDB/*",
            "*/Application Support/Bitwarden/data.json",
            "*/Application Support/Bitwarden/Cookies*",
            "~/Library/Application Support/Bitwarden/*.json",
        ),
    },
    "dashlane": {
        "title": "Dashlane caches",
        "paths": (
            "~/Library/Caches/com.dashlane.dashlanemacdesktop/",
            "~/Library/Application Support/Dashlane/Cache/",
            "~/Library/Application Support/Dashlane/Code Cache/",
            "~/Library/Containers/com.dashlane.Dashlane/Data/Library/Caches/",
        ),
        "protected_patterns": (
            "*/Application Support/Dashlane/Local Storage/*",
            "*/Application Support/Dashlane/IndexedDB/*",
            "*/Containers/com.dashlane.Dashlane/Data/Documents/*",
            "*/Containers/com.dashlane.Dashlane/Data/Library/Application Support/*",
        ),
    },
    "sequelAce": {
        "title": "Sequel Ace caches",
        "paths": (
            "~/Library/Caches/com.sequel-ace.sequel-ace/",
            "~/Library/Containers/com.sequel-ace.sequel-ace/Data/Library/Caches/",
        ),
        "protected_patterns": (
            "*/Containers/com.sequel-ace.sequel-ace/Data/Documents/*",
            "*/Containers/com.sequel-ace.sequel-ace/Data/Library/Application Support/*",
            "*/Containers/com.sequel-ace.sequel-ace/Data/Library/Preferences/*",
            "*.spf",
        ),
    },
    "orbStack": {
        "title": "OrbStack caches",
        "paths": (
            "~/Library/Caches/com.kdrag0n.MacVirt/",
            "~/Library/Application Support/OrbStack/cache/",
        ),
        "protected_patterns": (
            "*/Application Support/OrbStack/ssh-keys/*",
            "*/Application Support/OrbStack/config*",
            "*/Application Support/OrbStack/machines/*",
            "*/Application Support/OrbStack/docker*",
        ),
    },
    "transmit": {
        "title": "Transmit caches",
        "paths": (
            "~/Library/Caches/com.panic.Transmit/",
            "~/Library/Containers/com.panic.Transmit/Data/Library/Caches/",
        ),
        "protected_patterns": (
            "*/Containers/com.panic.Transmit/Data/Documents/*",
            "*/Containers/com.panic.Transmit/Data/Library/Application Support/*",
            "*/Containers/com.panic.Transmit/Data/Library/Preferences/*",
            "~/Library/Application Support/Transmit/*",
            "*.transmitdoc",
        ),
    },
    "nordVPN": {
        "title": "NordVPN caches",
        "paths": (
            "~/Library/Caches/com.nordvpn.osx/",
            "~/Library/Containers/com.nordvpn.osx-apple-auth/Data/Library/Caches/",
        ),
        "protected_patterns": (
            "*/Containers/com.nordvpn.osx-apple-auth/Data/Library/Preferences/*",
            "*/Application Support/NordVPN/*",
            "~/Library/Application Support/NordVPN/*",
        ),
    },
    "surfshark": {
        "title": "Surfshark caches",
        "paths": (
            "~/Library/Caches/com.surfshark.vpn/",
            "~/Library/Containers/com.surfshark.vpnclient.macos/Data/Library/Caches/",
        ),
        "protected_patterns": (
            "*/Containers/com.surfshark.vpnclient.macos/Data/Library/Preferences/*",
            "*/Containers/com.surfshark.vpnclient.macos/Data/Documents/*",
            "*/Application Support/Surfshark/*",
        ),
    },
    "grammarly": {
        "title": "Grammarly caches",
        "paths": (
            "~/Library/Caches/com.grammarly.ProjectLlama/",
            "~/Library/Application Support/Grammarly/Cache/",
            "~/Library/Application Support/Grammarly/Code Cache/",
            "~/Library/Application Support/Grammarly/GPUCache/",
        ),
        "protected_patterns": (
            "*/Application Support/Grammarly/Local Storage/*",
            "*/Application Support/Grammarly/IndexedDB/*",
            "*/Application Support/Grammarly/Cookies*",
            "*/Application Support/Grammarly/Preferences",
            "*/Application Support/Grammarly/user data/*",
        ),
    },
    "mimestream": {
        "title": "Mimestream caches",
        "paths": (
            "~/Library/Caches/com.mimestream.Mimestream/",
            "~/Library/Containers/com.mimestream.Mimestream/Data/Library/Caches/",
        ),
        "protected_patterns": (
            "*/Containers/com.mimestream.Mimestream/Data/Documents/*",
            "*/Containers/com.mimestream.Mimestream/Data/Library/Application Support/*",
            "*/Containers/com.mimestream.Mimestream/Data/Library/Preferences/*",
        ),
    },
    "reeder": {
        "title": "Reeder caches",
        "paths": (
            "~/Library/Caches/com.reederapp.feedly.macOS/",
            "~/Library/Containers/com.reederapp.feedly.macOS/Data/Library/Caches/",
        ),
        "protected_patterns": (
            "*/Containers/com.reederapp.feedly.macOS/Data/Documents/*",
            "*/Containers/com.reederapp.feedly.macOS/Data/Library/Application Support/*",
            "*/Containers/com.reederapp.feedly.macOS/Data/Library/Preferences/*",
        ),
    },
    "kindle": {
        "title": "Kindle caches",
        "paths": (
            "~/Library/Caches/com.amazon.Kindle/",
            "~/Library/Containers/com.amazon.Lassen/Data/Library/Caches/",
            "~/Library/Application Support/Kindle/Cache/",
        ),
        "protected_patterns": (
            "*/Containers/com.amazon.Lassen/Data/Documents/*",
            "*/Application Support/Kindle/My Kindle Content/*",
            "~/Library/Application Support/Kindle/*",
            "*.azw3",
            "*.epub",
            "*.mobi",
        ),
    },
    "cleanShot": {
        "title": "CleanShot X caches",
        "paths": (
            "~/Library/Caches/pl.maketheweb.cleanshotx/",
            "~/Library/Caches/com.cleanshot.*/",
            "~/Library/Containers/pl.maketheweb.cleanshotx/Data/Library/Caches/",
        ),
        "protected_patterns": (
            "*/Containers/pl.maketheweb.cleanshotx/Data/Documents/*",
            "*/Containers/pl.maketheweb.cleanshotx/Data/Library/Application Support/*",
            "*/Containers/pl.maketheweb.cleanshotx/Data/Library/Preferences/*",
            "~/Pictures/CleanShot/*",
            "~/Desktop/CleanShot*",
        ),
    },
    "snagit": {
        "title": "Snagit caches",
        "paths": (
            "~/Library/Caches/com.TechSmith.Snagit2024/",
            "~/Library/Containers/com.TechSmith.Snagit2024/Data/Library/Caches/",
        ),
        "protected_patterns": (
            "*/Containers/com.TechSmith.Snagit2024/Data/Documents/*",
            "*/Containers/com.TechSmith.Snagit2024/Data/Library/Application Support/*",
            "*/Containers/com.TechSmith.Snagit2024/Data/Library/Preferences/*",
            "*/Application Support/TechSmith/Snagit/*",
            "*.snagproj",
        ),
    },
    "obs": {
        "title": "OBS Studio caches",
        "paths": (
            "~/Library/Application Support/obs-studio/plugin_config/obs-browser/Cache/",
            "~/Library/Caches/com.obsproject.obs-studio/",
        ),
        "protected_patterns": (
            "*/obs-studio/basic/scenes/*",
            "*/obs-studio/basic/profiles/*",
            "*.json",
        ),
    },
    "davinciResolve": {
        "title": "DaVinci Resolve caches",
        "paths": (
            "~/Library/Caches/Blackmagic Design/DaVinci Resolve/",
            "~/Library/Caches/com.blackmagic-design.DaVinciResolve/",
            "~/Library/Application Support/Blackmagic Design/DaVinci Resolve/CacheClip/",
            "~/Movies/CacheClip/",
        ),
        "protected_patterns": (
            "*.drp",
            "*.drt",
        ),
    },
    "audacity": {
        "title": "Audacity caches",
        "paths": (
            "~/Library/Application Support/audacity/AutoSave/",
            "~/Library/Caches/org.audacityteam.audacity/",
        ),
        "protected_patterns": (
            "*.aup3",
            "*.aup",
        ),
    },
    "ableton": {
        "title": "Ableton Live caches",
        "paths": (
            "~/Library/Caches/Ableton/",
            "~/Music/Ableton/User Library/Caches/",
        ),
        "protected_patterns": (
            "*.als",
            "*.adg",
            "*.alp",
        ),
    },
    "camtasia": {
        "title": "Camtasia caches",
        "paths": (
            "~/Library/Caches/com.techsmith.camtasia2024/",
            "~/Library/Containers/com.techsmith.camtasia2024/Data/Library/Caches/",
        ),
        "protected_patterns": (
            "*.cmproj",
            "*.trec",
        ),
    },
    "screenflow": {
        "title": "ScreenFlow caches",
        "paths": (
            "~/Library/Caches/net.telestream.screenflow*/",
            "~/Library/Application Support/Telestream/ScreenFlow/Cache/",
        ),
        "protected_patterns": ("*.screenflow",),
    },
    "lightroom": {
        "title": "Adobe Lightroom caches",
        "paths": (
            "~/Library/Caches/Adobe/Lightroom/",
            "~/Library/Application Support/Adobe/Lightroom/Camera Raw/Cache/",
        ),
        "protected_patterns": (
            "*.lrcat",
            "*.lrcat-journal",
        ),
    },
    "photoshop": {
        "title": "Adobe Photoshop caches",
        "paths": (
            "~/Library/Caches/Adobe/Photoshop/",
            "~/Library/Caches/com.adobe.Photoshop/",
        ),
        "protected_patterns": (
            "*.psd",
            "*.psb",
        ),
    },
    "illustrator": {
        "title": "Adobe Illustrator caches",
        "paths": (
            "~/Library/Caches/Adobe/Illustrator/",
            "~/Library/Caches/com.adobe.illustrator/",
        ),
        "protected_patterns": (
            "*.ai",
            "*.eps",
        ),
    },
    "rhinoceros": {
        "title": "Rhinoceros 3D caches",
        "paths": (
            "~/Library/Caches/com.mcneel.rhinoceros/",
            "~/Library/Application Support/McNeel/Rhinoceros/*/AutoSave/",
        ),
        "protected_patterns": (
            "*.3dm",
            "*.3dmbak",
        ),
    },
    "sketchup": {
        "title": "SketchUp caches",
        "paths": (
            "~/Library/Caches/com.sketchup.SketchUp*/",
            "~/Library/Application Support/SketchUp */SketchUp/Cache/",
        ),
        "protected_patterns": (
            "*.skp",
            "*.skb",
        ),
    },
    "procreate": {
        "title": "Procreate caches",
        "paths": (
            "~/Library/Containers/com.savageinteractive.procreate/Data/Library/Caches/",
            "~/Library/Containers/com.savageinteractive.procreate.dreams/Data/Library/Caches/",
        ),
        "protected_patterns": (
            "*/Containers/com.savageinteractive.procreate*/Data/Documents/*",
            "*.procreate",
        ),
    },
    "rekordbox": {
        "title": "rekordbox caches",
        "paths": (
            "~/Library/Caches/com.pioneerdj.rekordbox/",
            "~/Library/Application Support/Pioneer/rekordbox/share/",
        ),
        "protected_patterns": (
            "*/rekordbox/*.db",
            "*.xml",
        ),
    },
    "reasonStudios": {
        "title": "Reason Studios caches",
        "paths": (
            "~/Library/Caches/se.propellerhead.reason/",
            "~/Library/Application Support/Reason/Cache/",
        ),
        "protected_patterns": (
            "*.reason",
            "*.repatch",
        ),
    },
    "adobeCreativeCloud": {
        "title": "Adobe Creative Cloud caches",
        "paths": (
            "~/Library/Caches/Adobe/Creative Cloud/",
            "~/Library/Application Support/Adobe/CEF/cef_cache/",
        ),
        "protected_patterns": (
            "*/Adobe/OOBE/*",
            "*/Adobe/Creative Cloud Libraries/*",
        ),
    },
    "dBeaver": {
        "title": "DBeaver caches",
        "paths": (
            "~/Library/Caches/org.jkiss.dbeaver.core/",
            "~/Library/Application Support/DBeaverData/workspace6/.metadata/",
        ),
        "protected_patterns": (
            "*/DBeaverData/Configuration/*",
            "*/DBeaverData/workspace6/General/*",
            "*/DBeaverData/drivers/*",
            "*.dbeaver",
            "*.sql",
        ),
    },
    "datagrip": {
        "title": "DataGrip caches",
        "paths": (
            "~/Library/Caches/JetBrains/DataGrip*/",
            "~/Library/Logs/JetBrains/DataGrip*/",
        ),
        "protected_patterns": (
            "*/JetBrains/DataGrip*/options/*",
            "*/JetBrains/DataGrip*/consoles/*",
            "*.sql",
        ),
    },
    "redisInsight": {
        "title": "Redis Insight caches",
        "paths": (
            "~/Library/Application Support/Redis Insight/Cache/",
            "~/Library/Caches/com.redis.RedisInsight/",
        ),
        "protected_patterns": (
            "*/Redis Insight/rdi_storage/*",
            "*/Redis Insight/settings/*",
            "*.rdb",
        ),
    },
    "robo3t": {
        "title": "Robo 3T / Studio 3T caches",
        "paths": (
            "~/Library/Caches/3T Software Ltd/",
            "~/Library/Caches/org.robomongo.robomongo/",
        ),
        "protected_patterns": (
            "*/3T Software Ltd/Studio 3T/connections/*",
            "*/robomongo/config/*",
            "*.json",
            "*.bson",
        ),
    },
    "wireshark": {
        "title": "Wireshark caches",
        "paths": (
            "~/Library/Caches/org.wireshark.Wireshark/",
            "~/Library/Application Support/Wireshark/cache/",
        ),
        "protected_patterns": (
            "*/Wireshark/profiles/*",
            "*/Wireshark/plugins/*",
            "*.pcap",
            "*.pcapng",
        ),
    },
    "kap": {
        "title": "Kap screen recorder caches",
        "paths": (
            "~/Library/Caches/com.wulkano.kap/",
            "~/Library/Application Support/Kap/Cache/",
        ),
        "protected_patterns": ("*/Kap/plugins/*",),
    },
    "notionEnhancer": {
        "title": "Notion Enhancer caches",
        "paths": (
            "~/Library/Caches/notion-enhancer/",
            "~/Library/Application Support/notion-enhancer/cache/",
        ),
    },
    "logiOptions": {
        "title": "Logi Options+ caches",
        "paths": (
            "~/Library/Caches/com.logi.OptionsPlus/",
            "~/Library/Application Support/Logitech/Logishrd/",
        ),
        "protected_patterns": (
            "*/Logitech/OptionsPlus/settings.json",
            "*/Logitech/OptionsPlus/devices/*",
        ),
    },
    "elgatoControl": {
        "title": "Elgato Control Center caches",
        "paths": ("~/Library/Caches/com.elgato.ControlCenter/",),
    },
    "microsoftRemoteDesktop": {
        "title": "Microsoft Remote Desktop caches",
        "paths": (
            "~/Library/Caches/com.microsoft.rdc.macos/",
            "~/Library/Containers/com.microsoft.rdc.mac/Data/Library/Caches/",
        ),
        "protected_patterns": (
            "*/Microsoft Remote Desktop/books/*",
            "*/Group Containers/UBF8T346G9.com.microsoft.rdc/*",
        ),
    },
    "cyberduck": {
        "title": "Cyberduck caches",
        "paths": (
            "~/Library/Caches/ch.sudo.cyberduck/",
            "~/Library/Application Support/Cyberduck/Cache/",
        ),
        "protected_patterns": (
            "*/Cyberduck/Bookmarks.plist",
            "*/Cyberduck/Profiles/*",
        ),
    },
    "alDente": {
        "title": "AlDente battery manager caches",
        "paths": (
            "~/Library/Caches/com.apphousekitchen.aldente-pro/",
            "~/Library/Containers/com.apphousekitchen.aldente-pro/Data/Library/Caches/",
        ),
    },
    "iStatMenus": {
        "title": "iStat Menus caches",
        "paths": ("~/Library/Caches/com.bjango.istatmenusstatus/",),
        "protected_patterns": (
            "*/iStat Menus/Config.plist",
            "*/iStat Menus/Sensors/*",
        ),
    },
    "bartender": {
        "title": "Bartender menu bar caches",
        "paths": ("~/Library/Caches/com.surteesstudios.Bartender/",),
    },
    "hazel": {
        "title": "Hazel file automation caches",
        "paths": ("~/Library/Caches/com.noodlesoft.HazelHelper/",),
        "protected_patterns": (
            "*/Hazel/Rules/*",
            "*/Hazel/Rules.plist",
        ),
    },
    "betterTouchTool": {
        "title": "BetterTouchTool caches",
        "paths": ("~/Library/Caches/com.hegenberg.BetterTouchTool/",),
        "protected_patterns": (
            "*/BetterTouchTool/*.bttdata",
            "*/BetterTouchTool/License*",
        ),
    },
    "karabiner": {
        "title": "Karabiner-Elements caches",
        "paths": (
            "~/Library/Caches/org.pqrs.Karabiner-Elements/",
            "~/.karabiner.d/cache/",
        ),
        "protected_patterns": (
            "*/karabiner/karabiner.json",
            "*/Karabiner-Elements/assets/*",
            "*/Karabiner-Elements/complex_modifications/*",
        ),
    },
    "quicksilver": {
        "title": "Quicksilver launcher caches",
        "paths": ("~/Library/Caches/com.blacktree.Quicksilver/",),
        "protected_patterns": ("*/Quicksilver/Plug-ins/*", "*/Quicksilver/Triggers.plist"),
    },
    "microsoftOutlook": {
        "title": "Microsoft Outlook caches",
        "paths": (
            "~/Library/Caches/com.microsoft.Outlook/",
            "~/Library/Containers/com.microsoft.Outlook/Data/Library/Caches/",
            "~/Library/Group Containers/UBF8T346G9.Office/Outlook/Outlook 15 Profiles/Cache/",
        ),
        "protected_patterns": (
            "*/Outlook/Outlook 15 Profiles/*/Data/*",
            "*/Outlook/Outlook 15 Profiles/Main Profile/Identity*",
        ),
    },
    "soundSource": {
        "title": "SoundSource caches",
        "paths": ("~/Library/Caches/com.rogueamoeba.soundsource/",),
    },
    "audioHijack": {
        "title": "Audio Hijack caches",
        "paths": ("~/Library/Caches/com.rogueamoeba.audiohijack/",),
        "protected_patterns": ("*/Audio Hijack/*.ahsession",),
    },
    "displayLink": {
        "title": "DisplayLink Manager caches",
        "paths": ("~/Library/Caches/com.displaylink.displaylinkmanager/",),
    },
    "corsairIcue": {
        "title": "Corsair iCUE caches",
        "paths": ("~/Library/Caches/com.corsair.icue/",),
        "protected_patterns": ("*/iCUE/Profiles/*",),
    },
    "razerSynapse": {
        "title": "Razer Synapse caches",
        "paths": ("~/Library/Caches/com.razer.synapse2/",),
        "protected_patterns": ("*/Razer Synapse/Profiles/*",),
    },
    "folx": {
        "title": "Folx download manager caches",
        "paths": (
            "~/Library/Caches/com.eltima.Folx3/",
            "~/Library/Caches/com.folx.*/",
            "~/Library/Application Support/Eltima/Folx3/Cache/",
        ),
        "protected_patterns": ("*/Folx3/Downloads/*", "*/Folx3/Tags/*"),
    },
    # Long-tail GUI application caches, aligned with Mole's
    # ``clean_user_gui_applications`` (lib/clean/app_caches.sh). Each rule is
    # scoped to regenerable cache/log/tmp leaves; accounts, documents,
    # databases, preferences, and downloaded media stay protected.
    "wecom": {
        "title": "WeCom caches",
        "paths": ("~/Library/Caches/com.tencent.WeWorkMac/",),
        "protected_patterns": ("*/Containers/com.tencent.WeWorkMac/Data/Documents/*",),
    },
    "tencentMeeting": {
        "title": "Tencent Meeting / VooV Meeting caches",
        "paths": ("~/Library/Caches/com.tencent.meeting/",),
        "protected_patterns": ("*/Tencent Meeting/*",),
    },
    "skype": {
        "title": "Skype caches",
        "paths": ("~/Library/Caches/com.skype.skype/",),
    },
    "legcord": {
        "title": "Legcord caches",
        "paths": ("~/Library/Application Support/legcord/Cache/",),
        "protected_patterns": (
            "*/legcord/Cookies*",
            "*/legcord/Local Storage/*",
            "*/legcord/IndexedDB/*",
            "*/legcord/Preferences",
        ),
    },
    "chatgpt": {
        "title": "ChatGPT desktop caches",
        "paths": ("~/Library/Caches/com.openai.chat/",),
        "protected_patterns": ("*/Application Support/com.openai.chat/*",),
    },
    "claudeDesktop": {
        "title": "Claude desktop caches and logs",
        "paths": (
            "~/Library/Caches/com.anthropic.claudefordesktop/",
            "~/Library/Logs/Claude/",
        ),
        "protected_patterns": ("*/Application Support/Claude/*",),
    },
    "lmStudio": {
        "title": "LM Studio caches",
        "paths": ("~/Library/Caches/com.lmstudio.lmstudio/",),
        # LM Studio <= 0.3.5 kept models, chats, and presets under
        # ~/.cache/lm-studio; newer builds use ~/.lmstudio. Neither tree is a
        # cleanup target; only the reverse-DNS cache directory is covered.
        "protected_patterns": ("*/.cache/lm-studio/*", "*/.lmstudio/*"),
    },
    "premierePro": {
        "title": "Adobe Premiere Pro caches and media cache files",
        "paths": (
            "~/Library/Caches/com.adobe.PremierePro.*/",
            "~/Library/Application Support/Adobe/Common/Media Cache Files/",
        ),
        "protected_patterns": ("*.prproj", "*.prpreset"),
    },
    "cinema4d": {
        "title": "Cinema 4D caches",
        "paths": ("~/Library/Caches/com.maxon.cinema4d/",),
        "protected_patterns": ("*.c4d",),
    },
    "autodeskCaches": {
        "title": "Autodesk application caches",
        "paths": ("~/Library/Caches/com.autodesk.*/",),
        "protected_patterns": ("*.dwg", "*.dxf", "*.rvt", "*.iam", "*.ipt"),
    },
    "miaoYan": {
        "title": "MiaoYan caches",
        "paths": ("~/Library/Caches/com.tw93.MiaoYan/",),
    },
    "klee": {
        "title": "Klee caches",
        "paths": (
            "~/Library/Caches/com.klee.desktop/",
            "~/Library/Caches/klee_desktop/",
        ),
    },
    "ora": {
        "title": "Ora caches",
        "paths": ("~/Library/Caches/com.orabrowser.app/",),
    },
    "filo": {
        "title": "Filo caches",
        "paths": ("~/Library/Caches/com.filo.client/",),
    },
    "flomo": {
        "title": "flomo caches",
        "paths": ("~/Library/Caches/com.flomoapp.mac/",),
    },
    "quark": {
        "title": "Quark video cache",
        "paths": ("~/Library/Application Support/Quark/Cache/videoCache/",),
        "protected_patterns": ("*/Quark/Download/*", "*/Quark/Downloads/*"),
    },
    "netNewsWire": {
        "title": "NetNewsWire caches",
        "paths": ("~/Library/Containers/com.ranchero.NetNewsWire-Evergreen/Data/Library/Caches/",),
        "protected_patterns": (
            "*/Containers/com.ranchero.NetNewsWire-Evergreen/Data/Documents/*",
            "*/Containers/com.ranchero.NetNewsWire-Evergreen/Data/Library/Preferences/*",
        ),
    },
    "mindNode": {
        "title": "MindNode caches",
        "paths": ("~/Library/Containers/com.ideasoncanvas.mindnode/Data/Library/Caches/",),
        "protected_patterns": (
            "*/Containers/com.ideasoncanvas.mindnode/Data/Documents/*",
            "*/Containers/com.ideasoncanvas.mindnode/Data/Library/Application Support/*",
            "*/Containers/com.ideasoncanvas.mindnode/Data/Library/Preferences/*",
        ),
    },
    "kaku": {
        "title": "Kaku caches",
        "paths": ("~/.cache/kaku/",),
    },
    "spacedrive": {
        "title": "Spacedrive thumbnail caches",
        "paths": ("~/Library/Application Support/spacedrive/thumbnails/",),
        "protected_patterns": (
            "*/spacedrive/library.db*",
            "*/spacedrive/config/*",
            "*/spacedrive/sd*/**",
        ),
    },
    "folo": {
        "title": "Folo caches",
        "paths": ("~/Library/Containers/is.follow/Data/Library/Application Support/Folo/Cache/Cache_Data/",),
        "protected_patterns": (
            "*/Folo/Cookies*",
            "*/Folo/Local Storage/*",
            "*/Folo/IndexedDB/*",
        ),
    },
    "neteaseMusic": {
        "title": "NetEase Cloud Music caches",
        "paths": ("~/Library/Caches/com.netease.163music/",),
        "protected_patterns": ("*/Containers/com.netease.163music/Data/Documents/*",),
    },
    "qqMusic": {
        "title": "QQ Music caches",
        "paths": (
            "~/Library/Caches/com.tencent.QQMusic/",
            "~/Library/Caches/com.tencent.QQMusicMac/",
            "~/Library/Containers/com.tencent.QQMusicMac/Data/Library/Caches/",
            "~/Library/Containers/com.tencent.QQMusicMac/Data/Library/Application Support/QQMusicMac/iRRCache/",
            "~/Library/Containers/com.tencent.QQMusicMac/Data/Library/Application Support/QQMusicMac/iLog/",
            "~/Library/Containers/com.tencent.QQMusicMac/Data/Library/Application Support/QQMusicMac/iCache/",
            "~/Library/Containers/com.tencent.QQMusicMac/Data/Library/Application Support/QQMusicMac/iTemp/",
        ),
        # iDownloadProxy holds offline downloads and must never be swept with
        # the streaming/log cache leaves.
        "protected_patterns": (
            "*/QQMusicMac/iDownloadProxy/*",
            "*/Containers/com.tencent.QQMusicMac/Data/Documents/*",
        ),
    },
    "kugouMusic": {
        "title": "Kugou Music caches",
        "paths": ("~/Library/Caches/com.kugou.mac/",),
        "protected_patterns": ("*/Containers/com.kugou.mac/Data/Documents/*",),
    },
    "kuwoMusic": {
        "title": "Kuwo Music caches",
        "paths": ("~/Library/Caches/com.kuwo.mac/",),
        "protected_patterns": ("*/Containers/com.kuwo.mac/Data/Documents/*",),
    },
    "appleTV": {
        "title": "Apple TV caches",
        "paths": ("~/Library/Caches/com.apple.TV/",),
        "protected_patterns": ("*.m4v", "*.mov", "*.mp4"),
    },
    "plex": {
        "title": "Plex desktop caches",
        "paths": ("~/Library/Caches/tv.plex.player.desktop/",),
        "protected_patterns": ("*/Plex Media Server/*",),
    },
    "iina": {
        "title": "IINA caches",
        "paths": ("~/Library/Caches/com.colliderli.iina/",),
    },
    "mpv": {
        "title": "mpv caches",
        "paths": ("~/Library/Caches/io.mpv/",),
        "protected_patterns": ("*/.config/mpv/*", "*/Application Support/mpv/watch_later/*"),
    },
    "iqiyi": {
        "title": "iQIYI caches",
        "paths": ("~/Library/Caches/com.iqiyi.player/",),
        "protected_patterns": ("*/Containers/com.iqiyi.player/Data/Documents/*",),
    },
    "tencentVideo": {
        "title": "Tencent Video caches",
        "paths": (
            "~/Library/Caches/com.tencent.tenvideo/",
            "~/Library/Containers/com.tencent.tenvideo/Data/Library/Application Support/Upgrade/",
            "~/Library/Containers/com.tencent.tenvideo/Data/Library/Application Support/VideoNative/",
            "~/Library/Containers/com.tencent.tenvideo/Data/Library/Application Support/documentCache/",
        ),
        "protected_patterns": (
            "*/Containers/com.tencent.tenvideo/Data/Documents/*",
            "*/Containers/com.tencent.tenvideo/Data/Library/Preferences/*",
        ),
    },
    "bilibili": {
        "title": "Bilibili caches",
        "paths": ("~/Library/Caches/tv.danmaku.bili/",),
        "protected_patterns": ("*/Containers/tv.danmaku.bili/Data/Documents/*",),
    },
    "douyu": {
        "title": "Douyu caches",
        "paths": ("~/Library/Caches/com.douyu.*/",),
    },
    "huya": {
        "title": "Huya caches",
        "paths": ("~/Library/Caches/com.huya.*/",),
    },
    "senPlayer": {
        "title": "SenPlayer video cache",
        "paths": ("~/Library/Containers/com.wuziqi.SenPlayer/Data/tmp/videoCache/",),
        "protected_patterns": ("*/Containers/com.wuziqi.SenPlayer/Data/Documents/*",),
    },
    "stremio": {
        "title": "Stremio caches",
        "paths": (
            "~/Library/Caches/smart.stremio*/",
            "~/Library/Application Support/stremio/stremio-server/stremio-cache/",
        ),
        "protected_patterns": ("*/stremio/stremio-server/stremio-server.sqlite*",),
    },
    "aria2gui": {
        "title": "Aria2 GUI caches",
        "paths": ("~/Library/Caches/net.xmac.aria2gui/",),
        "protected_patterns": ("*.aria2",),
    },
    "transmission": {
        "title": "Transmission caches",
        "paths": ("~/Library/Caches/org.m0k.transmission/",),
        "protected_patterns": ("*.torrent", "*/Application Support/Transmission/Resume/*"),
    },
    "qbittorrent": {
        "title": "qBittorrent caches",
        "paths": ("~/Library/Caches/com.qbittorrent.qBittorrent/",),
        "protected_patterns": ("*.torrent", "*/qBittorrent/BT_backup/*"),
    },
    "downie": {
        "title": "Downie caches",
        "paths": ("~/Library/Caches/com.downie.Downie-*/",),
        "protected_patterns": ("*/Downie*/Downloads/*", "*.downielink"),
    },
    "pacifist": {
        "title": "Pacifist caches",
        "paths": ("~/Library/Caches/com.charlessoft.pacifist/",),
    },
    "steam": {
        "title": "Steam web, depot, and shader caches",
        "paths": (
            "~/Library/Caches/com.valvesoftware.steam/",
            "~/Library/Application Support/Steam/htmlcache/",
            "~/Library/Application Support/Steam/appcache/",
            "~/Library/Application Support/Steam/depotcache/",
            "~/Library/Application Support/Steam/steamapps/shadercache/",
            "~/Library/Application Support/Steam/logs/",
        ),
        # Installed games (steamapps/common + manifests), account data, and
        # config stay untouched; only regenerable web/depot/shader caches and
        # logs are reachable.
        "protected_patterns": (
            "*/Steam/steamapps/common/*",
            "*/Steam/steamapps/*.acf",
            "*/Steam/steamapps/*.manifest",
            "*/Steam/userdata/*",
            "*/Steam/config/*",
            "*/Steam/ssfn*",
        ),
    },
    "epicGames": {
        "title": "Epic Games Launcher caches",
        "paths": ("~/Library/Caches/com.epicgames.EpicGamesLauncher/",),
        "protected_patterns": ("*/Epic/EpicGamesLauncher/Saved/Config/*",),
    },
    "battleNet": {
        "title": "Battle.net caches",
        "paths": (
            "~/Library/Caches/com.blizzard.Battle.net/",
            "~/Library/Application Support/Battle.net/Cache/",
        ),
    },
    "eaApp": {
        "title": "EA app caches",
        "paths": ("~/Library/Caches/com.ea.*/",),
    },
    "gogGalaxy": {
        "title": "GOG Galaxy caches",
        "paths": ("~/Library/Caches/com.gog.galaxy/",),
    },
    "riotGames": {
        "title": "Riot Games caches",
        "paths": ("~/Library/Caches/com.riotgames.*/",),
    },
    "minecraft": {
        "title": "Minecraft logs and web caches",
        "paths": (
            "~/Library/Application Support/minecraft/logs/",
            "~/Library/Application Support/minecraft/crash-reports/",
            "~/Library/Application Support/minecraft/webcache/",
            "~/Library/Application Support/minecraft/webcache2/",
        ),
        "protected_patterns": (
            "*/minecraft/saves/*",
            "*/minecraft/mods/*",
            "*/minecraft/resourcepacks/*",
            "*/minecraft/options.txt",
            "*/minecraft/*.json",
        ),
    },
    "lunarClient": {
        "title": "Lunar Client game and launcher caches",
        "paths": (
            "~/.lunarclient/game-cache/",
            "~/.lunarclient/launcher-cache/",
            "~/.lunarclient/logs/",
            "~/.lunarclient/offline/*/logs/",
            "~/.lunarclient/offline/files/*/logs/",
        ),
        "protected_patterns": ("*/.lunarclient/settings*", "*/.lunarclient/launcher-profiles/*"),
    },
    "pcsx2": {
        "title": "PCSX2 caches and logs",
        "paths": (
            "~/Library/Caches/net.pcsx2.PCSX2/",
            "~/Library/Application Support/PCSX2/cache/",
            "~/Library/Logs/PCSX2/",
        ),
        "protected_patterns": (
            "*/PCSX2/memcards/*",
            "*/PCSX2/saves/*",
            "*/PCSX2/inis/*",
            "*.iso",
        ),
    },
    "rpcs3": {
        "title": "RPCS3 caches and logs",
        "paths": (
            "~/Library/Caches/net.rpcs3.rpcs3/",
            "~/Library/Application Support/rpcs3/logs/",
        ),
        "protected_patterns": ("*/rpcs3/dev_hdd0/home/*", "*/rpcs3/dev_flash/*", "*.ps3"),
    },
    "youdaoDict": {
        "title": "Youdao Dictionary caches",
        "paths": ("~/Library/Caches/com.youdao.YoudaoDict/",),
    },
    "eudict": {
        "title": "Eudic dictionary caches",
        "paths": ("~/Library/Caches/com.eudic.*/",),
    },
    "bobTranslate": {
        "title": "Bob translation caches",
        "paths": ("~/Library/Caches/com.bob-build.Bob/",),
    },
    "camo": {
        "title": "Camo caches",
        "paths": ("~/Library/Caches/com.reincubate.camo/",),
    },
    "xnip": {
        "title": "Xnip caches",
        "paths": ("~/Library/Caches/com.xnipapp.xnip/",),
    },
    "sparkMail": {
        "title": "Spark Mail caches",
        "paths": ("~/Library/Caches/com.readdle.smartemail-Mac/",),
    },
    "airmail": {
        "title": "Airmail caches",
        "paths": ("~/Library/Caches/com.airmail.*/",),
    },
    "anydo": {
        "title": "Any.do caches",
        "paths": ("~/Library/Caches/com.any.do.*/",),
    },
    "ghostty": {
        "title": "Ghostty caches",
        "paths": ("~/Library/Caches/com.mitchellh.ghostty/",),
        "protected_patterns": ("*/.config/ghostty/*",),
    },
    "inputSourcePro": {
        "title": "Input Source Pro caches",
        "paths": ("~/Library/Caches/com.runjuu.Input-Source-Pro/",),
    },
    "wakatime": {
        "title": "WakaTime caches",
        "paths": ("~/Library/Caches/macos-wakatime.WakaTime/",),
        "protected_patterns": ("*/.wakatime.cfg", "*/.wakatime/*"),
    },
    "weType": {
        "title": "WeType image and dictionary update caches",
        "paths": (
            "~/Library/Application Support/WeType/com.onevcat.Kingfisher.ImageCache.WeType/",
            "~/Library/Application Support/WeType/DictUpdate/",
        ),
        # Engine state and the user dictionary live beside these leaves and
        # must be preserved.
        "protected_patterns": ("*/WeType/UserDict/*", "*/WeType/*.db", "*/WeType/Config/*"),
    },
    "mihomoParty": {
        "title": "mihomo-party caches and logs",
        "paths": (
            "~/Library/Application Support/mihomo-party/Cache/",
            "~/Library/Application Support/mihomo-party/Code Cache/",
            "~/Library/Application Support/mihomo-party/GPUCache/",
            "~/Library/Application Support/mihomo-party/DawnGraphiteCache/",
            "~/Library/Application Support/mihomo-party/DawnWebGPUCache/",
            "~/Library/Application Support/mihomo-party/logs/",
        ),
        "protected_patterns": (
            "*/mihomo-party/Cookies*",
            "*/mihomo-party/Local Storage/*",
            "*/mihomo-party/IndexedDB/*",
            "*/mihomo-party/Preferences",
            "*/mihomo-party/config/*",
            "*/mihomo-party/profiles/*",
        ),
    },
    "stash": {
        "title": "Stash caches",
        "paths": ("~/Library/Caches/ws.stash.app.mac/",),
    },
    "logseq": {
        "title": "Logseq caches",
        "paths": ("~/Library/Caches/com.logseq.*/",),
        "protected_patterns": ("*/Logseq/*/graphs/*",),
    },
    "yinxiang": {
        "title": "Yinxiang Note caches",
        "paths": ("~/Library/Caches/com.yinxiang.*/",),
        "protected_patterns": (
            "*/Containers/com.yinxiang.*/Data/Documents/*",
            "*/Application Support/Yinxiang*/Accounts/*",
        ),
    },
    "theUnarchiver": {
        "title": "The Unarchiver caches",
        "paths": ("~/Library/Caches/cx.c3.theunarchiver/",),
    },
    "teamViewer": {
        "title": "TeamViewer caches",
        "paths": ("~/Library/Caches/com.teamviewer.*/",),
    },
    "anyDesk": {
        "title": "AnyDesk caches",
        "paths": ("~/Library/Caches/com.anydesk.*/",),
        "protected_patterns": ("*/.anydesk/*",),
    },
    "toDesk": {
        "title": "ToDesk caches",
        "paths": ("~/Library/Caches/com.todesk.*/",),
    },
    "sunlogin": {
        "title": "Sunlogin remote caches",
        "paths": ("~/Library/Caches/com.sunlogin.*/",),
    },
}
