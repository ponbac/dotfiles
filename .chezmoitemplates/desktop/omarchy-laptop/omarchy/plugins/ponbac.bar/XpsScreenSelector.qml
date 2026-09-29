import QtQuick
import Quickshell
import Quickshell.Hyprland
import "ScreenSelection.js" as ScreenSelection

QtObject {
    // Quickshell's screens are the surfaces the bar can actually target.
    // Hyprland provides descriptive names; stale IPC-only monitors cannot win.
    readonly property string selectedScreen: ScreenSelection.selectScreen(
        Quickshell.screens, Hyprland.monitors.values)
}
