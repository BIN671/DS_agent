(function(){
'use strict';
const COLS = 10, ROWS = 20, BLOCK = 30;
const COLORS = [null,'#6fe3ff','#ffd166','#c792ea','#8affc1','#ff8fa3','#7aa2ff','#ffb86b'];
const SHAPES = {
  I: { c:1, m:[[0,0,0,0],[1,1,1,1],[0,0,0,0],[0,0,0,0]] },
  O: { c:2, m:[[2,2],[2,2]] },
  T: { c:3, m:[[0,3,0],[3,3,3],[0,0,0]] },
  S: { c:4, m:[[0,4,4],[4,4,0],[0,0,0]] },
  Z: { c:5, m:[[5,5,0],[0,5,5],[0,0,0]] },
  J: { c:6, m:[[6,0,0],[6,6,6],[0,0,0]] },
  L: { c:7, m:[[0,0,7],[7,7,7],[0,0,0]] }
};
const KEYS = Object.keys(SHAPES);

function randPiece(){ const k = KEYS[Math.floor(Math.random()*KEYS.length)]; const s = SHAPES[k]; return { type:k, matrix: s.m.map(function(r){return r.slice();}), color: s.c, x: Math.floor((COLS - s.m[0].length)/2), y: 0 }; }
function rotateSmall(m){ const R=m.length, C=m[0].length; const r=[]; for(let x=0;x<C;x++){ const col=[]; for(let y=R-1;y>=0;y--){ col.push(m[y][x]); } r.push(col); } return r; }

function Game(){
  this.board = Array.from({length:ROWS},function(){return Array(COLS).fill(0);});
  this.piece = null; this.next = randPiece();
  this.score = 0; this.lines = 0; this.level = 1;
  this.dropCounter = 0; this.dropInterval = 800; this.lastTime = 0;
  this.alive = true; this.paused = false; this.started = false;
}
Game.prototype.reset = function(){
  this.board = Array.from({length:ROWS},function(){return Array(COLS).fill(0);});
  this.piece = null; this.next = randPiece();
  this.score = 0; this.lines = 0; this.level = 1;
  this.dropCounter = 0; this.dropInterval = 800; this.lastTime = 0;
  this.alive = true; this.paused = false; this.started = true;
  this.spawn();
};
Game.prototype.spawn = function(){
  this.piece = this.next; this.next = randPiece();
  if (this.collide(this.board, this.piece)) { this.gameOver(); }
};
Game.prototype.collide = function(board, p, dx, dy){
  dx = dx || 0; dy = dy || 0;
  for (let y=0;y<p.matrix.length;y++){
    for (let x=0;x<p.matrix[y].length;x++){
      if (!p.matrix[y][x]) continue;
      const nx = p.x + x + dx, ny = p.y + y + dy;
      if (nx < 0 || nx >= COLS || ny >= ROWS) return true;
      if (ny >= 0 && board[ny][nx]) return true;
    }
  }
  return false;
};
Game.prototype.merge = function(){
  const p = this.piece;
  for (let y=0;y<p.matrix.length;y++) for (let x=0;x<p.matrix[y].length;x++){
    if (p.matrix[y][x]) {
      const ny = p.y+y, nx = p.x+x;
      if (ny>=0) this.board[ny][nx] = p.color;
    }
  }
};
Game.prototype.clearLines = function(){
  let cleared = 0;
  for (let y=ROWS-1;y>=0;y--){
    if (this.board[y].every(function(v){return v;})) {
      this.board.splice(y,1); this.board.unshift(Array(COLS).fill(0));
      cleared++; y++;
    }
  }
  if (cleared){
    const pts = [0,100,300,500,800][cleared] * this.level;
    this.score += pts; this.lines += cleared;
    const nl = Math.floor(this.lines/10)+1;
    if (nl !== this.level){ this.level = nl; this.dropInterval = Math.max(100, 800 - (this.level-1)*70); }
  }
};
Game.prototype.drop = function(){
  if (!this.alive || this.paused) return;
  if (!this.collide(this.board, this.piece, 0, 1)) { this.piece.y++; }
  else { this.merge(); this.clearLines(); this.spawn(); }
  this.dropCounter = 0;
};
Game.prototype.hardDrop = function(){
  if (!this.alive || this.paused) return;
  while (!this.collide(this.board, this.piece, 0, 1)) this.piece.y++;
  this.merge(); this.clearLines(); this.spawn(); this.dropCounter = 0;
};
Game.prototype.move = function(dx){
  if (!this.alive || this.paused) return;
  if (!this.collide(this.board, this.piece, dx, 0)) this.piece.x += dx;
};
Game.prototype.rotate = function(){
  if (!this.alive || this.paused) return;
  if (this.piece.type === 'O') return;
  const m = rotateSmall(this.piece.matrix);
  const test = { matrix: m, color: this.piece.color, x: this.piece.x, y: this.piece.y };
  const kicks = [0,-1,1,-2,2];
  for (const k of kicks){
    test.x = this.piece.x + k;
    if (!this.collide(this.board, test)) { this.piece.matrix = m; this.piece.x = test.x; return; }
  }
};
Game.prototype.gameOver = function(){ this.alive = false; this.started = false; if (this.onGameOver) this.onGameOver(); };

// ---------- DOM ----------
var $ = function(id){ return document.getElementById(id); };
var connStatus = $('conn-status');
var lobby = $('lobby'), gameSection = $('game');
var roomCard = $('room-card'), roomNameEl = $('room-name');
var playersList = $('players-list'), btnStart = $('btn-start');
var inName = $('in-name'), inRoom = $('in-room'), inServer = $('in-server');
var btnConnect = $('btn-connect'), btnSolo = $('btn-solo');
var canvasMain = $('canvas-main'), ctxMain = canvasMain.getContext('2d');
var canvasNext = $('canvas-next'), ctxNext = canvasNext.getContext('2d');
var scoreEl = $('score'), linesEl = $('lines'), levelEl = $('level');
var overlay = $('overlay'), overlayText = overlay.querySelector('.overlay-text'), btnRestart = $('btn-restart');
var opponentsList = $('opponents-list');
var chatLog = $('chat-log'), chatForm = $('chat-form'), chatInput = $('chat-input');

var game = new Game();
var ws = null;
var myId = null;
var myName = 'Player';
var roomId = 'lobby';
var isHost = false;
var roomStarted = false;
var solo = false;
var opponents = {};
var running = false;
var lastTs = 0;
var rafId = null;
var netAccum = 0;

function setStatus(text, cls){ connStatus.textContent = text; connStatus.className = 'status ' + cls; }

function defaultServerUrl(){
  var p = location.protocol === 'https:' ? 'wss:' : 'ws:';
  return p + '//' + location.host;
}
if (!inServer.value) inServer.value = location.host ? defaultServerUrl() : 'ws://localhost:3000';
if (location.host) {
  var ls = localStorage.getItem('tetris-name');
  if (ls) inName.value = ls;
}

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
    var ghostY = piece.y;
    // ghost: find landing
    var test = { matrix: piece.matrix, x: piece.x, y: piece.y };
    while (true){
      var canDown = true;
      for (let yy=0; yy<test.matrix.length; yy++) for (let xx=0; xx<test.matrix[yy].length; xx++){
        if (!test.matrix[yy][xx]) continue;
        var ny = test.y + yy + 1, nx = test.x + xx;
        if (ny >= ROWS) { canDown = false; break; }
        if (ny >= 0 && board[ny] && board[ny][nx]) { canDown = false; break; }
      }
      if (!canDown) break;
      test.y++;
    }
    ghostY = test.y;
    ctx.globalAlpha = 0.22;
    for (let y=0;y<piece.matrix.length;y++) for (let x=0;x<piece.matrix[y].length;x++){
      if (piece.matrix[y][x]){
        var gy = ghostY + y; if (gy < 0) continue;
        drawCell(ctx, piece.x + x, gy, COLORS[piece.matrix[y][x]] || '#888', blockSize);
      }
    }
    ctx.globalAlpha = 1;
    for (let y=0;y<piece.matrix.length;y++) for (let x=0;x<piece.matrix[y].length;x++){
      if (piece.matrix[y][x]){
        var py = piece.y + y; if (py < 0) continue;
        drawCell(ctx, piece.x + x, py, COLORS[piece.matrix[y][x]] || '#888', blockSize);
      }
    }
  }
}

