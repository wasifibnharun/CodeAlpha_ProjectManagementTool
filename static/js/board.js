(() => {
  const root = document.querySelector("[data-board-root]");
  if (!root) return;
  const csrf = document.querySelector(".csrf-holder input[name=csrfmiddlewaretoken]").value;
  let dragged = null;
  root.querySelectorAll("[draggable=true]").forEach((card) => {
    card.addEventListener("dragstart", () => { dragged = card; card.classList.add("dragging"); });
    card.addEventListener("dragend", () => card.classList.remove("dragging"));
  });
  root.querySelectorAll(".task-dropzone").forEach((zone) => {
    zone.addEventListener("dragover", (event) => { event.preventDefault(); zone.classList.add("drag-over"); if (dragged) zone.appendChild(dragged); });
    zone.addEventListener("dragleave", () => zone.classList.remove("drag-over"));
    zone.addEventListener("drop", async (event) => {
      event.preventDefault(); zone.classList.remove("drag-over");
      if (!dragged) return;
      const cards = [...zone.querySelectorAll(".task-card")];
      const response = await fetch(dragged.dataset.moveUrl, {method: "POST", headers: {"Content-Type": "application/json", "X-CSRFToken": csrf}, body: JSON.stringify({board_id: zone.closest("[data-board-id]").dataset.boardId, position: cards.indexOf(dragged)})});
      if (!response.ok) { window.location.reload(); return; }
      zone.querySelector(".column-empty")?.remove(); dragged = null;
    });
  });
})();
