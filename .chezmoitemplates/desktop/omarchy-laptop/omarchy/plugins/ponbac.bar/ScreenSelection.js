// Shared with QML; no shell commands, filesystem state, or fixed DP numbers.
function selectScreen(screens, monitors) {
    var candidates = [];
    var available = screens || [];
    var descriptions = monitors || [];
    for (var i = 0; i < available.length; i++) {
        var screen = available[i];
        if (!screen || !screen.name || screen.name === "FALLBACK"
                || !(screen.width > 0) || !(screen.height > 0)) continue;
        var description = "";
        for (var j = 0; j < descriptions.length; j++) {
            if (descriptions[j] && descriptions[j].name === screen.name) {
                description = String(descriptions[j].description || "");
                break;
            }
        }
        var rank = 3;
        if (description.indexOf("DELL U2717D") !== -1) rank = 0;
        else if (description.indexOf("DELL P2723QE") !== -1) rank = 1;
        else if (/^(eDP|LVDS|DSI)-/.test(screen.name)) rank = 2;
        candidates.push({ name: screen.name, rank: rank });
    }
    candidates.sort(function(a, b) {
        if (a.rank !== b.rank) return a.rank - b.rank;
        return a.name < b.name ? -1 : a.name > b.name ? 1 : 0;
    });
    return candidates.length ? candidates[0].name : "";
}
