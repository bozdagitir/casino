const SUIT_SYMBOL = { S: "♠", H: "♥", D: "♦", C: "♣" };
const RED_SUITS = new Set(["H", "D"]);

let state = null;
let selectedHand = new Set();
let selectedTable = new Set();

function parseCard(card) {
  const suit = card.slice(-1);
  const rank = card.slice(0, -1);
  return { rank, suit };
}

function cardEl(card, { selected, kind, onClick } = {}) {
  const { rank, suit } = parseCard(card);
  const el = document.createElement("div");
  el.className = "card" + (RED_SUITS.has(suit) ? " red" : "");
  if (selected) el.classList.add("selected");
  if (!onClick) el.classList.add("static");
  el.innerHTML = `<div class="rank">${rank}</div><div class="suit">${SUIT_SYMBOL[suit]}</div>`;
  if (onClick) el.addEventListener("click", onClick);
  return el;
}

function backEl() {
  const el = document.createElement("div");
  el.className = "card back";
  return el;
}

function setsEqual(a, b) {
  if (a.size !== b.size) return false;
  for (const x of a) if (!b.has(x)) return false;
  return true;
}

function findMatchingMove() {
  if (!state || !state.moves) return null;
  return state.moves.find(
    (m) => setsEqual(new Set(m.hand), selectedHand) && setsEqual(new Set(m.table), selectedTable)
  );
}

function render() {
  if (!state) return;

  document.getElementById("message").textContent = state.message || "";
  document.getElementById("sweeps").textContent =
    `Sweeps — you: ${state.sweeps.you}, computer: ${state.sweeps.computer}`;
  document.getElementById("talonCount").textContent = state.talonCount;
  document.getElementById("computerCount").textContent = `(${state.computerCount} cards)`;
  document.getElementById("computerPile").textContent = `${state.piles.computer.length} cards`;
  document.getElementById("playerPile").textContent = `Pile: ${state.piles.you.length} cards`;

  const computerHandEl = document.getElementById("computerHand");
  computerHandEl.innerHTML = "";
  if (state.computerHand) {
    state.computerHand.forEach((c) => computerHandEl.appendChild(cardEl(c)));
  } else {
    for (let i = 0; i < state.computerCount; i++) computerHandEl.appendChild(backEl());
  }

  const tableEl = document.getElementById("table");
  tableEl.innerHTML = "";
  state.table.forEach((c) => {
    const clickable = state.yourTurn ? () => toggleTable(c) : null;
    tableEl.appendChild(cardEl(c, { selected: selectedTable.has(c), onClick: clickable }));
  });

  const handEl = document.getElementById("hand");
  handEl.innerHTML = "";
  state.hand.forEach((c) => {
    const clickable = state.yourTurn ? () => toggleHand(c) : null;
    handEl.appendChild(cardEl(c, { selected: selectedHand.has(c), onClick: clickable }));
  });

  const move = findMatchingMove();
  document.getElementById("playMove").disabled = !move;

  let hint;
  if (state.dealOver) {
    hint = `Deal over — you: ${state.score.you}, computer: ${state.score.computer}.`;
  } else if (!state.yourTurn) {
    hint = "Computer is thinking...";
  } else if (move) {
    hint = move.table.length
      ? `Ready: play ${move.hand.join(", ")} and take ${move.table.join(", ")}.`
      : `Ready: place ${move.hand.join(", ")} on the table.`;
  } else if (selectedHand.size === 0) {
    hint = "Select one or more cards from your hand, and — optionally — table cards whose values add up to the same total, then press Play.";
  } else {
    hint = "That combination isn't a legal move yet. Adjust your selection.";
  }
  document.getElementById("hint").textContent = hint;
}

function toggleHand(card) {
  if (selectedHand.has(card)) selectedHand.delete(card);
  else selectedHand.add(card);
  render();
}

function toggleTable(card) {
  if (selectedTable.has(card)) selectedTable.delete(card);
  else selectedTable.add(card);
  render();
}

function clearSelection() {
  selectedHand = new Set();
  selectedTable = new Set();
  render();
}

function showError(text) {
  document.getElementById("message").textContent = text;
}

async function request(path, options) {
  let res;
  try {
    res = await fetch(path, options);
  } catch (err) {
    showError("Couldn't reach the server. Check your connection and try again.");
    return null;
  }
  let data;
  try {
    data = await res.json();
  } catch (err) {
    showError("The server sent back something unexpected.");
    return null;
  }
  if (!res.ok) {
    const errorText = data.error || "That move was rejected.";
    await fetchState();
    showError(`${errorText} The board has been re-synced.`);
    return null;
  }
  return data;
}

async function fetchState() {
  const data = await request("/api/state");
  if (!data) return;
  state = data;
  clearSelection();
}

async function newDeal() {
  const data = await request("/api/new", { method: "POST" });
  if (!data) return;
  state = data;
  clearSelection();
}

let submitting = false;

async function playMove() {
  if (submitting) return;
  const move = findMatchingMove();
  if (!move) return;
  submitting = true;
  document.getElementById("playMove").disabled = true;
  try {
    const data = await request("/api/move", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(move),
    });
    if (!data) return;
    state = data;
    clearSelection();
  } finally {
    submitting = false;
  }
}

document.getElementById("newDeal").addEventListener("click", newDeal);
document.getElementById("clearSelection").addEventListener("click", clearSelection);
document.getElementById("playMove").addEventListener("click", playMove);

fetchState();
