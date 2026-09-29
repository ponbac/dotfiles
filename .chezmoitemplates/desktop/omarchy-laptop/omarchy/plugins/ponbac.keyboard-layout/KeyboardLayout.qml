import QtQuick
import Quickshell
import Quickshell.Hyprland
import Quickshell.Io
import qs.Ui
import qs.Commons
import "KeyboardLayoutModel.js" as KeyboardLayoutModel

BarWidget {
  id: root
  moduleName: "omarchy.keyboard-layout"


  property string layoutFull: ""
  // The keyboard the last reading spoke for, which is the one a click switches,
  // and separately the one activelayout named as being typed on. A reading
  // confirms the first is really there, so the click has a keyboard to reach
  // from the first reading onwards rather than only after a switch, and stops
  // naming one that has been unplugged.
  property string keyboardName: ""
  property string typedKeyboardName: ""
  // Keyboards on the seat, buttons and virtual ones excluded, and whether the
  // last reading left that shape in doubt.
  property int keyboardCount: 0
  property bool keyboardUnresolved: false
  // Nothing to read or switch on the single-layout install most people run, so
  // the widget ships on the bar and stays out of the way until there are two.
  // An older Hyprland that doesn't report the list keeps showing the label.
  property bool multipleLayouts: true
  // Short language code per layout description ("English (US)": "en"), read from
  // xkb's own table rather than maintained by hand.
  property var layoutBriefs: ({})
  readonly property string layoutLabel: KeyboardLayoutModel.shortLabel(layoutFull, layoutBriefs)
  readonly property string layoutMonogram: layoutLabel.length > 0 ? layoutLabel.charAt(0).toUpperCase() : ""
  // The xkb code of the active layout and of every layout on the keyboard. The
  // ones with a flag get a greyscale flag dot; anything else keeps the keycap.
  property string layoutCode: ""
  property var layoutCodes: []
  readonly property bool showFlag: KeyboardLayoutModel.hasFlag(layoutCode)

  // A query already in flight was started before this event, so it may read the
  // layout the switch replaced. Remember the request and re-run once it lands
  // rather than dropping it; nothing else would correct the label afterwards.
  property bool refreshPending: false

  function refresh() {
    if (queryProc.running) {
      refreshPending = true
      return
    }

    refreshPending = false
    queryProc.running = true
  }

  // Keyboards someone can actually type on, which is not everything Hyprland
  // calls a keyboard.
  function typedKeyboards(keyboards) {
    return keyboards.filter(k => KeyboardLayoutModel.isTypedKeyboard(k.name))
  }

  // The main flag names no keyboard for long: fcitx5 takes it with the virtual
  // keyboard it binds to inject, which leaves no typed keyboard holding it and
  // nothing to read at all, and once that unbinds it lands on whichever device
  // Hyprland saw last, a power button included. Go by layout progress instead,
  // and by the keyboard activelayout named.
  function selectKeyboard(typed) {
    return KeyboardLayoutModel.selectKeyboard(typed, root.typedKeyboardName)
  }

  // switchxkblayout is a hyprctl command rather than a dispatcher, so it has to
  // be run rather than sent over the dispatch socket. It switches the keyboard
  // the last reading spoke for, so a click always advances the device the label
  // is describing. Switching the seat together would reach the typed keyboard
  // without having to name it, but it would also carry the buttons along, and
  // the whole read depends on those staying where they started: once a button
  // has been advanced too, a toggle that wraps the keyboard back to the first
  // layout leaves the button reading as the furthest along, and the label
  // follows the button.
  function cycleLayout() {
    if (!root.keyboardName || !root.bar) return
    root.bar.run("hyprctl switchxkblayout " + Util.shellQuote(root.keyboardName) + " next")
    refreshTimer.restart()
  }

  Component.onCompleted: {
    briefsProc.running = true
    refresh()
  }

  Connections {
    target: Hyprland
    function onRawEvent(event) {
      if (!event || !event.name) return
      var name = String(event.name)
      // The event names the keyboard that switched ahead of the layout it moved
      // to, and that is the keyboard being typed on whatever holds the main flag.
      if (name === "activelayout") {
        const named = KeyboardLayoutModel.eventKeyboardName(event)
        if (named) root.typedKeyboardName = named
      }

      // A reload that adds a layout to kb_layout decides whether the widget
      // shows at all, and leaves every keyboard on the layout it was already
      // reading, so it raises no activelayout to notice it by.
      if (name.indexOf("activelayout") !== -1 || name === "configreloaded") root.refresh()
    }
  }

  Process {
    id: queryProc
    command: ["hyprctl", "-j", "devices"]
    onRunningChanged: {
      if (running) {
        stallTimer.restart()
        return
      }

      stallTimer.stop()
      if (root.refreshPending) root.refresh()
    }
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: {
        let listed
        try {
          listed = JSON.parse(text || "{}").keyboards
        } catch (e) {
          return
        }

        // A query the watchdog killed reports nothing at all, and an empty
        // string parses into the same shape a seat with no keyboards would.
        // Tell them apart by the list itself, so only a reading that reached
        // hyprctl gets to speak for the seat.
        if (!Array.isArray(listed)) return

        const typed = root.typedKeyboards(listed)
        const kb = root.selectKeyboard(typed)
        if (!kb || !kb.active_keymap) {
          // Either the last keyboard has been unplugged, which the label has to
          // stop describing and the click has to stop naming, or keyboards are
          // there and none of them reports a keymap. Both leave the shape in
          // doubt, so keep asking rather than letting a count from before it
          // changed settle the poll.
          root.keyboardUnresolved = true
          if (typed.length === 0) {
            root.layoutFull = ""
            root.layoutCode = ""
            root.keyboardName = ""
          }
          return
        }

        root.keyboardUnresolved = false
        root.keyboardCount = typed.length
        root.keyboardName = String(kb.name || "")
        root.multipleLayouts = kb.layout === undefined || String(kb.layout).indexOf(",") !== -1
        root.layoutFull = kb.active_keymap
        root.layoutCode = KeyboardLayoutModel.layoutCode(kb)
        root.layoutCodes = kb.layout === undefined ? [] : String(kb.layout).split(",").map(c => c.trim())
      }
    }
  }

  // The table only changes when xkb data is upgraded, so read it at startup and
  // leave it alone. The bar is built per monitor, so this runs once per widget.
  // The exotic rulesets cover layouts like trans (IPA) that ship in the same xkb
  // package and set just as well, so load them or those labels lose their code.
  Process {
    id: briefsProc
    command: ["xkbcli", "list", "--load-exotic"]
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: root.layoutBriefs = KeyboardLayoutModel.layoutBriefs(text)
    }
  }

  Timer {
    id: refreshTimer
    interval: 600
    onTriggered: root.refresh()
  }

  // A query that never returns would freeze the label until the shell restarts,
  // since a Process that is already running can't be re-run. Give up on one that
  // overstays so the next refresh gets through, and ask again: the reading it
  // never delivered may have been the only one due on a settled seat, and
  // nothing else would come back for it.
  Timer {
    id: stallTimer
    interval: 5000
    onTriggered: {
      queryProc.running = false
      refreshTimer.restart()
    }
  }

  // Which keyboard on a crowded seat the label is describing can change without
  // Hyprland announcing it, since a device arriving or leaving raises no event
  // of its own, and that can only be learned by asking. Poll while there is that
  // ambiguity, until a first reading lands so a query that failed at login still
  // recovers, and while a reading has left the seat's shape in doubt. The
  // one-keyboard install has none of those, and is left alone rather than
  // spawning hyprctl forever for an answer that cannot change.
  Timer {
    interval: 10000
    running: !root.keyboardName || root.keyboardUnresolved || root.keyboardCount > 1
    repeat: true
    onTriggered: root.refresh()
  }

  visible: layoutLabel !== "" && multipleLayouts
  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight

  BarIconButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    dimmed: false
    iconComponent: Component {
      Item {
        // Every flag on the keyboard stays loaded and they crossfade, so a
        // switch reads as the dot turning over rather than a hard swap.
        Repeater {
          model: root.layoutCodes.filter(c => KeyboardLayoutModel.hasFlag(c))

          Image {
            required property string modelData
            readonly property bool current: modelData === root.layoutCode
            readonly property color fg: button.foreground

            // Whole-pixel position, and rasterised well above display size then
            // mipmapped down, so the fractional monitor scale doesn't soften it.
            // Optical spacing beside the power glyph; keep the full hit target.
            x: Math.round((parent.width - width) / 2) - 2
            // Lifted to the optical centre the neighbouring glyphs sit on,
            // which is above the canvas midline.
            y: Math.round((parent.height - height) / 2) - 1
            width: 13
            height: 13
            sourceSize: Qt.size(width * 4, height * 4)
            smooth: true
            mipmap: true
            source: KeyboardLayoutModel.flagSvg(modelData, Qt.rgba(fg.r, fg.g, fg.b, 1).toString())
            opacity: current ? 1 : 0
            scale: current ? 1 : 0.6
            rotation: current ? 0 : -60

            Behavior on opacity { NumberAnimation { duration: 220 } }
            Behavior on scale { NumberAnimation { duration: 320; easing.type: Easing.OutBack } }
            Behavior on rotation { NumberAnimation { duration: 320; easing.type: Easing.OutBack } }
          }
        }

        Rectangle {
          visible: !root.showFlag
          readonly property int keySize: Math.max(1, button.opticalSize - 2)

          anchors.centerIn: parent
          width: keySize
          height: keySize
          radius: Math.max(2, Math.round(keySize * 0.18))
          color: "transparent"
          border.color: button.foreground
          border.width: 1

          TextMetrics {
            id: monogramMetrics
            font.family: button.fontFamily
            font.pixelSize: Math.max(1, button.fontSize - 2)
            font.bold: true
            text: root.layoutMonogram
          }

          Text {
            id: monogram
            anchors.centerIn: parent
            anchors.horizontalCenterOffset: implicitWidth / 2 - (
              monogramMetrics.tightBoundingRect.x + monogramMetrics.tightBoundingRect.width / 2
            ) - 0.75
            anchors.verticalCenterOffset: implicitHeight / 2 - (
              baselineOffset + monogramMetrics.tightBoundingRect.y + monogramMetrics.tightBoundingRect.height / 2
            ) - 0.5 + (root.layoutMonogram === "S" ? 0.75 : 0)
            text: root.layoutMonogram
            color: button.foreground
            font: monogramMetrics.font
            renderType: Text.NativeRendering
          }
        }
      }
    }
    tooltipText: root.layoutFull
    onPressed: function() { root.cycleLayout() }
  }
}