function drawNext(){
  ctxNext.fillStyle = '#05080f';
  ctxNext.fillRect(0,0,canvasNext.width,canvasNext.height);
  if (!game.next) return;
  var m = game.next.matrix;
  var size = 24;
  var offX = (canvasNext.width - m[0].length*size)/2;
  var offY = (canvasNext.height - m.length*size)/2;
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
  var ids = Object.keys(opponents);
  if (ids.length === 0){
    opponentsList.innerHTML = '<p class="hint">Нет соперников — ждём игроков…</p>';
    return;
  }
  // rebuild if count changed
  if (opponentsList.children.length !== ids.length || opponentsList.dataset.signature !== ids.join(',')){
    opponentsList.innerHTML = '';
    opponentsList.dataset.signature = ids.join(',');
    ids.forEach(function(id){
      var op = opponents[id];
      var div = document.createElement('div');
      div.className = 'opponent';
      div.id = 'opp-' + id;
      var title = document.createElement('div');
      title.textContent = op.name || ('#' + id);
      var c = document.createElement('canvas');
      c.width = 100; c.height = 200;
      var sc = document.createElement('div');
      sc.className = 'op-score';
      sc.textContent = '0';
      div.appendChild(title); div.appendChild(c); div.appendChild(sc);
      opponentsList.appendChild(div);
    });
  }
  ids.forEach(function(id){
    var op = opponents[id];
    var div = document.getElementById('opp-' + id);
    if (!div) return;
    var c = div.querySelector('canvas');
    var ctx = c.getContext('2d');
    ctx.fillStyle = '#05080f';
    ctx.fillRect(0,0,c.width,c.height);
    if (op.board){
      var bs = c.width / COLS;
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
  var dt = ts - lastTs;
  lastTs = ts;

  if (game.started && game.alive && !game.paused){
    game.dropCounter += dt;
    if (game.dropCounter > game.dropInterval){
      game.drop();
    }
  }

  render();

  // send state ~5/s
  netAccum += dt;
  if (netAccum > 200 && ws && ws.readyState === 1 && game.started){
    netAccum = 0;
    sendState();
  }

  rafId = requestAnimationFrame(loop);
}

function startLoop(){
  if (running) return;
  running = true; lastTs = 0;
  rafId = requestAnimationFrame(loop);
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
    if (running && !solo){
      game.paused = true;
      showOverlay('Соединение потеряно');
    }
  };
  ws.onerror = function(){ setStatus('offline', 'offline'); };
  ws.onmessage = function(ev){
    var m; try { m = JSON.parse(ev.data); } catch(e){ return; }
    handleMessage(m);
  };
}

function handleMessage(m){
  if (m.type === 'welcome'){
    myId = m.id;
    if (m.name) myName = m.name;
  } else if (m.type === 'room'){
    roomStarted = m.started;
    isHost = (m.hostId === myId);
    roomNameEl.textContent = m.roomId;
    playersList.innerHTML = '';
    m.players.forEach(function(p){
      var li = document.createElement('li');
      var who = p.name + (p.id === m.hostId ? ' ★' : '');
      if (p.id === myId) who += ' (you)';
      li.innerHTML = '<span>' + escapeHtml(who) + '</span><span>' + (p.alive ? 'alive' : 'dead') + '</span>';
      playersList.appendChild(li);
    });
    btnStart.disabled = !(isHost && m.players.length >= 1);
    roomCard.hidden = false;
    if (!m.started && roomStarted){
      // was running, now stopped (winner announced)
      game.started = false;
    }
    roomStarted = m.started;
    if (m.started && !game.started && !solo){
      // start signal came
    }
  } else if (m.type === 'start'){
    startGame(false);
  } else if (m.type === 'state'){
    if (m.id === myId) return;
    var op = opponents[m.id] || {};
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
    var line = document.createElement('div');
    if (m.system){
      line.className = 'system';
      line.textContent = m.text;
    } else {
      var from = document.createElement('span');
      from.className = 'from'; from.textContent = (m.from || '?') + ': ';
      var txt = document.createElement('span'); txt.textContent = m.text;
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
    // guest waits for host
    overlayText.textContent = 'Ожидание хоста…';
    overlay.hidden = false;
  }
});

// ---------- Lobby handlers ----------
btnConnect.addEventListener('click', function(){
  var name = inName.value.trim() || 'Player';
  localStorage.setItem('tetris-name', name);
  var room = inRoom.value.trim() || 'lobby';
  var url = inServer.value.trim() || defaultServerUrl();
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
  var t = chatInput.value.trim();
  if (!t) return;
  chatInput.value = '';
  if (ws && ws.readyState === 1) ws.send(JSON.stringify({ type: 'chat', text: t }));
});

// ---------- Keyboard ----------
window.addEventListener('keydown', function(e){
  if (gameSection.hidden) return;
  if (e.target && (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA')) return;
  var k = e.key;
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
