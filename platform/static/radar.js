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
  svg.setAttribute("aria-label", "Радар баллов без заливки секторов");

  var maxScore = 0;
  for (var i = 0; i < blocks.length; i += 1) {
    var score = Number(blocks[i].score);
    if (score > maxScore) {
      maxScore = score;
    }
  }
  if (maxScore <= 0) {
    maxScore = 1;
  }

  var step = (Math.PI * 2) / blocks.length;
  var points = [];
  for (var index = 0; index < blocks.length; index += 1) {
    var angle = -Math.PI / 2 + step * index;
    var value = Number(blocks[index].score);
    if (!isFinite(value) || value < 0) {
      value = 0;
    }
    var ratio = value / maxScore;
    var x = center + Math.cos(angle) * radius * ratio;
    var y = center + Math.sin(angle) * radius * ratio;
    points.push(x + "," + y);

    var axis = document.createElementNS(svg.namespaceURI, "line");
    axis.setAttribute("x1", String(center));
    axis.setAttribute("y1", String(center));
    axis.setAttribute("x2", String(center + Math.cos(angle) * radius));
    axis.setAttribute("y2", String(center + Math.sin(angle) * radius));
    axis.setAttribute("stroke", "#9aa0a6");
    svg.appendChild(axis);

    var mark = document.createElementNS(svg.namespaceURI, "circle");
    mark.setAttribute("cx", String(x));
    mark.setAttribute("cy", String(y));
    mark.setAttribute("r", "4");
    mark.setAttribute("fill", "#1f4e79");
    svg.appendChild(mark);

    var label = document.createElementNS(svg.namespaceURI, "text");
    label.setAttribute("x", String(center + Math.cos(angle) * (radius + 36)));
    label.setAttribute("y", String(center + Math.sin(angle) * (radius + 36)));
    label.setAttribute("text-anchor", "middle");
    label.setAttribute("fill", "#1c1c1c");
    label.textContent = blocks[index].code + ": " + blocks[index].score;
    svg.appendChild(label);
  }

  var shape = document.createElementNS(svg.namespaceURI, "polygon");
  shape.setAttribute("points", points.join(" "));
  shape.setAttribute("fill", "none");
  shape.setAttribute("stroke", "#1f4e79");
  shape.setAttribute("stroke-width", "2");
  svg.appendChild(shape);
  host.appendChild(svg);
})();
