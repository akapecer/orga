(function () {
  "use strict";

  var balloonEl = null;
  var balloonTimer = null;

  function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
  }

  function setDynamicHeight(selectEl, optionCount, rowPx, minVh, maxVh) {
    if (!selectEl) return;
    var rows = clamp(optionCount + 2, 8, 30);
    selectEl.size = rows;
    var pixels = clamp(rows * rowPx, window.innerHeight * minVh, window.innerHeight * maxVh);
    selectEl.style.setProperty("height", Math.round(pixels) + "px", "important");
    selectEl.style.setProperty("min-height", Math.round(pixels) + "px", "important");
  }

  function updateHeights() {
    // Desktop filter_horizontal selected box
    var chosen = document.getElementById("id_piatti_to");
    if (chosen) {
      setDynamicHeight(chosen, chosen.options.length, 30, 0.35, 0.8);
    }

    // Mobile fallback single multiple-select
    var fallback = document.getElementById("id_piatti");
    if (fallback) {
      var selectedCount = 0;
      for (var i = 0; i < fallback.options.length; i += 1) {
        if (fallback.options[i].selected) selectedCount += 1;
      }
      setDynamicHeight(fallback, Math.max(selectedCount, 8), 30, 0.35, 0.8);
    }
  }

  function ensureBalloon() {
    if (balloonEl) return balloonEl;
    balloonEl = document.createElement("div");
    balloonEl.className = "menu-option-balloon";
    balloonEl.setAttribute("aria-live", "polite");
    balloonEl.style.display = "none";
    document.body.appendChild(balloonEl);
    return balloonEl;
  }

  function showBalloon(message, anchorEl) {
    if (!message || !anchorEl) return;
    var el = ensureBalloon();
    el.textContent = message;
    el.style.display = "block";

    var rect = anchorEl.getBoundingClientRect();
    var maxWidth = Math.min(window.innerWidth - 24, 320);
    el.style.maxWidth = maxWidth + "px";

    var top = rect.top - el.offsetHeight - 10;
    if (top < 8) top = rect.bottom + 10;
    var left = rect.left + (rect.width / 2) - (el.offsetWidth / 2);
    left = Math.max(8, Math.min(left, window.innerWidth - el.offsetWidth - 8));

    el.style.top = Math.round(top) + "px";
    el.style.left = Math.round(left) + "px";

    if (balloonTimer) window.clearTimeout(balloonTimer);
    balloonTimer = window.setTimeout(function () {
      if (balloonEl) balloonEl.style.display = "none";
    }, 2200);
  }

  function onSelectInteract(selectEl) {
    if (!selectEl || !selectEl.options || selectEl.selectedIndex < 0) return;
    var opt = selectEl.options[selectEl.selectedIndex];
    if (!opt || !opt.text) return;
    showBalloon(opt.text.trim(), selectEl);
  }

  document.addEventListener("DOMContentLoaded", function () {
    updateHeights();

    document.addEventListener("change", function (event) {
      if (!event.target || event.target.tagName !== "SELECT") return;
      if (event.target.id === "id_piatti" || event.target.id === "id_piatti_to" || event.target.id === "id_piatti_from") {
        window.setTimeout(updateHeights, 50);
        onSelectInteract(event.target);
      }
    });

    document.addEventListener("click", function (event) {
      if (!event.target || event.target.tagName !== "OPTION") return;
      var parent = event.target.parentElement;
      if (!parent || parent.tagName !== "SELECT") return;
      if (parent.id === "id_piatti" || parent.id === "id_piatti_to") {
        window.setTimeout(function () { onSelectInteract(parent); }, 30);
      }
    });

    // Django filter_horizontal moves options via buttons/JS; poll briefly after load.
    var ticks = 0;
    var interval = window.setInterval(function () {
      updateHeights();
      ticks += 1;
      if (ticks > 20) window.clearInterval(interval);
    }, 300);
  });
})();
