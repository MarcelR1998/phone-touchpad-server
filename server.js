const express = require("express");
const http = require("http");
const { Server } = require("socket.io");
const { spawn } = require("child_process");
const path = require("path");
const os = require("os");

const app = express();
const server = http.createServer(app);
const io = new Server(server);

// Serve static files
app.use(express.static(path.join(__dirname, "public")));

// Spawn the Python mouse controller
const mouse = spawn("python3", [path.join(__dirname, "mouse.py")], {
  stdio: ["pipe", "pipe", "pipe"],
});

let screenInfo = { width: 1920, height: 1080 };

mouse.stdout.on("data", (data) => {
  for (const line of data.toString().split("\n").filter(Boolean)) {
    try {
      const msg = JSON.parse(line);
      if (msg.type === "screen") {
        screenInfo = { width: msg.width, height: msg.height };
        console.log(`Screen: ${screenInfo.width}x${screenInfo.height}`);
      }
    } catch {}
  }
});

mouse.stderr.on("data", (data) => {
  console.error("mouse.py:", data.toString().trim());
});

mouse.on("close", (code) => {
  console.error(`mouse.py exited with code ${code}`);
  process.exit(1);
});

function sendMouse(cmd) {
  mouse.stdin.write(JSON.stringify(cmd) + "\n");
}

io.on("connection", (socket) => {
  console.log("Client connected");

  socket.emit("screen", screenInfo);

  socket.on("move", (data) => {
    sendMouse({ action: "move", dx: data.dx, dy: data.dy });
  });

  socket.on("click", (data) => {
    sendMouse({ action: "click", button: data?.button || 1 });
  });

  socket.on("scroll", (data) => {
    sendMouse({ action: "scroll", direction: data.direction });
  });

  socket.on("down", (data) => {
    sendMouse({ action: "down", button: data?.button || 1 });
  });

  socket.on("up", (data) => {
    sendMouse({ action: "up", button: data?.button || 1 });
  });

  socket.on("key", (data) => {
    sendMouse({ action: "key", key: data.key });
  });

  socket.on("modifier_down", (data) => {
    sendMouse({ action: "modifier_down", key: data.key });
  });

  socket.on("modifier_up", (data) => {
    sendMouse({ action: "modifier_up", key: data.key });
  });

  socket.on("disconnect", () => {
    console.log("Client disconnected");
  });
});

const PORT = 3000;
server.listen(PORT, "0.0.0.0", () => {
  const addresses = [];
  const nets = os.networkInterfaces();
  for (const name of Object.keys(nets)) {
    for (const net of nets[name]) {
      if (net.family === "IPv4" && !net.internal) {
        addresses.push(net.address);
      }
    }
  }
  console.log(`\nPhone touchpad server running on port ${PORT}`);
  console.log(`\nOpen on your phone:`);
  for (const addr of addresses) {
    console.log(`  http://${addr}:${PORT}`);
  }
  console.log(`\nLocal: http://localhost:${PORT}\n`);
});
