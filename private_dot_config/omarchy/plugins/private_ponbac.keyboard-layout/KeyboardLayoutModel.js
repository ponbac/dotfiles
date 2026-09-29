// Label math for the keyboard layout widget, kept Qt-free so it can be unit
// tested under node (test/shell.d/keyboard-layout-test.sh).

// xkbcli list prints YAML, and every layout and variant block pairs a brief with
// the description hyprctl reports as the active keymap:
//
//   - layout: 'us'
//     variant: ''
//     brief: 'en'
//     description: English (US)
//
// The models and option groups it also prints carry no brief of their own, and
// a brief never carries past the block it was printed in, so neither reaches
// the table.
function layoutBriefs(text) {
  var briefs = {}
  var brief = ""

  String(text || "").split("\n").forEach(function (line) {
    if (/^\s*- /.test(line)) brief = ""

    var field = line.match(/^  (brief|description): (.*)$/)
    if (!field) return

    if (field[1] === "brief") {
      brief = field[2].replace(/^'|'$/g, "")
    } else if (brief) {
      briefs[field[2]] = brief
      brief = ""
    }
  })

  return briefs
}

// The brief is a short language code rather than a country one, which keeps the
// label sensible for the layouts named after a language: Esperanto reads EO and
// Arabic reads AR. It is the same code GNOME shows in its own indicator.
//
// Layouts missing from the table fall back to the first word of the description,
// which reads as ENG/POR but at least says something.
//
// Nearly every brief is a bare two-letter code, but a few tack a script onto it
// (Burmese (Zawgyi) is my-zwg) and the custom layout's is a word, so drop the
// script and cap the result at the same three characters the fallback gets.
// The widget sits between fixed neighbours on the bar and has no room to grow.
function shortLabel(description, briefs) {
  if (!description) return ""

  // A description like "constructor" reaches an inherited member rather than a
  // brief, so take the lookup only when it hands back the string it promises.
  var brief = (briefs || {})[description]
  var label = typeof brief === "string" && brief ? brief.split("-")[0] : description.split(/\s+/)[0]
  return label.substring(0, 3).toUpperCase()
}

// Hyprland's activelayout event pairs the keyboard that switched with the layout
// it moved to. Quickshell cuts the event into that many fields, so a description
// carrying a comma of its own stays in one piece; a binding old enough to hand
// back only the raw string gets split by hand. The virtual keyboard fcitx5 binds
// to inject announces switches too, and names a keyboard nobody types on.
function eventKeyboardName(event) {
  var parts

  try {
    if (event && event.parse) parts = event.parse(2)
  } catch (error) {
  }

  if (!parts) parts = String(event && event.data ? event.data : "").split(",")

  var name = String(parts[0] || "")
  return name.indexOf("hl-virtual-keyboard") === 0 ? "" : name
}

// Hyprland reports more than keyboards as keyboards. fcitx5 binds a virtual one
// to inject through, which keeps the us layout the input method gave it, and the
// ACPI power button, lid switch and sleep key each arrive carrying the seat's
// layout list without anyone ever typing on them. Both answer to switchxkblayout
// and both can hold the main flag, so a widget that reads or switches whatever
// the seat hands it ends up describing a button. Leave them out and what remains
// is keyboards, which is what the rest of this file can then assume.
//
// Missing a name here costs the accuracy the seat had before, never a keyboard:
// anything unrecognised stays in the list.
var UNTYPED_KEYBOARDS = /^(hl-virtual-keyboard|power-button|sleep-button|lid-switch|video-bus)/

function isTypedKeyboard(name) {
  return !UNTYPED_KEYBOARDS.test(String(name || ""))
}

// Every keyboard on the seat carries the same layout list unless one was given
// its own, but only the one being typed on advances through it. So the
// furthest-advanced is the one worth reading, and a switch names the keyboard it
// moved, which settles a seat holding two real keyboards outright.
//
// The name is taken whenever a keyboard still answers to it, wherever that
// keyboard sits in the list. Comparing positions instead would read the wrong
// keyboard the moment one wrapped from the last layout back to the first, which
// is the ordinary way round a pair of them. Applying a layout to the whole seat
// names a keyboard too, but leaves every one of them on the same layout, so the
// label reads the same whichever of them the name settles on.
function selectKeyboard(typed, namedByEvent) {
  var keyboards = typed || []

  return keyboards.find(function (keyboard) {
    return keyboard.name === namedByEvent
  }) || keyboards.reduce(function (furthest, keyboard) {
    return layoutIndex(keyboard) > layoutIndex(furthest) ? keyboard : furthest
  }, keyboards[0])
}

function layoutIndex(keyboard) {
  return (keyboard && keyboard.active_layout_index) || 0
}

