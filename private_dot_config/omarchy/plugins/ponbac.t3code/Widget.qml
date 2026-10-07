import QtQuick
import QtQuick.Shapes
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Ui

BarWidget {
  id: root
  moduleName: "ponbac.t3code"

  // The shell palette has no yellow/blue/green roles, so these default to the
  // Ayaka theme and can be overridden per widget in shell.json.
  readonly property color needsYouColor: setting("needsYouColor", "#ffcc66")
  readonly property color workingColor: setting("workingColor", "#80b3ff")
  readonly property color doneColor: setting("doneColor", "#80e680")
  readonly property color foreground: root.bar ? root.bar.barForeground : Color.foreground
  readonly property string fontFamily: root.bar ? root.bar.fontFamily : Style.font.family
  readonly property string windowClass: "com\\.t3tools\\.T3Code"
  readonly property int maxCardRows: 6

  // Other machines whose T3 Code servers are counted too, from shell.json:
  //   { "id": "ponbac.t3code", "remotes": ["dev-1"] }
  // Each one runs `t3code-status --serve` (t3code-status.service) on the tailnet.
  readonly property var remotes: {
    var value = setting("remotes", [])
    return typeof value === "string" ? [value] : value
  }

  property var needsYou: []
  property var working: []
  property var done: []
  property date now: new Date()

  readonly property bool shown: needsYou.length > 0 || working.length > 0 || done.length > 0
  readonly property bool cardShown: root.shown && button.tooltipHovered && cardDelay.elapsed
  readonly property string helperPath: Quickshell.env("HOME") + "/.local/bin/t3code-status"
  readonly property var helperCommand: {
    var command = [root.helperPath, "--watch"]
    for (var i = 0; i < root.remotes.length; i++) command.push("--peer", String(root.remotes[i]))
    return command
  }
  readonly property var groups: [
    { kind: "needsYou", label: "Needs you", tint: root.needsYouColor, items: root.needsYou, suffix: "" },
    { kind: "working", label: "Working", tint: root.workingColor, items: root.working, suffix: "" },
    { kind: "done", label: "Done", tint: root.doneColor, items: root.done, suffix: " ago" }
  ]
  readonly property var activeGroups: groups.filter(function(group) { return group.items.length > 0 })

  function applyPayload(payload) {
    var ok = payload && payload.status === "ok"
    root.needsYou = ok && payload.needsYou ? payload.needsYou : []
    root.working = ok && payload.working ? payload.working : []
    root.done = ok && payload.done ? payload.done : []
    root.now = new Date()
  }

  function age(since, suffix) {
    var started = Date.parse(since)
    if (isNaN(started)) return ""
    var minutes = Math.max(0, Math.floor((root.now.getTime() - started) / 60000))
    if (minutes < 1) return "now"
    if (minutes < 60) return minutes + "m" + suffix
    var hours = Math.floor(minutes / 60)
    if (hours < 24) return hours + "h " + (minutes % 60) + "m" + suffix
    return Math.floor(hours / 24) + "d" + suffix
  }

  function focusApp() {
    Quickshell.execDetached(["omarchy-hyprland-focus-app", root.windowClass])
  }

  visible: root.shown
  implicitWidth: visible ? pill.implicitWidth + Style.space(8) : 0
  implicitHeight: visible ? barSize : 0

  // The helper stays running, merges this machine with the remotes' feeds,
  // and prints a record only when something changes.
  Process {
    id: watchProc
    command: root.helperCommand
    running: true
    // The widget's shell.json settings arrive after creation, and a running
    // process keeps the command it was started with.
    onCommandChanged: {
      running = false
      restartTimer.interval = 200
      restartTimer.restart()
    }
    stdout: SplitParser {
      onRead: function(line) {
        try {
          root.applyPayload(JSON.parse(line || "{}"))
        } catch (e) {
          root.applyPayload(null)
        }
      }
    }
    onExited: {
      root.applyPayload(null)
      if (!restartTimer.running) restartTimer.restart()
    }
  }

  Timer {
    id: restartTimer
    interval: 5000
    onTriggered: {
      interval = 5000
      watchProc.running = true
    }
  }

  Timer {
    id: cardDelay
    property bool elapsed: false
    interval: 250
    onTriggered: {
      root.now = new Date()
      elapsed = true
    }
  }

  Connections {
    target: button
    function onTooltipHoveredChanged() {
      cardDelay.elapsed = false
      if (button.tooltipHovered) cardDelay.restart()
      else cardDelay.stop()
    }
  }

  Timer {
    interval: 30000
    running: root.cardShown
    repeat: true
    onTriggered: root.now = new Date()
  }

  // Status glyph shared by the pill and the card: dot, spinner or check.
  component Glyph: Item {
    id: glyph

    property string kind: ""
    property color tint: "white"

    implicitWidth: Style.space(9)
    implicitHeight: Style.space(9)

    Rectangle {
      visible: glyph.kind === "needsYou"
      anchors.centerIn: parent
      width: Style.space(6)
      height: width
      radius: width / 2
      color: glyph.tint
    }

    Shape {
      id: spinner
      visible: glyph.kind === "working"
      anchors.fill: parent
      preferredRendererType: Shape.CurveRenderer

      ShapePath {
        strokeColor: glyph.tint
        strokeWidth: 1.6
        fillColor: "transparent"
        capStyle: ShapePath.RoundCap

        PathAngleArc {
          centerX: spinner.width / 2
          centerY: spinner.height / 2
          radiusX: spinner.width / 2 - 1
          radiusY: spinner.height / 2 - 1
          startAngle: 0
          sweepAngle: 250
        }
      }

      NumberAnimation on rotation {
        from: 0
        to: 360
        duration: 1100
        loops: Animation.Infinite
        running: glyph.kind === "working"
      }
    }

    Shape {
      id: check
      visible: glyph.kind === "done"
      anchors.fill: parent
      preferredRendererType: Shape.CurveRenderer

      ShapePath {
        strokeColor: glyph.tint
        strokeWidth: 1.6
        fillColor: "transparent"
        capStyle: ShapePath.RoundCap
        joinStyle: ShapePath.RoundJoin
        startX: check.width * 0.12
        startY: check.height * 0.54
        PathLine { x: check.width * 0.39; y: check.height * 0.8 }
        PathLine { x: check.width * 0.88; y: check.height * 0.22 }
      }
    }
  }

  // One neutral pill; a segment per non-empty group, split by hairlines.
  Rectangle {
    id: pill
    anchors.centerIn: parent
    implicitWidth: segments.implicitWidth
    implicitHeight: Style.space(18)
    width: implicitWidth
    height: implicitHeight
    radius: height / 2
    color: Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.1)

    Row {
      id: segments
      anchors.centerIn: parent
      height: parent.height

      Repeater {
        model: root.activeGroups

        Item {
          id: segment

          required property var modelData
          required property int index

          implicitWidth: segmentContent.implicitWidth + Style.space(15)
          width: implicitWidth
          height: segments.height

          Rectangle {
            visible: segment.index > 0
            width: 1
            height: parent.height
            color: Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.22)
          }

          Row {
            id: segmentContent
            anchors.centerIn: parent
            spacing: Style.space(5)

            Glyph {
              anchors.verticalCenter: parent.verticalCenter
              kind: segment.modelData.kind
              tint: segment.modelData.tint
            }

            Text {
              anchors.verticalCenter: parent.verticalCenter
              text: String(segment.modelData.items.length)
              color: segment.modelData.tint
              font.family: root.fontFamily
              font.pixelSize: Style.font.caption
              font.weight: Font.Bold
              font.features: { "tnum": 1 }
              renderType: Text.NativeRendering
            }
          }
        }
      }
    }
  }

  WidgetButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    keepSpace: true
    onPressed: function() { root.focusApp() }
  }

  // Hover card, drawn here instead of the bar's plain tooltip bubble.
  PopupWindow {
    id: card

    readonly property int cardWidth: Style.space(330)

    visible: root.cardShown
    color: "transparent"
    implicitWidth: cardWidth
    implicitHeight: Math.ceil(cardBody.implicitHeight)

    anchor {
      id: cardAnchor
      window: root.QsWindow.window
      adjustment: PopupAdjustment.Slide
      edges: Edges.Top | Edges.Left
      gravity: Edges.Bottom | Edges.Right
      rect.width: 1
      rect.height: 1

      onAnchoring: {
        var window = root.QsWindow.window
        if (!window) return
        var point = window.contentItem.mapFromItem(root, root.width / 2 - card.cardWidth / 2, root.height + Style.space(6))
        cardAnchor.rect.x = Math.round(point.x)
        cardAnchor.rect.y = Math.round(point.y)
      }
    }

    Rectangle {
      id: cardBody
      width: card.cardWidth
      implicitHeight: cardColumn.implicitHeight + Style.space(12)
      radius: Style.space(9)
      color: Qt.rgba(10 / 255, 10 / 255, 18 / 255, 0.9)
      border.width: 1
      border.color: Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.22)

      Column {
        id: cardColumn
        x: Style.space(6)
        y: Style.space(6)
        width: parent.width - Style.space(12)

        Repeater {
          model: root.activeGroups

          Column {
            id: section

            required property var modelData
            required property int index
            readonly property var rows: modelData.items.slice(0, root.maxCardRows)
            readonly property int hidden: modelData.items.length - rows.length

            width: cardColumn.width

            Item {
              visible: section.index > 0
              width: parent.width
              height: Style.space(11)

              Rectangle {
                anchors.verticalCenter: parent.verticalCenter
                x: Style.space(6)
                width: parent.width - Style.space(12)
                height: 1
                color: Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.1)
              }
            }

            Item {
              width: parent.width
              height: Style.space(20)

              Glyph {
                x: Style.space(6)
                anchors.verticalCenter: parent.verticalCenter
                kind: section.modelData.kind
                tint: section.modelData.tint
              }

              Text {
                x: Style.space(21)
                anchors.verticalCenter: parent.verticalCenter
                text: section.modelData.label.toUpperCase()
                color: section.modelData.tint
                font.family: root.fontFamily
                font.pixelSize: Math.max(8, Style.font.caption - 1)
                font.weight: Font.Bold
                font.letterSpacing: 1
                renderType: Text.NativeRendering
              }
            }

            Repeater {
              model: section.rows

              Item {
                id: row

                required property var modelData

                width: section.width
                height: Style.space(20)

                Text {
                  id: rowAge
                  anchors.right: parent.right
                  anchors.rightMargin: Style.space(6)
                  anchors.verticalCenter: parent.verticalCenter
                  text: (row.modelData.host ? row.modelData.host + " · " : "") + root.age(row.modelData.since, section.modelData.suffix)
                  color: Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.45)
                  font.family: root.fontFamily
                  font.pixelSize: Style.font.caption
                  renderType: Text.NativeRendering
                }

                Text {
                  anchors.left: parent.left
                  anchors.leftMargin: Style.space(21)
                  anchors.right: rowAge.left
                  anchors.rightMargin: Style.space(10)
                  anchors.verticalCenter: parent.verticalCenter
                  text: String(row.modelData.title || "")
                  textFormat: Text.PlainText
                  elide: Text.ElideRight
                  color: root.foreground
                  font.family: root.fontFamily
                  font.pixelSize: Style.font.bodySmall
                  renderType: Text.NativeRendering
                }
              }
            }

            Text {
              visible: section.hidden > 0
              x: Style.space(21)
              height: Style.space(20)
              verticalAlignment: Text.AlignVCenter
              text: "+" + section.hidden + " more"
              color: Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.45)
              font.family: root.fontFamily
              font.pixelSize: Style.font.caption
              renderType: Text.NativeRendering
            }
          }
        }
      }
    }
  }
}
