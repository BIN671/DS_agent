'use strict';
// LAN client: rendering, websocket, lobby, chat.
// Depends on global Game/COLS/ROWS/COLORS/BLOCK from tetris.js
(function(){
const $ = function(id){ return document.getElementById(id); };
const connStatus = $('conn-status');
const lobby = $('lobby'), gameSection = $('game');
const roomCard = $('room-card'), roomNameEl = $('room-name');
const playersList = $('players-list'), btnStart = $('btn-start');
const inName = $('in-name'), inRoom = $('in-room'), inServer = $('in-server');
const btnConnect = $('btn-connect'), btnSolo = $('btn-solo');
const canvasMain = $('canvas-main'), ctxMain = canvasMain.getContext('2d');
const canvasNext = $('canvas-next'), ctxNext = canvasNext.getContext('2d');
const scoreEl = $('score'), linesEl = $('lines'), levelEl = $('level');
const overlay = $('overlay'), overlayText = overlay.querySelector('.overlay-text'), btnRestart = $('btn-restart');
const opponentsList = $('opponents-list');
const chatLog = $('chat-log'), chatForm = $('chat-form'), chatInput = $('chat-input');

const game = new Game();
let ws = null;
let myId = null;
let myName = 'Player';
let roomId = 'lobby';
let isHost = false;
let solo = false;
let opponents = {};
let running = false;
let lastTs = 0;
let netAccum = 0;

function setStatus(text, cls){ connStatus.textContent = text; connStatus.className = 'status ' + cls; }
function defaultServerUrl(){
  const p = location.protocol === 'https:' ? 'wss:' : 'ws:';
  return p + '//' + location.host;
}
if (location.host) inServer.value = defaultServerUrl();
const savedName = localStorage.getItem('tetris-name');
if (savedName) inName.value = savedName;

// ---------- Rendering ----------
function drawCell(ctx, x, y, color, size){
  ctx.fillStyle = color;
  ctx.fillRect(x*size, y*size, size, size);
  ctx.strokeStyle = 'rgba(0,0,0,0.35)';
  ctx.lineWidth = 1;
  ctx.strokeRect(x*size + 0.5, y*size + 0.5, size-1, size-1);
  ctx.fillStyle = 'rgba(255,255,255,0.18)';
  ctx.fillRect(x*size+2, y*size+2, size-4, 3);
}
function drawBoard(ctx, board, piece, blockSize){
  ctx.fillStyle = '#05080f';
  ctx.fillRect(0,0,COLS*blockSize, ROWS*blockSize);
  ctx.strokeStyle = 'rgba(255,255,255,0.04)';
  ctx.lineWidth = 1;
  for (let x=1;x<COLS;x++){ ctx.beginPath(); ctx.moveTo(x*blockSize+0.5,0); ctx.lineTo(x*blockSize+0.5, ROWS*blockSize); ctx.stroke(); }
  for (let y=1;y<ROWS;y++){ ctx.beginPath(); ctx.moveTo(0, y*blockSize+0.5); ctx.lineTo(COLS*blockSize, y*blockSize+0.5); ctx.stroke(); }
  for (let y=0;y<ROWS;y++) for (let x=0;x<COLS;x++){
    if (board[y] && board[y][x]) drawCell(ctx, x, y, COLORS[board[y][x]] || '#888', blockSize);
  }
  if (piece && piece.matrix){
    const test = { matrix: piece.matrix, x: piece.x, y: piece.y };
    while (true){
      let canDown = true;
      for (let yy=0; yy<test.matrix.length; yy++) for (let xx=0; xx<test.matrix[yy].length; xx++){
        if (!test.matrix[yy][xx]) continue;
        const ny = test.y + yy + 1, nx = test.x + xx;
        if (ny >= ROWS) { canDown = false; break; }
        if (ny >= 0 && board[ny] && board[ny][nx]) { canDown = false; break; }
      }
      if (!canDown) break;
      test.y++;
    }
    const ghostY = test.y;
    ctx.globalAlpha = 0.22;
    for (let y=0;y<piece.matrix.length;y++) for (let x=0;x<piece.matrix[y].length;x++){
      if (piece.matrix[y][x]){
        const gy = ghostY + y; if (gy < 0) continue;
        drawCell(ctx, piece.x + x, gy, COLORS[piece.matrix[y][x]] || '#888', blockSize);
      }
    }
    ctx.globalAlpha = 1;
    for (let y=0;y<piece.matrix.length;y++) for (let x=0;x<piece.matrix[y].length;x++){
      if (piece.matrix[y][x]){
        const py = piece.y + y; if (py < 0) continue;
        drawCell(ctx, piece.x + x, py, COLORS[piece.matrix[y][x]] || '#888', blockSize);
      }
    }
  }
}
function drawNext(){
  ctxNext.fillStyle = '#05080f';
  ctxNext.fillRect(0,0,canvasNext.width,canvasNext.height);
  if (!game.next) return;
  const m = game.next.matrix;
  const size = 24;
  const offX = (canvasNext.width - m[0].length*size)/2;
  const offY = (canvasNext.height - m.length*size)/2;
  for (let y=0;y<m.length;y++) for (let x=0;x<m[y].length;x++){
    if (m[y][x]){
      ctxNext.fillStyle = COLORS[m[y][x]] || '#888';
      ctxNext.fillRect(offX + x*size, offY + y*size, size, size);
      ctxNext.strokeStyle = 'rgba(0,0,0,0.35)';
      ctxNext.strokeRect(offX + x*size + 0.5, offY + y*size + 0.5, size-1, size-1);
    }
  }
}
function drawOpponents(){
  const ids = Object.keys(opponents);
  if (ids.length === 0){
    opponentsList.innerHTML = '<p class="hint">Нет соперников — ждём игроков…</p>';
    return;
  }
  if (opponentsList.dataset.signature !== ids.join(',')){
    opponentsList.innerHTML = '';
    opponentsList.dataset.signature = ids.join(',');
    ids.forEach(function(id){
      const op = opponents[id];
      const div = document.createElement('div');
      div.className = 'opponent';
      div.id = 'opp-' + id;
      const title = document.createElement('div');
      title.textContent = op.name || ('#' + id);
      const c = document.createElement('canvas');
      c.width = 100; c.height = 200;
      const sc = document.createElement('div');
      sc.className = 'op-score';
      sc.textContent = '0';
      div.appendChild(title); div.appendChild(c); div.appendChild(sc);
      opponentsList.appendChild(div);
    });
  }
  ids.forEach(function(id){
    const op = opponents[id];
    const div = document.getElementById('opp-' + id);
    if (!div) return;
    const c = div.querySelector('canvas');
    const ctx = c.getContext('2d');
    ctx.fillStyle = '#05080f';
    ctx.fillRect(0,0,c.width,c.height);
    if (op.board){
      const bs = c.width / COLS;
      for (let y=0;y<ROWS;y++) for (let x=0;x<COLS;x++){
        if (op.board[y] && op.board[y][x]){
          ctx.fillStyle = COLORS[op.board[y][x]] || '#888';
          ctx.fillRect(x*bs, y*bs, bs, bs);
        }
      }
    }
    div.querySelector('.op-score').textContent = op.score || 0;
    div.classList.toggle('dead', op.alive === false);
  });
}
function updateHud(){
  scoreEl.textContent = game.score;
  linesEl.textContent = game.lines;
  levelEl.textContent = game.level;
}
function render(){
  drawBoard(ctxMain, game.board, game.piece, BLOCK);
  drawNext();
  updateHud();
  drawOpponents();
}

// ---------- Loop ----------
function loop(ts){
  if (!running) return;
  if (!lastTs) lastTs = ts;
  const dt = ts - lastTs;
  lastTs = ts;
  if (game.started && game.alive && !game.paused){
    game.dropCounter += dt;
    if (game.dropCounter > game.dropInterval) game.drop();
  }
  render();
  netAccum += dt;
  if (netAccum > 200 && ws && ws.readyState === 1 && game.started){
    netAccum = 0;
    sendState();
  }
  requestAnimationFrame(loop);
}
function startLoop(){
  if (running) return;
  running = true; lastTs = 0;
  requestAnimationFrame(loop);
}

// ---------- Networking ----------
function sendState(){
  if (!ws || ws.readyState !== 1) return;
  ws.send(JSON.stringify({
    type: 'state',
    board: game.board,
    score: game.score,
    lines: game.lines,
    level: game.level,
    alive: game.alive
  }));
}
function connect(serverUrl, name, room){
  if (ws) { try { ws.close(); } catch(e){} ws = null; }
  myName = name || 'Player';
  roomId = room || 'lobby';
  setStatus('connecting…', 'connecting');
  try { ws = new WebSocket(serverUrl); }
  catch(e){ setStatus('offline', 'offline'); alert('Неверный адрес сервера'); return; }
  ws.onopen = function(){
    setStatus('online', 'online');
    ws.send(JSON.stringify({ type: 'join', name: myName, room: roomId }));
  };
  ws.onclose = function(){
    setStatus('offline', 'offline');
    if (running && !solo){ game.paused = true; showOverlay('Соединение потеряно'); }
  };
  ws.onerror = function(){ setStatus('offline', 'offline'); };
  ws.onmessage = function(ev){
    let m; try { m = JSON.parse(ev.data); } catch(e){ return; }
    handleMessage(m);
  };
}
function handleMessage(m){
  if (m.type === 'welcome'){
    myId = m.id;
    if (m.name) myName = m.name;
  } else if (m.type === 'room'){
    isHost = (m.hostId === myId);
    roomNameEl.textContent = m.roomId;
    playersList.innerHTML = '';
    m.players.forEach(function(p){
      const li = document.createElement('li');
      let who = p.name + (p.id === m.hostId ? ' ★' : '');
      if (p.id === myId) who += ' (you)';
      li.innerHTML = '<span>' + escapeHtml(who) + '</span><span>' + (p.alive ? 'alive' : 'dead') + '</span>';
      playersList.appendChild(li);
    });
    btnStart.disabled = !(isHost && m.players.length >= 1);
    roomCard.hidden = false;
  } else if (m.type === 'start'){
    startGame(false);
  } else if (m.type === 'state'){
    if (m.id === myId) return;
    const op = opponents[m.id] || {};
    op.name = m.name;
    op.board = m.board;
    op.score = m.score;
    op.alive = m.alive;
    opponents[m.id] = op;
  } else if (m.type === 'gameover'){
    if (m.id === myId) return;
    if (opponents[m.id]) opponents[m.id].alive = false;
  } else if (m.type === 'winner'){
    if (m.id === myId) showOverlay('🏆 Победа!');
    else if (m.name) showOverlay('Победитель: ' + m.name);
    else showOverlay('Игра окончена');
  } else if (m.type === 'chat'){
    const line = document.createElement('div');
    if (m.system){
      line.className = 'system';
      line.textContent = m.text;
    } else {
      const from = document.createElement('span');
      from.className = 'from'; from.textContent = (m.from || '?') + ': ';
      const txt = document.createElement('span'); txt.textContent = m.text;
      line.appendChild(from); line.appendChild(txt);
    }
    chatLog.appendChild(line);
    chatLog.scrollTop = chatLog.scrollHeight;
  }
}
function escapeHtml(s){ return String(s).replace(/[&<>"']/g, function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]; }); }

// ---------- Game flow ----------
function startGame(alone){
  solo = !!alone;
  opponents = {};
  opponentsList.innerHTML = '';
  opponentsList.dataset.signature = '';
  lobby.hidden = true;
  gameSection.hidden = false;
  overlay.hidden = true;
  game.reset();
  game.onGameOver = function(){
    if (ws && ws.readyState === 1 && !solo) ws.send(JSON.stringify({ type: 'gameover' }));
    if (solo) showOverlay('Игра окончена');
  };
  game.started = true;
  startLoop();
}
function showOverlay(text){
  overlayText.textContent = text;
  overlay.hidden = false;
}
btnRestart.addEventListener('click', function(){
  overlay.hidden = true;
  if (solo || isHost){
    startGame(solo);
    if (!solo && ws && ws.readyState === 1) ws.send(JSON.stringify({ type: 'start' }));
  } else if (ws && ws.readyState === 1) {
    overlayText.textContent = 'Ожидание хоста…';
    overlay.hidden = false;
  }
});

// ---------- Lobby handlers ----------
btnConnect.addEventListener('click', function(){
  const name = inName.value.trim() || 'Player';
  localStorage.setItem('tetris-name', name);
  const room = inRoom.value.trim() || 'lobby';
  const url = inServer.value.trim() || defaultServerUrl();
  connect(url, name, room);
});
btnSolo.addEventListener('click', function(){ startGame(true); });
btnStart.addEventListener('click', function(){
  if (!ws || ws.readyState !== 1) return;
  ws.send(JSON.stringify({ type: 'start' }));
});

// ---------- Chat ----------
chatForm.addEventListener('submit', function(e){
  e.preventDefault();
  const t = chatInput.value.trim();
  if (!t) return;
  chatInput.value = '';
  if (ws && ws.readyState === 1) ws.send(JSON.stringify({ type: 'chat', text: t }));
});

// ---------- Keyboard ----------
window.addEventListener('keydown', function(e){
  if (gameSection.hidden) return;
  if (e.target && (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA')) return;
  const k = e.key;
  if (k === 'ArrowLeft' || k === 'a' || k === 'A'){ game.move(-1); e.preventDefault(); }
  else if (k === 'ArrowRight' || k === 'd' || k === 'D'){ game.move(1); e.preventDefault(); }
  else if (k === 'ArrowDown' || k === 's' || k === 'S'){ game.drop(); e.preventDefault(); }
  else if (k === 'ArrowUp' || k === 'x' || k === 'X' || k === 'w' || k === 'W'){ game.rotate(); e.preventDefault(); }
  else if (k === ' '){ game.hardDrop(); e.preventDefault(); }
  else if (k === 'p' || k === 'P' || k === 'Escape'){
    if (game.alive && game.started){ game.paused = !game.paused; if (game.paused) showOverlay('Пауза'); else overlay.hidden = true; }
    e.preventDefault();
  }
});

// ---------- Boot ----------
setStatus('offline', 'offline');
render();
})();
