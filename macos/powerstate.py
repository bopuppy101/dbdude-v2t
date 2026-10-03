"""macOS notification adapter. Registration precedes the initial state query."""
import os
import Quartz
from Cocoa import NSObject, NSWorkspace, NSDistributedNotificationCenter


class PowerObserver(NSObject):
    def received_(self, notification):
        self.callback(str(notification.name()))


def session_awake():
    """Fail closed if display/session information cannot be read."""
    try:
        session = Quartz.CGSessionCopyCurrentDictionary()
        if not session or not session.get('kCGSSessionOnConsoleKey', False):
            return False
        if session.get('kCGSSessionUserIDKey') != os.getuid():
            return False
        if not session.get('kCGSessionLoginDoneKey', False):
            return False
        if session.get('CGSSessionScreenIsLocked', False):
            return False
        error, displays, count = Quartz.CGGetOnlineDisplayList(32, None, None)
        return error == 0 and any(not Quartz.CGDisplayIsAsleep(d) for d in displays[:count])
    except Exception:
        return False


class PowerNotifications:
    def __init__(self, callback):
        self.observer = PowerObserver.alloc().init()
        self.observer.callback = callback
        self.workspace = NSWorkspace.sharedWorkspace().notificationCenter()
        self.distributed = NSDistributedNotificationCenter.defaultCenter()
        for name in ('NSWorkspaceScreensDidSleepNotification', 'NSWorkspaceScreensDidWakeNotification',
                     'NSWorkspaceWillSleepNotification', 'NSWorkspaceDidWakeNotification',
                     'NSWorkspaceSessionDidResignActiveNotification', 'NSWorkspaceSessionDidBecomeActiveNotification'):
            self.workspace.addObserver_selector_name_object_(self.observer, 'received:', name, None)
        for name in ('com.apple.screenIsLocked', 'com.apple.screenIsUnlocked'):
            self.distributed.addObserver_selector_name_object_(self.observer, 'received:', name, None)

    def close(self):
        self.workspace.removeObserver_(self.observer)
        self.distributed.removeObserver_(self.observer)
