// A large, natural-moving pointer for agent-browser videos.
//
// Loaded into every page through ~/.agent-browser/config.json, but it shows only while
// `agent-browser record start <file> --cursor` runs: it waits for agent-browser's own small
// recording pointer to appear, hides it, and draws this one instead. Screenshots taken
// outside a recording never contain it.
//
// Movement and press feel follow Playwriter's ghost cursor (MIT, github.com/remorses/playwriter):
// the pointer glides at a speed set by distance with ease-in-out, and a press is a short
// scale with a strong ease-out. The pointer artwork is its Screen Studio macOS pointer. Unlike
// Playwriter, a press waits until the pointer has arrived, so the click never lands before the
// pointer, and every click leaves a ripple.
//
// Real input (`click`, `hover`, `mouse move`, drags) drives it. A script's `element.click()`
// sends no pointer events, so the pointer glides to that element afterwards; prefer real input.
(() => {
	let isTop = false;
	try {
		isTop = window.top === window;
	} catch {}
	if (!isTop || window.__bigRecordingCursor) return;
	window.__bigRecordingCursor = true;

	const HEIGHT = 60; // CSS px; 120 device px in a 2x recording.
	const WIDTH = Math.round((HEIGHT * 618) / 958);
	const HOTSPOT_X = Math.round(WIDTH * 0.14);
	const HOTSPOT_Y = Math.round(HEIGHT * 0.06);
	const MOVE_EASING = "cubic-bezier(0.65, 0, 0.35, 1)"; // ease-in-out cubic
	const PRESS_EASING = "cubic-bezier(0.23, 1, 0.32, 1)"; // strong ease-out
	const PRESS_MS = 140;
	const SPEED_PX_PER_MS = 1.2;
	const MIN_MOVE_MS = 220;
	const MAX_MOVE_MS = 1200;
	const BUILT_IN = "agent-browser-recording-cursor";

	const host = document.createElement("big-recording-cursor");
	host.setAttribute("aria-hidden", "true");
	host.inert = true;
	host.style.cssText =
		"all: initial !important; position: fixed !important; inset: 0 !important; z-index: 2147483647 !important; pointer-events: none !important; display: none !important;";
	const root = host.attachShadow({ mode: "closed" });
	root.innerHTML = `
		<style>
			.move {
				position: fixed; left: 0; top: 0; will-change: transform;
				transition-property: transform; transition-timing-function: ${MOVE_EASING};
			}
			.press {
				width: ${WIDTH}px; height: ${HEIGHT}px; transform-origin: ${HOTSPOT_X}px ${HOTSPOT_Y}px;
				transition: transform ${PRESS_MS}ms ${PRESS_EASING};
			}
			.press svg { display: block; width: 100%; height: 100%; }
			.ripple {
				position: fixed; left: 0; top: 0; width: 72px; height: 72px; margin: -36px 0 0 -36px;
				border-radius: 50%; box-sizing: border-box; border: 4px solid rgb(37 99 235);
				background: rgb(59 130 246 / 0.3);
				animation: ripple 650ms ${PRESS_EASING} forwards;
			}
			@keyframes ripple {
				from { transform: var(--at) scale(0.25); opacity: 1; }
				to { transform: var(--at) scale(1); opacity: 0; }
			}
		</style>
		<div class="move"><div class="press"><svg width="618" height="958" viewBox="0 0 618 958" fill="none" xmlns="http://www.w3.org/2000/svg"><g filter="url(#filter0_d_384_27)"><path fill-rule="evenodd" clip-rule="evenodd" d="M127.062 37.0331L540.696 451.555C592.653 503.66 555.794 592.574 482.226 592.574L421.831 592.569L481.821 735.054C492.331 760.021 492.479 787.652 482.265 812.767C472.002 837.932 452.561 857.57 427.496 868.08C414.864 873.359 401.64 876.024 388.121 876.024C347.117 876.024 310.358 851.6 294.47 813.804L231.42 663.918L190.368 700.337C137.029 747.508 53 709.663 53 638.413V67.6744C53 28.9903 99.7268 9.64828 127.062 37.0331Z" fill="white"/><path fill-rule="evenodd" clip-rule="evenodd" d="M102.316 99.652C102.316 93.1882 110.162 89.9316 114.701 94.5204L504.897 485.555C526.164 506.871 511.065 543.236 480.967 543.236L347.546 543.161L436.342 754.143C447.542 780.788 435.009 811.429 408.414 822.581C381.72 833.781 351.128 821.298 339.977 794.702L250.293 581.352L158.517 662.644C137.991 680.801 106.319 668.145 102.664 642.323L102.316 637.331V99.652Z" fill="black"/></g><defs><filter id="filter0_d_384_27" x="0.34" y="0.799219" width="617.32" height="957.144" filterUnits="userSpaceOnUse" color-interpolation-filters="sRGB"><feFlood flood-opacity="0" result="BackgroundImageFix"/><feColorMatrix in="SourceAlpha" type="matrix" values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 127 0" result="hardAlpha"/><feOffset dy="29.26"/><feGaussianBlur stdDeviation="26.33"/><feComposite in2="hardAlpha" operator="out"/><feColorMatrix type="matrix" values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0.65 0"/><feBlend mode="normal" in2="BackgroundImageFix" result="effect1_dropShadow_384_27"/><feBlend mode="normal" in="SourceGraphic" in2="effect1_dropShadow_384_27" result="shape"/></filter></defs></svg></div></div>`;
	const move = root.querySelector(".move");
	const press = root.querySelector(".press");

	let x = innerWidth / 2;
	let y = innerHeight / 2;
	let arrivesAt = 0;
	let shown = false;

	const glide = (toX, toY) => {
		const distance = Math.hypot(toX - x, toY - y);
		// The first position after appearing is a jump, not a slide from the centre.
		const ms = shown && distance > 0 ? Math.min(MAX_MOVE_MS, Math.max(MIN_MOVE_MS, distance / SPEED_PX_PER_MS)) : 0;
		x = toX;
		y = toY;
		move.style.transitionDuration = `${Math.round(ms)}ms`;
		move.style.transform = `translate3d(${x - HOTSPOT_X}px, ${y - HOTSPOT_Y}px, 0)`;
		arrivesAt = performance.now() + ms;
	};
	glide(x, y);

	// Presses play once the pointer has arrived, in order.
	let pressQueue = Promise.resolve();
	const whenArrived = (effect) => {
		pressQueue = pressQueue.then(
			() =>
				new Promise((resolve) => {
					setTimeout(() => {
						effect();
						resolve();
					}, Math.max(0, arrivesAt - performance.now()));
				}),
		);
	};
	const ripple = () => {
		const ring = document.createElement("div");
		ring.className = "ripple";
		ring.style.setProperty("--at", `translate(${x}px, ${y}px)`);
		ring.addEventListener("animationend", () => ring.remove());
		root.append(ring);
	};
	const down = () =>
		whenArrived(() => {
			press.style.transform = "scale(0.82)";
			ripple();
		});
	const up = () =>
		whenArrived(
			() => new Promise((resolve) => setTimeout(resolve, PRESS_MS)).then(() => (press.style.transform = "scale(1)")),
		);

	const options = { capture: true, passive: true };
	addEventListener("pointermove", (event) => glide(event.clientX, event.clientY), options);
	addEventListener("pointerdown", (event) => {
		glide(event.clientX, event.clientY);
		down();
	}, options);
	addEventListener("pointerup", up, options);
	addEventListener("click", (event) => {
		if (event.isTrusted || !(event.target instanceof Element)) return;
		const box = event.target.getBoundingClientRect();
		glide(box.left + box.width / 2, box.top + box.height / 2);
		down();
		up();
	}, options);

	// Show only while agent-browser records with --cursor, and stay on top of the page.
	// agent-browser puts its pointer directly under <html>, so only <html>'s children are watched.
	const watched = new WeakSet();
	const sync = () => {
		const html = document.documentElement;
		if (!html) return;
		if (!watched.has(html)) {
			watched.add(html);
			observer.observe(html, { childList: true });
		}
		const builtIn = html.querySelector(`:scope > ${BUILT_IN}`);
		if (builtIn) builtIn.style.setProperty("visibility", "hidden", "important");
		shown = builtIn !== null;
		host.style.setProperty("display", shown ? "block" : "none", "important");
		if (shown && html.lastElementChild !== host) html.append(host);
	};
	const observer = new MutationObserver(sync);
	observer.observe(document, { childList: true });
	sync();
})();
