import { createReadStream, existsSync, statSync } from "node:fs";
import { createServer } from "node:http";
import { extname, join, normalize } from "node:path";

const root = new URL("../dist/", import.meta.url).pathname;
const types = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
  ".wasm": "application/wasm",
  ".xml": "application/xml; charset=utf-8",
};

function resolve(requestPath) {
  const decoded = decodeURIComponent(requestPath.split("?", 1)[0]);
  const relative = normalize(decoded).replace(/^(\.\.(\/|\\|$))+/, "").replace(/^\//, "");
  const direct = join(root, relative);
  if (existsSync(direct) && statSync(direct).isFile()) return direct;
  const index = join(direct, "index.html");
  if (existsSync(index)) return index;
  return join(root, "404.html");
}

createServer((request, response) => {
  const file = resolve(request.url ?? "/");
  const notFound = file.endsWith("404.html") && !request.url?.startsWith("/404");
  response.writeHead(notFound ? 404 : 200, {
    "Content-Type": types[extname(file)] ?? "application/octet-stream",
    "Cache-Control": "no-store",
  });
  createReadStream(file).pipe(response);
}).listen(4321, "127.0.0.1", () => {
  process.stdout.write("Serving dist at http://127.0.0.1:4321\n");
});
