"""Native macOS app — menu bar, NSPopover, and WKWebView dashboard."""

import os, sys, threading


def run_native_app(port, mc, sm):
    """Run native macOS app with menu bar monitor + popover + WKWebView dashboard."""
    import objc
    from AppKit import (
        NSApplication, NSApp, NSObject, NSStatusBar, NSVariableStatusItemLength,
        NSMenu, NSMenuItem, NSFont, NSAttributedString, NSImage, NSAlert,
        NSWindow, NSWindowStyleMaskTitled, NSWindowStyleMaskClosable,
        NSWindowStyleMaskMiniaturizable, NSWindowStyleMaskResizable,
        NSBackingStoreBuffered, NSApplicationActivationPolicyAccessory,
        NSPopover, NSEvent,
    )
    from Foundation import (
        NSTimer, NSRunLoop, NSDefaultRunLoopMode, NSURL, NSURLRequest,
        NSDictionary, NSMakeRect, NSSize,
    )
    import WebKit

    from . import VERSION
    from .updater import check_for_updates, self_update

    url = f"http://localhost:{port}"
    popover_url = f"http://localhost:{port}/popover"

    # NSMinYEdge = 1 (show popover below the menu bar button)
    NSMinYEdge = 1
    # NSRightMouseDownMask = 1 << 3 = 8 (not 1 << 25)
    NSRightMouseDownMask = 1 << 3

    class AppDelegate(NSObject):
        _window = None
        _webview = None
        _status_item = None
        _timer = None
        _popover = None
        _popover_webview = None
        _event_monitor = None

        def applicationDidFinishLaunching_(self, notification):
            NSApp.setActivationPolicy_(NSApplicationActivationPolicyAccessory)

            # ── Menu bar status item ──
            self._status_item = NSStatusBar.systemStatusBar().statusItemWithLength_(NSVariableStatusItemLength)
            self._status_item.setTitle_("⚡ MacStressMonitor")

            # ── Popover ──
            self._popover = NSPopover.alloc().init()
            self._popover.setBehavior_(1)  # NSPopoverBehaviorTransient

            # Popover content: WKWebView
            popover_rect = NSMakeRect(0, 0, 320, 520)
            config = WebKit.WKWebViewConfiguration.alloc().init()
            # Inject native flag so JS can detect WKWebView
            native_script = WebKit.WKUserScript.alloc().initWithSource_injectionTime_forMainFrameOnly_(
                'window.__MACSTRESS_NATIVE__=true;', 0, True  # 0 = WKUserScriptInjectionTimeAtDocumentStart
            )
            config.userContentController().addUserScript_(native_script)
            self._popover_webview = WebKit.WKWebView.alloc().initWithFrame_configuration_(
                popover_rect, config
            )

            from AppKit import NSViewController
            vc = NSViewController.alloc().init()
            vc.setView_(self._popover_webview)
            self._popover.setContentSize_(NSSize(320, 520))
            self._popover.setContentViewController_(vc)

            req = NSURLRequest.requestWithURL_(NSURL.URLWithString_(popover_url))
            self._popover_webview.loadRequest_(req)

            # ── Left-click: toggle popover (use string selector) ──
            button = self._status_item.button()
            if button:
                button.setTarget_(self)
                button.setAction_("togglePopover:")

            # ── Right-click menu ──
            menu = NSMenu.alloc().init()
            open_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Open Dashboard", "openDashboard:", "d")
            open_item.setTarget_(self)
            menu.addItem_(open_item)

            menu.addItem_(NSMenuItem.separatorItem())

            upd_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Check for Updates...", "checkUpdate:", "")
            upd_item.setTarget_(self)
            menu.addItem_(upd_item)

            menu.addItem_(NSMenuItem.separatorItem())

            start_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Start All Stress Tests", "startAll:", "s")
            start_item.setTarget_(self)
            menu.addItem_(start_item)

            stop_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Stop All Stress Tests", "stopAll:", "x")
            stop_item.setTarget_(self)
            menu.addItem_(stop_item)

            menu.addItem_(NSMenuItem.separatorItem())

            quit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Quit MacStressMonitor", "quit:", "q")
            quit_item.setTarget_(self)
            menu.addItem_(quit_item)

            self._menu = menu

            # ── Right-click: monitor events and show menu ──
            # We monitor right-mouse-down events locally and check if they hit our button
            def right_click_handler(event):
                btn = self._status_item.button()
                if btn:
                    loc = event.locationInWindow()
                    win = event.window()
                    btn_win = btn.window()
                    if win and btn_win and win == btn_win:
                        local = btn.convertPoint_fromView_(loc, None)
                        if btn.mouse_inRect_ofView_(local, btn.bounds(), btn):
                            self._status_item.popUpStatusItemMenu_(self._menu)
                            return None  # consume the event
                return event

            self._event_monitor = NSEvent.addLocalMonitorForEventsMatchingMask_handler_(
                NSRightMouseDownMask, right_click_handler
            )

            # ── Timer for menu bar updates ──
            self._timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
                1.0, self, "updateMenuBar:", None, True
            )
            NSRunLoop.currentRunLoop().addTimer_forMode_(self._timer, NSDefaultRunLoopMode)

            # Auto-open dashboard
            self.openDashboard_(None)

        def togglePopover_(self, sender):
            """Left-click: toggle the metrics popover."""
            if self._popover.isShown():
                self._popover.performClose_(sender)
            else:
                button = self._status_item.button()
                if button:
                    req = NSURLRequest.requestWithURL_(NSURL.URLWithString_(popover_url))
                    self._popover_webview.loadRequest_(req)
                    self._popover.showRelativeToRect_ofView_preferredEdge_(
                        button.bounds(), button, NSMinYEdge
                    )

        def checkUpdate_(self, sender):
            result = check_for_updates(silent=True)
            has_update = False
            latest_ver = VERSION
            if result:
                has_update, latest_ver = result

            if has_update:
                msg = f"Нова версія доступна: v{latest_ver}"
                info = f"Поточна: v{VERSION}. Натисніть 'Оновити' для автоматичного оновлення."
            else:
                msg = "Ви використовуєте останню версію."
                info = f"MacStress v{VERSION}"

            alert = NSAlert.alloc().init()
            alert.setMessageText_(msg)
            alert.setInformativeText_(info)
            alert.addButtonWithTitle_("OK")
            if has_update:
                alert.addButtonWithTitle_("Оновити")

            resp = alert.runModal()
            if has_update and resp == 1001:
                ok, err = self_update(target_ver=latest_ver)
                if ok:
                    a2 = NSAlert.alloc().init()
                    a2.setMessageText_("Оновлено! Перезапуск...")
                    a2.addButtonWithTitle_("OK")
                    a2.runModal()
                    os.execv(sys.executable, [sys.executable] + sys.argv)
                else:
                    a2 = NSAlert.alloc().init()
                    a2.setMessageText_(f"Помилка: {err}")
                    a2.addButtonWithTitle_("OK")
                    a2.runModal()

        def updateMenuBar_(self, timer):
            """Update menu bar with live CPU / RAM / Temp / Power stats."""
            try:
                snap = mc.get_snapshot()
                cpu = snap.get("cpu_usage", 0)
                mem = snap.get("mem_used_pct", 0)
                ct = snap.get("cpu_temp")
                pw = snap.get("total_power_w")

                parts = [f"CPU {cpu:.0f}%", f"RAM {mem:.0f}%"]
                if ct is not None:
                    parts.append(f"{ct:.0f}°C")
                if pw is not None:
                    parts.append(f"{pw:.1f}W")
                title = "  ".join(parts)

                font = NSFont.monospacedDigitSystemFontOfSize_weight_(12.0, 0.0)
                attrs = NSDictionary.dictionaryWithObject_forKey_(font, "NSFont")
                attr_str = NSAttributedString.alloc().initWithString_attributes_(title, attrs)
                self._status_item.setAttributedTitle_(attr_str)
            except Exception:
                pass

        def openDashboard_(self, sender):
            if self._window and self._window.isVisible():
                self._window.makeKeyAndOrderFront_(None)
                NSApp.activateIgnoringOtherApps_(True)
                return

            style = (NSWindowStyleMaskTitled | NSWindowStyleMaskClosable |
                     NSWindowStyleMaskMiniaturizable | NSWindowStyleMaskResizable)
            rect = NSMakeRect(100, 100, 1200, 750)
            self._window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
                rect, style, NSBackingStoreBuffered, False
            )
            self._window.setTitle_("MacStressMonitor Dashboard")
            self._window.setMinSize_((800, 500))
            self._window.setReleasedWhenClosed_(False)

            try:
                from AppKit import NSAppearance
                dark = NSAppearance.appearanceNamed_("NSAppearanceNameDarkAqua")
                if dark:
                    self._window.setAppearance_(dark)
            except Exception:
                pass

            config = WebKit.WKWebViewConfiguration.alloc().init()
            self._webview = WebKit.WKWebView.alloc().initWithFrame_configuration_(
                rect, config
            )
            req = NSURLRequest.requestWithURL_(NSURL.URLWithString_(url))
            self._webview.loadRequest_(req)
            self._window.setContentView_(self._webview)
            self._window.center()
            self._window.makeKeyAndOrderFront_(None)
            NSApp.activateIgnoringOtherApps_(True)

        def startAll_(self, sender):
            threading.Thread(target=sm.start_all, args=(600,), daemon=True).start()

        def stopAll_(self, sender):
            threading.Thread(target=sm.stop_all, daemon=True).start()

        def quit_(self, sender):
            sm.stop_all()
            mc.stop()
            NSApp.terminate_(None)

    app = NSApplication.sharedApplication()
    delegate = AppDelegate.alloc().init()
    app.setDelegate_(delegate)

    # Expose delegate for server.py access
    import macstress.native_app as _mod
    _mod._delegate = delegate

    app.run()