// The xkb layout code ("us", "se") the keyboard is on, read from its layout
// list by the active index. Descriptions vary by variant, the code does not.
function layoutCode(keyboard) {
  if (!keyboard || keyboard.layout === undefined) return ""
  var codes = String(keyboard.layout).split(",")
  return String(codes[layoutIndex(keyboard)] || "").trim()
}

// Muted flag dots, drawn in a 20x20 box inside a circle. The real colours are
// pulled toward grey so the dot sits quietly beside the monochrome icons, with
// the white parts in the bar's foreground so it follows the theme.
//
// The US flag is cut down to seven bands and a plain canton. Each band is a
// seventh of the box, which is 2 device pixels at the 13px dot on a 1.0667x
// output, so every stripe edge lands on a pixel boundary instead of blurring.
//
// Qt's SVG renderer ignores clipPath, so every rectangle is clipped to the
// circle here and emitted as a polygon instead.
var FLAG_TINTS = { blue: "#4a6a8f", red: "#8f5a5a", yellow: "#e6d9a8" }
var US_BAND = 20 / 7

var FLAG_RECTS = {
  se: function (light) {
    return [
      [FLAG_TINTS.blue, 0, 0, 20, 20],
      [FLAG_TINTS.yellow, 5.6, 0, 9, 20],
      [FLAG_TINTS.yellow, 0, 8.3, 20, 11.7]
    ]
  },
  us: function (light) {
    return [[light, 0, 0, 20, 20]].concat([0, 2, 4, 6].map(function (i) {
      return [FLAG_TINTS.red, 0, i * US_BAND, 20, (i + 1) * US_BAND]
    }), [[FLAG_TINTS.blue, 0, 0, 10, 3 * US_BAND]])
  }
}

function circlePolygon() {
  var points = []
  for (var i = 0; i < 64; i++) {
    var a = (i / 64) * 2 * Math.PI
    points.push([10 + 10 * Math.cos(a), 10 + 10 * Math.sin(a)])
  }
  return points
}

// Sutherland-Hodgman against each side of an axis-aligned rectangle.
function clipToRect(points, x0, y0, x1, y1) {
  var edges = [
    [function (p) { return p[0] >= x0 }, function (p, q) { return [x0, p[1] + (q[1] - p[1]) * (x0 - p[0]) / (q[0] - p[0])] }],
    [function (p) { return p[0] <= x1 }, function (p, q) { return [x1, p[1] + (q[1] - p[1]) * (x1 - p[0]) / (q[0] - p[0])] }],
    [function (p) { return p[1] >= y0 }, function (p, q) { return [p[0] + (q[0] - p[0]) * (y0 - p[1]) / (q[1] - p[1]), y0] }],
    [function (p) { return p[1] <= y1 }, function (p, q) { return [p[0] + (q[0] - p[0]) * (y1 - p[1]) / (q[1] - p[1]), y1] }]
  ]

  edges.forEach(function (edge) {
    var inside = edge[0], cross = edge[1], out = []
    points.forEach(function (p, i) {
      var prev = points[(i + points.length - 1) % points.length]
      if (inside(p)) {
        if (!inside(prev)) out.push(cross(prev, p))
        out.push(p)
      } else if (inside(prev)) {
        out.push(cross(prev, p))
      }
    })
    points = out
  })

  return points
}

function hasFlag(code) {
  return Object.prototype.hasOwnProperty.call(FLAG_RECTS, code)
}

// A data URL for the flag, with a translucent rim in the foreground colour to
// keep the edge crisp on light wallpapers. Empty for layouts without a flag.
function flagSvg(code, foreground) {
  if (!hasFlag(code)) return ""
  var light = foreground || "#e6e6e6"
  var circle = circlePolygon()
  var shapes = FLAG_RECTS[code](light).map(function (r) {
    var points = clipToRect(circle, r[1], r[2], r[3], r[4])
    return '<polygon fill="' + r[0] + '" points="' + points.map(function (p) {
      return p[0].toFixed(2) + "," + p[1].toFixed(2)
    }).join(" ") + '"/>'
  }).join("")
  var svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20">' + shapes +
    '<circle cx="10" cy="10" r="9.35" fill="none" stroke="' + light + '" stroke-opacity=".45" stroke-width="1.3"/>' +
    '</svg>'
  return "data:image/svg+xml;utf8," + encodeURIComponent(svg)
}

if (typeof module !== "undefined") {
  module.exports = {
    eventKeyboardName: eventKeyboardName,
    flagSvg: flagSvg,
    hasFlag: hasFlag,
    isTypedKeyboard: isTypedKeyboard,
    layoutBriefs: layoutBriefs,
    layoutCode: layoutCode,
    selectKeyboard: selectKeyboard,
    shortLabel: shortLabel
  }
}
