(function () {
  var dataNode = document.getElementById("radar-data");
  var host = document.getElementById("radar-chart");
  if (!dataNode || !host) {
    return;
  }
  var snapshot = JSON.parse(dataNode.textContent);
  var blocks = snapshot && snapshot.blocks ? snapshot.blocks : [];
  if (!blocks.length) {
    return;
  }

  var size = 420;
  var center = size / 2;
  var radius = 130;
  var svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 " + size + " " + size);
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", "Радар баллов");

  var step = (Math.PI * 2) / blocks.length;
  var hasScale = false;
  for (var i = 0; i < blocks.length; i += 1) {
    if (blocks[i].chart_fill) {
      hasScale = true;
      break;
    }
  }

  if (hasScale) {
    var rings = [0.36, 0.51, 0.66, 0.85, 1];
    for (var ring = 0; ring < rings.length; ring += 1) {
      var guide = document.createElementNS(svg.namespaceURI, "circle");
      guide.setAttribute("cx", String(center));
      guide.setAttribute("cy", String(center));
      guide.setAttribute("r", String(radius * rings[ring]));
      guide.setAttribute("fill", "none");
      guide.setAttribute("stroke", "#e5e7eb");
      svg.appendChild(guide);
    }
  }

  for (var index = 0; index < blocks.length; index += 1) {
    var angle = -Math.PI / 2 + step * index;
    var block = blocks[index];
    var ratio = Number(block.chart_ratio);
    if (!isFinite(ratio) || ratio < 0) {
      ratio = 0;
    }
    if (ratio > 1) {
      ratio = 1;
    }

    var axis = document.createElementNS(svg.namespaceURI, "line");
    axis.setAttribute("x1", String(center));
    axis.setAttribute("y1", String(center));
    axis.setAttribute("x2", String(center + Math.cos(angle) * radius));
    axis.setAttribute("y2", String(center + Math.sin(angle) * radius));
    axis.setAttribute("stroke", "#c5cad3");
    svg.appendChild(axis);

    if (block.chart_fill && ratio > 0) {
      var reach = radius * ratio;
      if (blocks.length === 1) {
        var disk = document.createElementNS(svg.namespaceURI, "circle");
        disk.setAttribute("cx", String(center));
        disk.setAttribute("cy", String(center));
        disk.setAttribute("r", String(reach));
        disk.setAttribute("fill", block.chart_fill);
        svg.appendChild(disk);
      } else {
        var start = angle - step / 2;
        var end = angle + step / 2;
        var x0 = center + Math.cos(start) * reach;
        var y0 = center + Math.sin(start) * reach;
        var x1 = center + Math.cos(end) * reach;
        var y1 = center + Math.sin(end) * reach;
        var large = end - start > Math.PI ? 1 : 0;
        var path = document.createElementNS(svg.namespaceURI, "path");
        path.setAttribute(
          "d",
          "M " + center + " " + center +
            " L " + x0 + " " + y0 +
            " A " + reach + " " + reach + " 0 " + large + " 1 " + x1 + " " + y1 +
            " Z"
        );
        path.setAttribute("fill", block.chart_fill);
        path.setAttribute("stroke", "#ffffff");
        path.setAttribute("stroke-width", "1");
        svg.appendChild(path);
      }

      var mark = document.createElementNS(svg.namespaceURI, "circle");
      mark.setAttribute("cx", String(center + Math.cos(angle) * reach));
      mark.setAttribute("cy", String(center + Math.sin(angle) * reach));
      mark.setAttribute("r", "3.5");
      mark.setAttribute("fill", "#1c2430");
      svg.appendChild(mark);
    }

    var label = document.createElementNS(svg.namespaceURI, "text");
    label.setAttribute("x", String(center + Math.cos(angle) * (radius + 40)));
    label.setAttribute("y", String(center + Math.sin(angle) * (radius + 40)));
    label.setAttribute("text-anchor", "middle");
    label.setAttribute("fill", "#1c2430");
    label.setAttribute("font-size", "13");
    var score = block.score;
    label.textContent = score === null || score === "" ? block.code : block.code + ": " + score;
    svg.appendChild(label);
  }

  host.appendChild(svg);
})();
