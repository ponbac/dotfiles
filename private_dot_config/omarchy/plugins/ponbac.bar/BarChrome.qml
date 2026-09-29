import QtQuick
import QtQuick.Shapes

// Shibumi V2 "notch" chrome: content-width island whose outer (screen) edge
// is the long side, with cubic shoulders into a shorter inner edge.
// Geometry tokens match HANCORE-linux/Shibumi-Shell RunChrome.qml.
Item {
  id: root

  property color color: "transparent"
  property color borderColor: "transparent"
  property real borderWidth: 1
  property real wing: 14
  property real bodyRadius: 9
  property string wideEdge: "top"

  // Three-stop gradient along the island's long axis. When set it replaces
  // `color`. Drawn by a scene-graph Shape so per-stop alpha survives a cold
  // start, which Canvas fillStyle does not.
  property bool gradientFill: false
  property color gradientStart: "transparent"
  property color gradientMid: "transparent"
  property color gradientEnd: "transparent"

  readonly property real kappa: 0.55228475
  readonly property bool horizontal: wideEdge === "top" || wideEdge === "bottom"

  onColorChanged: canvas.requestPaint()
  onBorderColorChanged: canvas.requestPaint()
  onBorderWidthChanged: canvas.requestPaint()
  onWingChanged: canvas.requestPaint()
  onBodyRadiusChanged: canvas.requestPaint()
  onWideEdgeChanged: canvas.requestPaint()
  onGradientFillChanged: canvas.requestPaint()
  onWidthChanged: canvas.requestPaint()
  onHeightChanged: canvas.requestPaint()
  Component.onCompleted: canvas.requestPaint()

  // Qt Canvas fillStyle/strokeStyle drop alpha on the first paint after a
  // cold start (reboot / shell restart). Put RGB in the style and alpha in
  // globalAlpha; item opacity on the caller is the other half of this.
  function channel8(v) {
    var n = Number(v)
    if (!isFinite(n))
      return 0
    if (n > 1)
      return Math.max(0, Math.min(255, Math.round(n)))
    return Math.max(0, Math.min(255, Math.round(n * 255)))
  }

  function unitAlpha(c) {
    var a = Number(c.a)
    if (!isFinite(a))
      return 1
    if (a > 1)
      return Math.max(0, Math.min(1, a / 255))
    return Math.max(0, Math.min(1, a))
  }

  function rgbStyle(c) {
    return "rgb(" + channel8(c.r) + ", " + channel8(c.g) + ", " + channel8(c.b) + ")"
  }

  function notchMetrics(w, h) {
    var wing = Math.min(root.wing, w / 2, h)
    var body = Math.min(root.bodyRadius, wing)
    var edge = wing + body
    if (edge > w / 2)
      edge = w / 2
    if (edge > h)
      edge = h
    return { wing: wing, body: body, k: root.kappa, edge: edge }
  }

  // Fill extends 1px past the screen edge so canvas AA cannot leave a
  // wallpaper sliver on that pixel row.
  function fillNotch(ctx, w, h) {
    var m = notchMetrics(w, h)
    var k = m.k
    var wing = m.wing
    var body = m.body
    var edge = m.edge

    ctx.beginPath()
    if (root.wideEdge === "bottom") {
      ctx.moveTo(0, h + 1)
      ctx.lineTo(w, h + 1)
      ctx.lineTo(w, h)
      ctx.bezierCurveTo(w - k * wing, h, w - wing + (1 - k) * body, 0, w - edge, 0)
      ctx.lineTo(edge, 0)
      ctx.bezierCurveTo(wing - (1 - k) * body, 0, wing - (1 - k) * wing, h, 0, h)
    } else if (root.wideEdge === "left") {
      ctx.moveTo(-1, 0)
      ctx.lineTo(-1, h)
      ctx.lineTo(0, h)
      ctx.bezierCurveTo(0, h - k * wing, w, h - wing + (1 - k) * body, w, h - edge)
      ctx.lineTo(w, edge)
      ctx.bezierCurveTo(w, wing - (1 - k) * body, 0, wing - (1 - k) * wing, 0, 0)
    } else if (root.wideEdge === "right") {
      ctx.moveTo(w + 1, 0)
      ctx.lineTo(w + 1, h)
      ctx.lineTo(w, h)
      ctx.bezierCurveTo(w, h - k * wing, 0, h - wing + (1 - k) * body, 0, h - edge)
      ctx.lineTo(0, edge)
      ctx.bezierCurveTo(0, wing - (1 - k) * body, w, wing - (1 - k) * wing, w, 0)
    } else {
      ctx.moveTo(0, -1)
      ctx.lineTo(w, -1)
      ctx.lineTo(w, 0)
      ctx.bezierCurveTo(w - k * wing, 0, w - wing + (1 - k) * body, h, w - edge, h)
      ctx.lineTo(edge, h)
      ctx.bezierCurveTo(wing - (1 - k) * body, h, wing - (1 - k) * wing, 0, 0, 0)
    }
    ctx.closePath()
    ctx.fill()
  }

  // SVG twin of fillNotch for the Shape fill; keep the two in step.
  function notchSvg(w, h) {
    if (w < 8 || h < 8)
      return ""
    var m = notchMetrics(w, h)
    var k = m.k
    var wing = m.wing
    var body = m.body
    var edge = m.edge
    function c(x1, y1, x2, y2, x, y) {
      return " C " + x1 + " " + y1 + " " + x2 + " " + y2 + " " + x + " " + y
    }

    if (root.wideEdge === "bottom")
      return "M 0 " + (h + 1) + " L " + w + " " + (h + 1) + " L " + w + " " + h
        + c(w - k * wing, h, w - wing + (1 - k) * body, 0, w - edge, 0)
        + " L " + edge + " 0"
        + c(wing - (1 - k) * body, 0, wing - (1 - k) * wing, h, 0, h) + " Z"
    if (root.wideEdge === "left")
      return "M -1 0 L -1 " + h + " L 0 " + h
        + c(0, h - k * wing, w, h - wing + (1 - k) * body, w, h - edge)
        + " L " + w + " " + edge
        + c(w, wing - (1 - k) * body, 0, wing - (1 - k) * wing, 0, 0) + " Z"
    if (root.wideEdge === "right")
      return "M " + (w + 1) + " 0 L " + (w + 1) + " " + h + " L " + w + " " + h
        + c(w, h - k * wing, 0, h - wing + (1 - k) * body, 0, h - edge)
        + " L 0 " + edge
        + c(0, wing - (1 - k) * body, w, wing - (1 - k) * wing, w, 0) + " Z"
    return "M 0 -1 L " + w + " -1 L " + w + " 0"
      + c(w - k * wing, 0, w - wing + (1 - k) * body, h, w - edge, h)
      + " L " + edge + " " + h
      + c(wing - (1 - k) * body, h, wing - (1 - k) * wing, 0, 0, 0) + " Z"
  }

  // Stroke the inner contour only. A stroke on the screen edge AA-blends
  // into the wallpaper and reads as a 1px gap.
  function strokeInner(ctx, w, h) {
    var m = notchMetrics(w, h)
    var k = m.k
    var wing = m.wing
    var body = m.body
    var edge = m.edge
    var inset = Math.max(0.5, root.borderWidth / 2)

    ctx.beginPath()
    if (root.wideEdge === "bottom") {
      ctx.moveTo(w - inset, h)
      ctx.bezierCurveTo(w - k * wing, h - inset, w - wing + (1 - k) * body, inset, w - edge, inset)
      ctx.lineTo(edge, inset)
      ctx.bezierCurveTo(wing - (1 - k) * body, inset, wing - (1 - k) * wing, h - inset, inset, h)
    } else if (root.wideEdge === "left") {
      ctx.moveTo(0, h - inset)
      ctx.bezierCurveTo(inset, h - k * wing, w - inset, h - wing + (1 - k) * body, w - inset, h - edge)
      ctx.lineTo(w - inset, edge)
      ctx.bezierCurveTo(w - inset, wing - (1 - k) * body, inset, wing - (1 - k) * wing, 0, inset)
    } else if (root.wideEdge === "right") {
      ctx.moveTo(w, h - inset)
      ctx.bezierCurveTo(w - inset, h - k * wing, inset, h - wing + (1 - k) * body, inset, h - edge)
      ctx.lineTo(inset, edge)
      ctx.bezierCurveTo(inset, wing - (1 - k) * body, w - inset, wing - (1 - k) * wing, w, inset)
    } else {
      ctx.moveTo(w - inset, 0)
      ctx.bezierCurveTo(w - k * wing, inset, w - wing + (1 - k) * body, h - inset, w - edge, h - inset)
      ctx.lineTo(edge, h - inset)
      ctx.bezierCurveTo(wing - (1 - k) * body, h - inset, wing - (1 - k) * wing, inset, inset, 0)
    }
    ctx.stroke()
  }

  Shape {
    anchors.fill: parent
    visible: root.gradientFill
    preferredRendererType: Shape.CurveRenderer

    ShapePath {
      strokeWidth: -1
      strokeColor: "transparent"
      fillGradient: LinearGradient {
        x1: 0
        y1: 0
        x2: root.horizontal ? root.width : 0
        y2: root.horizontal ? 0 : root.height
        GradientStop { position: 0; color: root.gradientStart }
        GradientStop { position: 0.5; color: root.gradientMid }
        GradientStop { position: 1; color: root.gradientEnd }
      }
      PathSvg { path: root.notchSvg(root.width, root.height) }
    }
  }

  Canvas {
    id: canvas
    anchors.fill: parent
    antialiasing: true
    contextType: "2d"
    renderTarget: Canvas.Image

    onPaint: {
      var ctx = getContext("2d")
      if (!ctx || root.width < 8 || root.height < 8)
        return

      ctx.reset()
      ctx.clearRect(0, 0, width, height)

      var fillA = root.unitAlpha(root.color)
      if (!root.gradientFill && fillA > 0.001) {
        ctx.globalAlpha = fillA
        ctx.fillStyle = root.rgbStyle(root.color)
        root.fillNotch(ctx, width, height)
      }

      var strokeA = root.unitAlpha(root.borderColor)
      if (root.borderWidth > 0 && strokeA > 0.001) {
        ctx.globalAlpha = strokeA
        ctx.strokeStyle = root.rgbStyle(root.borderColor)
        ctx.lineWidth = root.borderWidth
        ctx.lineJoin = "round"
        ctx.lineCap = "butt"
        root.strokeInner(ctx, width, height)
      }
    }
  }
}
